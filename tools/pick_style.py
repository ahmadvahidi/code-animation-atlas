#!/usr/bin/env python3
"""Suggest styles for a topic.

    python3 tools/pick_style.py "a video about losing money to inflation"
    python3 tools/pick_style.py "calm ending, hope" --coded-only

Scores every style on keyword overlap with its `fits` (what it suits), `look` and `title`,
then prints a shortlist. It is a shortlist tool, not an oracle: read the prompt of the two
or three it suggests before committing.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOP = {"a", "an", "the", "of", "to", "for", "and", "or", "in", "on", "with", "about",
        "video", "clip", "short", "scene", "make", "style", "look"}


def tokens(text):
    return {w for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in STOP}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topic", nargs="+")
    ap.add_argument("--coded-only", action="store_true", help="only styles that ship code")
    ap.add_argument("--limit", type=int, default=6)
    a = ap.parse_args()
    topic = set()
    for t in a.topic:
        topic |= tokens(t)
    rows = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    tags = json.load(open(os.path.join(ROOT, "tools", "english_tags.json"), encoding="utf-8"))
    scored = []
    for r in rows:
        if a.coded_only and not r["code"]:
            continue
        hay = tokens(r["fits"] + " " + r["look"] + " " + r["title"] + " " + r["kw"]
                     + " " + tags.get(r["id"], ""))
        score = len(topic & hay)
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: (-x[0], x[1]["id"]))
    if not scored:
        print("no keyword overlap — read INDEX.md by mood instead", file=sys.stderr)
        return 1
    for score, r in scored[: a.limit]:
        tag = "code" if r["code"] else "prompt"
        print(f"{r['id']:<5}{tag:<7}{score:<3}{r['title']}  — {r['fits'] or r['look']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
