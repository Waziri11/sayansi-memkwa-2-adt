#!/usr/bin/env python3
"""Refresh JSON snapshots embedded in the generated offline preloader."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRELOADER = ROOT / "assets/offline-preloader.js"
START = "  var INLINE = "
END = ";\n  var BASE_DIR"


def main() -> None:
    source = PRELOADER.read_text()
    start = source.index(START) + len(START)
    end = source.index(END, start)
    inline = json.loads(source[start:end])

    # Files introduced after the original export must be explicitly added to
    # the inline snapshot so file:// and offline reading use the same data.
    for required in (
        "./content/i18n/sw-TZ/sign-language-timings.json",
        "./content/i18n/sw-TZ/videos.json",
    ):
        inline.setdefault(required, {})

    refreshed = []
    for key in list(inline):
        path = ROOT / key.removeprefix("./")
        if path.exists():
            inline[key] = json.loads(path.read_text()) if key.endswith(".json") else path.read_text()
            refreshed.append(key)

    replacement = json.dumps(inline, ensure_ascii=False, separators=(",", ":"))
    PRELOADER.write_text(source[:start] + replacement + source[end:])
    print(json.dumps({"refreshed": refreshed, "count": len(refreshed)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
