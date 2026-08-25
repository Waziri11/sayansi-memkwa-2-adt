#!/usr/bin/env python3
"""Audit or remove audio for illustration captions and print footers."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "content/i18n/sw-TZ"
AUDIO = I18N / "audio"

CAPTION = re.compile(r"^\s*Kielelezo\s+namba\s+\d+(?:\s*\([^)]+\))?\s*:", re.I)
FOOTER = re.compile(
    r"(?:SAYANSI\s+MEMKWA\s*2\s*\.indd|"
    r"(?:^|\s)\d{1,2}[/-]\d{1,2}[/-]20\d{2}\s+\d{1,2}:\d{2}\s*$)",
    re.I,
)
# These two captions split "Kielelezo namba ...:" and its descriptive text
# across adjacent data IDs in the same HTML element.
CAPTION_CONTINUATIONS = {
    "pg008_n0017",
    "pg047_n0010",
    # Labels printed directly beneath stove illustrations.
    "pg048_n0005",
    "pg048_n0007",
    "pg050_n0010",
    "pg050_n0012",
    # Labels printed directly beneath the six tool illustrations.
    "pg079_n0016",
    "pg079_n0019",
    "pg079_n0022",
    "pg079_n0025",
    "pg079_n0028",
    "pg079_n0031",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remove", action="store_true", help="Delete forbidden MP3 files.")
    args = parser.parse_args()

    texts = json.loads((I18N / "texts.json").read_text())
    audios = json.loads((I18N / "audios.json").read_text())
    forbidden = {
        key: "caption" if CAPTION.search(value) else "footer"
        for key, value in texts.items()
        if CAPTION.search(value) or FOOTER.search(value)
    }
    for key in CAPTION_CONTINUATIONS:
        forbidden[key] = "caption"
        easy_read_key = f"{key}_easy_read"
        if easy_read_key in texts:
            forbidden[easy_read_key] = "caption"
    mapped = sorted(key for key in forbidden if key in audios)
    candidates = {
        path
        for key in forbidden
        for path in (
            AUDIO / f"{key}.mp3",
            AUDIO / f"{key}_easy_read.mp3",
        )
    }
    files = sorted(path for path in candidates if path.exists())

    if args.remove:
        for path in files:
            path.unlink(missing_ok=True)

    result = {
        "forbidden_text_ids": len(forbidden),
        "caption_ids": sum(kind == "caption" for kind in forbidden.values()),
        "footer_ids": sum(kind == "footer" for kind in forbidden.values()),
        "mapped_in_audios_json": len(mapped),
        "forbidden_mp3_files": 0 if args.remove else len(files),
        "removed_mp3_files": len(files) if args.remove else 0,
    }
    print(json.dumps(result, indent=2))
    if mapped or (files and not args.remove):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
