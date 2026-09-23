#!/usr/bin/env python3
"""Find what a creator's audience keeps asking for that the creator never answered.

The manual version of this job is a week of watching videos and reading
comments, and the shortcut — guessing a product from three videos — is how you
build something nobody asked for. Neither is necessary: comments are a JSON
endpoint.

Two stages, deliberately separate:

  HARVEST  YouTube Data API v3. Recent videos, then top-level comments per
           video, paginated. Pure retrieval, no interpretation. Cached to disk
           so re-clustering never re-pays for the fetch.

  CLUSTER  Gemini reads the harvested comments and groups them into demand
           clusters, each with a count, verbatim quotes, and whether an
           existing video title already covers it.

The split matters. The harvest is checkable — the raw comments sit in a file
you can read. Only the clustering is a model's judgment, and it cites the
comments it clustered, so a wrong cluster is visible rather than invisible.

Quota: ~1 unit per API call, 10,000 units/day on a free key. A 30-video
harvest with 5 comment pages each is ~150 units. Quota is not the constraint.

Usage:
    export YOUTUBE_API_KEY=...        # console.cloud.google.com, YouTube Data API v3
    export GEMINI_API_KEY=...         # aistudio.google.com/apikey (may be the same key)

    ./demand_harvest.py @channelhandle --out-dir demand/
    ./demand_harvest.py @handle --videos 40 --pages 8 --out-dir demand/
    ./demand_harvest.py @handle --out-dir demand/ --harvest-only
    ./demand_harvest.py --from-cache demand/handle.raw.json -o report.md

Stdlib only.
"""

import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

YT = "https://youtube.googleapis.com/youtube/v3"
GEMINI = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")

# Comments are graded, not just filtered. A first pass on a consumer channel
# showed why: a bare "?" or a bare "why" catches rhetoric ("Who wants a
# stylus?", "So we go back to horizontal videos? lol") at roughly 8 pieces of
# noise per real question. Tightening the regex until only real demand survives
# also drops real demand, so instead both tiers are kept and labelled, and the
# clustering pass is told which tier may found a cluster.
#
# STRONG: someone asking for help with their own situation, or asking the
# creator to make something. This is unmet demand, and only these found a
# cluster.
STRONG_RE = re.compile(
    r"\bhow (do|can|would|should|d[oi]) (i|we|you)\b"
    # "can't" only means demand when a task follows. Live data matched "I cannot
    # unsee it", "phones I can't afford", "I can't wait" on a looser version of
    # this clause — all feeling, no task.
    r"|\b(i|we) (can'?t|cannot|couldn'?t) (figure out|work out|get|find|seem to|manage to)\b"
    r"|\b(i|we) (don'?t|didn'?t) know (how|where|what|which)\b"
    r"|\b(i|we) have no idea (how|where|what|which)\b"
    r"|\bi'?m (stuck|lost|confused|struggling|new to)\b"
    r"|\b(stuck|struggling) (on|with|at)\b"
    r"|\bcan (you|u) (please )?(make|do|cover|explain|show|teach)\b"
    r"|\b(could|would) you (please )?(make|do|cover|explain|show)\b"
    r"|\bplease (make|do|cover|explain|show|teach)\b"
    r"|\b(video|tutorial|guide|series) (on|about|for) \w+"
    r"|\bany (tips|advice|recommendations?) (on|for|about)\b"
    r"|\b(is|are) there (a|an|any) \w+"
    r"|\bwhat (do|should|would) (i|you|we) (do|use|charge|pick|choose)\b"
    r"|\bhow much (do|should|would) (i|you)\b"
    r"|\bwish (there was|someone|you would|you'?d)\b"
    r"|\banyone know (how|where|if|what)\b"
    r"|\bdoes anyone (know|have)\b",
    re.I,
)

# WEAK: question-shaped, but might be rhetoric or commentary. Corroborates a
# cluster the strong tier already established; never founds one.
WEAK_RE = re.compile(
    r"\?|\bhow to\b|\bwhat about\b|\bwhy\b|\bconfus|\bhelp\b|\bstruggl",
    re.I,
)


def grade(text):
    """'strong' | 'weak' | None — None is dropped before it costs a token."""
    if len(text) < 15:
        return None
    if STRONG_RE.search(text):
        return "strong"
    if WEAK_RE.search(text):
        return "weak"
    return None


def get(url, timeout=60):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:700]
        raise SystemExit(
            f"youtube HTTP {exc.code} on {url.split('?')[0]}\n{detail}\n\n"
            "If this says the API is not enabled: the key is valid but YouTube Data\n"
            "API v3 is off for its project. Enable it once in the Google Cloud console\n"
            "(APIs & Services -> Library -> YouTube Data API v3 -> Enable)."
        )
    except urllib.error.URLError as exc:
        raise SystemExit(f"youtube unreachable: {exc.reason}")


def yt(path, key, **params):
    params["key"] = key
    return get(f"{YT}/{path}?{urllib.parse.urlencode(params)}")


def resolve_channel(handle, key):
    """Handle, @handle, channel URL or raw channel ID -> (channel_id, title, uploads)."""
    handle = handle.strip()
    m = re.search(r"youtube\.com/(?:@([\w.\-]+)|channel/(UC[\w\-]{20,})|c/([\w.\-]+))", handle)
    if m:
        handle = m.group(1) or m.group(2) or m.group(3)
    handle = handle.lstrip("@")

    if re.fullmatch(r"UC[\w\-]{20,}", handle):
        data = yt("channels", key, part="snippet,contentDetails,statistics", id=handle)
    else:
        data = yt("channels", key, part="snippet,contentDetails,statistics", forHandle=handle)

    items = data.get("items") or []
    if not items:
        raise SystemExit(f"no channel found for '{handle}'")
    c = items[0]
    return {
        "channel_id": c["id"],
        "title": c["snippet"]["title"],
        "subscribers": int(c.get("statistics", {}).get("subscriberCount", 0) or 0),
        "hidden_subs": c.get("statistics", {}).get("hiddenSubscriberCount", False),
        "uploads": c["contentDetails"]["relatedPlaylists"]["uploads"],
        "description": c["snippet"].get("description", ""),
    }


def recent_videos(uploads, key, limit):
    out, token = [], None
    while len(out) < limit:
        page = yt("playlistItems", key, part="snippet,contentDetails",
                  playlistId=uploads, maxResults=min(50, limit - len(out)),
                  **({"pageToken": token} if token else {}))
        for it in page.get("items", []):
            out.append({
                "video_id": it["contentDetails"]["videoId"],
                "title": it["snippet"]["title"],
                "published": it["contentDetails"].get("videoPublishedAt", ""),
            })
        token = page.get("nextPageToken")
        if not token:
            break
    return out[:limit]


def video_stats(video_ids, key):
    """View counts, so a cluster can be weighted by the reach of its videos."""
    stats = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        # snippet rides along on the same 1-unit call. It is here because a
        # creator's storefront usually lives in the video description, not the
        # channel About page — a 149k channel with a clean bio turned out to be
        # selling five products from links under every upload.
        data = yt("videos", key, part="statistics,snippet", id=",".join(chunk))
        for it in data.get("items", []):
            s = it.get("statistics", {})
            stats[it["id"]] = {
                "views": int(s.get("viewCount", 0) or 0),
                "comments": int(s.get("commentCount", 0) or 0),
                "description": it.get("snippet", {}).get("description", ""),
            }
    return stats


def comments(video_id, key, pages):
    """Top-level comments, relevance-ordered. Disabled comments are not an error."""
    out, token = [], None
    for _ in range(pages):
        try:
            page = yt("commentThreads", key, part="snippet", videoId=video_id,
                      maxResults=100, order="relevance", textFormat="plainText",
                      **({"pageToken": token} if token else {}))
        except SystemExit as exc:
            if "commentsDisabled" in str(exc) or "403" in str(exc):
                return out, "comments unavailable"
            raise
        for it in page.get("items", []):
            s = it["snippet"]["topLevelComment"]["snippet"]
            text = s.get("textDisplay", "").strip()
            out.append({
                "text": text,
                "likes": int(s.get("likeCount", 0) or 0),
                "replies": int(it["snippet"].get("totalReplyCount", 0) or 0),
                "signal": grade(text),
            })
        token = page.get("nextPageToken")
        if not token:
            break
    return out, None


def harvest(handle, key, n_videos, pages):
    ch = resolve_channel(handle, key)
    print(f"channel: {ch['title']}  ({ch['subscribers']:,} subs)", file=sys.stderr)

    vids = recent_videos(ch["uploads"], key, n_videos)
    print(f"videos: {len(vids)}", file=sys.stderr)
    stats = video_stats([v["video_id"] for v in vids], key)

    total = strong = weak = 0
    for v in vids:
        v.update(stats.get(v["video_id"], {}))
        cs, note = comments(v["video_id"], key, pages)
        if note:
            v["note"] = note
        v["comments"] = [c for c in cs if c["signal"]]
        s = sum(1 for c in v["comments"] if c["signal"] == "strong")
        total += len(cs)
        strong += s
        weak += len(v["comments"]) - s
        print(f"  {v['video_id']}  {len(cs):>4} fetched  {s:>3} strong  "
              f"{len(v['comments']) - s:>3} weak  {v['title'][:48]}", file=sys.stderr)

    ratio = (strong / total * 100) if total else 0
    print(f"\n{total:,} fetched · {strong:,} strong · {weak:,} weak "
          f"({ratio:.1f}% strong)", file=sys.stderr)
    if ratio < 3:
        print("  low strong-signal density: this audience does not ask this creator for help.\n"
              "  That is itself a finding — a creator whose comments are reactions rather than\n"
              "  questions is a weak candidate regardless of size.", file=sys.stderr)
    return {"channel": ch, "videos": vids,
            "counts": {"fetched": total, "strong": strong, "weak": weak, "kept": strong + weak}}


CLUSTER_PROMPT = """You are given every question-shaped comment from a YouTube creator's
recent videos, plus the titles of those videos.

Find the DEMAND CLUSTERS: topics the audience repeatedly asks about. Then
establish, from the video titles alone, whether the creator has already covered
each one.

Output markdown, clusters ordered by strength (count first, then total likes).

For each cluster:

### <the question, phrased as the audience phrases it>
- **asked:** <n> times across <m> videos | **likes on those comments:** <total>
- **already covered by a video?** YES (name the title) / NO / PARTIAL (name it)
- **verbatim:** 3-5 real comments, quoted exactly, no cleanup
- **what a buyer wants:** the concrete deliverable implied - a checklist, a
  script, a template, a walkthrough, a decision tree. Be specific.

Rules:
- Comments are tagged STRONG or WEAK. A STRONG comment is someone asking for
  help with their own situation, or asking the creator to make something. Only
  STRONG comments may found a cluster. WEAK comments are question-shaped but
  often rhetoric or commentary ("Who wants a stylus?"); use them only to
  corroborate a cluster that at least 3 STRONG comments already established,
  and never count a WEAK comment toward the minimum.
- A cluster needs at least 3 distinct STRONG comments. Fewer is noise; say so
  and drop it.
- Quote exactly. Never paraphrase into a quote, never invent a comment.
- Do not merge distinct problems to make a cluster look bigger.
- Judge coverage only from the titles given. If a title is ambiguous, say
  PARTIAL and name it - do not assume.
- End with **THE PICK**: the single cluster with the most demand and no
  coverage, and one sentence on why it beats the runner-up.
- If no cluster clears 3 comments, say so plainly and recommend a different
  creator. Do not manufacture a finding.
"""


def cluster(raw, key, model):
    lines = [f"CREATOR: {raw['channel']['title']} ({raw['channel']['subscribers']:,} subscribers)", "",
             "VIDEO TITLES (for the coverage check):"]
    for v in raw["videos"]:
        lines.append(f"- [{v['video_id']}] {v['title']}  ({v.get('views', 0):,} views)")
    lines += ["", "COMMENTS:"]
    for tier in ("strong", "weak"):
        lines.append(f"\n-- {tier.upper()} SIGNAL --")
        for v in raw["videos"]:
            for c in v["comments"]:
                if c.get("signal") == tier:
                    lines.append(f"[{v['video_id']} | {c['likes']} likes] {c['text']}")

    body = {"contents": [{"parts": [{"text": CLUSTER_PROMPT + "\n\n---\n\n" + "\n".join(lines)}]}]}
    req = urllib.request.Request(
        f"{GEMINI}/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            payload = json.loads(r.read())
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"gemini HTTP {exc.code}\n{exc.read().decode(errors='replace')[:700]}")

    cand = (payload.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
    used = payload.get("usageMetadata", {}).get("promptTokenCount", 0)
    return text, used


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("handle", nargs="?", help="@handle, channel URL, or channel ID")
    ap.add_argument("--from-cache", help="skip the harvest, cluster this .raw.json")
    ap.add_argument("--videos", type=int, default=25, help="recent videos to read (default 25)")
    ap.add_argument("--pages", type=int, default=4, help="comment pages per video, 100 each (default 4)")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("-o", "--out", help="report path (default <out-dir>/<handle>.demand.md)")
    ap.add_argument("--harvest-only", action="store_true", help="fetch and cache, no clustering")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.from_cache:
        raw = json.loads(pathlib.Path(args.from_cache).read_text())
        slug = re.sub(r"\W+", "-", raw["channel"]["title"].lower()).strip("-")
    else:
        if not args.handle:
            ap.error("give a handle, or --from-cache a previous harvest")
        yt_key = os.environ.get("YOUTUBE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not yt_key:
            raise SystemExit("set YOUTUBE_API_KEY (or GEMINI_API_KEY if one key serves both)")
        raw = harvest(args.handle, yt_key, args.videos, args.pages)
        slug = re.sub(r"\W+", "-", raw["channel"]["title"].lower()).strip("-")
        cache = out_dir / f"{slug}.raw.json"
        cache.write_text(json.dumps(raw, indent=2, ensure_ascii=False))
        print(f"raw comments -> {cache}", file=sys.stderr)

    if args.harvest_only:
        return

    kept = raw.get("counts", {}).get("kept", 0)
    if kept < 20:
        print(f"warning: only {kept} demand-shaped comments — thin evidence, widen with"
              " --videos/--pages before trusting any cluster", file=sys.stderr)

    g_key = os.environ.get("GEMINI_API_KEY")
    if not g_key:
        raise SystemExit("set GEMINI_API_KEY to cluster (the harvest is cached, so re-run is free)")

    print(f"clustering with {args.model}...", file=sys.stderr)
    report, used = cluster(raw, g_key, args.model)

    header = (f"# Demand report — {raw['channel']['title']}\n\n"
              f"`{raw['channel']['subscribers']:,}` subscribers · "
              f"{len(raw['videos'])} videos read · "
              f"{raw['counts']['fetched']:,} comments fetched · "
              f"{raw['counts'].get('strong',0):,} strong · "
              f"model `{args.model}`\n\n"
              f"Clusters below are a model's grouping of the raw comments in "
              f"`{slug}.raw.json`. Quotes are checkable against that file.\n\n---\n\n")

    path = pathlib.Path(args.out) if args.out else out_dir / f"{slug}.demand.md"
    path.write_text(header + report)
    print(f"report -> {path}  ({used:,} prompt tokens)", file=sys.stderr)


if __name__ == "__main__":
    main()
