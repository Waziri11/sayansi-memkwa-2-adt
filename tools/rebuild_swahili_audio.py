#!/usr/bin/env python3
"""Audit and rebuild ADT narration with natural Tanzanian Swahili numbers."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "content/i18n/sw-TZ"
VOICE = "sw-TZ-RehemaNeural"

ONES = ("sifuri", "moja", "mbili", "tatu", "nne", "tano", "sita", "saba", "nane", "tisa")
TENS = {10: "kumi", 20: "ishirini", 30: "thelathini", 40: "arobaini", 50: "hamsini", 60: "sitini", 70: "sabini", 80: "themanini", 90: "tisini"}
ORDINALS = {1: "kwanza", 2: "pili", 3: "tatu", 4: "nne", 5: "tano", 6: "sita", 7: "saba", 8: "nane", 9: "tisa", 10: "kumi"}
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10}
LETTERS = {"a": "a", "b": "be", "c": "che", "d": "de", "e": "e", "f": "fe", "g": "ge", "h": "he", "i": "i"}
REPORTED_PAGES = {3, 13, 14, 22, 23, 24, 29, 32, 38, 39, 66, 82, 84, 89, 92, 103}
QUESTION_PAGES = {8, 13, 14, 15, 16, 19, 20, 21, 29, 30, 35, 38, 39, 46, 48, 53, 54, 58, 60, 66, 67, 76, 82, 83, 86, 89, 91, 103}

SPEECH_OVERRIDES = {
    "pg003_n0040": "Sura ya kumi na nne",
    "pg004_n0010": "Sura ya kumi na nne",
    "pg023_n0028": "Swali la sita. Mwambie rafiki yako agonge chuma.",
    "pg039_n0030": "Swali la kumi na saba. Tunakausha mazao kwa kutumia nishati ya mwanga.",
    "pg044_n0002": "Swali la tano.",
    "pg044_n0048": "Swali la sita.",
    "pg044_n0051": "Swali la saba.",
    "pg044_n0054": "Swali la nane.",
    "pg044_n0057": "Swali la tisa.",
    "pg044_n0060": "Swali la kumi.",
    "pg042_n0030": "Moja.",
    "pg042_n0038": "Mbili.",
    "pg043_n0002": "Tatu. Safisha jokofu.",
    "pg043_n0013": "Nne. Panga vyakula kwa usahihi na usalama.",
    "pg043_n0021": "Tano. Funga mlango wa jokofu kwa usahihi.",
    "pg043_n0029": "Swali la kwanza. Taja vyakula vinavyoweza kuwekwa katika sehemu ya jokofu isiyogandisha.",
    "pg043_n0030": "Swali la pili. Orodhesha faida tatu za kutumia jokofu.",
    "pg043_n0031": "Swali la tatu. Fafanua mambo matano ya kuzingatia wakati wa kutumia jokofu.",
    "pg043_n0032": "Swali la nne. Onesha hatua utakazofuata wakati wa kusafisha jokofu.",
    "pg062_n0014": "Moja. Chukua kikombe cha plastiki chenye maji, weka juu ya meza.",
    "pg071_n0026": "Kazi namba moja. Kutumia simu ya mkononi.",
    "pg076_n0009": "Hatua ya kwanza. Chomeka waya wa antena au dishi kwenye kisimbuzi.",
    "pg073_n0024": "Hatua ya kwanza. Weka betri kwenye redio au chomeka redio kwenye soketi ya umeme ili redio ipate nishati.",
    "pg073_n0026": "Hatua ya pili. Washa redio kwa kutumia kitufe cha kuwashia.",
    "pg073_n0028": "Hatua ya tatu. Tafuta stesheni kwa kuweka masafa tofauti, kisha simamisha kwenye stesheni unayohitaji.",
    "pg073_n0031": "Hatua ya nne. Punguza au ongeza sauti kulingana na mahitaji.",
    "pg073_n0033": "Hatua ya tano. Anza kusikiliza redio.",
    "pg094_n0026": "Hatua ya kwanza. Chukua pamba katika mafungu mawili na iloweshe kwa maji.",
    "pg094_n0028": "Hatua ya pili. Chukua bilauri au chupa mbili.",
    "pg094_n0032": "Hatua ya tatu. Weka mbegu ya harage ndani ya kila pamba.",
    "pg094_n0035": "Hatua ya nne. Katika bilauri au chupa A weka barafu kila siku asubuhi, mchana na jioni.",
    "pg094_n0037": "Hatua ya tano. Katika bilauri au chupa B weka maji yasiyo na barafu.",
    "pg063_n0028": "Hatua ya kwanza.",
    "pg063_n0031": "Hatua ya pili.",
    "pg063_n0034": "Hatua ya tatu.",
    "pg063_n0037": "Hatua ya nne.",
    "pg091_n0005": "Hatua ya kwanza. Kubainisha tatizo.",
    "pg101_n0003": "Swali la kwanza.",
    "pg147_n0021": "Swali la kwanza.",
    "pg147_n0024": "Swali la pili.",
    "pg147_n0027": "Swali la tatu.",
    "pg147_n0030": "Swali la nne.",
    "pg147_n0033": "Swali la tano.",
}


def number_to_words(value: int) -> str:
    if value < 10:
        return ONES[value]
    if value < 100:
        tens, remainder = divmod(value, 10)
        base = TENS[tens * 10]
        return base if not remainder else f"{base} na {number_to_words(remainder)}"
    if value < 1000:
        hundreds, remainder = divmod(value, 100)
        base = "mia moja" if hundreds == 1 else f"mia {number_to_words(hundreds)}"
        return base if not remainder else f"{base} na {number_to_words(remainder)}"
    if value < 1_000_000:
        thousands, remainder = divmod(value, 1000)
        base = f"elfu {number_to_words(thousands)}"
        return base if not remainder else f"{base} na {number_to_words(remainder)}"
    return " ".join(ONES[int(digit)] for digit in str(value))


def ordinal(value: int) -> str:
    return ORDINALS.get(value, number_to_words(value))


def normalize_for_speech(text: str, key: str = "") -> str:
    if key in SPEECH_OVERRIDES:
        return SPEECH_OVERRIDES[key]
    spoken = text.replace("[[blank:", " ").replace("]]", " ")
    # RehemaNeural pronounces the apostrophe in ng'ombe unnaturally; omitting it
    # in the speech input preserves the correct Tanzanian Swahili pronunciation.
    spoken = re.sub(r"\bng[’']ombe\b", "ngombe", spoken, flags=re.I)
    spoken = re.sub(r"\bnge\b", "ng'e", spoken, flags=re.I)
    spoken = re.sub(r"\bVVU\b", "ve ve u", spoken)
    spoken = re.sub(r"\bUKIMWI\b", "u kimwi", spoken)
    spoken = re.sub(r"\bmbalimbali\b", "mbali mbali", spoken, flags=re.I)
    page = re.match(r"pg(\d{3})_", key)
    marker = re.fullmatch(r"\s*(\d+)\.\s*", spoken)
    if marker:
        value = int(marker.group(1))
        if page and int(page.group(1)) in QUESTION_PAGES:
            return f"Swali la {ordinal(value)}."
        return f"Namba {number_to_words(value)}."
    if page and int(page.group(1)) in QUESTION_PAGES:
        spoken = re.sub(r"^\s*(\d{1,2})\.\s*", lambda m: f"Swali la {ordinal(int(m.group(1)))}. ", spoken)
    spoken = re.sub(r"\b(Zoezi|Jaribio)(?: la)?\s+(\d+)\b", lambda m: f"{m.group(1)} la {ordinal(int(m.group(2)))}", spoken, flags=re.I)
    spoken = re.sub(r"\b(Sura|Shughuli) ya\s+(\d+)\b", lambda m: f"{m.group(1)} ya {ordinal(int(m.group(2)))}", spoken, flags=re.I)
    spoken = re.sub(r"\b(Kazi|Kielelezo|Jedwali) namba\s+(\d+)\b", lambda m: f"{m.group(1)} namba {number_to_words(int(m.group(2)))}", spoken, flags=re.I)
    spoken = re.sub(r"\((i{1,3}|iv|v|vi{0,3}|ix|x)\)", lambda m: number_to_words(ROMAN[m.group(1).lower()]), spoken, flags=re.I)
    spoken = re.sub(r"\b(Sehemu)\s+([A-I])\b", lambda m: f"{m.group(1)} {LETTERS[m.group(2).lower()]}", spoken)
    spoken = re.sub(r"\(([A-Ha-h])\)", lambda m: f" herufi {LETTERS[m.group(1).lower()]} ", spoken)
    spoken = re.sub(r"\b(ml)\b", "mililita", spoken, flags=re.I)
    spoken = re.sub(r"\b(kg)\b", "kilogramu", spoken, flags=re.I)
    spoken = re.sub(r"\b(cm)\b", "sentimeta", spoken, flags=re.I)
    spoken = re.sub(r"\b(sm)\b", "sentimeta", spoken, flags=re.I)
    spoken = re.sub(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", lambda m: f"tarehe {number_to_words(int(m.group(1)))} mwezi wa {number_to_words(int(m.group(2)))} mwaka {number_to_words(int(m.group(3)))}", spoken)
    spoken = re.sub(r"\b(\d+)\.(\d+)\b", lambda m: f"{number_to_words(int(m.group(1)))} nukta {' '.join(ONES[int(digit)] for digit in m.group(2))}", spoken)
    spoken = re.sub(r"\b\d+\b", lambda m: number_to_words(int(m.group())), spoken)
    spoken = spoken.replace("+", " kujumlisha ").replace("−", " kutoa ").replace("-", " kutoa ")
    return re.sub(r"\s+", " ", spoken).strip()


def needs_rebuild(key: str, text: str) -> bool:
    page = re.match(r"pg(\d{3})_", key)
    reported = bool(page and int(page.group(1)) in REPORTED_PAGES)
    numeric = bool(re.search(r"\d|\([A-Ia-i]\)|\b[IVX]{1,4}\b", text))
    return reported or numeric or key in {"pg106_im004_seg001_v1", "pg106_im004_seg001_v1_easy_read"}


async def generate(items: list[tuple[str, str]], audios: dict[str, str], concurrency: int) -> None:
    import edge_tts

    semaphore = asyncio.Semaphore(concurrency)
    failures: list[tuple[str, str]] = []

    async def one(key: str, visible: str) -> None:
        filename = audios.get(key)
        if not filename:
            return
        output = I18N / "audio" / filename
        temporary = output.with_suffix(output.suffix + ".tmp")
        try:
            async with semaphore:
                await edge_tts.Communicate(normalize_for_speech(visible, key), VOICE).save(str(temporary))
            temporary.replace(output)
        except Exception as error:  # pragma: no cover - network dependent
            failures.append((key, str(error)))
            temporary.unlink(missing_ok=True)

    await asyncio.gather(*(one(key, text) for key, text in items))
    if failures:
        raise RuntimeError(f"{len(failures)} audio generations failed; first: {failures[0]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--sample", type=int, default=20)
    parser.add_argument("--limit", type=int, default=0, help="Generate only the first N affected IDs (QA only).")
    parser.add_argument("--pages", default="", help="Optional comma-separated three-digit page numbers.")
    parser.add_argument("--ids", default="", help="Optional comma-separated text IDs to rebuild exactly.")
    parser.add_argument("--comment-matrix", action="store_true", help="Rebuild every narration asset affected by the comment-matrix remediation.")
    parser.add_argument(
        "--skip-git-modified",
        action="store_true",
        help="Resume a run by skipping audio files already modified in the worktree.",
    )
    parser.add_argument(
        "--standalone-markers-only",
        action="store_true",
        help="Rebuild only IDs whose entire visible value is a numbered list marker.",
    )
    args = parser.parse_args()
    texts = json.loads((I18N / "texts.json").read_text())
    audios = json.loads((I18N / "audios.json").read_text())
    requested_ids = {key.strip() for key in args.ids.split(",") if key.strip()}
    if args.comment_matrix:
        from apply_comment_matrix_fixes import AUDIO_DIR, FORCE_REBUILD, TARGET_PAGES, page_number
        requested_ids.update(
            key for key, filename in audios.items()
            if page_number(key) in TARGET_PAGES
            and (key in FORCE_REBUILD or not (AUDIO_DIR / filename).exists() or (AUDIO_DIR / filename).stat().st_size == 0)
        )
    items = [
        (key, value)
        for key, value in texts.items()
        if key in audios and (key in requested_ids if requested_ids else needs_rebuild(key, value))
    ]
    if args.standalone_markers_only:
        items = [(key, value) for key, value in items if re.fullmatch(r"\s*\d+\.\s*", value)]
    if args.pages:
        prefixes = tuple(f"pg{int(page):03d}_" for page in args.pages.split(","))
        items = [(key, value) for key, value in items if key.startswith(prefixes)]
    if args.skip_git_modified:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", str(I18N / "audio")],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        modified = {Path(line[3:]).name for line in status.splitlines() if len(line) > 3}
        items = [(key, value) for key, value in items if audios[key] not in modified]
    print(json.dumps({"voice": VOICE, "affected": len(items), "examples": [{"id": key, "visible": value, "spoken": normalize_for_speech(value, key)} for key, value in items[: args.sample]]}, ensure_ascii=False, indent=2))
    if args.generate:
        asyncio.run(generate(items[: args.limit or None], audios, args.concurrency))


if __name__ == "__main__":
    main()
