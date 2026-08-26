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
        const capWord = word.charAt(0).toUpperCase() + word.slice(1);
        const encoded = encodeURIComponent(capWord) + ".jpg";

        imgElement.onerror = function() {
            if (imgElement.src.startsWith(LOCAL_IMAGE_BASE)) {
                // Try relative path if testing locally
                imgElement.src = "../assets/images/" + encoded;
                imgElement.onerror = function() {
                    imgElement.src = REMOTE_IMAGE_BASE + encoded;
                    imgElement.onerror = function() {
                        imgElement.style.opacity = "0.2";
                    };
                };
            } else if (imgElement.src.includes("../assets/images/")) {
                imgElement.src = REMOTE_IMAGE_BASE + encoded;
                imgElement.onerror = function() {
                    imgElement.style.opacity = "0.2";
                };
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
    // Telemetry & Data Tracking (数据统计打点系统)
    // ==========================================
    const STATS_STORAGE_KEY = "ielts_vocab_fantasia_stats";

    function loadStats() {
        let stats = null;
        if (typeof GM_getValue === "function") {
            try {
                const gmData = GM_getValue(STATS_STORAGE_KEY, null);
                if (gmData) stats = (typeof gmData === "string") ? JSON.parse(gmData) : gmData;
            } catch (e) {}
        }
        if (!stats) {
            try {
                const raw = localStorage.getItem(STATS_STORAGE_KEY);
                if (raw) stats = JSON.parse(raw);
            } catch (e) {}
        }
        return stats || { summary: { marks: 0, modalOpens: 0, inputSuccess: 0 }, words: {} };
    }

    function saveStats(stats) {
        if (typeof GM_setValue === "function") {
            try {
                GM_setValue(STATS_STORAGE_KEY, stats);
            } catch (e) {}
        }
        try {
            localStorage.setItem(STATS_STORAGE_KEY, JSON.stringify(stats));
        } catch (e) {}

        window.dispatchEvent(new CustomEvent("ielts_stats_updated", { detail: stats }));

        // Cross-domain background sync to local server data/stats.json
        const payload = JSON.stringify(stats);
        if (typeof GM_xmlhttpRequest === "function") {
            try {
                GM_xmlhttpRequest({
                    method: "POST",
                    url: "http://127.0.0.1:8777/api/stats",
                    headers: { "Content-Type": "application/json" },
                    data: payload
                });
            } catch (e) {}
        } else if (typeof fetch === "function") {
            fetch("http://127.0.0.1:8777/api/stats", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: payload,
                mode: "cors"
            }).catch(() => {});
        }
    }

    function trackWordEvent(word, eventType) {
        if (!word) return;
        const stats = loadStats();
        const key = word.toLowerCase().trim();
        const now = Date.now();

        if (!stats.words) stats.words = {};
        if (!stats.summary) stats.summary = { marks: 0, modalOpens: 0, inputSuccess: 0 };

        if (!stats.words[key]) {
            stats.words[key] = {
                w: word,
                marks: 0,
                modalOpens: 0,
                inputSuccess: 0,
                lastUpdated: now
            };
        }

        const entry = stats.words[key];
        entry.lastUpdated = now;

        if (eventType === "mark") {
            entry.marks = (entry.marks || 0) + 1;
            stats.summary.marks = (stats.summary.marks || 0) + 1;
        } else if (eventType === "modal_open") {
            entry.modalOpens = (entry.modalOpens || 0) + 1;
            stats.summary.modalOpens = (stats.summary.modalOpens || 0) + 1;
        } else if (eventType === "input_success") {
            entry.inputSuccess = (entry.inputSuccess || 0) + 1;
            stats.summary.inputSuccess = (stats.summary.inputSuccess || 0) + 1;
        }

        saveStats(stats);
    }

    window.ieltsVocabStats = {
        getStats: loadStats,
        getSummary: () => loadStats().summary,
        getTopWords: (sortBy = "marks", limit = 10) => {
            const stats = loadStats();
            return Object.values(stats.words || {})
                .sort((a, b) => (b[sortBy] || 0) - (a[sortBy] || 0))
                .slice(0, limit);
        },
        exportJSON: () => JSON.stringify(loadStats(), null, 2),
        clearStats: () => {
            localStorage.removeItem(STATS_STORAGE_KEY);
            window.dispatchEvent(new CustomEvent("ielts_stats_updated", { detail: loadStats() }));
            if (typeof fetch === "function") {
                fetch("http://127.0.0.1:8777/api/stats", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ summary: { marks: 0, modalOpens: 0, inputSuccess: 0 }, words: {} })
                }).catch(() => {});
            }
            console.log("[IELTS Stats] Telemetry data cleared.");
        }
    };

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
                vertical-align: baseline !important;
                color: inherit !important;
                font-weight: 600 !important;
                text-decoration: none !important;
                background-color: rgba(244, 63, 94, 0.18) !important;
                border-radius: 3px !important;
                padding: 0 3.5px !important;
                margin: 0 1px !important;
                cursor: pointer !important;
                transition: background-color 0.15s ease !important;
            }
            strong.geek-vocab-mark:hover, em.geek-vocab-mark:hover {
                background-color: rgba(244, 63, 94, 0.3) !important;
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

            /* Bilingual Paragraph Translation Block */
            .isa-paragraph-translation {
                margin: 12px 0 16px !important;
                padding: 10px 14px !important;
                background: #f0f9ff !important;
                border-left: 3.5px solid #0284c7 !important;
                border-radius: 6px !important;
                box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04) !important;
                font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Segoe UI", Roboto, sans-serif !important;
                font-size: 13.5px !important;
                line-height: 1.65 !important;
                color: #334155 !important;
                position: relative !important;
                transition: all 0.2s ease !important;
                box-sizing: border-box !important;
            }
            .isa-trans-header {
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                margin-bottom: 6px !important;
                user-select: none !important;
            }
            .isa-trans-title {
                display: inline-flex !important;
                align-items: center !important;
                gap: 5px !important;
                font-size: 12px !important;
                font-weight: 600 !important;
                color: #0284c7 !important;
            }
            .isa-trans-tools {
                display: inline-flex !important;
                align-items: center !important;
                gap: 8px !important;
            }
            .isa-trans-btn {
                background: transparent !important;
                border: none !important;
                cursor: pointer !important;
                font-size: 12px !important;
                color: #64748b !important;
                padding: 1px 4px !important;
                border-radius: 3px !important;
                transition: color 0.15s !important;
            }
            .isa-trans-btn:hover {
                color: #0284c7 !important;
            }
            .isa-trans-btn.close:hover {
                color: #e11d48 !important;
            }
            .isa-trans-content {
                color: #1e293b !important;
                font-weight: normal !important;
            }
            .isa-trans-content.collapsed {
                display: none !important;
            }
            .isa-trans-loading {
                color: #64748b !important;
                font-style: italic !important;
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
            trackWordEvent(currentMemoryData.w, "input_success");
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
        trackWordEvent(entry.w, "modal_open");

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
                trackWordEvent(m.entry.w, "mark");

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
    // Google Neural Translation & Paragraph Insertion
    // ==========================================
    function translateTextGoogle(text) {
        return new Promise((resolve, reject) => {
            const cleanText = (text || "").trim();
            if (!cleanText) return resolve("");

            const googleUrl = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q=" + encodeURIComponent(cleanText);

            if (typeof GM_xmlhttpRequest === "function") {
                GM_xmlhttpRequest({
                    method: "GET",
                    url: googleUrl,
                    onload: function(res) {
                        try {
                            const data = JSON.parse(res.responseText);
                            const translated = (data[0] || []).map(item => item[0]).join("");
                            resolve(translated);
                        } catch (e) {
                            reject(e);
                        }
                    },
                    onerror: reject
                });
            } else {
                fetch(googleUrl)
                    .then(res => res.json())
                    .then(data => {
                        const translated = (data[0] || []).map(item => item[0]).join("");
                        resolve(translated);
                    })
                    .catch(() => {
                        // Fallback to local server translation proxy if CORS fails
                        fetch("http://127.0.0.1:8777/api/translate?q=" + encodeURIComponent(cleanText))
                            .then(r => r.json())
                            .then(d => resolve(d.translation || ""))
                            .catch(reject);
                    });
            }
        });
    }

    function findParagraphContainer(range) {
        if (!range) return null;
        let node = range.commonAncestorContainer;
        if (node.nodeType === Node.TEXT_NODE) node = node.parentElement;
        if (!node) return null;
        return node.closest("p, blockquote, li, pre, div.sample-box, article, section") || node;
    }

    function insertParagraphTranslation(targetParagraph, textToTranslate) {
        if (!targetParagraph || !textToTranslate) return;

        let transBox = targetParagraph.nextElementSibling;
        if (!transBox || !transBox.classList.contains("isa-paragraph-translation")) {
            transBox = document.createElement("div");
            transBox.className = "isa-paragraph-translation";
            transBox.innerHTML = `
                <div class="isa-trans-header">
                    <span class="isa-trans-title">🌐 段落中文翻译 (Google 神经翻译)</span>
                    <span class="isa-trans-tools">
                        <button class="isa-trans-btn toggle" title="折叠/展开">折叠 ▲</button>
                        <button class="isa-trans-btn close" title="关闭">✕</button>
                    </span>
                </div>
                <div class="isa-trans-content isa-trans-loading">正在翻译段落中...</div>
            `;
            targetParagraph.insertAdjacentElement("afterend", transBox);

            const contentEl = transBox.querySelector(".isa-trans-content");
            const toggleBtn = transBox.querySelector(".isa-trans-btn.toggle");
            const closeBtn = transBox.querySelector(".isa-trans-btn.close");

            toggleBtn.onclick = (e) => {
                e.stopPropagation();
                if (contentEl.classList.contains("collapsed")) {
                    contentEl.classList.remove("collapsed");
                    toggleBtn.textContent = "折叠 ▲";
                } else {
                    contentEl.classList.add("collapsed");
                    toggleBtn.textContent = "展开 ▼";
                }
            };

            closeBtn.onclick = (e) => {
                e.stopPropagation();
                transBox.remove();
            };
        } else {
            const contentEl = transBox.querySelector(".isa-trans-content");
            contentEl.className = "isa-trans-content isa-trans-loading";
            contentEl.textContent = "正在更新翻译中...";
        }

        const contentEl = transBox.querySelector(".isa-trans-content");

        translateTextGoogle(textToTranslate)
            .then(zhText => {
                if (!zhText) {
                    transBox.remove();
                    return;
                }
                contentEl.classList.remove("isa-trans-loading");
                contentEl.textContent = zhText;
            })
            .catch(() => {
                contentEl.classList.remove("isa-trans-loading");
                contentEl.textContent = "（翻译请求超时或网络受限，请稍后重试）";
            });
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
            const targetParagraph = findParagraphContainer(range);
            const textToTranslate = range.toString().trim() || (targetParagraph ? targetParagraph.innerText.trim() : "");
            highlightRange(range);
            if (targetParagraph && textToTranslate) {
                insertParagraphTranslation(targetParagraph, textToTranslate);
            }
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
    "version": "1.5.0",
    "description": "划选任意网页文本，一键在正文中直接标注《雅思词汇真经》核心词汇。Tips气泡与大图例句覆层100%对齐，支持输入单词校验并自动退出，支持段落下自动插入Google神经双语对照翻译。",
    "permissions": ["activeTab"],
    "host_permissions": [
        "https://translate.googleapis.com/*",
        "http://127.0.0.1/*",
        "http://localhost/*"
    ],
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
// @version      1.5.0
// @description  划选任意网页文本，一键在正文中直接标注《雅思词汇真经》核心词汇。Tips气泡与大图例句覆层100%对齐，支持输入单词校验并自动退出，支持段落下自动插入Google神经双语对照翻译。
// @author       极客助手
// @match        *://*/*
// @match        file:///*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @connect      localhost
// @connect      translate.googleapis.com
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

    <div class="sample-box" style="border-left: 4px solid #0284c7; background: #f0f9ff;">
        <h2 style="color: #0284c7; display: flex; justify-content: space-between; align-items: center;">
            <span>📊 数据统计看板</span>
            <span style="font-size: 13px; font-weight: normal;">
                <a href="stats.html" target="_blank" style="padding: 4px 10px; border-radius: 6px; background: #0284c7; color: #fff; text-decoration: none; font-weight: 500;">📋 打开完整统计表格页面 ➔</a>
            </span>
        </h2>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 16px 0; text-align: center;">
            <div style="background: #ffffff; padding: 12px; border-radius: 8px; border: 1px solid #e0f2fe;">
                <div style="font-size: 12px; color: #64748b;">累计标记单词</div>
                <div id="stat-marks" style="font-size: 24px; font-weight: 700; color: #0284c7;">0</div>
            </div>
            <div style="background: #ffffff; padding: 12px; border-radius: 8px; border: 1px solid #e0f2fe;">
                <div style="font-size: 12px; color: #64748b;">覆层查看次数</div>
                <div id="stat-modal" style="font-size: 24px; font-weight: 700; color: #7c3aed;">0</div>
            </div>
            <div style="background: #ffffff; padding: 12px; border-radius: 8px; border: 1px solid #e0f2fe;">
                <div style="font-size: 12px; color: #64748b;">拼写验证成功</div>
                <div id="stat-success" style="font-size: 24px; font-weight: 700; color: #16a34a;">0</div>
            </div>
        </div>
        <div id="top-words-container" style="font-size: 13px; color: #334155; background: #fff; border-radius: 8px; padding: 12px; border: 1px solid #e0f2fe;">
            <strong>🏆 高频打点单词 Top 5：</strong>
            <span id="top-words-list" style="color: #64748b;">暂无打点记录</span>
        </div>
    </div>

    <script src="content_script.js"></script>
    <script>
        function renderDashboard() {
            if (!window.ieltsVocabStats) return;
            const stats = window.ieltsVocabStats.getStats();
            const summary = stats.summary || { marks: 0, modalOpens: 0, inputSuccess: 0 };
            
            document.getElementById("stat-marks").textContent = summary.marks || 0;
            document.getElementById("stat-modal").textContent = summary.modalOpens || 0;
            document.getElementById("stat-success").textContent = summary.inputSuccess || 0;

            const top = window.ieltsVocabStats.getTopWords("marks", 5);
            const listEl = document.getElementById("top-words-list");
            if (top.length === 0) {
                listEl.textContent = "暂无打点记录，请先在上方划词标记";
            } else {
                listEl.innerHTML = top.map(w => `
                    <span style="display: inline-block; background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 12px; margin: 2px 4px; font-size: 12px;">
                        <strong>${w.w}</strong>: 标记 ${w.marks||0}次 | 覆层 ${w.modalOpens||0}次 | 拼写成功 ${w.inputSuccess||0}次
                    </span>
                `).join("");
            }
        }

        window.addEventListener("ielts_stats_updated", renderDashboard);
        window.addEventListener("DOMContentLoaded", renderDashboard);
        setTimeout(renderDashboard, 100);
    </script>
</body>
</html>
"""
test_html_path = TARGET_DIR / "test.html"
test_html_path.write_text(test_html_content, encoding="utf-8")
print(f"Generated {test_html_path}")

# 7. Generate dedicated statistics page (stats.html)
stats_html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>雅思真经打点与学习统计 · 数据管理台</title>
    <style>
        :root {
            --bg: #f8fafc;
            --surface: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --primary: #0284c7;
            --primary-light: #e0f2fe;
            --rose: #e11d48;
            --purple: #7c3aed;
            --green: #16a34a;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            padding: 32px 24px;
            line-height: 1.6;
        }
        .container {
            max-width: 1140px;
            margin: 0 auto;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            flex-wrap: wrap;
            gap: 16px;
        }
        .title-area h1 {
            font-size: 24px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .title-area p {
            font-size: 14px;
            color: var(--text-muted);
            margin-top: 4px;
        }
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .kpi-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .kpi-card .label {
            font-size: 13px;
            color: var(--text-muted);
            font-weight: 500;
        }
        .kpi-card .value {
            font-size: 32px;
            font-weight: 700;
            line-height: 1.1;
        }
        .kpi-card.blue .value { color: var(--primary); }
        .kpi-card.purple .value { color: var(--purple); }
        .kpi-card.green .value { color: var(--green); }
        .kpi-card.rose .value { color: var(--rose); }

        .toolbar {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }
        .search-box {
            display: flex;
            align-items: center;
            gap: 8px;
            flex: 1;
            max-width: 360px;
        }
        .search-box input {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.15s;
        }
        .search-box input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.12);
        }
        .filter-buttons {
            display: flex;
            gap: 8px;
        }
        .filter-btn {
            background: var(--bg);
            border: 1px solid var(--border);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            color: var(--text-muted);
            transition: all 0.15s;
        }
        .filter-btn.active {
            background: var(--primary);
            color: #fff;
            border-color: var(--primary);
        }
        .action-buttons {
            display: flex;
            gap: 8px;
        }
        .btn {
            padding: 7px 14px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border: 1px solid transparent;
            transition: all 0.15s;
            text-decoration: none;
        }
        .btn-outline {
            background: #fff;
            border-color: var(--border);
            color: var(--text-main);
        }
        .btn-outline:hover {
            background: var(--bg);
            border-color: #cbd5e1;
        }
        .btn-danger {
            background: #fff;
            border-color: #fecdd3;
            color: var(--rose);
        }
        .btn-danger:hover {
            background: #ffe4e6;
        }

        .table-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 14px;
        }
        thead th {
            background: #f1f5f9;
            padding: 12px 16px;
            font-weight: 600;
            color: #475569;
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
        }
        thead th:hover {
            background: #e2e8f0;
        }
        tbody tr {
            border-bottom: 1px solid var(--border);
            transition: background 0.1s;
        }
        tbody tr:hover {
            background: #f8fafc;
        }
        tbody td {
            padding: 14px 16px;
            vertical-align: middle;
        }
        .word-cell {
            font-weight: 600;
            color: #0f172a;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 15px;
        }
        .btn-speak {
            background: transparent;
            border: none;
            cursor: pointer;
            font-size: 14px;
            opacity: 0.6;
            transition: opacity 0.15s, transform 0.15s;
        }
        .btn-speak:hover {
            opacity: 1;
            transform: scale(1.15);
        }
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-blue { background: #e0f2fe; color: #0369a1; }
        .badge-purple { background: #f3e8ff; color: #6b21a8; }
        .badge-green { background: #dcfce7; color: #15803d; }
        .badge-gray { background: #f1f5f9; color: #64748b; }

        .time-cell {
            font-size: 13px;
            color: var(--text-muted);
            white-space: nowrap;
        }
        .empty-state {
            padding: 60px 20px;
            text-align: center;
            color: var(--text-muted);
        }
        .empty-state svg {
            width: 48px;
            height: 48px;
            color: #cbd5e1;
            margin-bottom: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="title-area">
                <h1>📊 雅思真经打点与学习统计</h1>
                <p>记录网页正文划词标记、全局覆层弹开、拼写验证等全流程学习轨迹 (数据已持久化)</p>
            </div>
            <div class="action-buttons">
                <button id="btn-sync" class="btn btn-outline" title="从本地服务器同步数据">🔄 同步本地数据</button>
                <button id="btn-export-csv" class="btn btn-outline">📥 导出 CSV</button>
                <button id="btn-export-json" class="btn btn-outline">📥 导出 JSON</button>
                <button id="btn-clear" class="btn btn-danger">🗑️ 清空统计</button>
            </div>
        </header>

        <section class="kpi-grid">
            <div class="kpi-card blue">
                <span class="label">📘 累计打点单词数</span>
                <span class="value" id="kpi-words">0</span>
            </div>
            <div class="kpi-card rose">
                <span class="label">🔖 网页正文标记总次数</span>
                <span class="value" id="kpi-marks">0</span>
            </div>
            <div class="kpi-card purple">
                <span class="label">🖼️ 全局覆层弹开查看总次数</span>
                <span class="value" id="kpi-modal">0</span>
            </div>
            <div class="kpi-card green">
                <span class="label">🎯 拼写验证成功总次数</span>
                <span class="value" id="kpi-success">0</span>
            </div>
        </section>

        <div class="toolbar">
            <div class="search-box">
                <input type="text" id="search-input" placeholder="🔍 搜索单词或中文释义...">
            </div>
            <div class="filter-buttons">
                <button class="filter-btn active" data-filter="all">全部</button>
                <button class="filter-btn" data-filter="marks">已标记词</button>
                <button class="filter-btn" data-filter="modal">已查看大图</button>
                <button class="filter-btn" data-filter="success">已拼写成功</button>
            </div>
        </div>

        <div class="table-card">
            <table>
                <thead>
                    <tr>
                        <th style="width: 60px;">#</th>
                        <th data-sort="w">单词 (Word) ⇅</th>
                        <th>释义 (Definition)</th>
                        <th data-sort="marks" style="text-align: center;">标记次数 ⇅</th>
                        <th data-sort="modalOpens" style="text-align: center;">覆层查看 ⇅</th>
                        <th data-sort="inputSuccess" style="text-align: center;">拼写成功 ⇅</th>
                        <th data-sort="lastUpdated">最近记录时间 ⇅</th>
                    </tr>
                </thead>
                <tbody id="table-body">
                    <tr>
                        <td colspan="7" class="empty-state">
                            <div>加载数据中...</div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const STATS_STORAGE_KEY = "ielts_vocab_fantasia_stats";
        let DICT = {};
        let currentSort = { field: "lastUpdated", order: "desc" };
        let currentFilter = "all";
        let searchQuery = "";

        // Load Dictionary
        fetch("data/dictionary.json")
            .then(res => res.json())
            .then(data => {
                DICT = data;
                render();
            })
            .catch(() => {
                render();
            });

        function loadStats() {
            try {
                const raw = localStorage.getItem(STATS_STORAGE_KEY);
                return raw ? JSON.parse(raw) : { summary: { marks: 0, modalOpens: 0, inputSuccess: 0 }, words: {} };
            } catch (e) {
                return { summary: { marks: 0, modalOpens: 0, inputSuccess: 0 }, words: {} };
            }
        }

        function saveStats(stats) {
            try {
                localStorage.setItem(STATS_STORAGE_KEY, JSON.stringify(stats));
                fetch("http://127.0.0.1:8777/api/stats", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(stats)
                }).catch(() => {});
            } catch (e) {}
        }

        function speakWord(word) {
            if (!window.speechSynthesis || !word) return;
            window.speechSynthesis.cancel();
            const utter = new SpeechSynthesisUtterance(word);
            utter.lang = "en-US";
            utter.rate = 0.92;
            window.speechSynthesis.speak(utter);
        }

        function formatDate(ts) {
            if (!ts) return "-";
            const d = new Date(ts);
            const y = d.getFullYear();
            const m = String(d.getMonth() + 1).padStart(2, "0");
            const day = String(d.getDate()).padStart(2, "0");
            const h = String(d.getHours()).padStart(2, "0");
            const min = String(d.getMinutes()).padStart(2, "0");
            return `${y}-${m}-${day} ${h}:${min}`;
        }

        function render() {
            const stats = loadStats();
            const wordsList = Object.values(stats.words || {});
            
            // Calculate KPI
            let totalMarks = 0;
            let totalModal = 0;
            let totalSuccess = 0;

            wordsList.forEach(w => {
                totalMarks += (w.marks || 0);
                totalModal += (w.modalOpens || 0);
                totalSuccess += (w.inputSuccess || 0);
            });

            document.getElementById("kpi-words").textContent = wordsList.length;
            document.getElementById("kpi-marks").textContent = totalMarks;
            document.getElementById("kpi-modal").textContent = totalModal;
            document.getElementById("kpi-success").textContent = totalSuccess;

            // Filter
            let filtered = wordsList.filter(item => {
                const w = item.w || "";
                const def = (DICT[w.toLowerCase()] && DICT[w.toLowerCase()].d) || "";
                
                if (searchQuery) {
                    const q = searchQuery.toLowerCase();
                    if (!w.toLowerCase().includes(q) && !def.includes(q)) return false;
                }

                if (currentFilter === "marks" && !(item.marks > 0)) return false;
                if (currentFilter === "modal" && !(item.modalOpens > 0)) return false;
                if (currentFilter === "success" && !(item.inputSuccess > 0)) return false;

                return true;
            });

            // Sort
            filtered.sort((a, b) => {
                let valA = a[currentSort.field];
                let valB = b[currentSort.field];

                if (currentSort.field === "w") {
                    valA = (valA || "").toLowerCase();
                    valB = (valB || "").toLowerCase();
                    return currentSort.order === "asc" ? valA.localeCompare(valB) : valB.localeCompare(valA);
                }

                valA = valA || 0;
                valB = valB || 0;
                return currentSort.order === "asc" ? valA - valB : valB - valA;
            });

            // Render Table
            const tbody = document.getElementById("table-body");
            if (filtered.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="7" class="empty-state">
                            <div style="font-size: 15px; margin-bottom: 4px;">📭 暂无打点统计记录</div>
                            <div style="font-size: 13px; color: #94a3b8;">在任意网页或测试页选中文本点击“标记真经”即可自动记录</div>
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = filtered.map((item, idx) => {
                const dictEntry = DICT[item.w.toLowerCase()];
                const def = dictEntry ? dictEntry.d : "-";

                return `
                    <tr>
                        <td style="color: #94a3b8; font-size: 13px;">${idx + 1}</td>
                        <td>
                            <div class="word-cell">
                                <span>${item.w}</span>
                                <button class="btn-speak" title="朗读" onclick="speakWord('${item.w}')">🔊</button>
                            </div>
                        </td>
                        <td style="color: #475569;">${def}</td>
                        <td style="text-align: center;">
                            <span class="badge ${item.marks > 0 ? 'badge-blue' : 'badge-gray'}">${item.marks || 0}</span>
                        </td>
                        <td style="text-align: center;">
                            <span class="badge ${item.modalOpens > 0 ? 'badge-purple' : 'badge-gray'}">${item.modalOpens || 0}</span>
                        </td>
                        <td style="text-align: center;">
                            <span class="badge ${item.inputSuccess > 0 ? 'badge-green' : 'badge-gray'}">${item.inputSuccess || 0}</span>
                        </td>
                        <td class="time-cell">${formatDate(item.lastUpdated)}</td>
                    </tr>
                `;
            }).join("");
        }

        // Event Listeners
        document.getElementById("search-input").addEventListener("input", (e) => {
            searchQuery = e.target.value.trim();
            render();
        });

        document.querySelectorAll(".filter-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                currentFilter = btn.dataset.filter;
                render();
            });
        });

        document.querySelectorAll("thead th[data-sort]").forEach(th => {
            th.addEventListener("click", () => {
                const field = th.dataset.sort;
                if (currentSort.field === field) {
                    currentSort.order = currentSort.order === "asc" ? "desc" : "asc";
                } else {
                    currentSort.field = field;
                    currentSort.order = "desc";
                }
                render();
            });
        });

        function syncFromServer(silent = false) {
            fetch("http://127.0.0.1:8777/api/stats")
                .then(res => res.json())
                .then(serverStats => {
                    if (serverStats && serverStats.words) {
                        const local = loadStats();
                        let changed = false;
                        Object.keys(serverStats.words).forEach(k => {
                            if (!local.words[k] || (serverStats.words[k].lastUpdated || 0) >= (local.words[k].lastUpdated || 0)) {
                                local.words[k] = serverStats.words[k];
                                changed = true;
                            }
                        });
                        if (changed) {
                            saveStats(local);
                        }
                        render();
                        if (!silent) alert("✅ 本地服务器数据已成功同步！");
                    }
                })
                .catch(() => {
                    if (!silent) alert("⚠️ 无法连接到本地图片/数据服务 (127.0.0.1:8777)，已加载浏览器缓存数据。");
                });
        }

        // Sync from server button
        document.getElementById("btn-sync").addEventListener("click", () => syncFromServer(false));

        // Export CSV
        document.getElementById("btn-export-csv").addEventListener("click", () => {
            const stats = loadStats();
            const list = Object.values(stats.words || {});
            if (list.length === 0) return alert("暂无数据可导出");

            let csv = "\\uFEFF序号,单词,释义,标记次数,覆层查看次数,拼写成功次数,最近更新时间\\n";
            list.forEach((item, i) => {
                const def = (DICT[item.w.toLowerCase()] && DICT[item.w.toLowerCase()].d) || "";
                csv += `${i + 1},"${item.w}","${def.replace(/"/g, '""')}",${item.marks||0},${item.modalOpens||0},${item.inputSuccess||0},"${formatDate(item.lastUpdated)}"\\n`;
            });

            const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `ielts_vocab_stats_${new Date().toISOString().slice(0,10)}.csv`;
            a.click();
            URL.revokeObjectURL(url);
        });

        // Export JSON
        document.getElementById("btn-export-json").addEventListener("click", () => {
            const stats = loadStats();
            const str = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(stats, null, 2));
            const a = document.createElement("a");
            a.href = str;
            a.download = `ielts_vocab_stats_${new Date().toISOString().slice(0,10)}.json`;
            a.click();
        });

        // Clear
        document.getElementById("btn-clear").addEventListener("click", () => {
            if (confirm("⚠️ 确定要清空所有单词打点统计数据吗？此操作不可恢复。")) {
                localStorage.removeItem(STATS_STORAGE_KEY);
                if (typeof GM_setValue === "function") {
                    try { GM_setValue(STATS_STORAGE_KEY, null); } catch (e) {}
                }
                fetch("http://127.0.0.1:8777/api/stats", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ summary: { marks: 0, modalOpens: 0, inputSuccess: 0 }, words: {} })
                }).catch(() => {});
                render();
            }
        });

        // Automatic synchronization on load and tab focus
        window.addEventListener("DOMContentLoaded", () => {
            render();
            syncFromServer(true);
        });
        window.addEventListener("focus", () => {
            render();
            syncFromServer(true);
        });
        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "visible") {
                render();
                syncFromServer(true);
            }
        });
    </script>
</body>
</html>
"""
stats_html_path = TARGET_DIR / "stats.html"
stats_html_path.write_text(stats_html_content, encoding="utf-8")
print(f"Generated {stats_html_path}")

