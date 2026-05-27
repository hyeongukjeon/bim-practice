const storeKey = "bim-practice-state-v1";
const optionMarks = ["①", "②", "③", "④"];

const data = window.BIM_QUESTIONS || { questions: [] };
const questions = data.questions || [];

const elements = {
  position: document.querySelector("#positionText"),
  score: document.querySelector("#scoreText"),
  source: document.querySelector("#sourceText"),
  number: document.querySelector("#numberText"),
  question: document.querySelector("#questionText"),
  options: document.querySelector("#options"),
  result: document.querySelector("#resultText"),
  prev: document.querySelector("#prevButton"),
  next: document.querySelector("#nextButton"),
  reset: document.querySelector("#resetButton"),
};

let state = loadState();

function loadState() {
  const fresh = {
    order: shuffle([...questions.keys()]),
    cursor: 0,
    answers: {},
    correct: 0,
    wrong: 0,
  };

  try {
    const saved = JSON.parse(localStorage.getItem(storeKey) || "null");
    if (!saved || saved.order?.length !== questions.length) {
      return fresh;
    }
    return {
      ...fresh,
      ...saved,
      answers: saved.answers || {},
    };
  } catch {
    return fresh;
  }
}

function saveState() {
  localStorage.setItem(storeKey, JSON.stringify(state));
}

function shuffle(items) {
  for (let i = items.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [items[i], items[j]] = [items[j], items[i]];
  }
  return items;
}

function currentQuestion() {
  return questions[state.order[state.cursor]];
}

function render() {
  if (!questions.length) {
    elements.question.textContent = "문제 데이터를 찾을 수 없습니다.";
    return;
  }

  const item = currentQuestion();
  const selected = state.answers[item.id];
  const isAnswered = Number.isInteger(selected);

  elements.position.textContent = `${state.cursor + 1} / ${questions.length}`;
  elements.score.textContent = `정답 ${state.correct} · 오답 ${state.wrong}`;
  elements.source.textContent = item.source;
  elements.source.title = item.source;
  elements.number.textContent = `${item.number}번`;
  elements.question.textContent = item.question;
  elements.prev.disabled = state.cursor === 0;

  elements.options.innerHTML = "";
  item.options.forEach((label, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "option";
    button.dataset.index = String(index);

    if (isAnswered && index === item.answer) {
      button.classList.add("correct");
    }
    if (isAnswered && index === selected && selected !== item.answer) {
      button.classList.add("wrong");
    }

    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = optionMarks[index];

    const text = document.createElement("span");
    text.className = "label";
    text.textContent = label;

    button.append(badge, text);
    button.addEventListener("click", () => choose(index));
    elements.options.append(button);
  });

  elements.result.className = "result";
  if (!isAnswered) {
    elements.result.textContent = "";
  } else if (selected === item.answer) {
    elements.result.textContent = "정답";
    elements.result.classList.add("correct");
  } else {
    elements.result.textContent = `오답 · 정답 ${optionMarks[item.answer]}`;
    elements.result.classList.add("wrong");
  }
}

function choose(index) {
  const item = currentQuestion();
  if (Number.isInteger(state.answers[item.id])) {
    return;
  }

  state.answers[item.id] = index;
  if (index === item.answer) {
    state.correct += 1;
  } else {
    state.wrong += 1;
  }
  saveState();
  render();
}

function nextQuestion() {
  if (state.cursor < state.order.length - 1) {
    state.cursor += 1;
  } else {
    state.order = shuffle([...questions.keys()]);
    state.cursor = 0;
    state.answers = {};
    state.correct = 0;
    state.wrong = 0;
  }
  saveState();
  render();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function prevQuestion() {
  if (state.cursor === 0) {
    return;
  }
  state.cursor -= 1;
  saveState();
  render();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function resetPractice() {
  state = {
    order: shuffle([...questions.keys()]),
    cursor: 0,
    answers: {},
    correct: 0,
    wrong: 0,
  };
  saveState();
  render();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

elements.next.addEventListener("click", nextQuestion);
elements.prev.addEventListener("click", prevQuestion);
elements.reset.addEventListener("click", resetPractice);

render();
