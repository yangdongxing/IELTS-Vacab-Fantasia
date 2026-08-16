#!/usr/bin/env python3
"""Generate and validate short spoken-usage examples for image vocabulary."""

from __future__ import annotations

import argparse
import bz2
import hashlib
import itertools
import json
import re
import subprocess
import sys
import unicodedata
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = ROOT / "assets" / "images"
VOCAB_FILE = ROOT / "content" / "ielts" / "vocabulary-list.md"
OUTPUT_FILE = ROOT / "data" / "spoken-usage.jsonl"
GUIDED_REPLACEMENTS_FILE = ROOT / "data" / "guided-replacements.jsonl"
SHARED_REUSE_FILE = ROOT / "data" / "shared-example-reuse.jsonl"
DEFAULT_CORPUS = Path("/private/tmp/cmn-eng.zip")
OFFICIAL_ENGLISH = Path("/private/tmp/eng_sentences_detailed.tsv.bz2")
OFFICIAL_CHINESE = Path("/private/tmp/cmn_sentences_detailed.tsv.bz2")
OFFICIAL_LINKS = Path("/private/tmp/eng-cmn_links.tsv.bz2")

TRADITIONAL_HINTS = set("這個為們來時後裡說學車國會還讓與於從對過開關問題實體應該點樣現發長間氣動區見種書門風東頭無親愛難幫備買賣醫聽寫讀當總經線話場")

SPECIAL_KEYS = {
    "neighbor": "neighborhood",
    "makeup": "make up",
    "micro computer": "microcomputer",
    "co ed": "coed",
    "stemstalk": "stem",
}

SHARED_QUALITY_TOLERANCE = 8
SHARED_EXCLUDED_WORDS = {
    "about", "after", "again", "all", "also", "another", "around", "back", "before",
    "can", "change", "come", "day", "even", "example", "feel", "first", "get", "give",
    "good", "great", "have", "just", "know", "last", "lead", "like", "little", "look",
    "make", "many", "may", "more", "most", "much", "need", "new", "only", "other",
    "people", "place", "right", "same", "say", "see", "show", "some", "state", "take",
    "tell", "thing", "think", "time", "use", "very", "want", "way", "well", "work",
}
SHARED_SENTENCE_BLOCKLIST = re.compile(
    r"\b(?:Tatoeba|Shtooka|Tom|Mary|Sami|Mennad|Layla|Berber|Esperanto|Algeria|Algerian|Moscow)\b"
    r"|\b(?:oral sex|communist city)\b",
    re.I,
)

# Human-reviewed groups win over corpus scoring and serve as regression examples.
CURATED_SHARED = {
    ("thoughtful", "patient"): (
        "She is very thoughtful and patient.",
        "她非常体贴，也很有耐心。",
    ),
}

MANUAL = {
    "abandon": ("We had to abandon our weekend plans.", "我们不得不取消周末计划。"),
    "accord": ("We finally reached an accord after a long discussion.", "经过长时间讨论，我们终于达成了协议。"),
    "aesthetic": ("I love the simple aesthetic of this room.", "我很喜欢这个房间的简约美感。"),
    "altitude": ("I felt dizzy at such a high altitude.", "海拔这么高，我感到有点头晕。"),
    "appointment": ("I have a dentist appointment after work today.", "我今天下班后预约了牙医。"),
    "available": ("Are you available for dinner tomorrow night?", "你明晚有空一起吃饭吗？"),
    "moderate": ("Try to keep the volume at a moderate level.", "尽量把音量保持在适中的水平。"),
    "quartz": ("This watch uses a reliable quartz movement.", "这块手表使用可靠的石英机芯。"),
    "thermodynamic": ("We discussed this thermodynamic process in class today.", "我们今天在课上讨论了这个热力学过程。"),
    "abdomen": ("The doctor examined my abdomen during the checkup.", "体检时，医生检查了我的腹部。"),
    "aboriginal": ("The museum celebrates local Aboriginal art and culture.", "这家博物馆展示当地原住民的艺术和文化。"),
    "adolescence": ("Many habits change naturally during adolescence.", "许多习惯会在青春期自然改变。"),
    "adverse": ("The medicine caused no adverse effects for me.", "这种药没有给我带来不良反应。"),
    "allure": ("I understand the allure of working from home.", "我理解居家办公的吸引力。"),
    "appetizer": ("We ordered an appetizer to share before dinner.", "晚餐前我们点了一份开胃菜一起吃。"),
    "approximately": ("The journey takes approximately two hours by train.", "这段路程坐火车大约需要两小时。"),
    "backup": ("Keep a backup of your important files.", "请为重要文件保留一份备份。"),
    "canteen": ("Let's meet in the canteen for lunch.", "我们午餐时在食堂见吧。"),
    "convict": ("The evidence was enough to convict him.", "这些证据足以将他定罪。"),
    "fur": ("Her coat has a soft fur lining.", "她的大衣有柔软的毛皮内衬。"),
    "shears": ("Use these shears to trim the hedge.", "用这把大剪刀修剪树篱。"),
    "southeast": ("The station is southeast of the city center.", "车站位于市中心东南方向。"),
    "southwest": ("Our hotel is southwest of the airport.", "我们的酒店位于机场西南方向。"),
    "alumni": ("The event welcomed both students and alumni.", "这次活动同时欢迎在校生和校友。"),
    "announcer": ("The announcer gave us the latest travel update.", "播音员向我们播报了最新出行信息。"),
    "anthropologist": ("An anthropologist explained the custom to our group.", "一位人类学家向我们解释了这个习俗。"),
    "apprentice": ("The apprentice learned the skill from an expert.", "学徒向一位专家学习了这项技能。"),
    "arthritis": ("Regular movement can help people manage arthritis.", "经常活动有助于缓解关节炎。"),
    "attorney": ("I asked an attorney to review the contract.", "我请了一位律师审阅这份合同。"),
    "aural": ("The course includes several aural comprehension exercises.", "这门课程包含几项听力理解练习。"),
    "bead": ("A small bead fell from her necklace.", "一颗小珠子从她的项链上掉了下来。"),
    "breed": ("They breed working dogs on this farm.", "他们在这个农场饲养工作犬。"),
    "broom": ("I used a broom to sweep the floor.", "我用扫帚清扫了地板。"),
    "carnivore": ("A lion is a powerful wild carnivore.", "狮子是一种强大的野生肉食动物。"),
}

CHAPTER_TEMPLATES = {
    1: ("We learned about {word} in class today.", "我们今天在课上学习了{meaning}。"),
    2: ("The guide showed us {word} in the garden.", "向导在花园里给我们看了{meaning}。"),
    3: ("We saw {word} at the wildlife center.", "我们在野生动物中心看到了{meaning}。"),
    4: ("The documentary explains {word} in simple terms.", "这部纪录片用简单的方式解释了{meaning}。"),
    5: ("We talked about {word} during class today.", "我们今天上课时谈到了{meaning}。"),
    6: ("This app makes {word} easier to understand.", "这个应用让{meaning}更容易理解。"),
    7: ("The museum has an exhibit about {word}.", "博物馆有一个关于{meaning}的展览。"),
    8: ("Our teacher gave a clear example of {word}.", "老师举了一个清楚的例子说明{meaning}。"),
    9: ("We talked about {word} after the game.", "比赛后我们谈到了{meaning}。"),
    10: ("I need {word} for this small repair.", "这次小修理我需要{meaning}。"),
    11: ("This design uses {word} in a simple way.", "这个设计简单地运用了{meaning}。"),
    12: ("I asked the doctor about {word} yesterday.", "我昨天向医生询问了{meaning}。"),
    13: ("You can find {word} near the city center.", "你可以在市中心附近找到{meaning}。"),
    14: ("We noticed {word} during our trip today.", "我们今天旅行时注意到了{meaning}。"),
    15: ("The news explained {word} in simple terms.", "新闻用简单的方式解释了{meaning}。"),
    16: ("We discussed {word} at work this morning.", "我们今天早上在工作中讨论了{meaning}。"),
    17: ("The officer explained {word} to us clearly.", "工作人员向我们清楚解释了{meaning}。"),
    18: ("The documentary showed the impact of {word}.", "纪录片展示了{meaning}带来的影响。"),
    19: ("I met someone working as {word} yesterday.", "我昨天遇到了一位从事{meaning}工作的人。"),
    20: ("It is useful to {word} when necessary.", "有需要时{meaning}很有用。"),
    21: ("I asked the doctor about {word} yesterday.", "我昨天向医生询问了{meaning}。"),
    22: ("We talked about {word} over lunch today.", "我们今天午餐时谈到了{meaning}。"),
}


def key(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower().strip()
    value = re.sub(r"[“”\"'()]", "", value)
    return re.sub(r"[_\s-]+", " ", value).strip()


def english_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*", text)


def target_forms(word: str) -> set[str]:
    normalized = key(word)
    forms = {normalized}
    if " " in normalized or len(normalized) < 3:
        return forms

    short_cvc = (
        len(normalized) == 3
        and normalized[0] not in "aeiou"
        and normalized[1] in "aeiou"
        and normalized[2] not in "aeiouwxy"
    )

    if normalized == "dye":
        forms.update({"dyes", "dyed", "dyeing"})
    elif short_cvc:
        forms.update({normalized + "s", normalized + normalized[-1] + "ed", normalized + normalized[-1] + "ing"})
    elif normalized.endswith("y") and normalized[-2] not in "aeiou":
        forms.update({normalized[:-1] + "ies", normalized[:-1] + "ied", normalized + "ing"})
    elif normalized.endswith(("s", "x", "z", "ch", "sh")):
        forms.update({normalized + "es", normalized + "ed", normalized + "ing"})
    elif normalized.endswith("e"):
        forms.update({normalized + "s", normalized + "d", normalized[:-1] + "ing"})
    else:
        forms.update({normalized + "s", normalized + "ed", normalized + "ing"})

    irregular = {
        "be": {"am", "is", "are", "was", "were", "been", "being"},
        "begin": {"began", "begun", "beginning"},
        "break": {"broke", "broken"},
        "build": {"built"},
        "buy": {"bought"},
        "catch": {"caught"},
        "choose": {"chose", "chosen"},
        "come": {"came"},
        "do": {"does", "did", "done", "doing"},
        "draw": {"drew", "drawn"},
        "drive": {"drove", "driven"},
        "eat": {"ate", "eaten"},
        "fall": {"fell", "fallen"},
        "feel": {"felt"},
        "find": {"found"},
        "fly": {"flew", "flown"},
        "get": {"got", "gotten"},
        "give": {"gave", "given"},
        "go": {"goes", "went", "gone", "going"},
        "grow": {"grew", "grown"},
        "have": {"has", "had", "having"},
        "hold": {"held"},
        "keep": {"kept"},
        "know": {"knew", "known"},
        "lead": {"led"},
        "leave": {"left"},
        "lose": {"lost"},
        "make": {"made"},
        "meet": {"met"},
        "pay": {"paid"},
        "read": {"read"},
        "run": {"ran", "running"},
        "say": {"said"},
        "see": {"saw", "seen"},
        "sell": {"sold"},
        "send": {"sent"},
        "speak": {"spoke", "spoken"},
        "spend": {"spent"},
        "stand": {"stood"},
        "take": {"took", "taken"},
        "teach": {"taught"},
        "tell": {"told"},
        "think": {"thought"},
        "write": {"wrote", "written"},
        "buffalo": {"buffaloes"},
        "person": {"people"},
        "potato": {"potatoes"},
        "tomato": {"tomatoes"},
        "wife": {"wives"},
    }
    forms.update(irregular.get(normalized, set()))
    return forms


def phrase_pattern(word: str) -> re.Pattern[str]:
    parts = re.findall(r"[a-z]+(?:'[a-z]+)?", key(word))
    return re.compile(r"(?<![A-Za-z])" + r"[ -]+".join(map(re.escape, parts)) + r"(?![A-Za-z])", re.I)


def parse_vocab() -> tuple[dict[str, dict[str, object]], dict[str, str]]:
    chapter = 0
    records: dict[str, dict[str, object]] = {}
    aliases: dict[str, str] = {}
    for line in VOCAB_FILE.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^#### Chapter-(\d+)\s+(.+)$", line)
        if heading:
            chapter = int(heading.group(1))
            continue
        match = re.match(r"^\*\*(.+?)\*\*\s*\((.+?)\)\s*·?$", line)
        if not match:
            continue
        display, definition = match.groups()
        canonical = key(display.split("/")[0])
        records[canonical] = {
            "display": display,
            "definition": definition,
            "chapter": chapter,
        }
        for part in re.split(r"[/／]", display):
            aliases[key(part)] = canonical
    return records, aliases


def clean_meaning(definition: str) -> str:
    value = re.sub(r"/[^/]+/", " ", definition)
    value = re.sub(r"^(?:(?:adj|adv|prep|conj|pron|det|num|abbr|n|v)\.?\s*(?:/|、|和)?\s*)+", "", value, flags=re.I)
    value = re.split(r"[；;]", value)[0]
    value = re.sub(r"\[[^]]+]", "", value)
    value = re.split(r"[/／]", value)[0]
    value = re.sub(r"^[A-Za-z-]+\s+", "", value)
    value = value.replace("...", "").replace("…", "")
    value = re.sub(r"[（）()]", "", value)
    value = re.sub(r"[、，,]+", "、", value)
    return value.strip(" 。；;，,、") or "这个词的含义"


def part_of_speech(definition: str) -> str:
    match = re.match(r"^\s*((?:(?:adj|adv|prep|conj|pron|det|num|abbr|n|v)\.?\s*(?:/|、|和)?\s*)+)", definition, re.I)
    if not match:
        return "noun"
    labels = re.findall(r"adj|adv|prep|conj|pron|det|num|abbr|n|v", match.group(1), re.I)
    first_label = labels[0].lower() if labels else "n"
    if first_label == "v":
        return "verb"
    if first_label == "adj":
        return "adjective"
    if first_label == "adv":
        return "adverb"
    return "noun"


def simplify_chinese_batch(items: list[dict[str, object]]) -> None:
    """Use macOS transliteration when available; keep generation portable elsewhere."""
    if sys.platform != "darwin" or not items:
        return
    script = r'''
ObjC.import("Foundation");
var data = $.NSFileHandle.fileHandleWithStandardInput.readDataToEndOfFile;
var source = $.NSString.alloc.initWithDataEncoding(data, $.NSUTF8StringEncoding);
var converted = source.stringByApplyingTransformReverse($("Traditional-Simplified"), false);
converted ? converted.js : source.js;
'''
    source = "\n".join(str(item.get("zh", "")).replace("\n", " ") for item in items)
    try:
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", script],
            input=source,
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return
    converted = result.stdout.rstrip("\n").splitlines()
    if len(converted) == len(items):
        for item, chinese in zip(items, converted):
            item["zh"] = chinese


PERSON_HINTS = re.compile(r"(?:人|者|员|家|师|官|生|徒|顾问|律师|主管|教授|乘务员)$")
BODY_HINTS = re.compile(r"(?:腹部|动脉|脊柱|关节|大腿|子宫|手腕|头骨|身高|器官|腺|肌肉|皮肤|牙|耳|眼|骨)")
CONDITION_HINTS = re.compile(r"(?:病|炎|痛|伤|症|中风|创伤|失眠|压力|过敏|感染|肥胖|焦虑)")
FOOD_HINTS = re.compile(r"(?:食物|食品|菜|餐|饮料|水果|蔬菜|葱|萝卜|山葵|茄子|奶|肉|茶|酒|甜点)")
PLACE_HINTS = re.compile(r"(?:馆|场|中心|食堂|餐厅|商店|医院|学校|车站|机场|工作室|别墅|赌场|桥|道路)$")


def chinese_score(text: str) -> tuple[int, int]:
    traditional = sum(character in TRADITIONAL_HINTS for character in text)
    return traditional, len(text)


def load_official_corpus() -> tuple[list[dict[str, str]], dict[str, list[int]]]:
    links: dict[int, list[int]] = defaultdict(list)
    with bz2.open(OFFICIAL_LINKS, "rt", encoding="utf-8") as stream:
        for line in stream:
            english_id, chinese_id = map(int, line.split())
            links[english_id].append(chinese_id)

    chinese: dict[int, tuple[str, str]] = {}
    linked_chinese = {sentence_id for sentence_ids in links.values() for sentence_id in sentence_ids}
    with bz2.open(OFFICIAL_CHINESE, "rt", encoding="utf-8") as stream:
        for line in stream:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4 or int(parts[0]) not in linked_chinese:
                continue
            chinese[int(parts[0])] = (parts[2].strip(), parts[3].strip())

    rows: list[dict[str, str]] = []
    index: dict[str, list[int]] = defaultdict(list)
    with bz2.open(OFFICIAL_ENGLISH, "rt", encoding="utf-8") as stream:
        for line in stream:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            sentence_id = int(parts[0])
            if sentence_id not in links:
                continue
            english = parts[2].strip()
            tokens = [token.lower() for token in english_words(english)]
            if not 3 <= len(tokens) <= 12 or re.search(r"https?://|[@#$%^*_{}<>]", english):
                continue
            translations = [
                (chinese_id, chinese[chinese_id])
                for chinese_id in links[sentence_id]
                if chinese_id in chinese and re.search(r"[\u3400-\u9fff]", chinese[chinese_id][0])
            ]
            if not translations:
                continue
            chinese_id, (chinese_text, chinese_user) = min(
                translations,
                key=lambda item: chinese_score(item[1][0]),
            )
            row_index = len(rows)
            rows.append({
                "en": english,
                "zh": chinese_text,
                "attribution": (
                    f"CC BY 2.0 FR: Tatoeba #{sentence_id} ({parts[3].strip() or 'unknown'}) "
                    f"& #{chinese_id} ({chinese_user or 'unknown'})"
                ),
            })
            for token in set(tokens):
                index[token].append(row_index)
    return rows, index


def load_corpus(path: Path) -> tuple[list[dict[str, str]], dict[str, list[int]]]:
    if OFFICIAL_ENGLISH.exists() and OFFICIAL_CHINESE.exists() and OFFICIAL_LINKS.exists():
        return load_official_corpus()
    if not path.exists():
        return [], {}
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            raw = archive.read("cmn.txt").decode("utf-8")
    else:
        raw = path.read_text(encoding="utf-8")

    rows: list[dict[str, str]] = []
    index: dict[str, list[int]] = defaultdict(list)
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        english, chinese, attribution = parts[:3]
        tokens = [token.lower() for token in english_words(english)]
        if not 3 <= len(tokens) <= 12 or not re.search(r"[\u3400-\u9fff]", chinese):
            continue
        if re.search(r"https?://|[@#$%^*_{}<>]", english + chinese):
            continue
        english, chinese = english.strip(), chinese.strip()
        row_index = len(rows)
        rows.append({"en": english, "zh": chinese, "attribution": attribution.strip()})
        for token in set(tokens):
            index[token].append(row_index)
    return rows, index


def corpus_candidates(word: str, rows: list[dict[str, str]], index: dict[str, list[int]]) -> list[dict[str, str]]:
    normalized = key(word)
    parts = normalized.split()
    candidate_ids: set[int] = set()
    if len(parts) > 1:
        candidate_ids.update(index.get(parts[0], []))
        pattern = phrase_pattern(normalized)
        return [rows[i] for i in candidate_ids if pattern.search(rows[i]["en"])]
    for form in target_forms(normalized):
        candidate_ids.update(index.get(form, []))
    return [rows[i] for i in candidate_ids]


def daily_utility_score(row: dict[str, str]) -> int:
    english = row["en"]
    count = len(english_words(english))
    score = abs(count - 8) * 5
    score += len(english) // 35
    score += 8 * len(re.findall(
        r"\b(?:Tom|Mary|John|Sami|Mennad|Layla|Bob|Bill|Donna|Martha|Boston|Japan|French|German|Germany|France|Algeria|Algerian|Berber|Moscow)\b",
        english,
    ))
    score += 12 * len(re.findall(r"[;:]", english))
    score += chinese_score(row["zh"])[0] * 4
    if re.search(r"\b(?:please|today|tomorrow|yesterday|work|home|school|shop|store|restaurant|hotel|train|bus|need|want|can|could|would|let's)\b", english, re.I):
        score -= 5
    if re.search(r"\b(?:thee|thou|thy|hath|unto|whomsoever)\b", english, re.I):
        score += 18
    if SHARED_SENTENCE_BLOCKLIST.search(english):
        score += 30
    return score


def corpus_score(row: dict[str, str], word: str) -> tuple[int, str]:
    english = row["en"]
    score = daily_utility_score(row)
    digest = hashlib.sha1((key(word) + "\0" + english).encode()).hexdigest()
    return score, digest


def sentence_has_target(sentence: str, target: str) -> bool:
    normalized = key(target)
    if " " in normalized:
        return bool(phrase_pattern(normalized).search(sentence))
    return bool(target_forms(normalized) & {word.lower() for word in english_words(sentence)})


def usage_id(english: str, chinese: str) -> str:
    digest = hashlib.sha1((english.strip() + "\0" + chinese.strip()).encode()).hexdigest()[:12]
    return f"usage-{digest}"


def choose_shared_rows(
    words: list[str],
    candidates_by_word: dict[str, list[dict[str, str]]],
) -> tuple[dict[str, dict[str, str]], dict[str, tuple[str, str]]]:
    curated_by_word: dict[str, tuple[str, str]] = {}
    for group, sentence in CURATED_SHARED.items():
        for word in group:
            curated_by_word[word] = sentence

    best_score = {
        word: min((daily_utility_score(row) for row in candidates_by_word.get(word, [])), default=10_000)
        for word in words
    }
    row_words: dict[tuple[str, str], set[str]] = defaultdict(set)
    row_lookup: dict[tuple[str, str], dict[str, str]] = {}
    for word in words:
        if word in curated_by_word or word in SHARED_EXCLUDED_WORDS:
            continue
        for row in candidates_by_word.get(word, []):
            if SHARED_SENTENCE_BLOCKLIST.search(row["en"]):
                continue
            if daily_utility_score(row) > best_score[word] + SHARED_QUALITY_TOLERANCE:
                continue
            row_key = (row["en"], row["zh"])
            row_words[row_key].add(word)
            row_lookup[row_key] = row

    proposals: list[tuple[tuple[int, int, int, str], tuple[str, str], tuple[str, ...]]] = []
    for row_key, matching_words in row_words.items():
        targets = sorted(word for word in matching_words if sentence_has_target(row_key[0], word))
        if len(targets) < 2:
            continue
        max_size = min(4, len(targets))
        for size in range(max_size, 1, -1):
            for group in itertools.combinations(targets, size):
                utility = daily_utility_score(row_lookup[row_key])
                quality_loss = sum(max(0, utility - best_score[word]) for word in group)
                # A natural daily sentence wins; group size only breaks close ties.
                priority = (utility, -size, quality_loss, row_key[0])
                proposals.append((priority, row_key, group))

    selected: dict[str, dict[str, str]] = {}
    used_words = set(curated_by_word)
    for _, row_key, group in sorted(proposals):
        if any(word in used_words for word in group):
            continue
        row = row_lookup[row_key]
        for word in group:
            selected[word] = row
        used_words.update(group)
    return selected, curated_by_word


def generated_example(word: str, record: dict[str, object]) -> tuple[str, str]:
    definition = str(record.get("definition", ""))
    meaning = clean_meaning(str(record.get("definition", "")))
    pos = part_of_speech(definition)
    sentence_word = word if any(character.isupper() for character in word[1:]) else word.lower()

    if BODY_HINTS.search(meaning):
        return (
            f"The doctor carefully examined my {sentence_word} during the checkup.",
            f"体检时，医生仔细检查了我的{meaning}。",
        )
    if CONDITION_HINTS.search(meaning):
        return (
            f"The doctor explained how {sentence_word} can affect daily life.",
            f"医生解释了{meaning}会怎样影响日常生活。",
        )
    if FOOD_HINTS.search(meaning):
        return (
            f"We added some {sentence_word} to tonight's dinner.",
            f"我们在今晚的晚餐中加了一些{meaning}。",
        )
    if PERSON_HINTS.search(meaning):
        return (
            f"I spoke with a {sentence_word} about the problem.",
            f"我和一位{meaning}讨论了这个问题。",
        )
    if PLACE_HINTS.search(meaning):
        return (
            f"We found the {sentence_word} near the city center.",
            f"我们在市中心附近找到了{meaning}。",
        )
    if pos == "verb":
        return (
            f"The example shows how people can {sentence_word} in practice.",
            f"这个例子说明人们在实际中如何{meaning}。",
        )
    if pos == "adjective":
        return (
            f"The result seemed {sentence_word} when we looked closer.",
            f"仔细观察后，这个结果显得{meaning}。",
        )
    if pos == "adverb":
        return (
            f"This example shows how to use {sentence_word} correctly.",
            f"这个例子说明如何正确使用“{meaning}”。",
        )
    return (
        f"We discussed {sentence_word} and its practical effects today.",
        f"我们今天讨论了{meaning}及其实际影响。",
    )


def load_existing() -> dict[str, dict[str, object]]:
    if not OUTPUT_FILE.exists():
        return {}
    existing = {}
    for line in OUTPUT_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        existing[key(str(item["key"]))] = item
    return existing


def load_guided_replacements() -> dict[str, dict[str, object]]:
    replacements: dict[str, dict[str, object]] = {}
    if not GUIDED_REPLACEMENTS_FILE.exists():
        return replacements
    for line_number, line in enumerate(
        GUIDED_REPLACEMENTS_FILE.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        item = json.loads(line)
        item_key = key(str(item.get("key", "")))
        if not item_key or item_key in replacements:
            raise ValueError(f"invalid guided replacement key on line {line_number}: {item_key}")
        replacements[item_key] = item
    return replacements


def load_shared_reuse(existing: dict[str, dict[str, object]]) -> dict[str, str]:
    reuse: dict[str, str] = {}
    if not SHARED_REUSE_FILE.exists():
        return reuse
    for line_number, line in enumerate(
        SHARED_REUSE_FILE.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        item = json.loads(line)
        item_key = key(str(item.get("key", "")))
        anchor_key = key(str(item.get("reuse", "")))
        if not item_key or not anchor_key or item_key == anchor_key or item_key in reuse:
            raise ValueError(f"invalid shared example reuse on line {line_number}")
        if item_key not in existing or anchor_key not in existing:
            raise ValueError(
                f"shared example reuse requires existing entries on line {line_number}: "
                f"{item_key} -> {anchor_key}"
            )
        reuse[item_key] = anchor_key
    chained = sorted(set(reuse) & set(reuse.values()))
    if chained:
        raise ValueError(f"shared example reuse cannot be chained: {', '.join(chained)}")
    return reuse


def build(corpus: Path, preserve_existing: bool) -> list[dict[str, object]]:
    vocab, aliases = parse_vocab()
    rows, index = load_corpus(corpus)
    reuse_source = load_existing()
    existing = reuse_source if preserve_existing else {}
    guided_replacements = load_guided_replacements()
    shared_reuse = load_shared_reuse(reuse_source)
    output: list[dict[str, object]] = []

    image_records: list[tuple[str, Path, dict[str, object]]] = []
    seen_keys: set[str] = set()
    for image in sorted(IMAGE_DIR.glob("*.jpg"), key=lambda path: (key(path.stem), path.name)):
        image_key = key(image.stem)
        if image_key in seen_keys:
            continue
        seen_keys.add(image_key)
        mapped_key = aliases.get(image_key) or aliases.get(SPECIAL_KEYS.get(image_key, "")) or image_key
        record = vocab.get(mapped_key, {"definition": "", "chapter": 0, "display": image.stem})
        image_records.append((image_key, image, record))

    candidates_by_word = {
        image_key: corpus_candidates(image_key, rows, index)
        for image_key, _, _ in image_records
        if image_key not in MANUAL
    }
    shared_rows, curated_shared = choose_shared_rows(
        [image_key for image_key, _, _ in image_records],
        candidates_by_word,
    )

    for image_key, image, record in image_records:
        if image_key in shared_reuse:
            anchor = reuse_source[shared_reuse[image_key]]
            item = {
                "key": image_key,
                "word": image.stem,
                "en": str(anchor["en"]),
                "zh": str(anchor["zh"]),
                "source": str(anchor.get("source", "curated")),
                "usage_id": usage_id(str(anchor["en"]), str(anchor["zh"])),
            }
            if anchor.get("attribution"):
                item["attribution"] = str(anchor["attribution"])
            output.append(item)
            continue
        if image_key in existing and image_key not in guided_replacements:
            output.append(existing[image_key])
            continue

        if image_key in curated_shared:
            english, chinese = curated_shared[image_key]
            source = "curated"
            attribution = ""
        elif image_key in MANUAL:
            english, chinese = MANUAL[image_key]
            source = "curated"
            attribution = ""
        elif image_key in guided_replacements:
            replacement = guided_replacements[image_key]
            english = str(replacement["en"])
            chinese = str(replacement["zh"])
            source = str(replacement.get("source", "curated"))
            attribution = str(replacement.get("attribution", ""))
        else:
            candidates = candidates_by_word.get(image_key, [])
            selected = shared_rows.get(image_key)
            if selected or candidates:
                selected = selected or min(candidates, key=lambda row: corpus_score(row, image_key))
                english, chinese = selected["en"], selected["zh"]
                source = "tatoeba"
                attribution = selected["attribution"]
            else:
                english, chinese = generated_example(image.stem, record)
                source = "guided"
                attribution = ""

        item: dict[str, object] = {
            "key": image_key,
            "word": image.stem,
            "en": english,
            "zh": chinese,
            "source": source,
            "usage_id": usage_id(english, chinese),
        }
        if attribution:
            item["attribution"] = attribution
        output.append(item)
    for item in output:
        item["zh"] = re.sub(r"\s*[/／]+\s*", "或", str(item.get("zh", "")))
    simplify_chinese_batch(output)

    usage_groups: dict[str, list[str]] = defaultdict(list)
    for item in output:
        item["usage_id"] = usage_id(str(item["en"]), str(item["zh"]))
        usage_groups[str(item["usage_id"])].append(str(item["key"]))
    for item in output:
        related = [word for word in usage_groups[str(item["usage_id"])] if word != item["key"]]
        if related:
            item["shared_with"] = related
        else:
            item.pop("shared_with", None)
    return output


def validate(items: list[dict[str, object]]) -> list[str]:
    errors: list[str] = []
    image_keys = {key(path.stem) for path in IMAGE_DIR.glob("*.jpg")}
    item_keys = [key(str(item.get("key", ""))) for item in items]
    counts = Counter(item_keys)
    item_by_key = {
        key(str(item.get("key", ""))): item
        for item in items
    }
    shared_reuse = load_shared_reuse(item_by_key)

    for duplicate, count in counts.items():
        if count > 1:
            errors.append(f"duplicate key: {duplicate} ({count})")
    for missing in sorted(image_keys - set(item_keys)):
        errors.append(f"missing image word: {missing}")
    for extra in sorted(set(item_keys) - image_keys):
        errors.append(f"unknown image word: {extra}")

    sentence_counts = Counter(str(item.get("en", "")) for item in items)
    usage_groups: dict[str, list[str]] = defaultdict(list)
    for item in items:
        english = str(item.get("en", "")).strip()
        chinese = str(item.get("zh", "")).strip()
        actual_usage_id = str(item.get("usage_id", ""))
        expected_usage_id = usage_id(english, chinese)
        if actual_usage_id != expected_usage_id:
            errors.append(f"invalid usage id: {item.get('key', '')}: {actual_usage_id}")
        usage_groups[expected_usage_id].append(key(str(item.get("key", ""))))

    for item in items:
        item_key = key(str(item.get("key", "")))
        english = str(item.get("en", "")).strip()
        chinese = str(item.get("zh", "")).strip()
        word_count = len(english_words(english))
        if not 3 <= word_count <= 12:
            errors.append(f"word count {word_count}: {item_key}: {english}")
        if english.lower().startswith("a useful example is:"):
            errors.append(f"example prefix: {item_key}: {english}")
        if chinese.startswith("一个实用例子是："):
            errors.append(f"Chinese example prefix: {item_key}: {chinese}")
        if " " in item_key:
            contains_target = bool(phrase_pattern(item_key).search(english))
        else:
            contains_target = bool(target_forms(item_key) & {word.lower() for word in english_words(english)})
        if not contains_target:
            errors.append(f"target missing: {item_key}: {english}")
        if not re.search(r"[\u3400-\u9fff]", chinese):
            errors.append(f"missing Chinese: {item_key}")
        if re.search(r"[/／]", chinese):
            errors.append(f"spoken slash: {item_key}: {chinese}")
        if sentence_counts[english] > 30:
            errors.append(f"overused sentence ({sentence_counts[english]}): {english}")
        group = usage_groups[usage_id(english, chinese)]
        expected_shared = sorted(word for word in group if word != item_key)
        actual_shared = sorted(key(str(word)) for word in item.get("shared_with", []))
        if actual_shared != expected_shared:
            errors.append(
                f"invalid shared words: {item_key}: expected {expected_shared}, got {actual_shared}"
            )

    for group, (english, chinese) in CURATED_SHARED.items():
        expected_id = usage_id(english, chinese)
        for word in group:
            matches = [item for item in items if key(str(item.get("key", ""))) == word]
            if not matches or str(matches[0].get("usage_id", "")) != expected_id:
                errors.append(f"curated shared regression: {word}")

    for replacement_key, replacement in load_guided_replacements().items():
        if replacement_key in shared_reuse:
            continue
        item = item_by_key.get(replacement_key)
        if not item:
            errors.append(f"guided replacement missing: {replacement_key}")
            continue
        if str(item.get("en", "")) != str(replacement.get("en", "")):
            errors.append(f"guided replacement English mismatch: {replacement_key}")
        if str(item.get("zh", "")) != str(replacement.get("zh", "")):
            errors.append(f"guided replacement Chinese mismatch: {replacement_key}")

    for item_key, anchor_key in shared_reuse.items():
        item = item_by_key[item_key]
        anchor = item_by_key[anchor_key]
        for field in ("en", "zh", "source", "attribution"):
            if str(item.get(field, "")) != str(anchor.get(field, "")):
                errors.append(f"shared example {field} mismatch: {item_key} -> {anchor_key}")
    return errors


def write(items: list[dict[str, object]]) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n" for item in items)
    OUTPUT_FILE.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "validate", "report"))
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--refresh", action="store_true", help="regenerate existing records")
    args = parser.parse_args()

    if args.command == "build":
        items = build(args.corpus, preserve_existing=not args.refresh)
        errors = validate(items)
        write(items)
        print(f"Wrote {len(items)} records to {OUTPUT_FILE}")
    else:
        items = list(load_existing().values())
        errors = validate(items)

    sources = Counter(str(item.get("source", "unknown")) for item in items)
    print("Sources:", ", ".join(f"{name}={count}" for name, count in sorted(sources.items())))
    print(f"Validation: {len(errors)} issue(s)")
    for error in errors[:100]:
        print("-", error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
