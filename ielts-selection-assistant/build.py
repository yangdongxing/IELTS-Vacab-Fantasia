#!/usr/bin/env python3
"""
Builder script for IELTS Selection Assistant (雅思真经划词划划看)
Customized Memory Modal Overlay:
1. Right-side context paragraph removed.
2. Input answer box strictly verifies the word in #geek-memory-word only.
3. Upon typing success: plays green correct animation + pronunciation, and automatically closes the memory card modal after ~550ms!
"""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET_DIR = Path(__file__).resolve().parent
DATA_DIR = TARGET_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 1. Parse vocabulary-list.md
vocab_file = ROOT / "content" / "ielts" / "vocabulary-list.md"
vocab_map = {}
if vocab_file.exists():
    vtext = vocab_file.read_text(encoding="utf-8")
    current_chapter = "General"
    for line in vtext.splitlines():
        if line.startswith("#### "):
            current_chapter = line.replace("#### ", "").strip()
        m = re.search(r"\*\*([^*]+)\*\*\s*\(([^)]+)\)", line)
        if m:
            raw_word = m.group(1).strip()
            raw_def = m.group(2).strip()
            parts = [p.strip() for p in raw_word.split("/") if p.strip()]
            canonical = parts[0]
            entry = {
                "word": canonical,
                "def": raw_def,
                "chapter": current_chapter
            }
            if len(parts) > 1:
                entry["aliases"] = parts[1:]
            vocab_map[canonical.lower()] = entry

# 2. Parse spoken-usage.jsonl
spoken_file = ROOT / "data" / "spoken-usage.jsonl"
spoken_map = {}
if spoken_file.exists():
    for line in spoken_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            k = str(item.get("key", "")).strip().lower()
            spoken_map[k] = {
                "en": item.get("en", "").strip(),
                "zh": item.get("zh", "").strip(),
                "focus": item.get("focus", "").strip()
            }
        except Exception:
            pass

# 3. Check existing images
images_dir = ROOT / "assets" / "images"
image_words = set()
if images_dir.exists():
    for p in images_dir.glob("*.jpg"):
        image_words.add(p.stem.lower())

unified_dict = {}
for k, v in vocab_map.items():
    canon_word = v["word"]
    has_img = canon_word.lower() in image_words or k in image_words
    sp = spoken_map.get(k) or spoken_map.get(canon_word.lower())
    
    unified_dict[k] = {
        "w": canon_word,
        "d": v["def"],
        "img": 1 if has_img else 0
    }
    if sp and sp.get("en") and sp.get("zh"):
        unified_dict[k]["sp"] = sp

dict_json_str = json.dumps(unified_dict, ensure_ascii=False, separators=(',', ':'))
dict_json_path = DATA_DIR / "dictionary.json"
dict_json_path.write_text(dict_json_str, encoding="utf-8")
print(f"Generated {dict_json_path} with {len(unified_dict)} words.")

CDN_IMAGE_BASE = "https://raw.githubusercontent.com/yangdongxing/IELTS-Vacab-Fantasia/main/assets/images/"

# Core JavaScript code with placeholders
js_template = """/**
 * IELTS Selection Assistant (雅思真经划词划划看)
 * Optimized Memory Modal:
 * - Clean modal without side context
 * - Input validates exact word in #geek-memory-word
 * - Automatic modal closure upon correct spelling
 */
(function() {
    "use strict";

    const DICTIONARY = __DICTIONARY_JSON__;
    const CDN_IMAGE_BASE = "__CDN_IMAGE_BASE__";
    const EDGE_PADDING = 12;

    // Irregular inflections mapping
    const IRREGULAR_LEMMAS = {
        was: "be", were: "be", been: "be",
        went: "go", gone: "go",
        saw: "see", seen: "see",
        took: "take", taken: "take",
        wrote: "write", written: "write",
        spoke: "speak", spoken: "speak",
        lost: "lose",
        began: "begin", begun: "begin",
        felt: "feel",
        found: "find",
        gave: "give", given: "give",
        ran: "run",
        swam: "swim", swum: "swim",
        flew: "fly", flown: "fly",
        built: "build",
        taught: "teach",
        thought: "think",
        bought: "buy",
        caught: "catch",
        drew: "draw", drawn: "draw",
        drove: "drive", driven: "drive",
        ate: "eat", eaten: "eat",
        fell: "fall", fallen: "fall",
        froze: "freeze", frozen: "freeze",
        grew: "grow", grown: "grow",
        held: "hold",
        hid: "hide", hidden: "hide",
        knew: "know", known: "know",
        laid: "lay", lain: "lie",
        led: "lead",
        left: "leave",
        made: "make",
        meant: "mean",
        met: "meet",
        paid: "pay",
        rode: "ride", ridden: "ride",
        rose: "rise", risen: "rise",
        said: "say",
        sold: "sell",
        sent: "send",
        shook: "shake", shaken: "shake",
        shone: "shine",
        shot: "shoot",
        showed: "show", shown: "show",
        shut: "shut",
        slept: "sleep",
        slid: "slide",
        spent: "spend",
        stood: "stand",
        stole: "steal", stolen: "steal",
        struck: "strike", stricken: "strike",
        swept: "sweep",
        swung: "swing",
        told: "tell",
        threw: "throw", thrown: "throw",
        understood: "understand",
        woke: "wake", woken: "wake",
        wore: "wear", worn: "wear",
        won: "win",
        wound: "wind",
        children: "child",
        men: "man",
        women: "woman",
        feet: "foot",
        teeth: "tooth",
        geese: "goose",
        mice: "mouse",
        criteria: "criterion",
        phenomena: "phenomenon"
    };

    const SKIP_WORDS = new Set([
        "the", "a", "an", "is", "am", "are", "was", "were", "be", "been", "being",
        "he", "she", "it", "they", "we", "you", "i", "me", "him", "her", "them", "us",
        "and", "or", "but", "if", "so", "as", "to", "in", "on", "at", "by", "for", "of", "with",
        "this", "that", "these", "those", "who", "which", "what", "where", "when", "why", "how",
        "not", "no", "yes", "can", "could", "will", "would", "shall", "should", "may", "might", "must"
    ]);

    function getWordLemmas(value) {
        const lemmas = new Set();
        if (!value) return lemmas;
        const lower = value.toLowerCase().replace(/[^a-z]/g, "");
        if (!lower || lower.length < 2) return lemmas;

        if (IRREGULAR_LEMMAS[lower]) {
            lemmas.add(IRREGULAR_LEMMAS[lower]);
        }

        // -ies -> -y
        if (lower.endsWith("ies") && lower.length > 4) {
            lemmas.add(lower.slice(0, -3) + "y");
        } else if (lower.endsWith("es") && lower.length > 3) {
            lemmas.add(lower.slice(0, -2));
            lemmas.add(lower.slice(0, -1));
        } else if (lower.endsWith("s") && !lower.endsWith("ss") && lower.length > 2) {
            lemmas.add(lower.slice(0, -1));
        }

        // -ied -> -y
        if (lower.endsWith("ied") && lower.length > 4) {
            lemmas.add(lower.slice(0, -3) + "y");
        } else if (lower.endsWith("ed") && lower.length > 3) {
            lemmas.add(lower.slice(0, -2));
            lemmas.add(lower.slice(0, -1));
            if (lower.length > 4 && lower[lower.length - 3] === lower[lower.length - 4]) {
                lemmas.add(lower.slice(0, -3));
            }
        }

        // -ing
        if (lower.endsWith("ying") && lower.length > 4) {
            lemmas.add(lower.slice(0, -4) + "ie");
        } else if (lower.endsWith("ing") && lower.length > 4) {
            lemmas.add(lower.slice(0, -3));
            lemmas.add(lower.slice(0, -3) + "e");
            if (lower.length > 5 && lower[lower.length - 4] === lower[lower.length - 5]) {
                lemmas.add(lower.slice(0, -4));
            }
            if (lower.endsWith("lling") && lower.length > 5) {
                lemmas.add(lower.slice(0, -5) + "l");
            }
        }

        // -ly / -ily
        if (lower.endsWith("ily") && lower.length > 4) {
            lemmas.add(lower.slice(0, -3) + "y");
        } else if (lower.endsWith("ly") && lower.length > 4) {
            lemmas.add(lower.slice(0, -2));
        }

        return lemmas;
    }

    function lookupWord(token) {
        if (!token) return null;
        const clean = token.toLowerCase().trim();
        if (SKIP_WORDS.has(clean)) return null;

        if (DICTIONARY[clean]) return DICTIONARY[clean];

        const candidates = getWordLemmas(clean);
        for (const cand of candidates) {
            if (DICTIONARY[cand] && !SKIP_WORDS.has(cand)) {
                return DICTIONARY[cand];
            }
        }
        return null;
    }

    function speakText(text) {
        if (!window.speechSynthesis || !text) return;
        window.speechSynthesis.cancel();
        const utter = new SpeechSynthesisUtterance(text);
        utter.lang = "en-US";
        utter.rate = 0.92;
        window.speechSynthesis.speak(utter);
    }

    const LOCAL_IMAGE_BASE = "http://127.0.0.1:8777/";
    const REMOTE_IMAGE_BASE = "__CDN_IMAGE_BASE__";

    function getImageUrl(word) {
        if (!word) return "";
        const capWord = word.charAt(0).toUpperCase() + word.slice(1);
        return LOCAL_IMAGE_BASE + encodeURIComponent(capWord) + ".jpg";
    }

    function setupImageFallback(imgElement, word) {
        if (!imgElement || !word) return;
        imgElement.onerror = function() {
            if (imgElement.src.startsWith(LOCAL_IMAGE_BASE)) {
                // If local server is not running, fallback to remote GitHub CDN
                const capWord = word.charAt(0).toUpperCase() + word.slice(1);
                imgElement.src = REMOTE_IMAGE_BASE + encodeURIComponent(capWord) + ".jpg";
                imgElement.onerror = function() {
                    imgElement.style.display = "none";
                };
            } else {
                imgElement.style.display = "none";
            }
        };
    }

    function answerKey(value) {
        return (value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
    }

    function isElementBold(element) {
        if (!element) return false;
        if (element.closest("b, strong, h1, h2, h3, h4, h5, h6, th")) return true;
        try {
            const computed = window.getComputedStyle(element);
            const weight = parseInt(computed.fontWeight, 10);
            if (!isNaN(weight) && weight >= 600) return true;
            if (computed.fontWeight === "bold" || computed.fontWeight === "bolder") return true;
        } catch (e) {}
        return false;
    }

    // ==========================================
    // Exact Project CSS Injection
    // ==========================================
    function injectProjectStyles() {
        if (document.getElementById("isa-exact-project-styles")) return;
        const style = document.createElement("style");
        style.id = "isa-exact-project-styles";
        style.textContent = `
            strong.geek-vocab-mark, em.geek-vocab-mark {
                position: relative !important;
                display: inline-block !important;
                color: inherit !important;
                font-weight: 700 !important;
                text-decoration: underline wavy currentColor !important;
                text-underline-offset: 4px !important;
                cursor: grab !important;
            }
            strong.geek-vocab-mark:active, em.geek-vocab-mark:active {
                cursor: grabbing !important;
            }

            .translation-bubble {
                position: absolute !important;
                bottom: 125% !important;
                left: 50% !important;
                transform: translateX(-50%) scale(0.8) !important;
                background-color: #e74c3c !important;
                color: #ffffff !important;
                padding: 6px 12px !important;
                border-radius: 6px !important;
                font-size: 14px !important;
                font-weight: normal !important;
                font-style: normal !important;
                white-space: nowrap !important;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
                opacity: 0 !important;
                pointer-events: none !important;
                transition: opacity 0.2s ease, transform 0.2s ease !important;
                z-index: 99999 !important;
            }
            .translation-bubble::after {
                content: "" !important;
                position: absolute !important;
                top: 100% !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                border-width: 6px !important;
                border-style: solid !important;
                border-color: #e74c3c transparent transparent transparent !important;
            }

            .translation-bubble.geek-has-word-image {
                background-color: #172033 !important;
                bottom: calc(100% + 8px) !important;
                left: 50% !important;
                top: auto !important;
                width: 240px !important;
                max-width: min(240px, calc(100vw - 32px)) !important;
                padding: 8px !important;
                white-space: normal !important;
                text-align: left !important;
                box-sizing: border-box !important;
                transform-origin: 50% 100% !important;
                pointer-events: none !important;
                border-radius: 8px !important;
            }
            .translation-bubble.geek-has-word-image::after {
                border-color: #172033 transparent transparent transparent !important;
            }
            .translation-bubble.geek-has-word-image.geek-bubble-below {
                top: calc(100% + 8px) !important;
                bottom: auto !important;
                transform-origin: 50% 0 !important;
            }
            .translation-bubble.geek-has-word-image.geek-bubble-below::after {
                top: auto !important;
                bottom: 100% !important;
                border-color: transparent transparent #172033 transparent !important;
            }

            @media (hover: hover) {
                strong.geek-vocab-mark:hover .translation-bubble,
                em.geek-vocab-mark:hover .translation-bubble {
                    opacity: 1 !important;
                    transform: translateX(-50%) scale(1) !important;
                    background-color: #e74c3c !important;
                }
                strong.geek-vocab-mark:hover .translation-bubble.geek-has-word-image,
                em.geek-vocab-mark:hover .translation-bubble.geek-has-word-image {
                    opacity: 1 !important;
                    transform: translateX(-50%) scale(1) !important;
                    background-color: #172033 !important;
                    pointer-events: auto !important;
                }
                strong.geek-vocab-mark:hover .translation-bubble.geek-has-word-image .geek-bubble-image,
                em.geek-vocab-mark:hover .translation-bubble.geek-has-word-image .geek-bubble-image {
                    pointer-events: auto !important;
                }
            }

            .geek-bubble-image {
                display: block !important;
                width: 100% !important;
                aspect-ratio: 1 / 1 !important;
                object-fit: cover !important;
                border-radius: 5px !important;
                background: rgba(255,255,255,0.14) !important;
                margin: 0 0 7px !important;
                box-shadow: inset 0 0 0 1px rgba(255,255,255,0.16) !important;
                cursor: zoom-in !important;
                pointer-events: none !important;
                transition: transform 0.15s ease, filter 0.15s ease !important;
            }
            .geek-bubble-image:hover {
                transform: scale(1.02) !important;
                filter: brightness(1.08) !important;
            }

            .geek-bubble-text {
                display: block !important;
                color: #fff !important;
                font-size: 13px !important;
                line-height: 1.35 !important;
                text-align: center !important;
                overflow-wrap: anywhere !important;
            }

            /* Floating Trigger Button */
            .isa-trigger-btn {
                position: fixed !important;
                background: #e11d48 !important;
                color: #fff !important;
                border-radius: 20px !important;
                padding: 6px 12px !important;
                box-shadow: 0 4px 18px rgba(225, 29, 72, 0.45), 0 2px 6px rgba(0, 0, 0, 0.15) !important;
                display: flex !important;
                align-items: center !important;
                gap: 6px !important;
                cursor: pointer !important;
                pointer-events: auto !important;
                transition: transform 0.15s ease, background 0.15s ease, box-shadow 0.15s ease !important;
                z-index: 100000 !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
                font-size: 13px !important;
                font-weight: 600 !important;
                border: 2px solid rgba(255, 255, 255, 0.9) !important;
                user-select: none !important;
                -webkit-user-select: none !important;
                animation: isaPop 0.15s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
            }
            .isa-trigger-btn:hover {
                transform: translateY(-2px) scale(1.04) !important;
                background: #be123c !important;
                box-shadow: 0 6px 22px rgba(225, 29, 72, 0.6) !important;
            }
            .isa-trigger-btn svg {
                width: 15px !important;
                height: 15px !important;
                fill: none !important;
                stroke: currentColor !important;
                stroke-width: 2.2 !important;
            }

            @keyframes isaPop {
                from { opacity: 0; transform: scale(0.7); }
                to { opacity: 1; transform: scale(1); }
            }

            /* Fullscreen Memory Modal Overlay Container */
            #geek-memory-modal {
                position: fixed !important;
                inset: 0 !important;
                display: none !important;
                align-items: center !important;
                justify-content: center !important;
                padding: 24px !important;
                background: rgba(2, 6, 23, 0.76) !important;
                backdrop-filter: blur(4px) !important;
                -webkit-backdrop-filter: blur(4px) !important;
                z-index: 100001 !important;
                box-sizing: border-box !important;
                pointer-events: auto !important;
            }
            #geek-memory-modal.open {
                display: flex !important;
            }
        `;
        document.head.appendChild(style);
    }
    injectProjectStyles();

    // ==========================================
    // Bubble Auto-Placement Logic (geek-bubble-below)
    // ==========================================
    function placeBubble(bubble) {
        if (!bubble || !bubble.classList.contains("geek-has-word-image")) return;
        const wordElement = bubble.parentElement;
        if (!wordElement) return;

        const bubbleRect = bubble.getBoundingClientRect();
        const wordRect = wordElement.getBoundingClientRect();
        const bubbleHeight = bubbleRect.height || 260;
        const gap = Math.max(8, wordRect.height * 0.25);
        const aboveTop = wordRect.top - gap - bubbleHeight;
        const belowBottom = wordRect.bottom + gap + bubbleHeight;
        const aboveIsClipped = aboveTop < EDGE_PADDING;
        const belowHasMoreRoom = window.innerHeight - wordRect.bottom > wordRect.top;
        const belowFits = belowBottom <= window.innerHeight - EDGE_PADDING;
        const shouldShowBelow = aboveIsClipped && (belowFits || belowHasMoreRoom);

        if (shouldShowBelow) {
            bubble.classList.add("geek-bubble-below");
        } else {
            bubble.classList.remove("geek-bubble-below");
        }
    }

    // ==========================================
    // Authentic Full Memory Modal Implementation
    // ==========================================
    let memoryModalRefs = null;
    let currentMemoryData = null;
    let autoCloseTimer = null;

    function createMemoryModal() {
        if (memoryModalRefs) return memoryModalRefs;

        const modal = document.createElement("div");
        modal.id = "geek-memory-modal";
        const shadow = modal.attachShadow({ mode: "open" });
        shadow.innerHTML = `
            <style>
                :host {
                    display: block;
                    width: 100%;
                    height: 100%;
                    pointer-events: auto;
                }
                .geek-memory-shell {
                    width: 100%;
                    height: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    position: relative;
                    box-sizing: border-box;
                }
                .geek-memory-card {
                    width: min(500px, calc(100vw - 48px));
                    height: min(740px, calc(100dvh - 48px));
                    max-height: calc(100vh - 48px);
                    display: grid;
                    grid-template-rows: auto minmax(80px, 1fr) auto auto auto;
                    overflow: hidden;
                    background: #111827;
                    color: #fff;
                    border: 1px solid rgba(255,255,255,0.16);
                    border-radius: 10px;
                    box-shadow: 0 24px 72px rgba(0,0,0,0.48);
                    padding: 16px;
                    box-sizing: border-box;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    pointer-events: auto;
                    user-select: text;
                    -webkit-user-select: text;
                    position: relative;
                }
                .geek-memory-word {
                    --geek-memory-word-drop: 0px;
                    margin: 0 0 14px;
                    color: #7dd3fc;
                    font-size: clamp(34px, 6vw, 56px);
                    line-height: 1.2;
                    font-weight: 800;
                    text-align: center;
                    overflow-wrap: anywhere;
                    position: relative;
                    z-index: 2;
                    transform: translate3d(0, 0, 0) scale(1);
                    backface-visibility: hidden;
                    transition:
                        transform 1080ms cubic-bezier(0.16, 1, 0.3, 1),
                        color 420ms ease-out,
                        text-shadow 420ms ease-out;
                    will-change: transform;
                    cursor: pointer;
                }
                .geek-memory-word.is-memorized {
                    color: #34d399;
                    text-shadow: 0 0 18px rgba(52, 211, 153, 0.38);
                    transform: translate3d(0, var(--geek-memory-word-drop), 0) scale(1.14);
                }
                .geek-memory-image {
                    display: block;
                    width: 100%;
                    height: 100%;
                    min-height: 0;
                    object-fit: cover;
                    border-radius: 8px;
                    background: rgba(255,255,255,0.06);
                    opacity: 1;
                    transition: opacity 480ms cubic-bezier(0.4, 0, 0.2, 1);
                    will-change: opacity;
                }
                .geek-memory-image.is-missing {
                    background: #991f2b;
                }
                .geek-memory-card.is-memorizing .geek-memory-image {
                    transition: opacity 820ms cubic-bezier(0.16, 1, 0.3, 1);
                    opacity: 0;
                }
                .geek-memory-translation {
                    margin: 12px 0 0;
                    color: rgba(255,255,255,0.86);
                    font-size: 18px;
                    line-height: 1.5;
                    text-align: center;
                    overflow-wrap: anywhere;
                }
                .geek-memory-example {
                    margin: 12px 0 0;
                    padding: 12px 0 0;
                    border-top: 1px solid rgba(255,255,255,0.12);
                    text-align: center;
                }
                .geek-memory-example[hidden] {
                    display: none;
                }
                .geek-memory-example-en {
                    margin: 0;
                    color: #f8fafc;
                    font-size: 17px;
                    font-weight: 650;
                    line-height: 1.45;
                    cursor: pointer;
                    overflow-wrap: anywhere;
                }
                .geek-memory-example-en:hover {
                    color: #7dd3fc;
                }
                .geek-memory-example-en strong {
                    color: #fde68a;
                    font-weight: 850;
                }
                .geek-memory-example-zh {
                    margin: 5px 0 0;
                    color: rgba(226,232,240,0.7);
                    font-size: 14px;
                    line-height: 1.45;
                    overflow-wrap: anywhere;
                }
                .geek-memory-answer {
                    width: 100%;
                    height: 48px;
                    min-width: 0;
                    margin: 16px 0 0;
                    padding: 0 14px;
                    border-radius: 8px;
                    border: 1px solid rgba(255,255,255,0.18);
                    background: rgba(255,255,255,0.08);
                    color: #fff;
                    box-sizing: border-box;
                    font: 18px/48px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    text-align: center;
                    outline: none;
                    text-transform: none;
                    caret-color: #7dd3fc;
                    pointer-events: auto;
                    user-select: text;
                    -webkit-user-select: text;
                }
                .geek-memory-answer::placeholder {
                    color: rgba(255,255,255,0.36);
                }
                .geek-memory-answer:focus {
                    border-color: #7dd3fc;
                    box-shadow: 0 0 0 3px rgba(125, 211, 252, 0.16);
                }
                .geek-memory-answer.is-wrong {
                    border-color: #fb7185;
                    box-shadow: 0 0 0 3px rgba(251, 113, 133, 0.16);
                }
                .geek-memory-answer.is-correct {
                    border-color: #34d399;
                    box-shadow: 0 0 0 3px rgba(52, 211, 153, 0.18);
                }
            </style>
            <div class="geek-memory-shell">
              <div class="geek-memory-card" role="dialog" aria-modal="true">
                <h2 class="geek-memory-word" id="geek-memory-word" title="点击朗读单词"></h2>
                <img class="geek-memory-image" id="geek-memory-image" alt="" draggable="false">
                <p class="geek-memory-translation" id="geek-memory-translation"></p>
                <div class="geek-memory-example" id="geek-memory-example" hidden>
                  <p class="geek-memory-example-en" id="geek-memory-example-en" title="点击朗读例句"></p>
                  <p class="geek-memory-example-zh" id="geek-memory-example-zh"></p>
                </div>
                <input class="geek-memory-answer" id="geek-memory-answer" type="text" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="请输入上方单词进行记忆校验">
              </div>
            </div>
        `;

        const shell = shadow.querySelector(".geek-memory-shell");
        const card = shadow.querySelector(".geek-memory-card");
        const answer = shadow.getElementById("geek-memory-answer");

        memoryModalRefs = {
            modal,
            card,
            word: shadow.getElementById("geek-memory-word"),
            image: shadow.getElementById("geek-memory-image"),
            translation: shadow.getElementById("geek-memory-translation"),
            example: shadow.getElementById("geek-memory-example"),
            exampleEnglish: shadow.getElementById("geek-memory-example-en"),
            exampleChinese: shadow.getElementById("geek-memory-example-zh"),
            answer,
        };

        shell.addEventListener("click", event => {
            if (event.target === shell) closeMemoryModal();
        });
        card.addEventListener("click", event => {
            if (event.target === card) requestAnimationFrame(focusMemoryAnswer);
        });

        memoryModalRefs.word.addEventListener("click", () => {
            if (currentMemoryData) {
                speakText(currentMemoryData.w);
            }
            requestAnimationFrame(focusMemoryAnswer);
        });

        memoryModalRefs.exampleEnglish.addEventListener("click", () => {
            if (currentMemoryData && currentMemoryData.sp && currentMemoryData.sp.en) {
                speakText(currentMemoryData.sp.en);
            }
            requestAnimationFrame(focusMemoryAnswer);
        });

        answer.addEventListener("input", handleAnswerInput);
        answer.addEventListener("keydown", event => {
            if (event.key === "Escape") {
                event.preventDefault();
                closeMemoryModal();
            }
        });

        document.body.appendChild(modal);
        return memoryModalRefs;
    }

    function isMemoryModalOpen() {
        const modal = document.getElementById("geek-memory-modal");
        return !!modal && modal.classList.contains("open");
    }

    function focusMemoryAnswer() {
        const answer = memoryModalRefs && memoryModalRefs.answer;
        if (!answer || !isMemoryModalOpen()) return;
        requestAnimationFrame(() => {
            if (isMemoryModalOpen()) {
                answer.focus({ preventScroll: true });
                answer.setSelectionRange(answer.value.length, answer.value.length);
            }
        });
    }

    function resetMemoryAnimation() {
        if (!memoryModalRefs) return;
        const { card, word } = memoryModalRefs;
        if (card) card.classList.remove("is-memorizing");
        if (word) {
            word.classList.remove("is-memorized");
            word.style.removeProperty("--geek-memory-word-drop");
        }
    }

    function playCorrectMemoryAnimation() {
        if (!memoryModalRefs) return;
        const { card, word, image } = memoryModalRefs;
        if (!card || !word || !image) return;

        resetMemoryAnimation();

        const wordRect = word.getBoundingClientRect();
        const imageRect = image.getBoundingClientRect();
        const wordCenter = wordRect.top + wordRect.height / 2;
        const imageCenter = imageRect.top + imageRect.height / 2;
        const dropDistance = Math.max(0, imageCenter - wordCenter);

        word.style.setProperty("--geek-memory-word-drop", `${dropDistance}px`);
        requestAnimationFrame(() => {
            if (!isMemoryModalOpen()) return;
            card.classList.add("is-memorizing");
            word.classList.add("is-memorized");
        });
    }

    function handleAnswerInput(event) {
        if (!currentMemoryData) return;
        clearTimeout(autoCloseTimer);

        const input = event.target;
        const typed = answerKey(input.value);
        // Strictly verify the exact word in #geek-memory-word
        const target = answerKey(currentMemoryData.w);

        input.classList.remove("is-correct", "is-wrong");
        resetMemoryAnimation();

        if (!typed) return;

        if (typed === target) {
            input.classList.add("is-correct");
            playCorrectMemoryAnimation();
            speakText(currentMemoryData.w);
            // Automatically close modal after 3 seconds upon success
            autoCloseTimer = setTimeout(() => {
                closeMemoryModal();
            }, 3000);
        } else if (!target.startsWith(typed)) {
            input.classList.add("is-wrong");
        }
    }

    function renderFocusedExample(element, sentence, focus) {
        element.textContent = "";
        if (!sentence || !focus) {
            element.textContent = sentence;
            return;
        }

        const index = sentence.toLowerCase().indexOf(focus.toLowerCase());
        if (index < 0) {
            element.textContent = sentence;
            return;
        }

        element.append(document.createTextNode(sentence.slice(0, index)));
        const strong = document.createElement("strong");
        strong.textContent = sentence.slice(index, index + focus.length);
        element.append(strong, document.createTextNode(sentence.slice(index + focus.length)));
    }

    function openMemoryModal(entry) {
        clearTimeout(autoCloseTimer);
        const refs = createMemoryModal();
        currentMemoryData = entry;

        resetMemoryAnimation();
        refs.word.textContent = entry.w;
        refs.image.src = getImageUrl(entry.w);
        refs.image.alt = `${entry.w} image`;
        setupImageFallback(refs.image, entry.w);
        refs.translation.textContent = `(${entry.d})`;

        const spoken = entry.sp || {};
        refs.example.hidden = !(spoken.en && spoken.zh);
        renderFocusedExample(refs.exampleEnglish, spoken.en || "", spoken.focus || "");
        refs.exampleChinese.textContent = spoken.zh || "";

        refs.answer.value = "";
        refs.answer.classList.remove("is-correct", "is-wrong");

        refs.modal.classList.add("open");
        focusMemoryAnswer();
        speakText(entry.w);
    }

    function closeMemoryModal() {
        clearTimeout(autoCloseTimer);
        if (memoryModalRefs && memoryModalRefs.modal) {
            memoryModalRefs.modal.classList.remove("open");
            if (memoryModalRefs.answer) memoryModalRefs.answer.blur();
        }
        currentMemoryData = null;
        resetMemoryAnimation();
    }

    // ==========================================
    // In-Place DOM Highlighting with Exact Bubble DOM
    // ==========================================
    function highlightRange(range) {
        if (!range || range.collapsed) return 0;

        const commonAncestor = range.commonAncestorContainer;
        const textNodes = [];

        const walker = document.createTreeWalker(
            commonAncestor.nodeType === Node.TEXT_NODE ? commonAncestor.parentNode : commonAncestor,
            NodeFilter.SHOW_TEXT,
            {
                acceptNode(node) {
                    if (!node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
                    if (node.parentElement && (
                        node.parentElement.closest("#geek-memory-modal") ||
                        node.parentElement.closest(".translation-bubble") ||
                        node.parentElement.tagName === "SCRIPT" ||
                        node.parentElement.tagName === "STYLE" ||
                        node.parentElement.tagName === "TEXTAREA" ||
                        node.parentElement.isContentEditable
                    )) {
                        return NodeFilter.FILTER_REJECT;
                    }
                    if (range.intersectsNode(node)) {
                        return NodeFilter.FILTER_ACCEPT;
                    }
                    return NodeFilter.FILTER_REJECT;
                }
            }
        );

        let currentNode;
        while ((currentNode = walker.nextNode())) {
            textNodes.push(currentNode);
        }

        if (textNodes.length === 0 && commonAncestor.nodeType === Node.TEXT_NODE && range.intersectsNode(commonAncestor)) {
            textNodes.push(commonAncestor);
        }

        let totalHighlighted = 0;

        textNodes.forEach(node => {
            const parent = node.parentNode;
            if (!parent || parent.classList.contains("geek-vocab-mark")) return;

            const text = node.nodeValue;
            const tokenRegex = /\\b[a-zA-Z\\'-]+\\b/g;
            let match;
            const matches = [];

            while ((match = tokenRegex.exec(text)) !== null) {
                const token = match[0];
                const entry = lookupWord(token);
                if (entry) {
                    matches.push({
                        start: match.index,
                        end: match.index + token.length,
                        token: token,
                        entry: entry
                    });
                }
            }

            if (matches.length === 0) return;

            const isAlreadyBold = isElementBold(parent);
            const fragment = document.createDocumentFragment();
            let lastIndex = 0;

            matches.forEach(m => {
                if (m.start > lastIndex) {
                    fragment.appendChild(document.createTextNode(text.slice(lastIndex, m.start)));
                }

                // Authentic Project DOM Structure:
                // <strong class="geek-vocab-mark">token<span class="translation-bubble geek-has-word-image"><img class="geek-bubble-image" /><span class="geek-bubble-text">...</span></span></strong>
                const mark = document.createElement("strong");
                mark.className = "geek-vocab-mark";
                mark.appendChild(document.createTextNode(m.token));

                const bubble = document.createElement("span");
                bubble.className = "translation-bubble geek-has-word-image";

                const image = document.createElement("img");
                image.className = "geek-bubble-image";
                image.src = getImageUrl(m.entry.w);
                image.alt = `${m.entry.w} image`;
                image.loading = "lazy";
                image.draggable = false;
                setupImageFallback(image, m.entry.w);
                image.addEventListener("load", () => placeBubble(bubble));
                image.addEventListener("click", (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    openMemoryModal(m.entry);
                });

                const textSpan = document.createElement("span");
                textSpan.className = "geek-bubble-text";
                textSpan.textContent = `(${m.entry.d})`;

                bubble.appendChild(image);
                bubble.appendChild(textSpan);
                mark.appendChild(bubble);

                mark.addEventListener("mouseenter", () => {
                    requestAnimationFrame(() => placeBubble(bubble));
                });
                mark.addEventListener("click", () => {
                    speakText(m.entry.w);
                });

                fragment.appendChild(mark);
                lastIndex = m.end;
                totalHighlighted++;
            });

            if (lastIndex < text.length) {
                fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
            }

            parent.replaceChild(fragment, node);
        });

        return totalHighlighted;
    }

    // ==========================================
    // Selection Trigger Button
    // ==========================================
    let currentTriggerBtn = null;

    function removeTriggerBtn() {
        if (currentTriggerBtn) {
            currentTriggerBtn.remove();
            currentTriggerBtn = null;
        }
    }

    function showTriggerButton(range, matchCount, x, y) {
        removeTriggerBtn();

        const btn = document.createElement("div");
        btn.className = "isa-trigger-btn";
        btn.innerHTML = `
            <svg viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>
            <span>标记真经 (${matchCount})</span>
        `;

        let posX = x + 10;
        let posY = y - 42;

        if (posY < 10) posY = y + 20;
        if (posX + 140 > window.innerWidth) posX = window.innerWidth - 150;

        btn.style.left = `${posX}px`;
        btn.style.top = `${posY}px`;

        btn.onclick = (e) => {
            e.stopPropagation();
            removeTriggerBtn();
            highlightRange(range);
            window.getSelection().removeAllRanges();
        };

        document.body.appendChild(btn);
        currentTriggerBtn = btn;
    }

    // ==========================================
    // Event Listeners
    // ==========================================
    document.addEventListener("mouseup", (event) => {
        if (currentTriggerBtn && currentTriggerBtn.contains(event.target)) {
            return;
        }
        if (isMemoryModalOpen()) {
            return;
        }

        setTimeout(() => {
            const selection = window.getSelection();
            if (!selection || selection.isCollapsed) {
                removeTriggerBtn();
                return;
            }

            const selectedText = selection.toString().trim();
            if (!selectedText || selectedText.length < 2) {
                removeTriggerBtn();
                return;
            }

            const tokens = selectedText.match(/\\b[a-zA-Z\\'-]+\\b/g);
            if (!tokens || tokens.length === 0) {
                removeTriggerBtn();
                return;
            }

            let matchCount = 0;
            for (const token of tokens) {
                if (lookupWord(token)) {
                    matchCount++;
                }
            }

            if (matchCount > 0) {
                const range = selection.getRangeAt(0).cloneRange();
                const rect = range.getBoundingClientRect();
                const btnX = rect.right > 0 ? rect.right : event.clientX;
                const btnY = rect.top > 0 ? rect.top : event.clientY;
                showTriggerButton(range, matchCount, btnX, btnY);
            } else {
                removeTriggerBtn();
            }
        }, 50);
    });

    document.addEventListener("mousedown", (event) => {
        if (currentTriggerBtn && !currentTriggerBtn.contains(event.target)) {
            removeTriggerBtn();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeMemoryModal();
            removeTriggerBtn();
            return;
        }
        if (isMemoryModalOpen()) {
            focusMemoryAnswer();
        }
    });

})();
"""

final_js_code = js_template.replace("__DICTIONARY_JSON__", dict_json_str).replace("__CDN_IMAGE_BASE__", CDN_IMAGE_BASE)

# 4. Generate Chrome Extension files
manifest = {
    "manifest_version": 3,
    "name": "雅思真经划词划划看 (IELTS Selection Assistant)",
    "version": "1.4.0",
    "description": "划选任意网页文本，一键在正文中直接标注《雅思词汇真经》核心词汇。Tips气泡与大图例句覆层100%对齐，支持输入单词校验并自动退出。",
    "permissions": ["activeTab"],
    "content_scripts": [
        {
            "matches": ["<all_urls>"],
            "js": ["content_script.js"],
            "run_at": "document_end"
        }
    ]
}
manifest_path = TARGET_DIR / "manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Generated {manifest_path}")

content_script_path = TARGET_DIR / "content_script.js"
content_script_path.write_text(final_js_code, encoding="utf-8")
print(f"Generated {content_script_path}")

# 5. Generate Tampermonkey Userscript (ielts-selection.user.js)
user_script_header = """// ==UserScript==
// @name         雅思真经划词划划看 (IELTS Selection Assistant)
// @namespace    https://github.com/yangdongxing/IELTS-Vacab-Fantasia
// @version      1.4.0
// @description  划选任意网页文本，一键在正文中直接标注《雅思词汇真经》核心词汇。Tips气泡与大图例句覆层100%对齐，支持输入单词校验并自动退出。
// @author       极客助手
// @match        *://*/*
// @match        file:///*
// @grant        none
// @run-at       document-end
// ==/UserScript==

"""
user_script_path = TARGET_DIR / "ielts-selection.user.js"
user_script_path.write_text(user_script_header + final_js_code, encoding="utf-8")
print(f"Generated {user_script_path}")

# 6. Generate test demo page (test.html)
test_html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>雅思真经划词助手 · 测试演示页</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f8fafc;
            color: #1e293b;
            padding: 40px 20px;
            line-height: 1.8;
            max-width: 840px;
            margin: 0 auto;
        }
        h1 {
            color: #0f172a;
            font-size: 26px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .subtitle {
            color: #64748b;
            font-size: 15px;
            margin-bottom: 30px;
        }
        .sample-box {
            background: #ffffff;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.06);
            margin-bottom: 24px;
            border: 1px solid #e2e8f0;
        }
        h2 {
            font-size: 18px;
            color: #e11d48;
            margin-bottom: 12px;
        }
        p {
            font-size: 16px;
            color: #334155;
            margin-bottom: 16px;
        }
        .guide-box {
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 8px;
            padding: 16px 20px;
            color: #166534;
            font-size: 14px;
            margin-bottom: 24px;
        }
    </style>
</head>
<body>
    <h1>📖 雅思真经划词划划看 (Selection Assistant)</h1>
    <div class="subtitle">选中文本 ➜ 点击按钮标记 ➜ Hover 查看 Tips ➜ 点击图片看大图 ➜ 键盘敲入单词验证成功后自动关闭。</div>

    <div class="guide-box">
        💡 <strong>操作测试步骤：</strong><br>
        1. 鼠标选中下方一段英文；<br>
        2. 点击弹出的 <strong>【📖 标记真经 (N)】</strong> 按钮；<br>
        3. 鼠标 <strong>Hover</strong> 到加粗单词上弹出 Tips 气泡；<br>
        4. <strong>点击 Tips 中的微缩图片</strong>打开全屏居中大图卡片；<br>
        5. 在底部输入框敲入单词（例如输入 <code>plateau</code>、<code>horizon</code> 等）：<br>
        &nbsp;&nbsp;• <strong>输入正确时</strong>：立即触发绿色对钩反馈与单词下落动画，播放发音，并<strong>等待 3 秒后自动平滑关闭覆层</strong>！<br>
        &nbsp;&nbsp;• 也可以随时按 <code>ESC</code> 键退出。
    </div>

    <div class="sample-box">
        <h2>测试段落 1：自然地理与极端气候</h2>
        <p>
            Standing at a high altitude on the plateau, the explorers observed the endless horizon. The earth's crust and lithosphere have experienced dramatic volcanic eruptions, discharging magma, ash, and toxic gases into the atmosphere. The heavy rainfall and storms caused devastating floods across the continent.
        </p>
    </div>

    <div class="sample-box">
        <h2>测试段落 2：旅行与时态变形测试（含已有加粗文本测试）</h2>
        <p>
            My sister was fond of traveling. Ever since graduating, she had been determined to organize a trip to an ancient temple. <b>Our pace was slow because the river frequently had sharp bends through deep valleys.</b> When we reached the valley, it was quiet and the columns of ice hung from the rocks. She disagreed with taking the train and preferred cycling.
        </p>
    </div>

    <div class="sample-box">
        <h2>测试段落 3：科技与现代生活</h2>
        <p>
            With artificial intelligence and computers simplifying complex calculations, scientists can easily predict environmental catastrophes, such as global warming and greenhouse effects caused by excessive carbon dioxide emissions.
        </p>
    </div>

    <script src="content_script.js"></script>
</body>
</html>
"""
test_html_path = TARGET_DIR / "test.html"
test_html_path.write_text(test_html_content, encoding="utf-8")
print(f"Generated {test_html_path}")
