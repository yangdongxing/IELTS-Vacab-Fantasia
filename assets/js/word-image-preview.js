(function () {
    "use strict";

    const scriptElement = document.currentScript;
    const siteRootUrl = new URL(scriptElement?.dataset.siteRoot || ".", document.baseURI).href;
    const MANIFEST_URL = new URL("__word_images__.json", siteRootUrl).href;
    const EDGE_PADDING = 12;
    const CORRECT_ADVANCE_DELAY = 3000;
    const MOBILE_MEMORY_MEDIA = "(max-width: 720px)";
    const MEMORY_SWIPE_MIN_DISTANCE = 48;
    const MEMORY_SWIPE_AXIS_RATIO = 1.2;

    let imageIndex = {};
    let activeBubble = null;
    let currentMemoryData = null;
    let memorySession = null;
    let paragraphCompletionPending = false;
    let autoAdvanceTimer = null;
    let memoryAnimationFrame = null;
    let memoryModalRefs = null;
    const bubbleMemoryData = new WeakMap();

    function normalizeWord(value) {
        return (value || "")
            .replace(/\([^)]*\)/g, " ")
            .replace(/[“”"']/g, "")
            .replace(/[.,;:!?，。；：！？]/g, " ")
            .replace(/_/g, " ")
            .replace(/\s+/g, " ")
            .trim()
            .toLowerCase();
    }

    function answerKey(value) {
        return normalizeWord(value).replace(/[\s-]+/g, "");
    }

    function memoryDataKey(data) {
        if (!data || !data.entry) return "";
        return [
            data.entry.url || "",
            data.displayWord || data.entry.word || "",
            data.translationText || "",
            data.entry.spoken?.en || "",
            data.entry.spoken?.zh || "",
            data.contextText || "",
        ].join("\u0001");
    }

    function contextTextFromElement(element) {
        if (!element) return "";

        const block = element.closest("p, li, blockquote, h1, h2, h3, h4, h5, h6");
        if (!block) return "";

        const clone = block.cloneNode(true);
        clone.querySelectorAll(".translation-bubble").forEach(node => node.remove());

        return (clone.textContent || "")
            .replace(/\s+/g, " ")
            .replace(/\s+([,.;:!?，。；：！？])/g, "$1")
            .trim();
    }

    function escapeRegExp(value) {
        return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }

    function renderContextText(container, text, displayWord) {
        if (!container) return;
        container.textContent = "";

        const sourceText = (text || "").trim();
        if (!sourceText) {
            container.textContent = "";
            return;
        }

        const phrase = (displayWord || "").trim();
        if (!phrase) {
            container.textContent = sourceText;
            return;
        }

        const pattern = new RegExp(escapeRegExp(phrase), "ig");
        let lastIndex = 0;
        let hasMatch = false;

        sourceText.replace(pattern, (match, offset) => {
            hasMatch = true;
            if (offset > lastIndex) {
                container.appendChild(document.createTextNode(sourceText.slice(lastIndex, offset)));
            }
            const mark = document.createElement("mark");
            mark.textContent = match;
            container.appendChild(mark);
            lastIndex = offset + match.length;
            return match;
        });

        if (!hasMatch) {
            container.textContent = sourceText;
            return;
        }

        if (lastIndex < sourceText.length) {
            container.appendChild(document.createTextNode(sourceText.slice(lastIndex)));
        }
    }

    function wordFromElement(element) {
        if (!element) return "";
        const firstText = Array.from(element.childNodes).find(node => node.nodeType === Node.TEXT_NODE);
        return normalizeWord(firstText ? firstText.textContent : element.textContent);
    }

    function displayWordFromElement(element) {
        if (!element) return "";
        const firstText = Array.from(element.childNodes).find(node => node.nodeType === Node.TEXT_NODE);
        return (firstText ? firstText.textContent : element.textContent).trim();
    }

    function compactKey(value) {
        return (value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "");
    }

    function addCandidateKeyVariants(keys, value) {
        const key = normalizeWord(value);
        if (!key) return;

        keys.add(key);
        keys.add(key.replace(/-/g, " "));
        keys.add(key.replace(/\s+/g, "-"));
        keys.add(key.replace(/^(a|an|the)\s+/, ""));

        const parts = key.split(/\s+/).filter(Boolean);
        if (parts.length > 1) {
            keys.add(parts[parts.length - 1]);
            keys.add(parts.slice(-2).join(" "));
            keys.add(parts.slice(-2).join("-"));
        }

        Array.from(keys).forEach(candidate => {
            const compact = compactKey(candidate);
            if (compact) keys.add(compact);
        });
    }

    function candidateKeys(word) {
        const key = normalizeWord(word);
        const keys = new Set();
        addCandidateKeyVariants(keys, key);
        key.split("/").forEach(part => addCandidateKeyVariants(keys, part));

        return Array.from(keys).filter(Boolean);
    }

    function findEntry(word) {
        for (const key of candidateKeys(word)) {
            const entries = imageIndex[key];
            if (entries && entries.length) return entries[0];
        }
        return null;
    }

    function prepareImageIndex(index) {
        if (!index || typeof index !== "object") return {};

        Object.values(index).forEach(entries => {
            if (!Array.isArray(entries)) return;
            entries.forEach(entry => {
                if (!entry || !entry.url) return;
                entry.url = new URL(entry.url.replace(/^\/+/, ""), siteRootUrl).href;
            });
        });
        return index;
    }

    function injectStyles() {
        const style = document.createElement("style");
        style.textContent = `
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
            strong:hover .translation-bubble.geek-has-word-image,
            em:hover .translation-bubble.geek-has-word-image,
            .translation-bubble.geek-has-word-image.force-show {
                background-color: #172033 !important;
                transform: translateX(-50%) scale(1) !important;
            }
            .translation-bubble.geek-has-word-image.force-show::after {
                border-color: #172033 transparent transparent transparent !important;
            }
            .translation-bubble.geek-has-word-image.geek-bubble-below.force-show::after {
                border-color: transparent transparent #172033 transparent !important;
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
            }
            .geek-bubble-text {
                display: block !important;
                color: #fff !important;
                font-size: 13px !important;
                line-height: 1.35 !important;
                text-align: center !important;
                overflow-wrap: anywhere !important;
            }
            #geek-memory-modal {
                position: fixed !important;
                inset: 0 !important;
                display: none !important;
                align-items: center !important;
                justify-content: center !important;
                padding: 24px !important;
                background: rgba(2, 6, 23, 0.76) !important;
                backdrop-filter: blur(4px) !important;
                z-index: 100001 !important;
                box-sizing: border-box !important;
                pointer-events: auto !important;
            }
            #geek-memory-modal.open {
                display: flex !important;
            }
            @media (max-width: 720px) {
                .translation-bubble.geek-has-word-image {
                    width: 190px !important;
                }
                .geek-bubble-text {
                    font-size: 12px !important;
                }
            }
        `;
        document.head.appendChild(style);
    }

    function getAnswerText(answer) {
        return answer ? answer.value : "";
    }

    function setAnswerText(answer, value) {
        if (answer) answer.value = value;
    }

    function moveCaretToEnd(element) {
        if (!element) return;
        element.focus({ preventScroll: true });
        const end = element.value.length;
        element.setSelectionRange(end, end);
    }

    function typeIntoAnswerFromKey(event, answer) {
        if (event.metaKey || event.ctrlKey || event.altKey) return false;

        let changed = false;

        if (event.key.length === 1) {
            setAnswerText(answer, getAnswerText(answer) + event.key);
            changed = true;
        } else if (event.key === "Backspace") {
            const current = getAnswerText(answer);
            if (current.length > 0) {
                setAnswerText(answer, current.slice(0, -1));
                changed = true;
            }
        } else if (event.key === "Delete") {
            return true;
        } else if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
            return true;
        }

        if (changed) {
            handleAnswerInput(answer);
            moveCaretToEnd(answer);
        }
        return changed;
    }

    function pasteIntoAnswer(text) {
        const answer = memoryModalRefs && memoryModalRefs.answer;
        if (!answer || !text) return false;

        setAnswerText(answer, getAnswerText(answer) + text);
        handleAnswerInput(answer);
        focusMemoryAnswer();
        return true;
    }

    function applyTextFallback(answer, text, start, end) {
        if (!answer || !text) return;

        answer.setRangeText(text, start, end, "end");
        handleAnswerInput(answer);
        focusMemoryAnswer();
    }

    function scheduleKeyInputFallback(event, answer) {
        if (!answer || event.isTrusted || event.isComposing || event.metaKey || event.ctrlKey || event.altKey) return;
        if (event.key.length !== 1 && event.key !== "Backspace" && event.key !== "Delete") return;

        const before = answer.value;
        const start = answer.selectionStart ?? before.length;
        const end = answer.selectionEnd ?? before.length;

        setTimeout(() => {
            if (answer.value !== before) return;

            if (event.key.length === 1) {
                applyTextFallback(answer, event.key, start, end);
            } else if (event.key === "Backspace") {
                if (start !== end) {
                    applyTextFallback(answer, "", start, end);
                } else if (start > 0) {
                    applyTextFallback(answer, "", start - 1, start);
                }
            } else if (event.key === "Delete") {
                if (start !== end) {
                    applyTextFallback(answer, "", start, end);
                } else if (start < before.length) {
                    applyTextFallback(answer, "", start, start + 1);
                }
            }
        }, 0);
    }

    function schedulePasteFallback(event, answer) {
        if (!answer || event.isTrusted || !event.clipboardData) return;

        const text = event.clipboardData.getData("text");
        if (!text) return;

        const before = answer.value;
        const start = answer.selectionStart ?? before.length;
        const end = answer.selectionEnd ?? before.length;

        setTimeout(() => {
            if (answer.value !== before) return;
            applyTextFallback(answer, text, start, end);
        }, 0);
    }

    function eventCameFromAnswer(event, answer) {
        if (event.target === answer) return true;
        return typeof event.composedPath === "function" && event.composedPath().includes(answer);
    }

    function handleMemoryModalKeydown(event) {
        if (!isMemoryModalOpen()) return false;

        const answer = memoryModalRefs && memoryModalRefs.answer;
        if (!answer) return false;

        if (event.key === "Escape") {
            event.preventDefault();
            event.stopImmediatePropagation();
            closeMemoryModal();
            return true;
        }

        if (paragraphCompletionPending) {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.stopImmediatePropagation();
                resetParagraphCompletion();
                dispatchNextWord(false);
                return true;
            }
            if (event.key === "Tab") {
                event.preventDefault();
                event.stopImmediatePropagation();
                return true;
            }
        }

        if (event.key === "Enter" || event.key === "Tab") {
            event.preventDefault();
            event.stopImmediatePropagation();
            dispatchNextWord(event.shiftKey);
            return true;
        }

        if (eventCameFromAnswer(event, answer)) {
            return false;
        }

        if (typeIntoAnswerFromKey(event, answer)) {
            event.preventDefault();
            event.stopImmediatePropagation();
            focusMemoryAnswer();
            return true;
        }

        return false;
    }

    function bindMemoryImageSwipe(image) {
        let touchStart = null;

        image.addEventListener("touchstart", event => {
            if (!window.matchMedia(MOBILE_MEMORY_MEDIA).matches || event.touches.length !== 1) {
                touchStart = null;
                return;
            }

            const touch = event.touches[0];
            touchStart = { x: touch.clientX, y: touch.clientY };
        }, { passive: true });

        image.addEventListener("touchmove", event => {
            if (!touchStart || event.touches.length !== 1) return;

            const touch = event.touches[0];
            const deltaX = touch.clientX - touchStart.x;
            const deltaY = touch.clientY - touchStart.y;
            if (Math.abs(deltaY) > 8 && Math.abs(deltaY) > Math.abs(deltaX)) {
                event.preventDefault();
            }
        }, { passive: false });

        image.addEventListener("touchend", event => {
            if (!touchStart) return;

            const touch = event.changedTouches[0];
            const deltaX = touch ? touch.clientX - touchStart.x : 0;
            const deltaY = touch ? touch.clientY - touchStart.y : 0;
            touchStart = null;

            const isVerticalSwipe =
                Math.abs(deltaY) >= MEMORY_SWIPE_MIN_DISTANCE
                && Math.abs(deltaY) > Math.abs(deltaX) * MEMORY_SWIPE_AXIS_RATIO;
            if (isVerticalSwipe) dispatchNextWord(deltaY > 0);
        }, { passive: true });

        image.addEventListener("touchcancel", () => {
            touchStart = null;
        }, { passive: true });
    }

    function createMemoryModal() {
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
                    width: min(520px, calc(100vw - 48px));
                    height: min(760px, calc(100dvh - 48px));
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
                    transition:
                        transform 1080ms cubic-bezier(0.16, 1, 0.3, 1),
                        color 420ms ease-out,
                        text-shadow 420ms ease-out;
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
                .geek-paragraph-complete {
                    position: absolute;
                    inset: 0;
                    z-index: 8;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                    background: rgba(17, 24, 39, 0.78);
                    backdrop-filter: blur(8px);
                    -webkit-backdrop-filter: blur(8px);
                    opacity: 0;
                    visibility: hidden;
                    pointer-events: none;
                    transition: opacity 260ms ease-out, visibility 260ms ease-out;
                }
                .geek-memory-card.is-paragraph-complete .geek-paragraph-complete {
                    opacity: 1;
                    visibility: visible;
                }
                .geek-paragraph-check {
                    position: relative;
                    display: grid;
                    place-items: center;
                    width: 72px;
                    height: 72px;
                    border: 2px solid rgba(52, 211, 153, 0.9);
                    border-radius: 50%;
                    color: #6ee7b7;
                    font-size: 42px;
                    font-weight: 700;
                    line-height: 1;
                    transform: scale(0.62);
                    opacity: 0;
                }
                .geek-memory-card.is-paragraph-complete .geek-paragraph-check {
                    animation: geek-paragraph-check-in 620ms cubic-bezier(0.16, 1, 0.3, 1) 120ms forwards;
                }
                .geek-paragraph-spark {
                    position: absolute;
                    left: 50%;
                    top: 50%;
                    width: 3px;
                    height: 18px;
                    border-radius: 2px;
                    background: #facc15;
                    opacity: 0;
                    transform: translate(-50%, -50%) rotate(var(--spark-angle)) translateY(-54px) scaleY(0.5);
                    transform-origin: center;
                }
                .geek-memory-card.is-paragraph-complete .geek-paragraph-spark {
                    animation: geek-paragraph-spark 720ms ease-out 180ms forwards;
                }
                .geek-paragraph-title {
                    margin: 8px 0 0;
                    color: #f8fafc;
                    font-size: 28px;
                    font-weight: 750;
                    line-height: 1.2;
                }
                .geek-paragraph-message {
                    margin: 0;
                    color: rgba(226, 232, 240, 0.78);
                    font-size: 16px;
                    line-height: 1.4;
                }
                @keyframes geek-paragraph-check-in {
                    0% { transform: scale(0.62); opacity: 0; }
                    68% { transform: scale(1.08); opacity: 1; }
                    100% { transform: scale(1); opacity: 1; }
                }
                @keyframes geek-paragraph-spark {
                    0% { opacity: 0; transform: translate(-50%, -50%) rotate(var(--spark-angle)) translateY(-44px) scaleY(0.45); }
                    35% { opacity: 1; }
                    100% { opacity: 0; transform: translate(-50%, -50%) rotate(var(--spark-angle)) translateY(-72px) scaleY(1); }
                }
                @media (prefers-reduced-motion: reduce) {
                    .geek-memory-card.is-paragraph-complete .geek-paragraph-check,
                    .geek-memory-card.is-paragraph-complete .geek-paragraph-spark {
                        animation-duration: 1ms;
                        animation-delay: 0ms;
                    }
                }
                @media (max-height: 680px) {
                    .geek-memory-card {
                        padding: 12px;
                    }
                    .geek-memory-word {
                        margin-bottom: 8px;
                        font-size: clamp(28px, 5vw, 42px);
                    }
                    .geek-memory-translation {
                        margin-top: 8px;
                        font-size: 16px;
                        line-height: 1.35;
                    }
                    .geek-memory-example {
                        margin-top: 8px;
                        padding-top: 8px;
                    }
                    .geek-memory-example-en {
                        font-size: 15px;
                        line-height: 1.35;
                    }
                    .geek-memory-example-zh {
                        margin-top: 3px;
                        font-size: 13px;
                        line-height: 1.35;
                    }
                    .geek-memory-answer {
                        height: 42px;
                        margin-top: 10px;
                        font: 16px/42px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    }
                }
                .geek-memory-context {
                    position: absolute;
                    right: max(24px, env(safe-area-inset-right));
                    top: 50%;
                    width: min(360px, calc((100vw - 620px) / 2 - 32px));
                    max-height: calc(100vh - 64px);
                    padding: 18px 20px;
                    box-sizing: border-box;
                    color: rgba(241, 245, 249, 0.9);
                    background: rgba(15, 23, 42, 0.58);
                    border-radius: 8px;
                    line-height: 1.72;
                    font: 18px/1.72 Georgia, "Times New Roman", serif;
                    overflow: auto;
                    transform: translateY(-50%);
                    pointer-events: auto;
                    user-select: text;
                    -webkit-user-select: text;
                }
                .geek-memory-context:empty {
                    display: none;
                }
                .geek-memory-context mark {
                    padding: 0 4px;
                    border-radius: 4px;
                    background: rgba(250, 204, 21, 0.22);
                    color: #fef08a;
                }
                @media (max-width: 1180px) {
                    .geek-memory-shell {
                        align-items: flex-start;
                        padding-top: 18px;
                        overflow: auto;
                    }
                    .geek-memory-context {
                        position: fixed;
                        left: 24px;
                        right: 24px;
                        top: auto;
                        bottom: 18px;
                        width: auto;
                        max-height: 28vh;
                        transform: none;
                        font-size: 16px;
                    }
                }
                @media (max-width: 720px) {
                    .geek-memory-image {
                        touch-action: none;
                        -webkit-user-drag: none;
                    }
                    .geek-memory-context {
                        display: none;
                    }
                }
            </style>
            <div class="geek-memory-shell">
              <div class="geek-memory-card" role="dialog" aria-modal="true">
                <h2 class="geek-memory-word" id="geek-memory-word" title="点击朗读单词和释义"></h2>
                <img class="geek-memory-image" id="geek-memory-image" alt="" draggable="false">
                <p class="geek-memory-translation" id="geek-memory-translation"></p>
                <div class="geek-memory-example" id="geek-memory-example" hidden>
                  <p class="geek-memory-example-en" id="geek-memory-example-en" title="点击朗读例句"></p>
                  <p class="geek-memory-example-zh" id="geek-memory-example-zh"></p>
                </div>
                <input class="geek-memory-answer" id="geek-memory-answer" type="text" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="输入单词或英文例句">
                <div class="geek-paragraph-complete" aria-live="polite" aria-hidden="true">
                  <div class="geek-paragraph-check">
                    <span aria-hidden="true">✓</span>
                    <i class="geek-paragraph-spark" style="--spark-angle: 0deg"></i>
                    <i class="geek-paragraph-spark" style="--spark-angle: 60deg"></i>
                    <i class="geek-paragraph-spark" style="--spark-angle: 120deg"></i>
                    <i class="geek-paragraph-spark" style="--spark-angle: 180deg"></i>
                    <i class="geek-paragraph-spark" style="--spark-angle: 240deg"></i>
                    <i class="geek-paragraph-spark" style="--spark-angle: 300deg"></i>
                  </div>
                  <p class="geek-paragraph-title">本段完成</p>
                  <p class="geek-paragraph-message">做得很好，继续保持</p>
                </div>
              </div>
              <aside class="geek-memory-context" id="geek-memory-context"></aside>
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
            context: shadow.getElementById("geek-memory-context"),
            paragraphComplete: shadow.querySelector(".geek-paragraph-complete"),
            answer,
        };

        shell.addEventListener("click", event => {
            if (event.target === shell) closeMemoryModal();
        });
        card.addEventListener("click", event => {
            if (event.target === card) requestAnimationFrame(focusMemoryAnswer);
        });
        memoryModalRefs.word.addEventListener("click", () => {
            speakVocabularyData(currentMemoryData);
            requestAnimationFrame(focusMemoryAnswer);
        });
        memoryModalRefs.exampleEnglish.addEventListener("click", () => {
            speakExampleData(currentMemoryData);
            requestAnimationFrame(focusMemoryAnswer);
        });
        bindMemoryImageSwipe(memoryModalRefs.image);
        document.body.appendChild(modal);

        answer.addEventListener("input", handleAnswerInput);
        answer.addEventListener("keydown", event => {
            if (event.key === "Escape") {
                event.preventDefault();
                closeMemoryModal();
                return;
            }

            if (paragraphCompletionPending) {
                if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    resetParagraphCompletion();
                    dispatchNextWord(false);
                    return;
                }
                if (event.key === "Tab") {
                    event.preventDefault();
                    return;
                }
            }

            if (event.key === "Enter" || event.key === "Tab") {
                event.preventDefault();
                dispatchNextWord(event.shiftKey);
                return;
            }

            scheduleKeyInputFallback(event, answer);
        });
        answer.addEventListener("paste", event => schedulePasteFallback(event, answer));

        window.geekMemoryInput = {
            isOpen: isMemoryModalOpen,
            handleKey: event => {
                if (!isMemoryModalOpen()) return false;
                return handleMemoryModalKeydown(event);
            },
            handlePaste: event => {
                if (!isMemoryModalOpen()) return false;
                if (eventCameFromAnswer(event, answer)) return false;
                const text = event.clipboardData ? event.clipboardData.getData("text") : "";
                return pasteIntoAnswer(text);
            },
            focus: focusMemoryAnswer,
        };

        window.geekMemoryOverlay = Object.assign(window.geekMemoryOverlay || {}, {
            openVocabulary: openVocabularySession,
        });
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
                moveCaretToEnd(answer);
            }
        });
    }

    function resetMemoryAnimation() {
        if (!memoryModalRefs) return;
        const { card, word } = memoryModalRefs;
        if (memoryAnimationFrame) {
            cancelAnimationFrame(memoryAnimationFrame);
            memoryAnimationFrame = null;
        }
        if (card) card.classList.remove("is-memorizing");
        if (word) {
            word.classList.remove("is-memorized");
            word.style.removeProperty("--geek-memory-word-drop");
        }
    }

    function resetParagraphCompletion() {
        paragraphCompletionPending = false;
        if (!memoryModalRefs) return;
        memoryModalRefs.card.classList.remove("is-paragraph-complete");
        memoryModalRefs.paragraphComplete.setAttribute("aria-hidden", "true");
    }

    function showParagraphCompletion() {
        if (!memoryModalRefs) return;
        paragraphCompletionPending = true;
        memoryModalRefs.paragraphComplete.setAttribute("aria-hidden", "false");
        memoryModalRefs.card.classList.add("is-paragraph-complete");
    }

    function isCurrentPageParagraphEnd() {
        return !memorySession
            && window.geekWordControls
            && typeof window.geekWordControls.isParagraphEnd === "function"
            && window.geekWordControls.isParagraphEnd();
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
        memoryAnimationFrame = requestAnimationFrame(() => {
            memoryAnimationFrame = null;
            if (!isMemoryModalOpen()) return;
            card.classList.add("is-memorizing");
            word.classList.add("is-memorized");
        });
    }

    function updateMemoryModal(data, options = {}) {
        if (!data || !memoryModalRefs) return;
        const previousKey = memoryDataKey(currentMemoryData);
        const nextKey = memoryDataKey(data);
        const isSameOpenCard = isMemoryModalOpen() && previousKey && previousKey === nextKey;

        if (isSameOpenCard && !options.force) return;

        currentMemoryData = data;
        const { word, image, translation, example, exampleEnglish, exampleChinese, context, answer } = memoryModalRefs;

        resetParagraphCompletion();
        resetMemoryAnimation();
        word.textContent = data.displayWord || data.entry.word;
        image.classList.toggle("is-missing", !data.entry.url);
        if (data.entry.url) {
            image.src = data.entry.url;
        } else {
            image.removeAttribute("src");
        }
        image.alt = `${data.displayWord || data.entry.word} image`;
        translation.textContent = data.translationText;
        const spoken = data.entry.spoken || {};
        example.hidden = !(spoken.en && spoken.zh);
        exampleEnglish.textContent = spoken.en || "";
        exampleChinese.textContent = spoken.zh || "";
        renderContextText(context, data.contextText, data.displayWord || data.entry.word);

        if (options.resetAnswer !== false) {
            setAnswerText(answer, "");
            answer.classList.remove("is-correct", "is-wrong");
            clearTimeout(autoAdvanceTimer);
        }

        if (isMemoryModalOpen() && options.focus !== false) {
            focusMemoryAnswer();
        }
    }

    function openMemoryModal(data, options = {}) {
        const modal = memoryModalRefs && memoryModalRefs.modal;
        if (!options.preserveSession) memorySession = null;
        updateMemoryModal(data, { force: true, resetAnswer: true, focus: false });
        modal.classList.add("open");
        focusMemoryAnswer();
        if (options.speak) speakMemoryData(data);
    }

    function vocabularyMemoryData(item) {
        const displayWord = (item && item.word || "").trim();
        const entry = findEntry(displayWord) || { word: displayWord, topic: "", url: "" };
        return {
            entry,
            displayWord,
            translationText: (item && item.trans || "").trim(),
            contextText: "",
        };
    }

    function speakMemoryData(data) {
        if (!data || !window.geekWordControls || typeof window.geekWordControls.speakMemory !== "function") {
            return false;
        }
        return window.geekWordControls.speakMemory(
            data.displayWord || data.entry.word,
            data.translationText || "",
            data.entry.spoken || {},
        );
    }

    function speakVocabularyData(data) {
        if (!data || !window.geekWordControls || typeof window.geekWordControls.speakVocabulary !== "function") return false;
        return window.geekWordControls.speakVocabulary(
            data.displayWord || data.entry.word,
            data.translationText || "",
        );
    }

    function speakExampleData(data) {
        if (!data || !window.geekWordControls || typeof window.geekWordControls.speakExample !== "function") return false;
        return window.geekWordControls.speakExample(data.entry.spoken || {});
    }

    function openVocabularySession(items, startIndex = 0) {
        const sessionItems = Array.isArray(items) ? items.filter(item => item && item.word) : [];
        if (!sessionItems.length) return false;

        const safeIndex = Number.isInteger(startIndex) && startIndex >= 0 && startIndex < sessionItems.length
            ? startIndex
            : 0;
        memorySession = { type: "vocabulary", items: sessionItems, index: safeIndex };
        const data = vocabularyMemoryData(sessionItems[safeIndex]);
        openMemoryModal(data, { preserveSession: true });
        speakMemoryData(data);
        return true;
    }

    function stepMemorySession(goBackward = false) {
        if (!memorySession || memorySession.type !== "vocabulary" || !memorySession.items.length) return false;

        const reverseOrder = window.geekWordControls
            && typeof window.geekWordControls.getReviewOrder === "function"
            && window.geekWordControls.getReviewOrder() === "reverse";
        let direction = reverseOrder ? -1 : 1;
        if (goBackward) direction *= -1;
        memorySession.index =
            (memorySession.index + direction + memorySession.items.length) % memorySession.items.length;
        const data = vocabularyMemoryData(memorySession.items[memorySession.index]);
        updateMemoryModal(data, { force: true, resetAnswer: true });
        speakMemoryData(data);
        return true;
    }

    function closeMemoryModal() {
        const modal = memoryModalRefs && memoryModalRefs.modal;
        const answer = memoryModalRefs && memoryModalRefs.answer;
        if (answer) answer.blur();
        if (modal) modal.classList.remove("open");
        memorySession = null;
        resetParagraphCompletion();
        resetMemoryAnimation();
        clearTimeout(autoAdvanceTimer);
    }

    function dispatchNextWord(goBackward = false) {
        if (stepMemorySession(goBackward)) {
            focusMemoryAnswer();
            return;
        }

        if (window.geekWordControls && typeof window.geekWordControls.step === "function") {
            window.geekWordControls.step(goBackward, { speak: false });
            focusMemoryAnswer();
            return;
        }

        document.dispatchEvent(new KeyboardEvent("keydown", {
            key: "Tab",
            code: "Tab",
            bubbles: true,
            cancelable: true,
            shiftKey: goBackward,
        }));
        focusMemoryAnswer();
    }

    function handleAnswerInput(eventOrInput) {
        if (!currentMemoryData) return;

        const input = eventOrInput.currentTarget || eventOrInput;
        const typed = answerKey(getAnswerText(input));
        const targets = [
            currentMemoryData.displayWord || currentMemoryData.entry.word,
            currentMemoryData.entry.spoken?.en || "",
        ].map(answerKey).filter(Boolean);
        input.classList.remove("is-correct", "is-wrong");
        resetParagraphCompletion();
        resetMemoryAnimation();
        clearTimeout(autoAdvanceTimer);

        if (!typed) return;
        if (targets.includes(typed)) {
            input.classList.add("is-correct");
            playCorrectMemoryAnimation();
            if (isCurrentPageParagraphEnd()) {
                showParagraphCompletion();
            } else {
                autoAdvanceTimer = setTimeout(() => dispatchNextWord(false), CORRECT_ADVANCE_DELAY);
            }
        } else if (!targets.some(target => target.startsWith(typed))) {
            input.classList.add("is-wrong");
        }
    }

    function placeBubble(bubble) {
        if (!bubble || !bubble.classList.contains("geek-has-word-image")) return;

        const wordElement = bubble.parentElement;
        if (!wordElement) return;

        const bubbleRect = bubble.getBoundingClientRect();
        const wordRect = wordElement.getBoundingClientRect();
        const bubbleHeight = bubbleRect.height || 0;
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

    function placeActiveBubble() {
        if (activeBubble) placeBubble(activeBubble);
    }

    function enhanceBubble(wordElement) {
        const bubble = wordElement.querySelector(".translation-bubble");
        if (!bubble || bubble.dataset.wordImageReady === "1") return;

        bubble.dataset.wordImageReady = "1";
        const entry = findEntry(wordFromElement(wordElement));
        if (!entry) return;

        const translationText = bubble.textContent.trim();
        const displayWord = displayWordFromElement(wordElement);
        const contextText = contextTextFromElement(wordElement);
        bubble.textContent = "";
        bubble.classList.add("geek-has-word-image");
        bubbleMemoryData.set(bubble, { entry, translationText, displayWord, contextText });

        const image = document.createElement("img");
        image.className = "geek-bubble-image";
        image.src = entry.url;
        image.alt = `${entry.word} image`;
        image.loading = "lazy";
        image.draggable = false;
        image.addEventListener("load", () => placeBubble(bubble));

        const text = document.createElement("span");
        text.className = "geek-bubble-text";
        text.textContent = translationText;

        bubble.appendChild(image);
        bubble.appendChild(text);

        wordElement.addEventListener("mouseenter", () => {
            activeBubble = bubble;
            requestAnimationFrame(() => placeBubble(bubble));
        });
        wordElement.addEventListener("focus", () => {
            activeBubble = bubble;
            requestAnimationFrame(() => placeBubble(bubble));
        });
        wordElement.addEventListener("mouseleave", () => {
            if (!bubble.classList.contains("force-show") && activeBubble === bubble) {
                activeBubble = null;
                bubble.classList.remove("geek-bubble-below");
            }
        });
    }

    function isVisibleBubble(bubble) {
        if (!bubble) return false;
        const styles = window.getComputedStyle(bubble);
        return Number(styles.opacity) > 0.5;
    }

    function handleImageCoordinateClick(event) {
        if (event.target && event.target.closest && event.target.closest("#geek-memory-modal")) return;

        for (const image of document.querySelectorAll(".translation-bubble.geek-has-word-image .geek-bubble-image")) {
            const bubble = image.closest(".translation-bubble");
            if (!isVisibleBubble(bubble)) continue;

            const rect = image.getBoundingClientRect();
            const hit =
                event.clientX >= rect.left &&
                event.clientX <= rect.right &&
                event.clientY >= rect.top &&
                event.clientY <= rect.bottom;

            if (!hit) continue;

            const data = bubbleMemoryData.get(bubble);
            if (!data) return;

            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            openMemoryModal(data, { speak: true });
            return;
        }
    }

    function clearForcedImageBubbles() {
        let cleared = false;
        document.querySelectorAll(".translation-bubble.geek-has-word-image.force-show").forEach(bubble => {
            bubble.classList.remove("force-show", "geek-bubble-below");
            cleared = true;
        });
        if (cleared) activeBubble = null;
    }

    function handleBlankClickCloseBubble(event) {
        const target = event.target;
        if (target && target.closest && (
            target.closest("strong, em") ||
            target.closest("#geek-memory-modal") ||
            target.closest("#geek-vocab-notebook") ||
            target.closest("#geek-tts-panel") ||
            target.closest("#geek-floating-dock")
        )) {
            return;
        }

        clearForcedImageBubbles();
    }

    function syncMemoryModalToBubble(bubble) {
        if (!isMemoryModalOpen()) return;
        if (memorySession && memorySession.type === "vocabulary") return;
        const data = bubbleMemoryData.get(bubble);
        if (!data) return;
        if (memoryDataKey(currentMemoryData) === memoryDataKey(data)) return;
        updateMemoryModal(data, { resetAnswer: true });
        speakMemoryData(data);
    }

    function enhanceAllBubbles() {
        document.querySelectorAll("strong, em").forEach(enhanceBubble);
    }

    function observeBubbleCreation() {
        const observer = new MutationObserver(mutations => {
            for (const mutation of mutations) {
                if (mutation.type === "childList" && mutation.addedNodes.length) {
                    requestAnimationFrame(enhanceAllBubbles);
                    continue;
                }

                if (mutation.type === "attributes" && mutation.target.classList.contains("translation-bubble")) {
                    const bubble = mutation.target;
                    if (bubble.classList.contains("force-show")) {
                        activeBubble = bubble;
                        requestAnimationFrame(() => placeBubble(bubble));
                        syncMemoryModalToBubble(bubble);
                    } else if (activeBubble === bubble) {
                        activeBubble = null;
                        bubble.classList.remove("geek-bubble-below");
                    }
                }
            }
        });

        observer.observe(document.body, {
            attributes: true,
            attributeFilter: ["class"],
            childList: true,
            subtree: true,
        });

        window.addEventListener("scroll", placeActiveBubble, { passive: true });
        window.addEventListener("resize", placeActiveBubble);
        document.addEventListener("click", handleImageCoordinateClick, true);
        document.addEventListener("click", handleBlankClickCloseBubble, true);
    }

    async function init() {
        injectStyles();
        createMemoryModal();

        try {
            if (window.__WORD_IMAGE_INDEX__) {
                imageIndex = prepareImageIndex(window.__WORD_IMAGE_INDEX__);
            } else {
                const response = await fetch(MANIFEST_URL, { cache: "no-store" });
                if (!response.ok) throw new Error(`Manifest request failed: ${response.status}`);
                imageIndex = prepareImageIndex(await response.json());
            }
            enhanceAllBubbles();
            setTimeout(enhanceAllBubbles, 600);
            setTimeout(enhanceAllBubbles, 1600);
            observeBubbleCreation();
        } catch (error) {
            console.warn("[word-image-preview] Failed to load image manifest", error);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
