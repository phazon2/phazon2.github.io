#!/usr/bin/env python3
"""Put format specs side by side to separate the FORMAT from one channel's quirks.

A single reference cannot tell you which of its choices are load-bearing. A
15-second mean shot might be the genre's convention or that one editor's
habit, and building a template on the wrong one bakes in a copy of a channel
instead of a reusable format.

Rule of thumb applied here: values that agree across references are the
format and should be fixed in the template; values that scatter are stylistic
and should be parameters. With only two references, agreement is suggestive,
not settled — the output labels it that way rather than overstating.

Usage:  ./compare_specs.py corpus/format-refs/*.md
"""

import argparse
import pathlib
import re
import statistics

# label -> regex capturing one numeric value from the spec's prose
FIELDS = [
    ("runtime_sec",     r"Total Runtime:\*{0,2}\s*\**\s*(?:\d+:)?(\d+):(\d+)"),
    ("shots",           r"Distinct Shots:\*{0,2}\s*\**\s*~?(\d+)"),
    ("mean_shot_sec",   r"Mean Shot Duration:\*{0,2}\s*\**\s*~?([\d.]+)"),
    ("cuts_per_min",    r"Cuts per Minute:\*{0,2}\s*\**\s*~?([\d.]+)"),
    ("first_hold_sec",  r"First Shot Hold:\*{0,2}\s*\**\s*~?([\d.]+)"),
    ("wpm",             r"Pace:\*{0,2}\s*\**\s*~?(\d+)\s*words"),
    ("time_to_content", r"Time to First Content:\*{0,2}\s*\**\s*~?(\d+)"),
]
ASPECT = re.compile(r"Aspect Ratio:\*{0,2}\s*\**\s*([0-9]+\s*:\s*[0-9]+)", re.I)
HEX = re.compile(r"#([0-9A-Fa-f]{6})")
NARRATION = re.compile(r"Narration:\*{0,2}\s*\**\s*([^\n.]{0,60})", re.I)


def parse(path):
    t = path.read_text()
    out = {"file": path.name}
    for name, pat in FIELDS:
        m = re.search(pat, t, re.I)
        if not m:
            continue
        if name == "runtime_sec" and m.lastindex == 2:
            out[name] = int(m.group(1)) * 60 + int(m.group(2))
        else:
            out[name] = float(m.group(m.lastindex or 1))
    a = ASPECT.search(t)
    if a:
        out["aspect"] = a.group(1).replace(" ", "")
    n = NARRATION.search(t)
    if n:
        out["narration"] = n.group(1).strip()[:40]
    out["palette"] = [h.upper() for h in dict.fromkeys(HEX.findall(t))][:8]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("specs", nargs="+")
    args = ap.parse_args()
    rows = [parse(pathlib.Path(p)) for p in args.specs]

    names = [r["file"][:16] for r in rows]
    print(f"{'field':<18}" + "".join(f"{n:>18}" for n in names) + "   verdict")
    print("-" * (18 + 18 * len(rows) + 30))

    for name, _ in FIELDS + [("aspect", None), ("narration", None)]:
        vals = [r.get(name) for r in rows]
        cells = "".join(f"{('-' if v is None else (f'{v:g}' if isinstance(v,float) else str(v)))[:17]:>18}"
                        for v in vals)
        present = [v for v in vals if v is not None]
        verdict = ""
        if len(present) >= 2:
            if all(isinstance(v, (int, float)) for v in present):
                lo, hi = min(present), max(present)
                spread = (hi - lo) / hi if hi else 0
                verdict = "FORMAT (agrees)" if spread <= 0.25 else f"varies {spread*100:.0f}% -> parameter"
            else:
                verdict = "FORMAT (agrees)" if len(set(present)) == 1 else "varies -> parameter"
        elif len(present) == 1:
            verdict = "only 1 ref — unproven"
        print(f"{name:<18}{cells}   {verdict}")

    print("\npalettes (channel identity — expect these to differ):")
    for r in rows:
        print(f"  {r['file'][:26]:<28}{' '.join(r['palette'][:6])}")

    shared = set(rows[0]["palette"])
    for r in rows[1:]:
        shared &= set(r["palette"])
    print(f"\ncolours shared by ALL refs: {' '.join(sorted(shared)) if shared else 'none'}")
    if len(rows) < 3:
        print(f"\nNOTE: {len(rows)} reference(s). Agreement here is suggestive, not settled —\n"
              "      two channels can share a habit without it being the genre's convention.")


if __name__ == "__main__":
    main()
