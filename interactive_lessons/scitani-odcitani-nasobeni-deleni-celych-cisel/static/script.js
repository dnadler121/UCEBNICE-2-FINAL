const expression = document.getElementById("expression");
const answer = document.getElementById("answer");
const message = document.getElementById("message");
const steps = document.getElementById("steps");
const mistakes = document.getElementById("mistakes");
const newButton = document.getElementById("newButton");
const checkButton = document.getElementById("checkButton");
const progressText = document.getElementById("progressText");
const progressBar = document.getElementById("progressBar");

let lessonSaved = false;

function selectedOperations() {
    return [...document.querySelectorAll('input[name="operation"]:checked')]
        .map(input => input.value);
}

function showMessage(text, type = "neutral") {
    message.textContent = text;
    message.className = `message ${type}`;
}

function updateProgress(done = 0, target = 10) {
    progressText.textContent = `${done} z ${target} příkladů`;
    progressBar.style.width = `${Math.min(100, (done / target) * 100)}%`;
}

async function createExample() {
    const response = await fetch(window.LESSON_URLS.newExample, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            count: document.getElementById("count").value,
            max_number: document.getElementById("maxNumber").value,
            operations: selectedOperations(),
            use_parentheses: document.getElementById("useParentheses").checked
        })
    });
    const data = await response.json();

    if (!data.ok) {
        showMessage(data.message || data.error, "error");
        return;
    }

    expression.innerHTML = data.expression;
    steps.textContent = "0";
    mistakes.textContent = "0";
    answer.value = "";
    answer.disabled = false;
    checkButton.disabled = false;
    updateProgress(data.completed_examples, data.target_examples);
    showMessage(data.message, "neutral");
    answer.focus();
}

async function saveCompletion(percent, grade) {
    if (lessonSaved) return;
    lessonSaved = true;
    const response = await fetch(window.LESSON_URLS.completeLesson, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({percent, grade})
    });
    const data = await response.json();
    if (!data.ok) {
        lessonSaved = false;
        showMessage(data.error || "Dokončení se nepodařilo uložit.", "error");
        return;
    }
    showMessage(`Lekce je dokončena. Výsledek ${percent} %, známka ${grade}.`, "success");
}

async function checkAnswer() {
    if (answer.value.trim() === "") {
        showMessage("Nejdříve napiš výsledek.", "error");
        answer.focus();
        return;
    }

    const response = await fetch(window.LESSON_URLS.checkAnswer, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({answer: answer.value})
    });
    const data = await response.json();

    if (!data.ok) {
        showMessage(data.message || data.error, "error");
        return;
    }

    expression.innerHTML = data.expression;
    if (data.steps !== undefined) steps.textContent = data.steps;
    if (data.mistakes !== undefined) mistakes.textContent = data.mistakes;
    updateProgress(data.completed_examples, data.target_examples);

    if (data.correct === false) {
        showMessage(data.message, "error");
        answer.select();
        return;
    }

    answer.value = "";
    showMessage(data.message, "success");

    if (data.lesson_finished) {
        answer.disabled = true;
        checkButton.disabled = true;
        newButton.disabled = true;
        await saveCompletion(data.percent, data.grade);
    } else if (data.finished) {
        answer.disabled = true;
        checkButton.disabled = true;
        setTimeout(createExample, 900);
    } else {
        answer.focus();
    }
}

newButton.addEventListener("click", createExample);
checkButton.addEventListener("click", checkAnswer);
answer.addEventListener("keydown", event => {
    if (event.key === "Enter") checkAnswer();
});

createExample();
