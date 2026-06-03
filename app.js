const STORE_KEY = "bim-practice-state-v3";
const optionMarks = ["①", "②", "③", "④"];
const EXAM_SIZE = 50;
const PASS_SCORE = 60;

const data = window.BIM_QUESTIONS || { questions: [] };
const questions = data.questions || [];
const questionById = new Map(questions.map((question) => [question.id, question]));

const elements = {
  home: document.querySelector("#homeView"),
  quiz: document.querySelector("#quizView"),
  summary: document.querySelector("#summaryView"),
  homeButton: document.querySelector("#homeButton"),
  reset: document.querySelector("#resetButton"),
  modeText: document.querySelector("#modeText"),
  position: document.querySelector("#positionText"),
  score: document.querySelector("#scoreText"),
  source: document.querySelector("#sourceText"),
  number: document.querySelector("#numberText"),
  question: document.querySelector("#questionText"),
  bookmark: document.querySelector("#bookmarkButton"),
  options: document.querySelector("#options"),
  result: document.querySelector("#resultText"),
  prev: document.querySelector("#prevButton"),
  next: document.querySelector("#nextButton"),
  bookmarkSummary: document.querySelector("#bookmarkSummary"),
  tabs: Array.from(document.querySelectorAll(".mode-tabs button")),
};

let state = loadState();

function makeSession(ids) {
  return {
    order: ids,
    cursor: 0,
    answers: {},
    correct: 0,
    wrong: 0,
  };
}

function defaultState() {
  return {
    view: "home",
    mode: "home",
    bookmarks: [],
    all: makeSession(shuffle(questions.map((question) => question.id))),
    bookmarksSession: makeSession([]),
    exam: {
      phase: "idle",
      session: makeSession([]),
      reviewSession: makeSession([]),
      reviewRound: 0,
      lastWrongIds: [],
    },
  };
}

function loadState() {
  const fresh = defaultState();
  try {
    const saved = JSON.parse(localStorage.getItem(STORE_KEY) || "null");
    if (!saved || saved.all?.order?.length !== questions.length) {
      return fresh;
    }
    return {
      ...fresh,
      ...saved,
      bookmarks: Array.isArray(saved.bookmarks) ? saved.bookmarks.filter((id) => questionById.has(id)) : [],
    };
  } catch {
    return fresh;
  }
}

function saveState() {
  localStorage.setItem(STORE_KEY, JSON.stringify(state));
}

function shuffle(items) {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function sampleIds(count) {
  return shuffle(questions.map((question) => question.id)).slice(0, Math.min(count, questions.length));
}

function activeSession() {
  if (state.mode === "all") return state.all;
  if (state.mode === "bookmarks") return state.bookmarksSession;
  if (state.mode === "exam-review") return state.exam.reviewSession;
  return state.exam.session;
}

function currentQuestion() {
  const session = activeSession();
  return questionById.get(session.order[session.cursor]);
}

function answeredCount(session) {
  return Object.keys(session.answers).length;
}

function modeLabel() {
  if (state.mode === "all") return "전체문제";
  if (state.mode === "bookmarks") return "북마크";
  if (state.mode === "exam-review") return `오답복습 ${state.exam.reviewRound}회`;
  return "랜덤 모의고사";
}

function enterHome() {
  state.view = "home";
  state.mode = "home";
  saveState();
  render();
}

function enterAll() {
  state.view = "quiz";
  state.mode = "all";
  if (!state.all.order.length || state.all.order.some((id) => !questionById.has(id))) {
    state.all = makeSession(shuffle(questions.map((question) => question.id)));
  }
  saveState();
  render();
}

function enterBookmarks() {
  state.view = "quiz";
  state.mode = "bookmarks";
  state.bookmarksSession = makeSession(state.bookmarks.filter((id) => questionById.has(id)));
  saveState();
  render();
}

function enterExam() {
  state.view = "summary";
  state.mode = "exam";
  saveState();
  render();
}

function startExam() {
  state.view = "quiz";
  state.mode = "exam";
  state.exam = {
    phase: "taking",
    session: makeSession(sampleIds(EXAM_SIZE)),
    reviewSession: makeSession([]),
    reviewRound: 0,
    lastWrongIds: [],
  };
  saveState();
  render();
}

function startReview(ids) {
  state.view = "quiz";
  state.mode = "exam-review";
  state.exam.phase = "review";
  state.exam.reviewRound += 1;
  state.exam.reviewSession = makeSession(ids);
  saveState();
  render();
}

function resetCurrentMode() {
  if (state.mode === "all") {
    state.all = makeSession(shuffle(questions.map((question) => question.id)));
    enterAll();
    return;
  }
  if (state.mode === "bookmarks") {
    enterBookmarks();
    return;
  }
  if (state.mode === "exam" || state.mode === "exam-review") {
    enterExam();
    return;
  }
  state.all = makeSession(shuffle(questions.map((question) => question.id)));
  saveState();
  render();
}

function choose(index) {
  const item = currentQuestion();
  const session = activeSession();
  if (!item || Number.isInteger(session.answers[item.id])) return;

  session.answers[item.id] = index;
  if (index === item.answer) {
    session.correct += 1;
  } else {
    session.wrong += 1;
  }
  saveState();
  render();
}

function prevQuestion() {
  const session = activeSession();
  if (session.cursor === 0) return;
  session.cursor -= 1;
  saveState();
  render();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function nextQuestion() {
  const session = activeSession();
  const item = currentQuestion();
  const isAnswered = item && Number.isInteger(session.answers[item.id]);

  if (session.cursor < session.order.length - 1) {
    session.cursor += 1;
    saveState();
    render();
    window.scrollTo({ top: 0, behavior: "smooth" });
    return;
  }

  if (state.mode === "exam" && isAnswered) {
    showExamResult();
    return;
  }

  if (state.mode === "exam-review" && isAnswered) {
    showReviewResult();
    return;
  }

  if (state.mode === "all") {
    state.all = makeSession(shuffle(questions.map((question) => question.id)));
    saveState();
    render();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

function toggleBookmark() {
  const item = currentQuestion();
  if (!item) return;

  if (state.bookmarks.includes(item.id)) {
    state.bookmarks = state.bookmarks.filter((id) => id !== item.id);
  } else {
    state.bookmarks = [item.id, ...state.bookmarks];
  }
  if (state.mode === "bookmarks") {
    const session = state.bookmarksSession;
    session.order = session.order.filter((id) => state.bookmarks.includes(id));
    if (session.cursor >= session.order.length) {
      session.cursor = Math.max(0, session.order.length - 1);
    }
  }
  saveState();
  render();
}

function wrongIdsFromSession(session) {
  return session.order.filter((id) => {
    const item = questionById.get(id);
    return item && session.answers[id] !== item.answer;
  });
}

function showExamResult() {
  const session = state.exam.session;
  state.exam.phase = "result";
  state.exam.lastWrongIds = wrongIdsFromSession(session);
  state.view = "summary";
  state.mode = "exam";
  saveState();
  render();
}

function showReviewResult() {
  const session = state.exam.reviewSession;
  const wrongIds = wrongIdsFromSession(session);
  state.exam.lastWrongIds = wrongIds;
  state.view = "summary";
  state.mode = "exam-review";
  state.exam.phase = wrongIds.length ? "review-result" : "complete";
  saveState();
  render();
}

function render() {
  renderShell();
  renderBookmarkSummary();
  if (state.view === "home") {
    renderHome();
  } else if (state.view === "summary") {
    renderSummary();
  } else {
    renderQuiz();
  }
}

function renderShell() {
  elements.home.hidden = state.view !== "home";
  elements.quiz.hidden = state.view !== "quiz";
  elements.summary.hidden = state.view !== "summary";
  elements.tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.mode === (state.mode === "exam-review" ? "exam" : state.mode)));
}

function renderBookmarkSummary() {
  const count = state.bookmarks.length;
  elements.bookmarkSummary.textContent = count ? `${count}문항을 저장했습니다.` : "저장한 문제만 다시 봅니다.";
}

function renderHome() {
  elements.summary.innerHTML = "";
}

function renderQuiz() {
  const session = activeSession();
  const item = currentQuestion();

  if (!item) {
    renderEmptyQuiz();
    return;
  }

  const selected = session.answers[item.id];
  const isAnswered = Number.isInteger(selected);
  const isBookmarked = state.bookmarks.includes(item.id);
  const current = session.cursor + 1;
  const total = session.order.length;

  elements.modeText.textContent = modeLabel();
  elements.position.textContent = `${current} / ${total}`;
  elements.score.textContent = scoreText(session);
  elements.source.textContent = item.source;
  elements.source.title = item.source;
  elements.number.textContent = `${item.number}번`;
  elements.question.textContent = item.question;
  elements.bookmark.textContent = isBookmarked ? "★" : "☆";
  elements.bookmark.classList.toggle("active", isBookmarked);
  elements.bookmark.setAttribute("aria-label", isBookmarked ? "북마크 제거" : "북마크 추가");
  elements.prev.disabled = session.cursor === 0;
  elements.next.disabled = (state.mode === "exam" || state.mode === "exam-review") && !isAnswered;
  elements.next.textContent = nextButtonText(session, isAnswered);

  elements.options.innerHTML = "";
  item.options.forEach((label, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "option";
    button.dataset.index = String(index);
    button.disabled = isAnswered;

    if (isAnswered && index === item.answer) button.classList.add("correct");
    if (isAnswered && index === selected && selected !== item.answer) button.classList.add("wrong");

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

function renderEmptyQuiz() {
  elements.modeText.textContent = modeLabel();
  elements.position.textContent = "";
  elements.score.textContent = "";
  elements.source.textContent = "";
  elements.number.textContent = "";
  elements.question.textContent = state.mode === "bookmarks" ? "북마크한 문제가 없습니다." : "문제 데이터를 찾을 수 없습니다.";
  elements.options.innerHTML = "";
  elements.result.textContent = state.mode === "bookmarks" ? "문제 화면의 별표를 눌러 저장해보세요." : "";
  elements.bookmark.textContent = "☆";
  elements.prev.disabled = true;
  elements.next.disabled = false;
  elements.next.textContent = "홈으로";
}

function scoreText(session) {
  if (state.mode === "exam") {
    return `풀이 ${answeredCount(session)} · 정답 ${session.correct} · 오답 ${session.wrong}`;
  }
  if (state.mode === "exam-review") {
    return `정답 ${session.correct} · 오답 ${session.wrong}`;
  }
  return `정답 ${session.correct} · 오답 ${session.wrong}`;
}

function nextButtonText(session, isAnswered) {
  const isLast = session.cursor === session.order.length - 1;
  if ((state.mode === "exam" || state.mode === "exam-review") && isLast && isAnswered) {
    return "결과 보기";
  }
  if (state.mode === "all" && isLast) {
    return "다시 섞기";
  }
  return "다음";
}

function renderSummary() {
  elements.summary.innerHTML = "";
  if (state.mode === "exam-review" && state.exam.phase === "complete") {
    elements.summary.append(summaryCard({
      kicker: "Complete",
      title: "모의고사 1회 학습완료",
      body: `오답 복습 ${state.exam.reviewRound}회차에서 모든 오답을 해결했습니다.`,
      stats: [`남은 오답 0개`, `복습 정답 ${state.exam.reviewSession.correct}개`],
      actions: [
        ["새 모의고사 시작", startExam, true],
        ["홈으로", enterHome, false],
      ],
    }));
    return;
  }

  if (state.mode === "exam-review") {
    const session = state.exam.reviewSession;
    const wrongIds = state.exam.lastWrongIds;
    elements.summary.append(summaryCard({
      kicker: `Review ${state.exam.reviewRound}`,
      title: "오답 복습 결과",
      body: wrongIds.length ? "아직 남은 오답만 다시 모아서 이어서 복습합니다." : "이번 오답 복습에서 모두 맞혔습니다.",
      stats: [`정답 ${session.correct}개`, `오답 ${wrongIds.length}개`],
      actions: [
        [`오답 ${wrongIds.length}개 다시 풀기`, () => startReview(wrongIds), true],
        ["새 모의고사", startExam, false],
      ],
    }));
    return;
  }

  const session = state.exam.session;
  if (state.exam.phase === "idle" || !session.order.length) {
    elements.summary.append(summaryCard({
      kicker: "Mock Test",
      title: "랜덤 모의고사 50문제",
      body: "200문항 중 50문항을 랜덤으로 뽑습니다. 답을 고르면 바로 정답 여부를 확인할 수 있습니다.",
      stats: [`합격 기준 ${PASS_SCORE}점`, `문항당 2점`],
      actions: [["모의고사 시작", startExam, true], ["홈으로", enterHome, false]],
    }));
    return;
  }

  const score = session.correct * 2;
  const passed = score >= PASS_SCORE;
  const wrongIds = state.exam.lastWrongIds;
  elements.summary.append(summaryCard({
    kicker: passed ? "Pass" : "Retry",
    title: passed ? "합격" : "불합격",
    body: `점수는 ${score}점입니다. ${passed ? "합격 기준을 넘겼습니다." : "오답 복습으로 부족한 부분을 바로 줄여봅니다."}`,
    stats: [`점수 ${score}점`, `정답 ${session.correct}개`, `오답 ${wrongIds.length}개`],
    actions: wrongIds.length
      ? [[`오답 ${wrongIds.length}개 풀기`, () => startReview(wrongIds), true], ["새 모의고사", startExam, false]]
      : [["모의고사 1회 학습완료", enterHome, true], ["새 모의고사", startExam, false]],
  }));
}

function summaryCard({ kicker, title, body, stats, actions }) {
  const card = document.createElement("div");
  card.className = "summary-card";

  const eyebrow = document.createElement("p");
  eyebrow.className = "eyebrow";
  eyebrow.textContent = kicker;

  const heading = document.createElement("h1");
  heading.textContent = title;

  const copy = document.createElement("p");
  copy.className = "summary-copy";
  copy.textContent = body;

  const statList = document.createElement("div");
  statList.className = "summary-stats";
  stats.forEach((stat) => {
    const item = document.createElement("span");
    item.textContent = stat;
    statList.append(item);
  });

  const actionList = document.createElement("div");
  actionList.className = "summary-actions";
  actions.forEach(([label, handler, primary]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = primary ? "nav-button primary" : "nav-button";
    button.textContent = label;
    button.addEventListener("click", handler);
    actionList.append(button);
  });

  card.append(eyebrow, heading, copy, statList, actionList);
  return card;
}

document.querySelectorAll("[data-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    if (button.dataset.mode === "all") enterAll();
    if (button.dataset.mode === "exam") enterExam();
    if (button.dataset.mode === "bookmarks") enterBookmarks();
  });
});

elements.homeButton.addEventListener("click", enterHome);
elements.reset.addEventListener("click", resetCurrentMode);
elements.prev.addEventListener("click", prevQuestion);
elements.next.addEventListener("click", () => {
  if (!currentQuestion()) {
    enterHome();
    return;
  }
  nextQuestion();
});
elements.bookmark.addEventListener("click", toggleBookmark);

render();
