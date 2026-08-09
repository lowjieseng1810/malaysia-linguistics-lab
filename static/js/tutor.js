/* =========================================
   Malaysian Linguistics Lab
   AI Tutor Widget — Client Interaction
   ========================================= */

document.addEventListener("DOMContentLoaded", function () {

    const widgetRoot =
        document.getElementById("ai-tutor-widget");

    const toggleButton =
        document.getElementById("ai-tutor-toggle-button");

    const closeButton =
        document.getElementById("ai-tutor-close-button");

    const clearButton =
        document.getElementById("ai-tutor-clear-button");

    const panel =
        document.getElementById("ai-tutor-panel");

    const quickActionsContainer =
        document.querySelector(".ai-tutor-quick-actions");

    const messagesContainer =
        document.getElementById("ai-tutor-messages");

    const notesArea =
        document.getElementById("ai-tutor-notes-area");

    const emptyState =
        document.getElementById("ai-tutor-empty-state");

    const form =
        document.getElementById("ai-tutor-form");

    const input =
        document.getElementById("ai-tutor-input");

    const sendButton =
        document.getElementById("ai-tutor-send-button");

    if (
        !widgetRoot ||
        !toggleButton ||
        !closeButton ||
        !panel ||
        !messagesContainer ||
        !form ||
        !input ||
        !sendButton
    ) {
        return;
    }

    const REQUEST_TIMEOUT_MS = 45000;

    const MAX_HISTORY_MESSAGES = 12;

    const MAX_PERSISTED_MESSAGES = 60;

    let isSending = false;

    let pendingAsk = null;

    let conversationHistory = [];

    // Every rendered bubble is also kept here (type/text/time) so the
    // conversation can be restored after navigating to another page,
    // without needing any backend/database changes.
    let renderedMessages = [];

    const STORAGE_KEY =
        "ai_tutor_history_v1_" +
        (widgetRoot.dataset.username || "guest");

    const MASCOT_URL =
        widgetRoot.dataset.mascotUrl || "";

    const FREE_CHAT_INTRO =
        "I'm ready for Free Chat. Ask me anything about languages, " +
        "linguistics, language learning, or Malaysian language heritage " +
        "\u2014 for example tones, morphology, dialects, vocabulary, or " +
        "pronunciation. What would you like to explore?";

    let activeMode = null;

    if (typeof window !== "undefined" && typeof window.marked !== "undefined") {
        try {
            window.marked.setOptions({
                breaks: true,
                gfm: true
            });
        } catch (configError) {
            // Ignore - fallback formatter still works.
        }
    }


    /* =========================================
       PANEL OPEN / CLOSE
       ========================================= */

    function notifyMascotLayout() {
        try {
            window.dispatchEvent(new CustomEvent("mmleLayoutChanged", {
                detail: { source: "ai-tutor" }
            }));
        } catch (err) {
            // Ignore older browsers without CustomEvent.
        }
    }

    function isVisibleBox(el) {
        if (!el) {
            return false;
        }
        const style = window.getComputedStyle(el);
        if (
            style.display === "none" ||
            style.visibility === "hidden" ||
            Number(style.opacity) === 0
        ) {
            return false;
        }
        const r = el.getBoundingClientRect();
        return r.width > 4 && r.height > 4;
    }

    /*
       Keep the floating AI Tutor button ABOVE bottom status chrome
       (e.g. “Finding your place in the world”) with clear separation.
       Positioning only — does not call any Tutor API.
    */
    function positionTutorFab() {
        const vh = window.innerHeight || 800;
        const mobile = (window.innerWidth || 800) < 576;
        let fabBottom = mobile ? 112 : 128;
        // Generous separation so status copy stays fully readable.
        const gap = mobile ? 36 : 48;

        const statusCandidates = [
            document.getElementById("globe-status"),
            document.querySelector(".globe-status"),
            document.querySelector(".earth-loading-status"),
            document.querySelector("[data-earth-status]")
        ];
        statusCandidates.forEach(function (status) {
            if (!isVisibleBox(status)) {
                return;
            }
            const r = status.getBoundingClientRect();
            // Only react when the status sits in the lower viewport band.
            if (r.bottom > vh * 0.5) {
                const clearOfStatus = Math.ceil(vh - r.top + gap);
                fabBottom = Math.max(fabBottom, clearOfStatus);
            }
        });

        // Stay reachable; do not climb into the upper half.
        fabBottom = Math.min(fabBottom, Math.floor(vh * 0.48));
        fabBottom = Math.max(fabBottom, mobile ? 104 : 120);

        const fabHeight = Math.max(
            toggleButton.getBoundingClientRect().height || 52,
            52
        );
        const panelBottom = fabBottom + Math.round(fabHeight) + 16;

        document.documentElement.style.setProperty(
            "--mmle-tutor-fab-bottom",
            fabBottom + "px"
        );
        document.documentElement.style.setProperty(
            "--mmle-tutor-panel-bottom",
            panelBottom + "px"
        );

        notifyMascotLayout();
    }

    function openTutorPanel() {

        panel.classList.add("is-open");

        toggleButton.setAttribute(
            "aria-expanded",
            "true"
        );

        positionTutorFab();

        window.setTimeout(function () {
            input.focus();
        }, 260);
    }

    function closeTutorPanel() {

        panel.classList.remove("is-open");

        toggleButton.setAttribute(
            "aria-expanded",
            "false"
        );

        positionTutorFab();
    }

    toggleButton.addEventListener(
        "click",
        function () {

            if (panel.classList.contains("is-open")) {
                closeTutorPanel();
            } else {
                openTutorPanel();
            }
        }
    );

    closeButton.addEventListener(
        "click",
        closeTutorPanel
    );


    /* =========================================
       PAGE CONTEXT
       Reads lang_key / level_num from the widget
       root itself, so a future step can populate
       these data attributes without any change
       needed here.
       ========================================= */

    function getPageContext() {

        return {
            langKey:
                widgetRoot.dataset.langKey || null,

            levelNum:
                widgetRoot.dataset.levelNum || null
        };
    }

    function getCsrfToken() {

        return widgetRoot.dataset.csrfToken || "";
    }


    /* =========================================
       TIME FORMATTING
       ========================================= */

    function getCurrentTimeLabel() {

        const now = new Date();

        let hours = now.getHours();

        const minutes = now.getMinutes()
            .toString()
            .padStart(2, "0");

        const period = hours >= 12 ? "PM" : "AM";

        hours = hours % 12;

        if (hours === 0) {
            hours = 12;
        }

        return hours + ":" + minutes + " " + period;
    }


    /* =========================================
       EMPTY STATE
       ========================================= */

    function hideEmptyState() {

        if (emptyState && !emptyState.hidden) {
            emptyState.hidden = true;
            emptyState.style.display = "none";
        }
    }

    function showEmptyState() {

        if (emptyState) {
            emptyState.hidden = false;
            emptyState.style.display = "";
        }

        // The conversation area may still be scrolled down from a
        // previous (now-cleared) conversation. Without this, the short
        // welcome card can render scrolled out of view above the
        // visible viewport instead of at the top where it belongs.
        if (notesArea) {
            notesArea.scrollTop = 0;
        }
    }


    /* =========================================
       PERSISTENT CONVERSATION HISTORY
       Conversation survives page navigation
       (sessionStorage), namespaced per logged-in
       user so a shared browser tab never leaks
       one learner's chat into another's session.
       ========================================= */

    function persistState() {

        try {
            const payload = {
                messages: renderedMessages.slice(-MAX_PERSISTED_MESSAGES),
                history: conversationHistory.slice(-MAX_HISTORY_MESSAGES)
            };

            window.sessionStorage.setItem(
                STORAGE_KEY,
                JSON.stringify(payload)
            );
        } catch (storageError) {
            // Storage unavailable (private browsing, quota, etc.) -
            // the tutor still works, it just won't persist across
            // page loads.
        }
    }

    function loadPersistedState() {

        try {
            const raw = window.sessionStorage.getItem(STORAGE_KEY);

            if (!raw) {
                return null;
            }

            const parsed = JSON.parse(raw);

            if (!parsed || typeof parsed !== "object") {
                return null;
            }

            return parsed;
        } catch (storageError) {
            return null;
        }
    }

    function clearPersistedState() {

        try {
            window.sessionStorage.removeItem(STORAGE_KEY);
        } catch (storageError) {
            // Ignore.
        }
    }


    /* =========================================
       MESSAGE RENDERING (chat bubble style)
       ========================================= */

    function buildAvatarElement() {

        const avatar =
            document.createElement("div");

        avatar.className = "ai-tutor-avatar";
        avatar.setAttribute("aria-hidden", "true");

        const image =
            document.createElement("img");

        image.src = MASCOT_URL;
        image.alt = "";
        image.decoding = "async";

        avatar.appendChild(image);

        return avatar;
    }


    /* =========================================
       MESSAGE FORMATTING
       Full Markdown (tables, lists, code blocks,
       bold/italic) via marked.js, sanitized with
       DOMPurify before ever touching innerHTML.
       Falls back to a small safe formatter if
       either library failed to load (e.g. offline).
       ========================================= */

    function escapeHtml(rawText) {

        const div = document.createElement("div");

        div.textContent = rawText;

        return div.innerHTML;
    }

    function formatInlineTextFallback(lineText) {

        return lineText.replace(
            /\*\*(.+?)\*\*/g,
            "<strong>$1</strong>"
        );
    }

    function formatMessageHtmlFallback(rawText) {

        const escaped = escapeHtml(rawText || "");

        const lines = escaped.split(/\n/);

        let html = "";
        let inList = false;

        lines.forEach(function (line) {

            const trimmed = line.trim();

            const bulletMatch =
                /^[-*]\s+(.*)/.exec(trimmed) ||
                /^\d+[.)]\s+(.*)/.exec(trimmed);

            if (bulletMatch) {

                if (!inList) {
                    html += "<ul class=\"ai-tutor-bullet-list\">";
                    inList = true;
                }

                html += "<li>" +
                    formatInlineTextFallback(bulletMatch[1]) +
                    "</li>";

                return;
            }

            if (inList) {
                html += "</ul>";
                inList = false;
            }

            if (trimmed !== "") {
                html += "<p>" +
                    formatInlineTextFallback(trimmed) +
                    "</p>";
            }
        });

        if (inList) {
            html += "</ul>";
        }

        return html;
    }

    function formatMessageHtml(rawText) {

        const text = rawText || "";

        const markdownAvailable =
            typeof window.marked !== "undefined" &&
            typeof window.DOMPurify !== "undefined";

        if (markdownAvailable) {

            try {
                const rawHtml = window.marked.parse(text);

                return window.DOMPurify.sanitize(rawHtml, {
                    ALLOWED_ATTR: ["href", "target", "rel", "class"]
                });
            } catch (markdownError) {
                // Fall through to the plain-text formatter below.
            }
        }

        return formatMessageHtmlFallback(text);
    }

    function renderMessage(type, text, options) {

        const settings = options || {};

        hideEmptyState();

        const messageElement =
            document.createElement("div");

        messageElement.className =
            "ai-tutor-message ai-tutor-message-" + type;

        if (type === "assistant" || type === "error") {
            messageElement.appendChild(
                buildAvatarElement()
            );
        }

        const bubble =
            document.createElement("div");

        bubble.className = "ai-tutor-bubble";

        const bubbleText =
            document.createElement("div");

        bubbleText.className = "ai-tutor-bubble-text";
        bubbleText.innerHTML = formatMessageHtml(text);

        bubble.appendChild(bubbleText);

        const meta =
            document.createElement("div");

        meta.className = "ai-tutor-meta";

        const time =
            document.createElement("span");

        time.className = "ai-tutor-time";
        time.textContent = settings.timeLabel || getCurrentTimeLabel();

        meta.appendChild(time);

        if (type === "user") {
            const ticks =
                document.createElement("span");

            ticks.className = "ai-tutor-ticks";
            ticks.setAttribute("aria-hidden", "true");
            ticks.textContent = "\u2713\u2713";

            meta.appendChild(ticks);
        }

        bubble.appendChild(meta);

        messageElement.appendChild(bubble);

        messagesContainer.appendChild(
            messageElement
        );

        if (!settings.skipPersist) {

            renderedMessages.push({
                type: type,
                text: text,
                timeLabel: time.textContent
            });

            persistState();
        }

        scrollMessagesToBottom();

        return messageElement;
    }

    function rememberHistory(role, text) {

        if (!text) {
            return;
        }

        conversationHistory.push({
            role: role,
            content: text
        });

        if (conversationHistory.length > MAX_HISTORY_MESSAGES) {
            conversationHistory =
                conversationHistory.slice(-MAX_HISTORY_MESSAGES);
        }

        persistState();
    }

    function restoreConversation() {

        const saved = loadPersistedState();

        if (!saved || !Array.isArray(saved.messages) || !saved.messages.length) {
            return;
        }

        saved.messages.forEach(function (item) {

            if (!item || typeof item.text !== "string" || !item.text) {
                return;
            }

            const type =
                (item.type === "user" || item.type === "error")
                    ? item.type
                    : "assistant";

            renderMessage(type, item.text, {
                timeLabel: item.timeLabel,
                skipPersist: true
            });
        });

        renderedMessages = saved.messages.slice(-MAX_PERSISTED_MESSAGES);

        if (Array.isArray(saved.history)) {
            conversationHistory = saved.history.slice(-MAX_HISTORY_MESSAGES);
        }
    }

    function startNewConversation() {

        messagesContainer.innerHTML = "";

        renderedMessages = [];

        conversationHistory = [];

        clearPersistedState();

        showEmptyState();

        input.value = "";

        input.focus();
    }

    if (clearButton) {

        clearButton.addEventListener(
            "click",
            function () {

                if (isSending) {
                    return;
                }

                startNewConversation();
            }
        );
    }

    function showTypingIndicator() {

        hideEmptyState();

        const messageElement =
            document.createElement("div");

        messageElement.className =
            "ai-tutor-message ai-tutor-message-assistant " +
            "ai-tutor-message-typing";

        messageElement.appendChild(
            buildAvatarElement()
        );

        const bubble =
            document.createElement("div");

        bubble.className =
            "ai-tutor-bubble ai-tutor-typing-bubble";

        for (let dotIndex = 0; dotIndex < 3; dotIndex++) {
            const dot =
                document.createElement("span");

            dot.className = "ai-tutor-typing-dot";

            bubble.appendChild(dot);
        }

        messageElement.appendChild(bubble);

        messagesContainer.appendChild(
            messageElement
        );

        scrollMessagesToBottom();

        return messageElement;
    }

    function scrollMessagesToBottom() {

        const scrollTarget = notesArea || messagesContainer;

        if (!scrollTarget) {
            return;
        }

        window.requestAnimationFrame(function () {

            try {
                scrollTarget.scrollTo({
                    top: scrollTarget.scrollHeight,
                    behavior: "smooth"
                });
            } catch (scrollError) {
                scrollTarget.scrollTop = scrollTarget.scrollHeight;
            }
        });
    }


    /* =========================================
       RESTORE PERSISTED CONVERSATION ON LOAD
       ========================================= */

    restoreConversation();


    /* =========================================
       SENDING STATE
       Disables the input, send button, quick
       actions AND suggestion chips together, so
       nothing can be double-clicked into firing
       two overlapping requests (no duplicate
       replies, no dead clicks mid-request).
       ========================================= */

    function setActiveMode(mode) {
        activeMode = mode || null;
        const actionButtons = panel.querySelectorAll(".ai-tutor-quick-action");
        actionButtons.forEach(function (button) {
            const on = mode && button.dataset.mode === mode;
            button.classList.toggle("is-active", !!on);
            button.setAttribute("aria-pressed", on ? "true" : "false");
        });
    }

    function setSendingState(sending) {

        isSending = sending;

        input.disabled = sending;

        sendButton.disabled = sending;

        panel.classList.toggle("is-sending", sending);

        const actionButtons = panel.querySelectorAll(
            ".ai-tutor-quick-action, .ai-tutor-suggestion-chip"
        );

        actionButtons.forEach(function (button) {
            button.disabled = sending;
        });

        if (clearButton) {
            clearButton.disabled = sending;
        }
    }

    function renderQuizCard(quiz) {
        if (!quiz || !quiz.options || !quiz.options.length) {
            return null;
        }
        hideEmptyState();

        const row = document.createElement("div");
        row.className = "ai-tutor-message-row ai-tutor-message-row--assistant";

        const bubble = document.createElement("div");
        bubble.className = "ai-tutor-message ai-tutor-message--assistant ai-tutor-quiz-card";

        const title = document.createElement("div");
        title.className = "ai-tutor-quiz-kicker";
        title.textContent = "QUIZ";

        const question = document.createElement("p");
        question.className = "ai-tutor-quiz-question";
        question.textContent = quiz.question || "Choose the best answer.";

        const optionsWrap = document.createElement("div");
        optionsWrap.className = "ai-tutor-quiz-options";
        optionsWrap.setAttribute("role", "group");
        optionsWrap.setAttribute("aria-label", "Quiz options");

        quiz.options.forEach(function (opt) {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "ai-tutor-quiz-option";
            btn.dataset.optionKey = opt.key || "";
            btn.dataset.optionText = opt.text || "";
            btn.innerHTML =
                '<span class="ai-tutor-quiz-option-key">' +
                escapeHtml(opt.key || "") +
                "</span>" +
                '<span class="ai-tutor-quiz-option-text">' +
                escapeHtml(opt.text || "") +
                "</span>";
            btn.addEventListener("click", function () {
                if (btn.disabled || isSending || bubble.classList.contains("is-answered")) {
                    return;
                }
                bubble.classList.add("is-answered");
                optionsWrap.querySelectorAll(".ai-tutor-quiz-option").forEach(function (el) {
                    el.disabled = true;
                });
                btn.classList.add("is-selected");
                sendTutorMessage(opt.key || opt.text || "", null, {
                    hideUserBubble: true,
                    quizAnswer: true
                });
            });
            optionsWrap.appendChild(btn);
        });

        bubble.appendChild(title);
        bubble.appendChild(question);
        bubble.appendChild(optionsWrap);
        row.appendChild(buildAvatarElement());
        row.appendChild(bubble);
        messagesContainer.appendChild(row);
        notesArea.scrollTop = notesArea.scrollHeight;
        rememberHistory("assistant", "QUIZ: " + (quiz.question || ""));
        return bubble;
    }

    function renderQuizResult(result, fallbackReply) {
        if (!result) {
            if (fallbackReply) {
                renderMessage("assistant", fallbackReply);
                rememberHistory("assistant", fallbackReply);
            }
            return;
        }
        hideEmptyState();
        const row = document.createElement("div");
        row.className = "ai-tutor-message-row ai-tutor-message-row--assistant";
        const bubble = document.createElement("div");
        bubble.className =
            "ai-tutor-message ai-tutor-message--assistant ai-tutor-quiz-result " +
            (result.correct ? "is-correct" : "is-incorrect");

        const verdict = document.createElement("p");
        verdict.className = "ai-tutor-quiz-verdict";
        if (result.correct) {
            verdict.textContent =
                "Correct: " +
                (result.selected_key ? result.selected_key + ". " : "") +
                (result.selected_text || "");
        } else {
            verdict.textContent =
                "Not quite. The correct answer is " +
                (result.correct_key ? result.correct_key + ". " : "") +
                (result.correct_answer || "");
        }

        bubble.appendChild(verdict);
        if (result.explanation) {
            const why = document.createElement("p");
            why.className = "ai-tutor-quiz-explain";
            why.textContent = result.explanation;
            bubble.appendChild(why);
        }

        const actions = document.createElement("div");
        actions.className = "ai-tutor-quiz-followups";
        const whyBtn = document.createElement("button");
        whyBtn.type = "button";
        whyBtn.className = "ai-tutor-quiz-followup";
        whyBtn.textContent = "Why?";
        whyBtn.addEventListener("click", function () {
            if (isSending) return;
            sendTutorMessage(
                "Why is that the correct answer for this quiz question?",
                "chat"
            );
        });
        const nextBtn = document.createElement("button");
        nextBtn.type = "button";
        nextBtn.className = "ai-tutor-quiz-followup ai-tutor-quiz-followup--primary";
        nextBtn.textContent = "Next question";
        nextBtn.addEventListener("click", function () {
            if (isSending) return;
            sendTutorMessage("", "quiz", { quizContinue: true });
        });
        actions.appendChild(whyBtn);
        actions.appendChild(nextBtn);
        bubble.appendChild(actions);

        row.appendChild(buildAvatarElement());
        row.appendChild(bubble);
        messagesContainer.appendChild(row);
        notesArea.scrollTop = notesArea.scrollHeight;
        rememberHistory(
            "assistant",
            verdict.textContent + (result.explanation ? " " + result.explanation : "")
        );
    }


    /* =========================================
       SEND MESSAGE TO BACKEND
       ========================================= */

    function sendTutorMessage(message, mode, options) {

        if (isSending) {
            return;
        }

        options = options || {};

        if (mode) {
            setActiveMode(mode);
        }

        // Free Chat opener stays local — no empty API round trip.
        if (mode === "chat" && !message) {
            hideEmptyState();
            renderMessage("assistant", FREE_CHAT_INTRO);
            rememberHistory("assistant", FREE_CHAT_INTRO);
            input.focus();
            return;
        }

        const context = getPageContext();
        const langKey =
            options.langKeyOverride ||
            options.langKey ||
            context.langKey;
        const levelNum =
            options.levelNumOverride != null
                ? options.levelNumOverride
                : context.levelNum;

        const historyToSend = conversationHistory.slice();

        if (message && !options.hideUserBubble) {
            renderMessage("user", message);
            rememberHistory("user", message);
        } else if (message && options.quizAnswer) {
            rememberHistory("user", "Selected: " + message);
        }

        const typingIndicator =
            showTypingIndicator();

        setSendingState(true);

        const controller =
            (typeof AbortController !== "undefined")
                ? new AbortController()
                : null;

        const timeoutId = window.setTimeout(function () {
            if (controller) {
                controller.abort();
            }
        }, REQUEST_TIMEOUT_MS);

        fetch("/api/tutor/chat", {

            method: "POST",

            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken()
            },

            signal: controller ? controller.signal : undefined,

            body: JSON.stringify({
                message: message,
                mode: mode,
                lang_key: langKey,
                level_num: levelNum,
                history: historyToSend,
                quiz_continue: !!options.quizContinue
            })

        })
            .then(function (response) {

                if (!response.ok) {
                    throw new Error(
                        "AI Tutor request failed."
                    );
                }

                return response.json();
            })
            .then(function (data) {

                typingIndicator.remove();

                if (data && data.quiz) {
                    if (data.reply) {
                        renderMessage("assistant", data.reply);
                        rememberHistory("assistant", data.reply);
                    }
                    renderQuizCard(data.quiz);
                    return;
                }

                if (data && data.quiz_result) {
                    renderQuizResult(data.quiz_result, data.reply);
                    return;
                }

                if (data && data.reply) {
                    renderMessage("assistant", data.reply);
                    rememberHistory("assistant", data.reply);
                } else {
                    renderMessage(
                        "error",
                        "The tutor could not be reached right now."
                    );
                }
            })
            .catch(function (error) {

                typingIndicator.remove();

                const isTimeout =
                    error && error.name === "AbortError";

                renderMessage(
                    "error",
                    isTimeout
                        ? "The tutor is taking too long to respond. " +
                          "Please try again."
                        : "The tutor is temporarily unavailable. " +
                          "Please try again."
                );
            })
            .finally(function () {

                window.clearTimeout(timeoutId);

                setSendingState(false);

                input.focus();

                if (pendingAsk) {
                    const next = pendingAsk;
                    pendingAsk = null;
                    window.setTimeout(function () {
                        window.AITutor.ask(next.message, next.options || {});
                    }, 0);
                }
            });
    }


    /* =========================================
       QUICK ACTIONS + EMPTY-STATE SUGGESTIONS
       ========================================= */

    function handleActionClick(event) {

        const button = event.target.closest(
            ".ai-tutor-quick-action, .ai-tutor-suggestion-chip"
        );

        if (!button || button.disabled || isSending) {
            return;
        }

        const mode = button.dataset.mode;
        setActiveMode(mode);
        sendTutorMessage("", mode);
    }

    if (quickActionsContainer) {

        quickActionsContainer.addEventListener(
            "click",
            handleActionClick
        );
    }

    if (emptyState) {

        emptyState.addEventListener(
            "click",
            handleActionClick
        );
    }


    /* =========================================
       TEXT INPUT FORM
       ========================================= */

    form.addEventListener(
        "submit",
        function (event) {

            event.preventDefault();

            if (isSending) {
                return;
            }

            const message = input.value.trim();

            if (!message) {
                return;
            }

            input.value = "";

            sendTutorMessage(message, null);
        }
    );


    /* =========================================
       FLOATING BUTTON SAFE POSITION
       ========================================= */

    positionTutorFab();
    window.addEventListener("resize", positionTutorFab);
    window.addEventListener("scroll", positionTutorFab, { passive: true });

    const statusEl = document.getElementById("globe-status");
    if (statusEl && typeof MutationObserver !== "undefined") {
        const statusObserver = new MutationObserver(function () {
            positionTutorFab();
        });
        statusObserver.observe(statusEl, {
            attributes: true,
            childList: true,
            characterData: true,
            subtree: true
        });
    }

    /* =========================================
       PUBLIC HOOK
       Lets other pages (e.g. the Dictionary) open
       this same widget and ask it a question,
       instead of building a second AI system.
       ========================================= */

    window.AITutor = {
        open: openTutorPanel,
        ask: function (message, options) {
            options = options || {};
            const mode = options.mode || null;
            if (!message && !mode) {
                return;
            }
            openTutorPanel();
            if (isSending) {
                /* Keep only the latest Dictionary/action request. */
                pendingAsk = { message: message || "", options: options };
                return;
            }
            if (mode) {
                setActiveMode(mode);
            }
            sendTutorMessage(message || "", mode, {
                langKeyOverride: options.langKey || options.langKeyOverride || null,
                levelNumOverride: options.levelNum != null ? options.levelNum : null,
                hideUserBubble: !!options.hideUserBubble
            });
        }
    };

});
