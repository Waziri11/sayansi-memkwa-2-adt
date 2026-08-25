#!/usr/bin/env python3
"""Synchronize the comment-matrix fixes across ADT text and audio manifests."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "content/i18n/sw-TZ"
TEXTS_PATH = I18N / "texts.json"
AUDIOS_PATH = I18N / "audios.json"
AUDIO_DIR = I18N / "audio"

TARGET_PAGES = {
    3, 4, 6, 7, 9, 11, 16, 17, 23, 27, 29, 31, 34, 35, 39, 41, 44, 47,
    56, 57, 58, 62, 64, 65, 68, 70, 71, 72, 76, 80, 81, 84, 86, 87, 90,
    10, 18, 20, 21, 28, 38, 42, 43, 53, 54, 63, 67, 69, 73, 94,
    91, 98, 100, 101, 103, 104, 107, 109, 110, 111, 113, 117, 118, 119,
    122, 130, 132, 145, 146, 147, 151,
}

FORCE_REBUILD = {
    "pg003_n0040", "pg004_n0010", "pg007_n0004", "pg007_n0017",
    "pg007_n0021", "pg023_n0028", "pg027_n0020", "pg027_n0021",
    "pg029_n0003", "pg031_n0010", "pg031_n0023", "pg039_n0030",
    "pg044_n0002", "pg044_n0019", "pg047_n0015", "pg047_n0016",
    "pg057_n0002", "pg057_n0004", "pg062_n0014", "pg071_n0026",
    "pg076_n0009", "pg091_n0005", "pg101_n0003", "pg106_n0020",
    "pg107_n0002", "pg109_n0018", "pg113_im004", "pg119_n0004",
    "pg145_n0044", "pg146_n0038", "pg146_n0040", "pg146_n0042",
    "pg147_n0021", "pg147_n0024", "pg147_n0027", "pg147_n0030",
    "pg147_n0033",
}

FORCE_REBUILD.update({
    "pg020_n0006", "pg020_n0015", "pg020_n0024", "pg020_n0033", "pg020_n0042",
    "pg020_n0052", "pg020_n0053", "pg020_n0054", "pg020_n0055", "pg020_n0056",
    "pg042_n0030", "pg042_n0038", "pg043_n0002", "pg043_n0013", "pg043_n0021",
    "pg043_n0029", "pg043_n0030", "pg043_n0031", "pg043_n0032",
    "pg044_n0048", "pg044_n0051", "pg044_n0054", "pg044_n0057", "pg044_n0060",
    "pg053_n0016", "pg053_n0017", "pg053_n0018", "pg053_n0019", "pg053_n0020",
    "pg053_n0021", "pg053_n0022", "pg053_n0023", "pg053_n0024", "pg053_n0025",
    "pg054_n0003", "pg054_n0004", "pg054_n0005", "pg054_n0006", "pg054_n0007",
    "pg054_n0008", "pg054_n0009", "pg054_n0010", "pg054_n0011", "pg054_n0012",
    "pg054_n0013", "pg054_n0014", "pg054_n0015", "pg054_n0016", "pg054_n0017",
    "pg054_n0018", "pg056_n0022", "pg056_n0024", "pg063_n0028", "pg063_n0031",
    "pg063_n0034", "pg063_n0037", "pg067_n0007", "pg067_n0009", "pg067_n0011",
    "pg067_n0013", "pg067_n0015", "pg067_n0017", "pg073_n0024", "pg073_n0026",
    "pg073_n0028", "pg073_n0031", "pg073_n0033", "pg094_n0026", "pg094_n0028",
    "pg094_n0032", "pg094_n0035", "pg094_n0037", "pg103_n0011", "pg103_n0013",
    "pg103_n0015",
})


def page_number(key: str) -> int | None:
    match = re.match(r"pg(\d{3})_", key)
    return int(match.group(1)) if match else None


def is_printing_metadata(value: str) -> bool:
    return bool(
        re.search(r"SAYANSI\s+MEMKWA\s+2\s*\.?(?:indd)?", value, re.I)
        or re.fullmatch(r"\s*\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s*", value)
    )


def is_redundant_caption(key: str, value: str) -> bool:
    if "_im" in key:
        return False
    return bool(re.match(r"^Kielelezo(?:\s+namba\s+\d+|\s*:).*:", value, re.I))


def main() -> None:
    texts = json.loads(TEXTS_PATH.read_text())
    audios = json.loads(AUDIOS_PATH.read_text())

    replacements = {
        "pg080_im006": "Mwanamke anashona nguo kwa cherehani huku mwanaume akikata kitambaa juu ya meza.",
        "pg039_n0030": "Tunakausha mazao kwa kutumia nishati ya mwanga.",
        "pg039_n0030_easy_read": "Tunakausha mazao kwa kutumia nishati ya mwanga.",
        "pg147_n0021": "1.", "pg147_n0021_easy_read": "1.",
        "pg147_n0024": "2.", "pg147_n0024_easy_read": "2.",
        "pg147_n0027": "3.", "pg147_n0027_easy_read": "3.",
        "pg147_n0030": "4.", "pg147_n0030_easy_read": "4.",
        "pg147_n0033": "5.", "pg147_n0033_easy_read": "5.",
    }
    texts.update(replacements)

    skipped = set()
    for key, value in texts.items():
        if "_ans_item" in key or is_printing_metadata(value) or is_redundant_caption(key, value):
            audios.pop(key, None)
            skipped.add(key)

    # The duplicate scanned image on Exercise 2 was removed in favour of the
    # accessible interactive questions below it.
    audios.pop("pg146_im006", None)
    skipped.add("pg146_im006")

    generated = set()
    for key, value in texts.items():
        page = page_number(key)
        if page not in TARGET_PAGES or key in skipped or not value.strip():
            continue
        filename = audios.setdefault(key, f"{key}.mp3")
        path = AUDIO_DIR / filename
        if key in FORCE_REBUILD or not path.exists() or path.stat().st_size == 0:
            generated.add(key)

    TEXTS_PATH.write_text(json.dumps(texts, ensure_ascii=False, indent=2) + "\n")
    AUDIOS_PATH.write_text(json.dumps(audios, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "narration_removed": len(skipped),
        "audio_to_generate": len(generated),
        "ids": sorted(generated),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
