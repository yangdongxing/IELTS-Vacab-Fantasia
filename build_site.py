from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import unicodedata
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parent
CONTENT_DIR = ROOT / "content"
DIST_DIR = ROOT / "dist"
ASSET_DIR = ROOT / "assets"
IMAGE_DIR = ASSET_DIR / "images"
STYLE_FILE = ASSET_DIR / "css" / "almond.css"
MONKEY_SCRIPT_FILE = ASSET_DIR / "js" / "monkey-for-extensions.js"
IMAGE_PREVIEW_SCRIPT_FILE = ASSET_DIR / "js" / "word-image-preview.js"
ASSET_FILES = (STYLE_FILE, MONKEY_SCRIPT_FILE, IMAGE_PREVIEW_SCRIPT_FILE)
SPOKEN_USAGE_FILE = ROOT / "data" / "spoken-usage.jsonl"
VOCABULARY_LIST_FILE = CONTENT_DIR / "ielts" / "vocabulary-list.md"
WORD_IMAGE_MANIFEST_FILE = "__word_images__.json"
WORD_IMAGE_SCRIPT_FILE = "word-images.js"
BUILD_STATE_FILE = DIST_DIR / ".build-state.json"


def local_html_link(target: str) -> str:
    if target.startswith(("#", "/", "mailto:", "tel:", "http://", "https://")):
        return target

    match = re.match(r"^([^?#]+)(.*)$", target)
    if match and match.group(1).lower().endswith(".md"):
        return match.group(1)[:-3] + ".html" + match.group(2)
    return target


def inline_markdown(text: str) -> str:
    escaped = html.escape(text, quote=False)

    escaped = re.sub(
        r"`([^`]+)`",
        lambda m: f"<code>{m.group(1)}</code>",
        escaped,
    )
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: (
            f'<a href="{html.escape(local_html_link(m.group(2)), quote=True)}">'
            f"{m.group(1)}</a>"
        ),
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    return escaped


def render_markdown(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    list_type: str | None = None
    in_code = False
    code_lines: list[str] = []

    def close_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            out.append(f"<p>{inline_markdown(' '.join(paragraph))}</p>")
            paragraph = []

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            out.append(f"</{list_type}>")
            list_type = None

    for raw_line in lines:
        line = raw_line.rstrip()

        if line.strip().startswith("```"):
            close_paragraph()
            close_list()
            if in_code:
                out.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(raw_line)
            continue

        if not line.strip():
            close_paragraph()
            close_list()
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            close_paragraph()
            close_list()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline_markdown(heading.group(2).strip())}</h{level}>")
            continue

        unordered = re.match(r"^\s*[-+*]\s+(.+)$", line)
        ordered = re.match(r"^\s*\d+\.\s+(.+)$", line)
        if unordered or ordered:
            close_paragraph()
            next_type = "ul" if unordered else "ol"
            if list_type != next_type:
                close_list()
                out.append(f"<{next_type}>")
                list_type = next_type
            item = unordered.group(1) if unordered else ordered.group(1)
            out.append(f"<li>{inline_markdown(item)}</li>")
            continue

        blockquote = re.match(r"^\s*>\s?(.*)$", line)
        if blockquote:
            close_paragraph()
            close_list()
            out.append(f"<blockquote>{inline_markdown(blockquote.group(1))}</blockquote>")
            continue

        if re.match(r"^\s*([-*_])(?:\s*\1){2,}\s*$", line):
            close_paragraph()
            close_list()
            out.append("<hr>")
            continue

        close_list()
        paragraph.append(line.strip())

    if in_code:
        out.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    close_paragraph()
    close_list()
    return "\n".join(out)


def page_title(markdown_text: str, fallback: str) -> str:
    for line in markdown_text.splitlines():
        heading = re.match(r"^#{1,6}\s+(.+)$", line.strip())
        if heading:
            return re.sub(r"[*_`]+", "", heading.group(1)).strip()
    return fallback


def image_key(word: str) -> str:
    key = Path(word).stem.lower()
    key = key.replace("_", " ")
    key = re.sub(r"\s+", " ", key)
    return key.strip()


def compact_image_key(key: str) -> str:
    ascii_key = unicodedata.normalize("NFD", key.lower())
    ascii_key = "".join(char for char in ascii_key if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", ascii_key)


IRREGULAR_LEMMAS = {
    "was": "be", "were": "be", "been": "be",
    "went": "go", "gone": "go",
    "saw": "see", "seen": "see",
    "took": "take", "taken": "take",
    "wrote": "write", "written": "write",
    "spoke": "speak", "spoken": "speak",
    "lost": "lose",
    "began": "begin", "begun": "begin",
    "felt": "feel",
    "found": "find",
    "gave": "give", "given": "give",
    "ran": "run",
    "swam": "swim", "swum": "swim",
    "flew": "fly", "flown": "fly",
    "built": "build",
    "taught": "teach",
    "thought": "think",
    "bought": "buy",
    "caught": "catch",
    "drew": "draw", "drawn": "draw",
    "drove": "drive", "driven": "drive",
    "ate": "eat", "eaten": "eat",
    "fell": "fall", "fallen": "fall",
    "froze": "freeze", "frozen": "freeze",
    "grew": "grow", "grown": "grow",
    "held": "hold",
    "hid": "hide", "hidden": "hide",
    "knew": "know", "known": "know",
    "laid": "lay", "lain": "lie",
    "led": "lead",
    "left": "leave",
    "made": "make",
    "meant": "mean",
    "met": "meet",
    "paid": "pay",
    "rode": "ride", "ridden": "ride",
    "rose": "rise", "risen": "rise",
    "said": "say",
    "sold": "sell",
    "sent": "send",
    "shook": "shake", "shaken": "shake",
    "shone": "shine",
    "shot": "shoot",
    "showed": "show", "shown": "show",
    "shut": "shut",
    "slept": "sleep",
    "slid": "slide",
    "spent": "spend",
    "stood": "stand",
    "stole": "steal", "stolen": "steal",
    "struck": "strike", "stricken": "strike",
    "swept": "sweep",
    "swung": "swing",
    "told": "tell",
    "threw": "throw", "thrown": "throw",
    "understood": "understand",
    "woke": "wake", "woken": "wake",
    "wore": "wear", "worn": "wear",
    "won": "win",
    "wound": "wind",
}

IRREGULAR_INFLECTIONS: dict[str, list[str]] = {}
for _inf, _base in IRREGULAR_LEMMAS.items():
    IRREGULAR_INFLECTIONS.setdefault(_base, []).append(_inf)


def image_key_aliases(key: str) -> set[str]:
    aliases = {
        key,
        key.replace("-", " "),
        re.sub(r"\s+", "-", key),
        re.sub(r"^(a|an|the)\s+", "", key),
    }

    # Add inflections for single words
    if " " not in key and "-" not in key and len(key) > 2:
        k = key.lower()
        # Irregular forms
        for inf in IRREGULAR_INFLECTIONS.get(k, []):
            aliases.add(inf)
        # Regular noun plurals / 3rd person singular verbs
        if k.endswith("y") and len(k) > 2 and k[-2] not in "aeiou":
            aliases.add(k[:-1] + "ies")
        elif k.endswith(("s", "sh", "ch", "x", "z")):
            aliases.add(k + "es")
        else:
            aliases.add(k + "s")

        # Regular verb past / participle (-ed)
        if k.endswith("y") and len(k) > 2 and k[-2] not in "aeiou":
            aliases.add(k[:-1] + "ied")
        elif k.endswith("e"):
            aliases.add(k + "d")
        else:
            aliases.add(k + "ed")
            if len(k) > 2 and k[-1] not in "aeiouy" and k[-2] in "aeiou" and (len(k) == 3 or k[-3] not in "aeiou"):
                aliases.add(k + k[-1] + "ed")

        # Regular verb participle (-ing)
        if k.endswith("ie"):
            aliases.add(k[:-2] + "ying")
        elif k.endswith("e") and not k.endswith(("ee", "oe", "ye")):
            aliases.add(k[:-1] + "ing")
        else:
            aliases.add(k + "ing")
            if len(k) > 2 and k[-1] not in "aeiouy" and k[-2] in "aeiou" and (len(k) == 3 or k[-3] not in "aeiou"):
                aliases.add(k + k[-1] + "ing")
        if k.endswith("l"):
            aliases.add(k + "ling")
            aliases.add(k + "lling")
            aliases.add(k + "led")
            aliases.add(k + "lled")

    parts = key.split()
    if len(parts) > 1:
        aliases.add(parts[-1])
        aliases.add(" ".join(parts[-2:]))
        aliases.add("-".join(parts[-2:]))

    for alias in list(aliases):
        compact = compact_image_key(alias)
        if compact:
            aliases.add(compact)

    return {alias for alias in aliases if alias}


def image_url(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    return quote(relative, safe="/-_.~")


def load_spoken_usage() -> dict[str, dict[str, str]]:
    usage: dict[str, dict[str, str]] = {}
    if not SPOKEN_USAGE_FILE.is_file():
        return usage
    for line_number, line in enumerate(SPOKEN_USAGE_FILE.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid spoken usage on line {line_number}: {error}") from error
        item_key = image_key(str(item.get("key", "")))
        if item_key in usage:
            raise ValueError(f"Duplicate spoken usage key on line {line_number}: {item_key}")
        english = str(item.get("en", "")).strip()
        spoken = {
            "en": english,
            "zh": str(item.get("zh", "")).strip(),
        }
        if "focus" in item:
            focus = str(item.get("focus", "")).strip()
            if not focus or focus.casefold() not in english.casefold():
                raise ValueError(f"Spoken focus is not in its sentence on line {line_number}: {item_key}")
            spoken["focus"] = focus
        usage[item_key] = spoken
    return usage


def load_vocabulary_aliases() -> dict[str, set[str]]:
    aliases: dict[str, set[str]] = {}
    if not VOCABULARY_LIST_FILE.is_file():
        return aliases
    for line in VOCABULARY_LIST_FILE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\*\*(.+?)\*\*\s*\(", line)
        if not match or "/" not in match.group(1):
            continue
        group = {image_key(part) for part in re.split(r"[/／]", match.group(1)) if part.strip()}
        for alias in group:
            aliases.setdefault(alias, set()).update(group)
    return aliases


def build_word_image_manifest() -> dict[str, list[dict[str, object]]]:
    entries: dict[str, list[dict[str, object]]] = {}
    spoken_usage = load_spoken_usage()
    vocabulary_aliases = load_vocabulary_aliases()
    if IMAGE_DIR.exists():
        for path in sorted(IMAGE_DIR.glob("*.jpg")):
            key = image_key(path.name)
            entry: dict[str, object] = {
                "word": path.stem,
                "topic": "",
                "url": image_url(path),
            }
            spoken = (
                spoken_usage.get(key)
                or spoken_usage.get(key.replace("-", " "))
                or spoken_usage.get(re.sub(r"\s+", "-", key))
            )
            if spoken and spoken["en"] and spoken["zh"]:
                entry["spoken"] = spoken
            entry_aliases = set(image_key_aliases(key))
            for vocabulary_alias in vocabulary_aliases.get(key, set()):
                entry_aliases.update(image_key_aliases(vocabulary_alias))
            for alias in sorted(entry_aliases):
                entries.setdefault(alias, []).append(entry)
    return entries


def asset_url(output_path: Path, asset_name: str) -> str:
    relative = os.path.relpath(DIST_DIR / asset_name, output_path.parent)
    return quote(Path(relative).as_posix(), safe="/-_.~")


def markdown_document(markdown_text: str, title: str, output_path: Path) -> bytes:
    rendered = render_markdown(markdown_text)
    safe_title = html.escape(title)
    stylesheet = asset_url(output_path, f"assets/{STYLE_FILE.relative_to(ASSET_DIR).as_posix()}")
    monkey_script = asset_url(output_path, f"assets/{MONKEY_SCRIPT_FILE.relative_to(ASSET_DIR).as_posix()}")
    image_manifest_script = asset_url(output_path, WORD_IMAGE_SCRIPT_FILE)
    image_preview_script = asset_url(
        output_path,
        f"assets/{IMAGE_PREVIEW_SCRIPT_FILE.relative_to(ASSET_DIR).as_posix()}",
    )
    site_root = asset_url(output_path, "")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <link rel="stylesheet" href="{stylesheet}">
</head>
<body>
{rendered}
<script src="{monkey_script}"></script>
<script src="{image_manifest_script}"></script>
<script src="{image_preview_script}" data-site-root="{site_root}"></script>
</body>
</html>
""".encode("utf-8")


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_bytes_if_changed(path: Path, content: bytes) -> bool:
    if path.is_file() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return True


def load_build_state() -> dict[str, object]:
    if not BUILD_STATE_FILE.is_file():
        return {}
    try:
        state = json.loads(BUILD_STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return state if isinstance(state, dict) else {}


def output_paths_for_source(relative: Path) -> list[Path]:
    if relative == Path("index.md"):
        return [DIST_DIR / "index.html"]
    return [DIST_DIR / relative.with_suffix(".html")]


def output_paths_for_stale_source(relative: Path) -> list[Path]:
    if relative == Path("README.md"):
        return [DIST_DIR / "README.html", DIST_DIR / "index.html"]
    return output_paths_for_source(relative)


def remove_stale_outputs(relative_text: str) -> int:
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts:
        return 0

    removed = 0
    for output_path in output_paths_for_stale_source(relative):
        if output_path.is_file():
            output_path.unlink()
            removed += 1
    return removed


def ensure_directory_link(source_dir: Path, dist_link: Path) -> bool:
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    expected_target = Path(os.path.relpath(source_dir, dist_link.parent))
    if dist_link.is_symlink() and Path(os.readlink(dist_link)) == expected_target:
        return False

    if dist_link.is_symlink() or dist_link.is_file():
        dist_link.unlink()
    elif dist_link.exists():
        shutil.rmtree(dist_link)
    dist_link.symlink_to(expected_target, target_is_directory=True)
    return True


def remove_path(path: Path) -> bool:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return True
    if path.exists():
        shutil.rmtree(path)
        return True
    return False


def prune_empty_dist_directories() -> None:
    directories = sorted(
        (path for path in DIST_DIR.rglob("*") if path.is_dir() and not path.is_symlink()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for directory in directories:
        try:
            directory.rmdir()
        except OSError:
            pass


def index_section(relative: Path) -> tuple[int, str]:
    parent = relative.parent.as_posix()
    sections = {
        "ielts": (10, "IELTS 词汇总表"),
        "ielts/chapters": (20, "IELTS 章节串记"),
        "ielts/40-stories": (25, "IELTS 40篇故事串记"),
        "ielts/vocabulary-notebooks": (30, "IELTS 生词本"),
        "ielts/phrase-notebooks": (40, "IELTS 词伙与短语"),
        "writing": (50, "IELTS 写作词伙"),
        "junior-high": (60, "初中英语"),
    }
    return sections.get(parent, (100, parent or "其他内容"))


def generated_index_markdown(source_records: list[tuple[Path, Path, str]]) -> str:
    grouped: dict[tuple[int, str], list[tuple[str, str]]] = {}
    for source_path, relative, _ in source_records:
        if relative == Path("index.md"):
            continue
        markdown_text = source_path.read_text(encoding="utf-8")
        title = page_title(markdown_text, source_path.stem)
        grouped.setdefault(index_section(relative), []).append((relative.as_posix(), title))

    lines = ["## 全部内容"]
    for section in sorted(grouped):
        lines.extend(["", f"### {section[1]}", ""])
        for relative_text, title in sorted(grouped[section]):
            lines.append(f"- [{title}]({relative_text})")
    return "\n".join(lines)


def index_source_digest(
    source_digest: str,
    source_records: list[tuple[Path, Path, str]],
) -> str:
    listing = "\n".join(
        f"{relative.as_posix()}\0{digest}"
        for _, relative, digest in source_records
        if relative != Path("index.md")
    )
    return hashlib.sha256(f"{source_digest}\n{listing}".encode("utf-8")).hexdigest()


def build_site() -> tuple[int, int, int, int]:
    if not CONTENT_DIR.is_dir():
        raise FileNotFoundError(f"Markdown content directory not found: {CONTENT_DIR}")

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    previous_state = load_build_state()
    previous_sources = previous_state.get("sources", {})
    if not isinstance(previous_sources, dict):
        previous_sources = {}
    renderer_digest = file_digest(Path(__file__))
    renderer_changed = previous_state.get("renderer") != renderer_digest

    raw_source_records: list[tuple[Path, Path, str]] = []
    for source_path in sorted(CONTENT_DIR.rglob("*.md")):
        relative = source_path.relative_to(CONTENT_DIR)
        source_digest = file_digest(source_path)
        raw_source_records.append((source_path, relative, source_digest))

    source_records: list[tuple[Path, Path, str]] = []
    current_sources: dict[str, str] = {}
    for source_path, relative, source_digest in raw_source_records:
        if relative == Path("index.md"):
            source_digest = index_source_digest(source_digest, raw_source_records)
        current_sources[relative.as_posix()] = source_digest
        source_records.append((source_path, relative, source_digest))

    removed_count = sum(
        remove_stale_outputs(relative_text)
        for relative_text in previous_sources.keys() - current_sources.keys()
    )

    compiled_count = 0
    unchanged_count = 0
    for source_path, relative, source_digest in source_records:
        relative_text = relative.as_posix()
        output_paths = output_paths_for_source(relative)

        if (
            not renderer_changed
            and previous_sources.get(relative_text) == source_digest
            and all(path.is_file() for path in output_paths)
        ):
            unchanged_count += 1
            continue

        markdown_text = source_path.read_text(encoding="utf-8")
        if relative == Path("index.md"):
            markdown_text = f"{markdown_text.rstrip()}\n\n{generated_index_markdown(raw_source_records)}\n"
        title = page_title(markdown_text, source_path.stem)
        for output_path in output_paths:
            write_bytes_if_changed(output_path, markdown_document(markdown_text, title, output_path))
        compiled_count += 1

    asset_count = 0
    for asset_file in ASSET_FILES:
        legacy_output = DIST_DIR / asset_file.name
        if legacy_output.is_file() or legacy_output.is_symlink():
            legacy_output.unlink()
            asset_count += 1

    manifest = build_word_image_manifest()
    manifest_json = json.dumps(manifest, ensure_ascii=False, separators=(",", ":"))
    asset_count += int(
        write_bytes_if_changed(
            DIST_DIR / WORD_IMAGE_MANIFEST_FILE,
            manifest_json.encode("utf-8"),
        )
    )
    asset_count += int(
        write_bytes_if_changed(
            DIST_DIR / WORD_IMAGE_SCRIPT_FILE,
            f"window.__WORD_IMAGE_INDEX__={manifest_json};\n".encode("utf-8"),
        )
    )
    asset_count += int(remove_path(DIST_DIR / ".DS_Store"))
    asset_count += int(remove_path(DIST_DIR / "images"))
    asset_count += int(ensure_directory_link(ASSET_DIR, DIST_DIR / "assets"))
    prune_empty_dist_directories()

    state = {
        "renderer": renderer_digest,
        "sources": current_sources,
    }
    write_bytes_if_changed(
        BUILD_STATE_FILE,
        (json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )

    return compiled_count, unchanged_count, removed_count, asset_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Incrementally build Markdown into static HTML.")
    parser.add_argument("command", choices=("build",))
    return parser.parse_args()


def main() -> None:
    parse_args()
    compiled, unchanged, removed, assets = build_site()
    print(
        f"Build complete: {compiled} changed/new Markdown, "
        f"{unchanged} unchanged, {removed} stale HTML removed, "
        f"{assets} static assets updated."
    )
    print(f"Static site: {DIST_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
