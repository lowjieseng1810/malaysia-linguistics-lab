/* =========================================
   Malaysia Linguistics Lab
   Universal Journey Learning Engine
   ========================================= */

document.addEventListener("DOMContentLoaded", function () {

    const lessonData =
        window.LEVEL_LESSON;

    if (
        !lessonData ||
        !Array.isArray(lessonData.steps)
    ) {
        console.error(
            "Lesson data could not be loaded."
        );

        return;
    }


    /* ================= ELEMENTS ================= */

    const stepLabel =
        document.getElementById(
            "step-label"
        );

    const learningTitle =
        document.getElementById(
            "learning-title"
        );

    const learningInstruction =
        document.getElementById(
            "learning-instruction"
        );

    const learningBody =
        document.getElementById(
            "learning-body"
        );

    const feedbackBox =
        document.getElementById(
            "feedback-box"
        );

    const hintArea =
        document.getElementById(
            "hint-area"
        );

    const hintButton =
        document.getElementById(
            "hint-button"
        );

    const hintBox =
        document.getElementById(
            "hint-box"
        );

    const actionButton =
        document.getElementById(
            "primary-action-button"
        );

    const replayButton =
        document.getElementById(
            "replay-action-button"
        );

    const actionHint =
        document.getElementById(
            "action-hint"
        );

    const progressFill =
        document.getElementById(
            "level-progress-fill"
        );

    const progressText =
        document.getElementById(
            "level-progress-text"
        );


    /* ================= STATE ================= */

    const savedStep =
        Math.min(
            Math.max(
                Number(
                    lessonData.savedStep
                ) || 0,
                0
            ),
            lessonData.steps.length
        );

    // If the learner already finished (current_step == total_steps), reopen
    // on the completion screen — not step 0.
    let currentStepIndex =
        savedStep >= lessonData.steps.length
            ? lessonData.steps.length
            : savedStep;

    let selectedAnswer = null;

    let answerChecked = false;

    // Completion POST is independent of step cursor. Using step count here
    // skipped /complete-level after refresh when steps were saved but the
    // level was never marked complete (next level stayed locked).
    let progressSaved = !!lessonData.levelCompleted;

    let progressSaving = false;

    let isReplaying = !!lessonData.replayMode;

    let stepSaving = false;

    let hintVisible = false;

    let discoverRevealed = false;

    let responseCompleted = false;

    let conversationRound = 0;

    let conversationHistory = [];

    let typewriterTimer = null;

    let typewriterActive = false;

    let typewriterFullText = "";

    let typewriterTarget = null;


    /* ================= MOTION ================= */

    const reducedMotion =
        window.matchMedia(
            "(prefers-reduced-motion: reduce)"
        );


    /* ================= PROGRESS ================= */

    function updateProgress() {

        const totalSteps =
            lessonData.steps.length;

        let progress = 0;

        if (totalSteps > 0) {

            progress = Math.round(
                (
                    currentStepIndex /
                    totalSteps
                ) * 100
            );

        }

        progress =
            Math.min(
                progress,
                100
            );

        progressFill.style.width =
            progress + "%";

        progressText.textContent =
            progress + "%";
    }


    /* ================= RESET ================= */

    function resetStepUI() {

        stopTypewriter();

        feedbackBox.className =
            "feedback-box";

        feedbackBox.textContent = "";

        hintBox.className =
            "hint-box";

        hintBox.textContent = "";

        hintButton.textContent =
            "Show Hint";

        hintButton.disabled = false;

        hintVisible = false;

        selectedAnswer = null;

        answerChecked = false;

        discoverRevealed = false;

        responseCompleted = false;

        conversationRound = 0;

        conversationHistory = [];

        actionButton.dataset.mode = "";

        actionButton.disabled = false;
    }


    /* ================= HINT ================= */

    function hideHintArea() {

        hintArea.style.display =
            "none";

        hintBox.className =
            "hint-box";

        hintBox.textContent = "";

        hintVisible = false;
    }


    function showHintArea(step) {

        if (!step.hint) {

            hideHintArea();

            return;
        }

        hintArea.style.display = "";

        hintButton.textContent =
            "Show Hint";

        hintButton.disabled = false;

        hintBox.className =
            "hint-box";

        hintBox.textContent = "";

        hintVisible = false;
    }


    hintButton.addEventListener(
        "click",
        function () {

            const step =
                lessonData.steps[
                    currentStepIndex
                ];

            if (
                !step ||
                !step.hint
            ) {
                return;
            }

            hintVisible =
                !hintVisible;

            if (hintVisible) {

                hintBox.textContent =
                    step.hint;

                hintBox.className =
                    "hint-box show";

                hintButton.textContent =
                    "Hide Hint";

            } else {

                hintBox.className =
                    "hint-box";

                hintBox.textContent = "";

                hintButton.textContent =
                    "Show Hint";

            }

        }
    );


    /* ================= OPTION BUTTONS ================= */

    function buildOptionsHTML(
        options,
        className
    ) {

        return options
            .map(
                function (
                    option,
                    index
                ) {

                    return (
                        '<button ' +
                        'type="button" ' +
                        'class="' +
                        className +
                        '" ' +
                        'data-option-index="' +
                        index +
                        '">' +
                            '<span class="option-text">' +
                                escapeHTML(
                                    option
                                ) +
                            '</span>' +
                            '<span class="answer-icon" ' +
                            'aria-hidden="true"></span>' +
                        '</button>'
                    );

                }
            )
            .join("");
    }


    function activateOptionSelection(
        selector
    ) {

        const optionButtons =
            learningBody.querySelectorAll(
                selector
            );

        optionButtons.forEach(
            function (button) {

                button.addEventListener(
                    "click",
                    function () {

                        if (answerChecked) {
                            return;
                        }

                        optionButtons.forEach(
                            function (item) {

                                item.classList.remove(
                                    "is-selected"
                                );

                            }
                        );

                        button.classList.add(
                            "is-selected"
                        );

                        selectedAnswer =
                            Number(
                                button.dataset
                                    .optionIndex
                            );

                        actionButton.disabled =
                            false;
                    }
                );

            }
        );
    }


    /* ================= OLD VOCABULARY ================= */

    function renderVocabularyStep(step) {

        resetStepUI();

        hideHintArea();

        stepLabel.textContent =
            "Learn";

        learningTitle.textContent =
            step.title;

        learningInstruction.textContent =
            step.instruction ||
            "Study this word before continuing.";

        let noteHTML = "";

        if (step.note) {

            noteHTML =
                '<p class="vocabulary-note">' +
                    escapeHTML(step.note) +
                '</p>';

        }

        learningBody.innerHTML =
            '<div class="vocabulary-box">' +
                '<p class="vocabulary-word">' +
                    escapeHTML(step.word) +
                '</p>' +
                '<p class="vocabulary-meaning">' +
                    escapeHTML(step.meaning) +
                '</p>' +
                noteHTML +
            '</div>';

        actionButton.disabled = false;

        actionButton.textContent =
            "Continue";

        actionHint.textContent =
            "Take a moment to remember the word.";
    }


    /* ================= OLD QUIZ ================= */

    function renderQuizStep(step) {

        resetStepUI();

        showHintArea(step);

        stepLabel.textContent =
            "Quick Check";

        learningTitle.textContent =
            step.question;

        learningInstruction.textContent =
            step.instruction ||
            "Choose the correct answer.";

        const optionsHTML =
            buildOptionsHTML(
                step.options,
                "quiz-option"
            );

        learningBody.innerHTML =
            '<div class="quiz-options">' +
                optionsHTML +
            '</div>';

        actionButton.disabled = true;

        actionButton.textContent =
            "Check Answer";

        actionHint.textContent =
            "Select one answer to continue.";

        activateOptionSelection(
            ".quiz-option"
        );
    }


    /* ================= OLD QUIZ CHECK ================= */

    function checkAnswer(step) {

        if (selectedAnswer === null) {
            return;
        }

        answerChecked = true;

        const optionButtons =
            learningBody.querySelectorAll(
                ".quiz-option"
            );

        markAnswerButtons(
            optionButtons,
            step.correctIndex
        );

        if (
            selectedAnswer ===
            step.correctIndex
        ) {

            feedbackBox.className =
                "feedback-box correct show answer-success";

            feedbackBox.textContent =
                step.correctFeedback ||
                "Correct! Well done.";

        } else {

            feedbackBox.className =
                "feedback-box wrong show answer-error";

            feedbackBox.textContent =
                step.wrongFeedback ||
                "Not quite. Review the correct answer and continue.";

        }

        hintButton.disabled = true;

        actionButton.textContent =
            "Continue";

        actionHint.textContent =
            "Continue when you are ready.";
    }


    /* ================= SCENE ================= */

    function renderSceneStep(step) {

        resetStepUI();

        hideHintArea();

        stepLabel.textContent =
            step.label ||
            "Journey";

        learningTitle.textContent =
            step.title ||
            "Your journey begins";

        learningInstruction.textContent =
            step.instruction ||
            "";

        const journeyNumber =
            step.journeyNumber
                ? (
                    '<span class="journey-number">' +
                        escapeHTML(
                            step.journeyNumber
                        ) +
                    '</span>'
                )
                : "";

        const description =
            step.description
                ? (
                    '<p class="journey-description">' +
                        escapeHTML(
                            step.description
                        ) +
                    '</p>'
                )
                : "";

        let pathHTML = "";

        if (
            Array.isArray(step.path) &&
            step.path.length > 0
        ) {

            pathHTML =
                '<div class="journey-path">' +
                    step.path
                        .map(
                            function (item) {

                                return (
                                    '<span class="journey-path-item">' +
                                        escapeHTML(item) +
                                    '</span>'
                                );

                            }
                        )
                        .join(
                            '<span class="journey-path-arrow" ' +
                            'aria-hidden="true">→</span>'
                        ) +
                '</div>';
        }

        learningBody.innerHTML =
            '<div class="journey-scene">' +
                journeyNumber +
                description +
                pathHTML +
            '</div>';

        actionButton.disabled = false;

        actionButton.textContent =
            step.buttonText ||
            "Begin Encounter";

        actionHint.textContent =
            step.actionHint ||
            "Enter the journey when you are ready.";
    }


    /* ================= DISCOVER ================= */

    function renderDiscoverStep(step) {

        resetStepUI();

        showHintArea(step);

        stepLabel.textContent =
            step.label ||
            "Encounter";

        learningTitle.textContent =
            step.title ||
            "Someone says:";

        learningInstruction.textContent =
            step.instruction ||
            "What do you think it means?";

        const optionsHTML =
            buildOptionsHTML(
                step.options,
                "journey-option"
            );

        learningBody.innerHTML =
            '<div class="discover-stage">' +

                '<div class="encounter-speaker">' +
                    escapeHTML(
                        step.speaker ||
                        "Someone"
                    ) +
                '</div>' +

                '<div class="encounter-expression">' +
                    escapeHTML(
                        step.expression
                    ) +
                '</div>' +

                '<div class="journey-options">' +
                    optionsHTML +
                '</div>' +

            '</div>';

        actionButton.disabled = true;

        actionButton.textContent =
            "Reveal Meaning";

        actionHint.textContent =
            "Choose what you think the expression means.";

        activateOptionSelection(
            ".journey-option"
        );
    }


    function revealDiscoverStep(step) {

        if (selectedAnswer === null) {
            return;
        }

        discoverRevealed = true;

        answerChecked = true;

        const optionButtons =
            learningBody.querySelectorAll(
                ".journey-option"
            );

        markAnswerButtons(
            optionButtons,
            step.correctIndex
        );

        const wasCorrect =
            selectedAnswer ===
            step.correctIndex;

        const resultLabel =
            wasCorrect
                ? "You understood it"
                : "Now you understand";

        learningBody.innerHTML =
            '<div class="discover-reveal">' +

                '<span class="reveal-label">' +
                    resultLabel +
                '</span>' +

                '<div class="reveal-expression">' +
                    escapeHTML(
                        step.expression
                    ) +
                '</div>' +

                '<div class="reveal-meaning">' +
                    escapeHTML(
                        step.meaning
                    ) +
                '</div>' +

                (
                    step.context
                        ? (
                            '<p class="reveal-context">' +
                                escapeHTML(
                                    step.context
                                ) +
                            '</p>'
                        )
                        : ""
                ) +

            '</div>';

        hideHintArea();

        feedbackBox.className =
            wasCorrect
                ? "feedback-box correct show answer-success"
                : "feedback-box show";

        feedbackBox.textContent =
            wasCorrect
                ? (
                    step.correctFeedback ||
                    "You worked out the meaning."
                )
                : (
                    step.wrongFeedback ||
                    "The meaning has now been revealed."
                );

        actionButton.disabled = false;

        actionButton.textContent =
            step.continueText ||
            "Continue the Meeting";

        actionHint.textContent =
            "Carry what you understood into the next moment.";
    }


    /* ================= RESPOND ================= */

    function renderRespondStep(step) {

        resetStepUI();

        showHintArea(step);

        stepLabel.textContent =
            step.label ||
            "Your Turn";

        learningTitle.textContent =
            step.title ||
            "Respond";

        learningInstruction.textContent =
            step.instruction ||
            "Choose how you would respond.";

        const optionsHTML =
            buildOptionsHTML(
                step.options,
                "response-option"
            );

        learningBody.innerHTML =
            '<div class="response-stage">' +

                '<div class="dialogue-turn dialogue-turn-other">' +

                    '<span class="dialogue-speaker">' +
                        escapeHTML(
                            step.speaker ||
                            "Someone"
                        ) +
                    '</span>' +

                    '<p class="dialogue-expression">' +
                        escapeHTML(
                            step.prompt
                        ) +
                    '</p>' +

                '</div>' +

                '<div class="dialogue-turn dialogue-turn-user">' +

                    '<span class="dialogue-speaker">' +
                        escapeHTML(
                            step.userLabel ||
                            "You"
                        ) +
                    '</span>' +

                    '<div class="response-options">' +
                        optionsHTML +
                    '</div>' +

                '</div>' +

            '</div>';

        actionButton.disabled = true;

        actionButton.textContent =
            "Respond";

        actionHint.textContent =
            "Choose your response.";

        activateOptionSelection(
            ".response-option"
        );
    }


    function checkResponse(step) {

        if (selectedAnswer === null) {
            return;
        }

        answerChecked = true;

        const optionButtons =
            learningBody.querySelectorAll(
                ".response-option"
            );

        markAnswerButtons(
            optionButtons,
            step.correctIndex
        );

        if (
            selectedAnswer !==
            step.correctIndex
        ) {

            feedbackBox.className =
                "feedback-box wrong show answer-error";

            feedbackBox.textContent =
                step.wrongFeedback ||
                "That response does not fit this moment yet.";

            actionButton.disabled = false;

            actionButton.textContent =
                "Try Again";

            actionButton.dataset.mode =
                "retry-response";

            actionHint.textContent =
                "Look at the exchange and choose again.";

            return;
        }

        responseCompleted = true;

        const correctResponse =
            step.options[
                step.correctIndex
            ];

        learningBody.innerHTML =
            '<div class="response-complete">' +

                '<div class="dialogue-turn dialogue-turn-other">' +

                    '<span class="dialogue-speaker">' +
                        escapeHTML(
                            step.speaker ||
                            "Someone"
                        ) +
                    '</span>' +

                    '<p class="dialogue-expression">' +
                        escapeHTML(
                            step.prompt
                        ) +
                    '</p>' +

                    (
                        step.promptMeaning
                            ? (
                                '<p class="dialogue-meaning">' +
                                    escapeHTML(
                                        step.promptMeaning
                                    ) +
                                '</p>'
                            )
                            : ""
                    ) +

                '</div>' +

                '<div class="dialogue-turn dialogue-turn-user">' +

                    '<span class="dialogue-speaker">' +
                        escapeHTML(
                            step.userLabel ||
                            "You"
                        ) +
                    '</span>' +

                    '<p class="dialogue-expression">' +
                        escapeHTML(
                            correctResponse
                        ) +
                    '</p>' +

                    (
                        step.responseMeaning
                            ? (
                                '<p class="dialogue-meaning">' +
                                    escapeHTML(
                                        step.responseMeaning
                                    ) +
                                '</p>'
                            )
                            : ""
                    ) +

                '</div>' +

                '<div class="exchange-complete">' +
                    escapeHTML(
                        step.successMessage ||
                        "You completed the exchange."
                    ) +
                '</div>' +

            '</div>';

        hideHintArea();

        feedbackBox.className =
            "feedback-box correct show answer-success";

        feedbackBox.textContent =
            step.correctFeedback ||
            "Your response fits the conversation.";

        actionButton.disabled = false;

        actionButton.textContent =
            step.continueText ||
            "Continue";

        actionHint.textContent =
            "The conversation can continue.";
    }


    function retryResponse(step) {

        actionButton.dataset.mode = "";

        renderRespondStep(step);
    }


   /* ================= CONVERSATION ================= */

function renderConversationStep(step) {

    resetStepUI();

    hideHintArea();

    stepLabel.textContent =
        step.label ||
        "Final Encounter";

    learningTitle.textContent =
        step.title ||
        "A Conversation";

    learningInstruction.textContent =
        step.instruction ||
        "Complete the conversation one moment at a time.";

    conversationRound = 0;

    conversationHistory = [];

    actionButton.style.display =
        "none";

    actionHint.textContent =
        "The conversation is beginning.";

    renderConversationRound(step);
}


function renderConversationRound(step) {

    const turns =
        Array.isArray(step.turns)
            ? step.turns
            : [];

    if (
        conversationRound >=
        turns.length
    ) {

        renderConversationComplete(
            step
        );

        return;
    }

    const turn =
        turns[
            conversationRound
        ];

    const historyHTML =
        buildConversationHistory();

    const optionsHTML =
        buildOptionsHTML(
            turn.options,
            "conversation-option"
        );

    learningBody.innerHTML =
        '<div class="conversation-stage conversation-flow">' +

            '<div class="conversation-progress">' +

                '<span>' +
                    'Conversation moment ' +
                    (
                        conversationRound + 1
                    ) +
                    ' of ' +
                    turns.length +
                '</span>' +

                '<div class="conversation-moment-dots">' +

                    turns
                        .map(
                            function (
                                item,
                                index
                            ) {

                                let stateClass =
                                    "";

                                if (
                                    index <
                                    conversationRound
                                ) {

                                    stateClass =
                                        " is-complete";

                                } else if (
                                    index ===
                                    conversationRound
                                ) {

                                    stateClass =
                                        " is-current";
                                }

                                return (
                                    '<span class="conversation-moment-dot' +
                                    stateClass +
                                    '"></span>'
                                );

                            }
                        )
                        .join("") +

                '</div>' +

            '</div>' +

            '<div class="conversation-thread" ' +
            'id="conversation-thread">' +

                historyHTML +

                '<div class="conversation-live-turn" ' +
                'id="conversation-live-turn">' +

                    '<div class="dialogue-turn dialogue-turn-other conversation-new-message">' +

                        '<span class="dialogue-speaker">' +
                            escapeHTML(
                                turn.speaker ||
                                "Someone"
                            ) +
                        '</span>' +

                        '<p class="dialogue-expression conversation-typing" ' +
                        'id="conversation-typing" ' +
                        'tabindex="0" ' +
                        'title="Click to reveal the full line">' +
                        '</p>' +

                    '</div>' +

                    '<div class="conversation-response-area" ' +
                    'id="conversation-response-area" ' +
                    'hidden>' +

                        '<div class="dialogue-turn dialogue-turn-user conversation-choice-bubble">' +

                            '<span class="dialogue-speaker">' +
                                escapeHTML(
                                    turn.userLabel ||
                                    "You"
                                ) +
                            '</span>' +

                            '<span class="conversation-choice-label">' +
                                'Choose what you say' +
                            '</span>' +

                            '<div class="conversation-options">' +
                                optionsHTML +
                            '</div>' +

                        '</div>' +

                    '</div>' +

                '</div>' +

            '</div>' +

        '</div>';

    const typingElement =
        document.getElementById(
            "conversation-typing"
        );

    const responseArea =
        document.getElementById(
            "conversation-response-area"
        );

    scrollConversationToBottom();

    startTypewriter(
        typingElement,
        turn.prompt,
        function () {

            responseArea.hidden =
                false;

            actionHint.textContent =
                "Choose how you respond.";

            activateConversationOptions(
                step,
                turn
            );

            scrollConversationToBottom();
        }
    );
}


function activateConversationOptions(
    step,
    turn
) {

    const optionButtons =
        learningBody.querySelectorAll(
            ".conversation-option"
        );

    optionButtons.forEach(
        function (button) {

            button.addEventListener(
                "click",
                function () {

                    if (answerChecked) {
                        return;
                    }

                    selectedAnswer =
                        Number(
                            button.dataset
                                .optionIndex
                        );

                    if (
                        selectedAnswer !==
                        turn.correctIndex
                    ) {

                        button.classList.add(
                            "is-wrong"
                        );

                        feedbackBox.className =
                            "feedback-box wrong show answer-error";

                        feedbackBox.textContent =
                            turn.wrongFeedback ||
                            "That response does not fit this moment.";

                        window.setTimeout(
                            function () {

                                button.classList.remove(
                                    "is-wrong"
                                );

                            },
                            500
                        );

                        return;
                    }

                    answerChecked = true;

                    button.classList.add(
                        "is-correct"
                    );

                    optionButtons.forEach(
                        function (item) {

                            item.disabled =
                                true;

                        }
                    );

                    const correctResponse =
                        turn.options[
                            turn.correctIndex
                        ];

                    conversationHistory.push({

                        speaker:
                            turn.speaker ||
                            "Someone",

                        prompt:
                            turn.prompt,

                        userLabel:
                            turn.userLabel ||
                            "You",

                        response:
                            correctResponse
                    });

                    const responseArea =
                        document.getElementById(
                            "conversation-response-area"
                        );

                    if (responseArea) {

                        responseArea.innerHTML =
                            '<div class="dialogue-turn dialogue-turn-user conversation-confirmed-response">' +

                                '<span class="dialogue-speaker">' +
                                    escapeHTML(
                                        turn.userLabel ||
                                        "You"
                                    ) +
                                '</span>' +

                                '<p class="dialogue-expression">' +
                                    escapeHTML(
                                        correctResponse
                                    ) +
                                '</p>' +

                            '</div>';

                    }

                    feedbackBox.className =
                        "feedback-box correct show answer-success";

                    feedbackBox.textContent =
                        turn.correctFeedback ||
                        "The conversation continues.";

                    actionHint.textContent =
                        "The conversation is continuing.";

                    scrollConversationToBottom();

                    window.setTimeout(
                        function () {

                            feedbackBox.className =
                                "feedback-box";

                            feedbackBox.textContent =
                                "";

                            selectedAnswer =
                                null;

                            answerChecked =
                                false;

                            conversationRound +=
                                1;

                            renderConversationRound(
                                step
                            );

                        },
                        reducedMotion.matches
                            ? 0
                            : 850
                    );

                }
            );

        }
    );
}


function buildConversationHistory() {

    return conversationHistory
        .map(
            function (
                turn,
                index
            ) {

                return (
                    '<div class="conversation-history-pair conversation-completed-pair" ' +
                    'data-conversation-turn="' +
                    index +
                    '">' +

                        '<div class="dialogue-turn dialogue-turn-other">' +

                            '<span class="dialogue-speaker">' +
                                escapeHTML(
                                    turn.speaker
                                ) +
                            '</span>' +

                            '<p class="dialogue-expression">' +
                                escapeHTML(
                                    turn.prompt
                                ) +
                            '</p>' +

                        '</div>' +

                        '<div class="dialogue-turn dialogue-turn-user">' +

                            '<span class="dialogue-speaker">' +
                                escapeHTML(
                                    turn.userLabel
                                ) +
                            '</span>' +

                            '<p class="dialogue-expression">' +
                                escapeHTML(
                                    turn.response
                                ) +
                            '</p>' +

                        '</div>' +

                    '</div>'
                );

            }
        )
        .join("");
}


function scrollConversationToBottom() {

    window.requestAnimationFrame(
        function () {

            const liveTurn =
                document.getElementById(
                    "conversation-live-turn"
                );

            if (!liveTurn) {
                return;
            }

            liveTurn.scrollIntoView({
                behavior:
                    reducedMotion.matches
                        ? "auto"
                        : "smooth",

                block:
                    "nearest"
            });

        }
    );
}


function renderConversationComplete(
    step
) {

    learningBody.innerHTML =
        '<div class="conversation-complete">' +

            '<div class="conversation-finale-header">' +

                '<span class="reveal-label">' +
                    escapeHTML(
                        step.completeLabel ||
                        "Conversation Complete"
                    ) +
                '</span>' +

                '<h3 class="conversation-finale-title">' +
                    'You carried the conversation.' +
                '</h3>' +

                '<p class="conversation-complete-message">' +
                    escapeHTML(
                        step.completeMessage ||
                        "You completed the full conversation."
                    ) +
                '</p>' +

            '</div>' +

            '<div class="conversation-history conversation-history-complete">' +
                buildConversationHistory() +
            '</div>' +

        '</div>';

    feedbackBox.className =
        "feedback-box correct show answer-success";

    feedbackBox.textContent =
        step.successMessage ||
        "You stayed with the conversation from beginning to end.";

    actionButton.style.display =
        "";

    actionButton.disabled = false;

    actionButton.textContent =
        step.continueText ||
        "Complete Journey";

    actionHint.textContent =
        "Your first full encounter is complete.";
}


    /* ================= TYPEWRITER ================= */

    function startTypewriter(
        target,
        text,
        onComplete
    ) {

        stopTypewriter();

        typewriterTarget =
            target;

        typewriterFullText =
            String(
                text ?? ""
            );

        if (
            reducedMotion.matches ||
            !typewriterFullText
        ) {

            target.textContent =
                typewriterFullText;

            typewriterActive =
                false;

            onComplete();

            return;
        }

        typewriterActive =
            true;

        target.textContent = "";

        let characterIndex = 0;

        function typeNextCharacter() {

            if (!typewriterActive) {
                return;
            }

            characterIndex += 1;

            target.textContent =
                typewriterFullText.slice(
                    0,
                    characterIndex
                );

            if (
                characterIndex >=
                typewriterFullText.length
            ) {

                typewriterActive =
                    false;

                typewriterTimer =
                    null;

                onComplete();

                return;
            }

            typewriterTimer =
                window.setTimeout(
                    typeNextCharacter,
                    40
                );
        }

        target.addEventListener(
            "click",
            skipCurrentTypewriter,
            {
                once: true
            }
        );

        target.addEventListener(
            "keydown",
            function (event) {

                if (
                    event.key === "Enter" ||
                    event.key === " "
                ) {

                    event.preventDefault();

                    skipCurrentTypewriter();

                }

            },
            {
                once: true
            }
        );

        typeNextCharacter();
    }


    function skipCurrentTypewriter() {

        if (
            !typewriterActive ||
            !typewriterTarget
        ) {
            return;
        }

        if (typewriterTimer) {

            window.clearTimeout(
                typewriterTimer
            );

        }

        typewriterTarget.textContent =
            typewriterFullText;

        typewriterActive = false;

        typewriterTimer = null;

        const responseArea =
            document.getElementById(
                "conversation-response-area"
            );

        if (responseArea) {

            responseArea.hidden =
                false;

        }

        actionHint.textContent =
            "Choose how you respond.";

        const step =
            lessonData.steps[
                currentStepIndex
            ];

        if (
            step &&
            step.type === "conversation"
        ) {

            const turn =
                step.turns[
                    conversationRound
                ];

            if (turn) {

                activateConversationOptions(
                    step,
                    turn
                );

            }
        }
    }


    function stopTypewriter() {

        if (typewriterTimer) {

            window.clearTimeout(
                typewriterTimer
            );

        }

        typewriterTimer = null;

        typewriterActive = false;

        typewriterFullText = "";

        typewriterTarget = null;
    }


    /* ================= ANSWER MARKING ================= */

    function markAnswerButtons(
        optionButtons,
        correctIndex
    ) {

        optionButtons.forEach(
            function (
                button,
                index
            ) {

                button.disabled = true;

                const answerIcon =
                    button.querySelector(
                        ".answer-icon"
                    );

                if (
                    index ===
                    correctIndex
                ) {

                    button.classList.add(
                        "is-correct"
                    );

                    if (answerIcon) {

                        answerIcon.textContent =
                            "✓";

                    }
                }

                if (
                    index ===
                        selectedAnswer &&
                    index !==
                        correctIndex
                ) {

                    button.classList.add(
                        "is-wrong"
                    );

                    if (answerIcon) {

                        answerIcon.textContent =
                            "✕";

                    }
                }

            }
        );
    }


    /* ================= SAVE STEP ================= */

    async function saveStepProgress(
        nextStep
    ) {

        if (!lessonData.saveStepUrl) {

            console.error(
                "Step save URL is missing."
            );

            return false;
        }

        if (stepSaving) {
            return false;
        }

        stepSaving = true;

        try {

            const response =
                await fetch(
                    lessonData.saveStepUrl,
                    {
                        method: "POST",

                       headers: {
    "Accept":
        "application/json",

    "Content-Type":
        "application/json",

    "X-CSRFToken":
        lessonData.csrfToken
},

                        body:
                            JSON.stringify({
                                currentStep:
                                    nextStep
                            })
                    }
                );

            const result =
                await response.json();

            if (
                !response.ok ||
                !result.success
            ) {

                throw new Error(
                    result.message ||
                    "Step progress could not be saved."
                );

            }

            return true;

        } catch (error) {

            console.error(
                "Step progress save failed:",
                error
            );

            return false;

        } finally {

            stepSaving = false;

        }
    }


    /* ================= SAVE COMPLETION ================= */

    async function saveProgress() {

        if (
            progressSaved ||
            progressSaving
        ) {
            return progressSaved;
        }

        if (!lessonData.saveUrl) {

            console.error(
                "Progress save URL is missing."
            );

            return false;
        }

        progressSaving = true;

        actionButton.disabled = true;

        actionButton.textContent =
            "Saving...";

        actionHint.textContent =
            "Saving your progress.";

        try {

            const response =
                await fetch(
                    lessonData.saveUrl,
                    {
                        method: "POST",

                        headers: {
    "Accept":
        "application/json",

    "X-CSRFToken":
        lessonData.csrfToken
}
                    }
                );

            const result =
                await response.json();

            if (
                !response.ok ||
                !result.success
            ) {

                throw new Error(
                    result.message ||
                    "Progress could not be saved."
                );

            }

            progressSaved = true;

            actionButton.disabled = false;

            actionButton.textContent =
                "Return to the Language";

            actionHint.textContent =
                "Your progress has been saved.";

            if (window.reportNewAchievements && result.new_achievements) {
                window.reportNewAchievements(result.new_achievements);
            }
            window.dispatchEvent(
                new CustomEvent("mascotCompanionEvent", {
                    detail: { type: "lesson_completed" }
                })
            );

            return true;

        } catch (error) {

            console.error(
                "Progress save failed:",
                error
            );

            actionButton.disabled = false;

            actionButton.textContent =
                "Try Saving Again";

            actionHint.textContent =
                "Progress was not saved. Please try again.";

            return false;

        } finally {

            progressSaving = false;

        }
    }


    /* ================= COMPLETION ================= */

    async function renderCompletion() {

        currentStepIndex =
            lessonData.steps.length;

        updateProgress();

        hideHintArea();

        stopTypewriter();

        learningTitle.style.display =
            "none";

        learningInstruction.style.display =
            "none";

        feedbackBox.className =
            "feedback-box";

        feedbackBox.textContent = "";

        stepLabel.textContent =
            "Journey Complete";

        learningBody.innerHTML =
            '<div class="completion-content journey-completion">' +

                '<div class="completion-badge">' +
                    '✓' +
                '</div>' +

                '<span class="reveal-label">' +
                    'Journey Complete' +
                '</span>' +

                '<h2>' +
                    'You completed this journey.' +
                '</h2>' +

                '<p>' +
                    'Your progress is being saved.' +
                '</p>' +

            '</div>';

        actionButton.style.display =
            "";

        actionButton.dataset.mode =
            "complete";

        actionButton.textContent =
            "Return to Course";

        if (actionHint) {
            actionHint.textContent =
                "Replay anytime — your completion stays saved.";
        }

        if (replayButton) {
            replayButton.hidden = false;
        }

        await saveProgress();

        if (progressSaved) {

            const completionParagraph =
                learningBody.querySelector(
                    ".completion-content p"
                );

            if (completionParagraph) {

                completionParagraph.textContent =
                    "Your progress is saved. Review this screen, or replay the journey from the start.";

            }
        }
    }


    function resetJourneyRuntimeState() {
        selectedAnswer = null;
        answerChecked = false;
        hintVisible = false;
        discoverRevealed = false;
        responseCompleted = false;
        conversationRound = 0;
        conversationHistory = [];
        stopTypewriter();
        hideHintArea();

        if (feedbackBox) {
            feedbackBox.className = "feedback-box";
            feedbackBox.textContent = "";
        }

        if (learningTitle) {
            learningTitle.style.display = "";
        }

        if (learningInstruction) {
            learningInstruction.style.display = "";
        }

        if (actionButton) {
            actionButton.dataset.mode = "";
            actionButton.disabled = false;
            actionButton.textContent = "Continue";
            actionButton.style.display = "";
        }

        if (actionHint) {
            actionHint.textContent =
                "Continue when you are ready.";
        }

        if (replayButton) {
            replayButton.hidden = true;
        }
    }


    function startReplayJourney() {
        isReplaying = true;
        currentStepIndex = 0;
        /* Completion remains in progress.completed; allow a fresh journey pass
           and an idempotent re-save when the learner finishes again. */
        progressSaved = false;
        resetJourneyRuntimeState();
        renderCurrentStep();
    }


    /* ================= RENDER CURRENT STEP ================= */

    function renderCurrentStep() {

        if (
            currentStepIndex >=
            lessonData.steps.length
        ) {

            renderCompletion();

            return;
        }

        const step =
            lessonData.steps[
                currentStepIndex
            ];

        if (!step || typeof step !== "object") {
            stepLabel.textContent = "Error";
            learningTitle.textContent =
                "This step could not be loaded.";
            learningInstruction.textContent =
                "The lesson data for this step is missing or invalid.";
            learningBody.innerHTML = "";
            actionButton.disabled = true;
            actionHint.textContent =
                "Return to the language page and try again.";
            return;
        }

        learningTitle.style.display = "";

        learningInstruction.style.display =
            "";

        actionButton.style.display = "";

        actionButton.dataset.mode = "";

        updateProgress();

        switch (step.type) {

            case "vocabulary":

                renderVocabularyStep(
                    step
                );

                break;


            case "quiz":

                renderQuizStep(
                    step
                );

                break;


            case "scene":

                renderSceneStep(
                    step
                );

                break;


            case "discover":

                renderDiscoverStep(
                    step
                );

                break;


            case "respond":

                renderRespondStep(
                    step
                );

                break;


            case "conversation":

                renderConversationStep(
                    step
                );

                break;


            default:

                console.error(
                    "Unknown lesson step type:",
                    step.type
                );

                stepLabel.textContent =
                    "Error";

                learningTitle.textContent =
                    "This step could not be loaded.";

                learningInstruction.textContent =
                    "The lesson contains an unsupported step type.";

                learningBody.innerHTML = "";

                hideHintArea();

                actionButton.disabled = true;

                actionHint.textContent =
                    "Check the course data and try again.";

        }
    }


    /* ================= MOVE TO NEXT STEP ================= */

    async function moveToNextStep() {

        actionButton.disabled = true;

        actionHint.textContent =
            "Saving your progress...";

        const nextStep =
            currentStepIndex + 1;

        const saved =
            await saveStepProgress(
                nextStep
            );

        if (!saved) {

            actionButton.disabled =
                false;

            actionHint.textContent =
                "Progress could not be saved. Try again.";

            return;
        }

        currentStepIndex =
            nextStep;

        renderCurrentStep();
    }


    /* ================= MAIN BUTTON ================= */

    if (replayButton) {
        replayButton.addEventListener(
            "click",
            function () {
                startReplayJourney();
            }
        );
    }

    actionButton.addEventListener(
        "click",
        async function () {

            if (
                actionButton.dataset.mode ===
                "complete"
            ) {

                if (!progressSaved) {

                    await saveProgress();

                    return;
                }

                window.location.href =
                    lessonData.returnUrl;

                return;
            }


            const currentStep =
                lessonData.steps[
                    currentStepIndex
                ];


            if (!currentStep) {
                return;
            }


            if (
                actionButton.dataset.mode ===
                "retry-response"
            ) {

                retryResponse(
                    currentStep
                );

                return;
            }


            if (
                currentStep.type ===
                    "quiz" &&
                !answerChecked
            ) {

                checkAnswer(
                    currentStep
                );

                return;
            }


            if (
                currentStep.type ===
                    "discover" &&
                !discoverRevealed
            ) {

                revealDiscoverStep(
                    currentStep
                );

                return;
            }


            if (
                currentStep.type ===
                    "respond" &&
                !responseCompleted
            ) {

                checkResponse(
                    currentStep
                );

                return;
            }


            await moveToNextStep();

        }
    );


    /* ================= SAFE TEXT ================= */

    function escapeHTML(value) {

        const element =
            document.createElement(
                "div"
            );

        element.textContent =
            String(
                value ?? ""
            );

        return element.innerHTML;
    }


    /* ================= START ================= */

    renderCurrentStep();

});