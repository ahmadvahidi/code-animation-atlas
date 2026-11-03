#!/usr/bin/env python3
"""Regenerate INDEX.md and index.json from styles/*.md.

    python3 tools/build_index.py

The five fields are read from each file: 分类 (category), 长什么样 (look), 适合 (suits),
关键词 (keywords); a ```js fence marks a style that ships a runnable implementation.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLES = os.path.join(ROOT, "styles")


def parse(path):
    txt = open(path, encoding="utf-8").read()
    rid = os.path.basename(path)[:-3]
    title = re.search(r"^#\s*(.+)$", txt, re.M)
    get = lambda pat: (re.search(pat, txt).group(1).strip() if re.search(pat, txt) else "")
    return {
        "id": rid,
        "title": title.group(1) if title else rid,
        "cat": get(r"- 分类：(.+)"),
        "look": get(r"- 长什么样：(.+)"),
        "fits": get(r"- 适合：(.+)"),
        "kw": get(r"- 关键词：(.+)"),
        "code": bool(re.search(r"```(?:js|javascript)\n", txt)),
        "bytes": len(txt.encode()),
    }


def main():
    rows = [parse(os.path.join(STYLES, f)) for f in sorted(os.listdir(STYLES))
            if f.endswith(".md") and not f.startswith("_")]
    json.dump(rows, open(os.path.join(ROOT, "index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)

    groups = {}
    for r in rows:
        groups.setdefault(r["cat"].split("·")[0].strip() or "Other", []).append(r)
    out = [f"# {len(rows)} animation styles — offline index", "",
           f"{len(rows)} styles, {sum(r['code'] for r in rows)} with a runnable JS reference "
           f"implementation.", ""]
    for g in sorted(groups):
        out.append(f"## {g} ({len(groups[g])})")
        out.append("")
        for r in groups[g]:
            out.append(f"- **{r['id']}** · {r['title']} — {r['fits'] or r['look']}")
        out.append("")
    open(os.path.join(ROOT, "INDEX.md"), "w", encoding="utf-8").write("\n".join(out))
    print(f"{len(rows)} styles, {sum(r['code'] for r in rows)} coded, {len(groups)} groups")


if __name__ == "__main__":
    main()
