#!/usr/bin/env python3
"""Generate a complete faceless episode: script -> poses -> narration -> MP4.

Targets the format measured from reference videos rather than invented
defaults. Only two values agreed across the references we compared, so only
those are fixed here:

    16:9        both references
    155 wpm     both references, matching exactly

Runtime, shot length and cuts-per-minute varied 47-55% between references, so
they are derived from the actual narration rather than pinned to a constant.

Two things make this survivable at volume:

RESUMABLE — every generated image and audio clip is cached by a hash of the
prompt that produced it. A failed or interrupted run re-uses everything it
already paid for, and editing one exercise regenerates only that exercise.

MODEL FALLBACK — image and TTS models are tried in order. gemini-3-pro-image
returned persistent 503s during development while a cheaper model produced
better output, so treating any single model as required would make scheduled
publishing fragile.

Frames are NOT rendered per-frame: one still per shot, animated by ffmpeg's
zoompan. Rendering 30fps PNGs for a 15-minute episode would be ~27k files and
tens of gigabytes for the same result.

Usage:
    export GEMINI_API_KEY=...
    ./make_episode.py episode.json --out-dir build/ep01
    ./make_episode.py episode.json --out-dir build/ep01 --dry-run
"""

import argparse
import base64
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
IMAGE_MODELS = ["gemini-3.1-flash-image", "gemini-3-pro-image", "gemini-2.5-flash-image"]
TTS_MODELS = ["gemini-2.5-flash-preview-tts", "gemini-3.1-flash-tts-preview"]

W, H, FPS = 1920, 1080, 30          # 16:9 — format constant
WPM = 155                            # format constant, both references

# Style is fixed so every pose renders the same character. The anatomical
# detail lives per-exercise: naming the exercise produces wrong limbs, naming
# joint angles and ground-contact points produces correct ones.
STYLE = ("Simple 3D-rendered cartoon figure, smooth matte {colour} plastic, rounded limbs, "
         "two small dark dot eyes, no other facial features. Plain flat {bg} background, "
         "soft studio lighting, full body visible and not cropped. ")
ANATOMY_GUARD = (" Exactly two arms and two legs, all four limbs clearly separate and never "
                 "merged or missing. Anatomically correct, natural joint angles.")


def log(m):
    print(m, file=sys.stderr, flush=True)


def cache_path(cache, kind, key, ext):
    h = hashlib.sha256(key.encode()).hexdigest()[:16]
    return cache / f"{kind}_{h}.{ext}"


def api_post(model, payload, key, timeout=300):
    req = urllib.request.Request(
        f"{BASE}/{model}:generateContent",
        data=json.dumps(payload).encode(),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def first_inline(resp):
    for p in resp.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        blob = p.get("inlineData") or p.get("inline_data")
        if blob:
            return base64.b64decode(blob["data"])
    return None


def generate(kind, prompt, key, cache, voice="Kore"):
    """Cached, fallback-chained call. Returns bytes, or None if all models fail."""
    ext = "png" if kind == "image" else "pcm"
    path = cache_path(cache, kind, prompt + (voice if kind == "tts" else ""), ext)
    if path.exists() and path.stat().st_size > 0:
        return path.read_bytes(), path

    models = IMAGE_MODELS if kind == "image" else TTS_MODELS
    for model in models:
        for attempt in range(2):
            if kind == "image":
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
            else:
                payload = {"contents": [{"parts": [{"text": prompt}]}],
                           "generationConfig": {
                               "responseModalities": ["AUDIO"],
                               "speechConfig": {"voiceConfig": {
                                   "prebuiltVoiceConfig": {"voiceName": voice}}}}}
            try:
                data = first_inline(api_post(model, payload, key))
            except urllib.error.HTTPError as e:
                log(f"    {model} HTTP {e.code}"); time.sleep(6); continue
            except Exception as e:
                log(f"    {model} {type(e).__name__}"); time.sleep(6); continue
            if data:
                path.write_bytes(data)
                return data, path
    return None, None


def pcm_to_wav(pcm_bytes, out):
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
        w.writeframes(pcm_bytes)
    return len(pcm_bytes) / 2 / 24000


def card(text_lines, out, palette, size=(W, H), font_path=None):
    """Render a text card. Kept separate from pose stills so typography is ours."""
    from PIL import Image, ImageDraw, ImageFont
    font_path = font_path or "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    img = Image.new("RGB", size, palette["bg"])
    d = ImageDraw.Draw(img)
    sizes = [int(size[1] * 0.11), int(size[1] * 0.055)]
    total = sum(sizes) + 30
    y = (size[1] - total) // 2
    for i, line in enumerate(text_lines[:2]):
        f = ImageFont.truetype(font_path, sizes[min(i, 1)])
        w = d.textbbox((0, 0), line, font=f)[2]
        d.text(((size[0] - w) // 2, y), line, font=f,
               fill=palette["accent"] if i == 0 else palette["ink"])
        y += sizes[min(i, 1)] + 30
    img.save(out)


def compose_pose(pose_png, out, palette, label, cue):
    """Place a pose render on the episode's background with its caption."""
    from PIL import Image, ImageDraw, ImageFont
    fp = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    canvas = Image.new("RGB", (W, H), palette["bg"])
    src = Image.open(pose_png).convert("RGB")
    scale = min((W * 0.62) / src.width, (H * 0.78) / src.height)
    src = src.resize((int(src.width * scale), int(src.height * scale)), Image.LANCZOS)
    canvas.paste(src, ((W - src.width) // 2, int(H * 0.13)))
    d = ImageDraw.Draw(canvas)
    fb = ImageFont.truetype(fp, 78)
    fs = ImageFont.truetype(fp, 44)
    wb = d.textbbox((0, 0), label, font=fb)[2]
    d.text(((W - wb) // 2, 46), label, font=fb, fill=palette["accent"])
    ws = d.textbbox((0, 0), cue, font=fs)[2]
    d.text(((W - ws) // 2, H - 108), cue, font=fs, fill=palette["ink"])
    canvas.save(out)


def shot_clip(ffmpeg, still, seconds, out, zoom_in=True):
    """One still -> one clip with a slow push, so static art still reads as motion."""
    frames = max(int(seconds * FPS), 2)
    z = ("min(zoom+0.0006,1.12)" if zoom_in else "if(lte(zoom,1.0),1.12,max(zoom-0.0006,1.0))")
    subprocess.run([
        ffmpeg, "-y", "-loop", "1", "-i", str(still), "-t", f"{seconds:.3f}",
        "-filter_complex",
        f"zoompan=z='{z}':d={frames}:s={W}x{H}:fps={FPS},format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(out)],
        capture_output=True, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--dry-run", action="store_true", help="plan and cost only")
    args = ap.parse_args()

    spec = json.loads(pathlib.Path(args.episode).read_text())
    pal = {k: tuple(v) for k, v in spec["palette"].items()}
    out = pathlib.Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    cache = out / "cache"; cache.mkdir(exist_ok=True)
    work = out / "work"; work.mkdir(exist_ok=True)

    # Flatten the episode into narration blocks and their visuals.
    blocks = [("hook", spec["hook"], None)]
    for seg in spec["segments"]:
        for ex in seg["exercises"]:
            blocks.append((seg["label"], ex["say"], ex))
    blocks.append(("outro", spec["outro"], None))

    words = sum(len(b[1].split()) for b in blocks)
    log(f"episode : {spec['title']}")
    log(f"blocks  : {len(blocks)}   words: {words}   est runtime: {words/WPM*60:.0f}s at {WPM} wpm")
    if args.dry_run:
        imgs = sum(1 for b in blocks if b[2])
        log(f"would generate {imgs} pose images + {len(blocks)} narration clips")
        return

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("no GEMINI_API_KEY")
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()

    clips, wavs = [], []
    for i, (label, say, ex) in enumerate(blocks):
        log(f"[{i+1}/{len(blocks)}] {label}")

        pcm, _ = generate("tts", say, key, cache, spec.get("voice", "Kore"))
        if not pcm:
            log("   narration failed — skipping block"); continue
        wav = work / f"a{i:03d}.wav"
        dur = pcm_to_wav(pcm, wav)
        wavs.append(wav)

        still = work / f"s{i:03d}.png"
        if ex:
            prompt = (STYLE.format(colour=spec["character"]["colour"],
                                   bg=spec["character"]["bg"])
                      + ex["pose"] + ANATOMY_GUARD)
            png, path = generate("image", prompt, key, cache)
            if not png:
                log("   pose failed — falling back to text card")
                card([ex["name"].upper(), ex["cue"]], still, pal)
            else:
                compose_pose(path, still, pal, ex["name"].upper(), ex["cue"])
        else:
            card(spec["cards"][label], still, pal)

        clip = work / f"v{i:03d}.mp4"
        shot_clip(ff, still, dur, clip, zoom_in=(i % 2 == 0))
        clips.append(clip)
        log(f"   {dur:.1f}s")

    if not clips:
        raise SystemExit("no clips produced")

    (work / "v.txt").write_text("".join(f"file '{c.name}'\n" for c in clips))
    (work / "a.txt").write_text("".join(f"file '{w.name}'\n" for w in wavs))
    subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(work/"v.txt"),
                    "-c", "copy", str(work/"video.mp4")], capture_output=True, check=True)
    subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(work/"a.txt"),
                    "-c", "copy", str(work/"audio.wav")], capture_output=True, check=True)
    final = out / "episode.mp4"
    subprocess.run([ff, "-y", "-i", str(work/"video.mp4"), "-i", str(work/"audio.wav"),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                    "-movflags", "+faststart", str(final)], capture_output=True, check=True)

    size_mb = final.stat().st_size / 1e6
    log(f"\n{final}  {size_mb:.1f} MB  {len(clips)} shots")
    log(f"cuts/min: {len(clips)/(sum(1 for _ in wavs) and 1) if False else ''}")


if __name__ == "__main__":
    main()
