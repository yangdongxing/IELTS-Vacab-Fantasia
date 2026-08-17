#!/usr/bin/env python3
"""Inspect and edit example focus phrases in spoken-usage.jsonl."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
USAGE_FILE = ROOT / "data" / "spoken-usage.jsonl"
BUILD_SCRIPT = ROOT / "build_site.py"
TRAILING_PUNCTUATION = ".,!?;:"
CONTEXT_PADDING = " \t\r\n.,!?;:'\"\u2018\u2019\u201c\u201d"


class FocusError(ValueError):
    pass


def normalize_key(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower().strip()
    value = re.sub(r"[\u201c\u201d\"'()]", "", value)
    return re.sub(r"[_\s-]+", " ", value).strip()


def phrase_pattern(phrase: str) -> re.Pattern[str]:
    phrase = phrase.translate(str.maketrans({"\u2018": "'", "\u2019": "'"}))
    parts: list[str] = []
    whitespace = False
    for character in phrase:
        if character.isspace():
            if not whitespace:
                parts.append(r"\s+")
            whitespace = True
            continue
        whitespace = False
        if character == "'":
            parts.append("['\u2018\u2019]")
        else:
            parts.append(re.escape(character))
    return re.compile("".join(parts), re.IGNORECASE)


def find_phrase(sentence: str, phrase: str) -> re.Match[str] | None:
    return phrase_pattern(phrase).search(sentence)


def comparable_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.translate(str.maketrans({
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    }))
    return re.sub(r"\s+", " ", value).strip().casefold()


def load_records(path: Path = USAGE_FILE) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    seen: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise FocusError(f"Cannot read {path}: {error}") from error

    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise FocusError(f"Invalid JSON on line {line_number}: {error}") from error
        if not isinstance(record, dict):
            raise FocusError(f"Record on line {line_number} is not a JSON object")

        record_key = normalize_key(str(record.get("key", "")))
        if not record_key:
            raise FocusError(f"Missing key on line {line_number}")
        if record_key in seen:
            raise FocusError(f"Duplicate key on line {line_number}: {record_key}")
        seen.add(record_key)

        sentence = str(record.get("en", "")).strip()
        if not sentence:
            raise FocusError(f"Missing English example on line {line_number}: {record_key}")
        if "focus" in record:
            focus = str(record.get("focus", "")).strip()
            if not focus or not find_phrase(sentence, focus):
                raise FocusError(f"Invalid focus on line {line_number}: {record_key}: {focus!r}")
        records.append(record)
    return records


def find_record(records: list[dict[str, object]], requested_key: str) -> dict[str, object]:
    wanted = normalize_key(requested_key)
    by_key = {normalize_key(str(record["key"])): record for record in records}
    record = by_key.get(wanted)
    if record:
        return record
    suggestions = difflib.get_close_matches(wanted, by_key, n=3, cutoff=0.6)
    hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
    raise FocusError(f"Unknown word: {requested_key}.{hint}")


def focus_from_input(value: str, sentence: str) -> str:
    markdown_matches = list(re.finditer(r"\*\*(.+?)\*\*", value, re.DOTALL))
    if "**" in value:
        if len(markdown_matches) != 1 or value.count("**") != 2:
            raise FocusError("Expected exactly one **bold phrase**")
        match = markdown_matches[0]
        surrounding_text = f"{value[:match.start()]}{value[match.end():]}".strip(CONTEXT_PADDING)
        if surrounding_text:
            plain_sentence = value.replace("**", "")
            if comparable_text(plain_sentence) != comparable_text(sentence):
                raise FocusError("Marked example does not match the stored English example")
        value = match.group(1)

    candidate = value.strip().rstrip(TRAILING_PUNCTUATION).rstrip()
    if not candidate:
        raise FocusError("Focus phrase cannot be empty")
    match = find_phrase(sentence, candidate)
    if not match:
        raise FocusError(f"Focus phrase is not in the example: {candidate!r}")
    return match.group(0)


def set_focus(record: dict[str, object], focus: str) -> None:
    record.pop("focus", None)
    ordered: dict[str, object] = {}
    inserted = False
    for field, value in record.items():
        ordered[field] = value
        if field == "zh":
            ordered["focus"] = focus
            inserted = True
    if not inserted:
        raise FocusError(f"Cannot set focus because {record.get('key')} has no Chinese example")
    record.clear()
    record.update(ordered)


def write_records(records: list[dict[str, object]], path: Path = USAGE_FILE) -> None:
    text = "".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        for record in records
    )
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def preview(sentence: str, focus: str) -> str:
    match = find_phrase(sentence, focus)
    if not match:
        return sentence
    return f"{sentence[:match.start()]}**{match.group(0)}**{sentence[match.end():]}"


def print_record(record: dict[str, object]) -> None:
    sentence = str(record["en"])
    focus = str(record.get("focus", ""))
    print(f"Word:    {record.get('word', record['key'])} ({record['key']})")
    print(f"English: {sentence}")
    print(f"Chinese: {record.get('zh', '')}")
    print(f"Focus:   {focus or '(none)'}")
    if focus:
        print(f"Preview: {preview(sentence, focus)}")


def build_site() -> None:
    result = subprocess.run([sys.executable, str(BUILD_SCRIPT), "build"], cwd=ROOT)
    if result.returncode:
        raise FocusError(f"Site build failed with exit code {result.returncode}")


def command_set(args: argparse.Namespace) -> None:
    records = load_records()
    record = find_record(records, args.key)
    sentence = str(record["en"])
    raw_focus = args.focus
    if raw_focus is None:
        print_record(record)
        raw_focus = input("New focus (empty input cancels): ").strip()
        if not raw_focus:
            print("Cancelled.")
            return
    focus = focus_from_input(raw_focus, sentence)
    if str(record.get("focus", "")) == focus:
        print(f"Unchanged: {record['key']} -> {focus}")
        return
    set_focus(record, focus)
    write_records(records)
    print(f"Updated: {record['key']} -> {focus}")
    print(f"Preview: {preview(sentence, focus)}")
    if not args.no_build:
        build_site()


def command_clear(args: argparse.Namespace) -> None:
    records = load_records()
    record = find_record(records, args.key)
    if "focus" not in record:
        print(f"No focus set for {record['key']}.")
        return
    removed = str(record.pop("focus"))
    write_records(records)
    print(f"Cleared: {record['key']} (was: {removed})")
    if not args.no_build:
        build_site()


def command_show(args: argparse.Namespace) -> None:
    print_record(find_record(load_records(), args.key))


def command_validate(_: argparse.Namespace) -> None:
    records = load_records()
    focused = sum("focus" in record for record in records)
    print(f"Validated {len(records)} records; {focused} focus phrases; 0 issues.")


def parser() -> argparse.ArgumentParser:
    main_parser = argparse.ArgumentParser(description=__doc__)
    commands = main_parser.add_subparsers(dest="command", required=True)

    set_parser = commands.add_parser("set", help="add or replace a focus phrase")
    set_parser.add_argument("key", help="vocabulary key, such as faint")
    set_parser.add_argument("focus", nargs="?", help="phrase or text containing one **bold phrase**")
    set_parser.add_argument("--no-build", action="store_true", help="do not rebuild the site")
    set_parser.set_defaults(handler=command_set)

    clear_parser = commands.add_parser("clear", help="remove a focus phrase")
    clear_parser.add_argument("key", help="vocabulary key")
    clear_parser.add_argument("--no-build", action="store_true", help="do not rebuild the site")
    clear_parser.set_defaults(handler=command_clear)

    show_parser = commands.add_parser("show", help="show an example and its focus phrase")
    show_parser.add_argument("key", help="vocabulary key")
    show_parser.set_defaults(handler=command_show)

    validate_parser = commands.add_parser("validate", help="validate every focus phrase")
    validate_parser.set_defaults(handler=command_validate)
    return main_parser


def main() -> int:
    args = parser().parse_args()
    try:
        args.handler(args)
    except (FocusError, EOFError, KeyboardInterrupt) as error:
        if isinstance(error, KeyboardInterrupt):
            print(file=sys.stderr)
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
