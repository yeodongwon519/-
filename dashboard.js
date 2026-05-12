/* ========================================================================
   Bizboard — multi-business personal dashboard
   Pure vanilla JS, localStorage-backed
   ======================================================================== */

const STORAGE_KEY = "bizboard:v1";
const COLORS = ["#6366f1", "#ec4899", "#22c55e", "#f59e0b", "#06b6d4", "#a855f7", "#ef4444", "#84cc16"];

const STATUS_LABELS = {
  active: "활발",
  paused: "유지",
  risk: "주의",
  idle: "대기",
};

/* ---------- State ---------- */
let state = {
  businesses: [],
  todos: [],
  routines: [],
  schedule: [],
};

let weekOffset = 0; // 0 = this week
let currentView = "today";

/* ---------- Utilities ---------- */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 7);

const pad = (n) => String(n).padStart(2, "0");
const todayStr = () => {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};
const dateStr = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const parseDate = (s) => {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
};
const dayOfWeek = (s) => parseDate(s).getDay(); // 0=Sun
const addDays = (d, n) => { const r = new Date(d); r.setDate(r.getDate() + n); return r; };

function getWeekDates(offset = 0) {
  const today = new Date();
  const day = today.getDay(); // 0=Sun, 1=Mon
  const mondayDelta = day === 0 ? -6 : 1 - day;
  const monday = addDays(today, mondayDelta + offset * 7);
  return Array.from({ length: 7 }, (_, i) => addDays(monday, i));
}

function formatKDate(d) {
  const wk = ["일", "월", "화", "수", "목", "금", "토"][d.getDay()];
  return `${d.getMonth() + 1}월 ${d.getDate()}일 (${wk})`;
}

/* ---------- Storage ---------- */
function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      state = { businesses: [], todos: [], routines: [], schedule: [], ...parsed };
    }
  } catch (e) {
    console.warn("load failed", e);
  }
}
function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

/* ---------- Business helpers ---------- */
const findBiz = (id) => state.businesses.find((b) => b.id === id);
const bizColor = (id) => findBiz(id)?.color || "#6366f1";
const bizName = (id) => findBiz(id)?.name || "—";

/* ---------- Toast ---------- */
let toastTimer;
function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 1800);
}

/* ---------- Navigation ---------- */
function switchView(view) {
  currentView = view;
  $$(".nav-item").forEach((n) => n.classList.toggle("active", n.dataset.view === view));
  $$(".view").forEach((s) => s.classList.toggle("active", s.dataset.view === view));
  const titles = { today: "오늘", businesses: "사업", routines: "루틴", schedule: "주간 일정", stats: "한눈에 보기" };
  $("#topTitle").textContent = titles[view];
  $("#topSubtitle").textContent = subtitleFor(view);
  renderAll();
}

function subtitleFor(view) {
  if (view === "today") {
    const d = new Date();
    return `${formatKDate(d)} · 정신없는 하루를 한눈에 정리해봐요`;
  }
  if (view === "businesses") return `${state.businesses.length}개의 사업을 관리 중`;
  if (view === "routines") return `${state.routines.length}개의 루틴`;
  if (view === "schedule") return "주간 시간 배분을 시각적으로 확인";
  if (view === "stats") return "전체 진척 · 시간 · 루틴 연속 달성";
  return "";
}

/* ===========================================================
   RENDER
   =========================================================== */
function renderAll() {
  if (currentView === "today") renderToday();
  else if (currentView === "businesses") renderBusinesses();
  else if (currentView === "routines") renderRoutines();
  else if (currentView === "schedule") renderSchedule();
  else if (currentView === "stats") renderStats();
}

/* ----- TODAY ----- */
function renderToday() {
  const today = todayStr();
  const todos = state.todos.filter((t) => t.date === today);
  const todosDone = todos.filter((t) => t.done).length;

  $("#statTodoDone").textContent = todosDone;
  $("#statTodoTotal").textContent = todos.length;
  $("#statTodoBar").style.width = todos.length ? `${(todosDone / todos.length) * 100}%` : "0%";

  const routinesToday = state.routines.filter((r) => routineActiveOn(r, today));
  const routinesDoneToday = routinesToday.filter((r) => r.history?.[today]).length;
  $("#statRoutineDone").textContent = routinesDoneToday;
  $("#statRoutineTotal").textContent = routinesToday.length;
  $("#statRoutineBar").style.width = routinesToday.length ? `${(routinesDoneToday / routinesToday.length) * 100}%` : "0%";

  const activeBiz = state.businesses.filter((b) => b.status !== "idle");
  $("#statBizCount").textContent = activeBiz.length;
  $("#statBizStatus").textContent = state.businesses.length
    ? `전체 ${state.businesses.length}개 중`
    : "사업 탭에서 추가해보세요";

  const top = [...state.businesses].sort((a, b) => (b.progress || 0) - (a.progress || 0))[0];
  $("#statFocus").textContent = top ? top.name : "—";

  // Today's todos
  const todoList = $("#todayTodoList");
  if (todos.length === 0) {
    todoList.innerHTML = `<li class="empty">아직 오늘 할 일이 없어요. + 추가로 등록해보세요.</li>`;
  } else {
    const sorted = [...todos].sort((a, b) => (a.time || "99").localeCompare(b.time || "99"));
    todoList.innerHTML = sorted.map(renderTodoItem).join("");
  }

  // Today's routines
  const routineList = $("#todayRoutineList");
  if (routinesToday.length === 0) {
    routineList.innerHTML = `<li class="empty">오늘 해당하는 루틴이 없어요.</li>`;
  } else {
    routineList.innerHTML = routinesToday.map((r) => renderRoutineDailyItem(r, today)).join("");
  }

  // Timeline
  renderTodayTimeline();
}

function renderTodoItem(t) {
  const b = t.businessId ? findBiz(t.businessId) : null;
  const tag = b ? `<span class="biz-tag"><span class="dot" style="background:${b.color}"></span>${escapeHtml(b.name)}</span>` : "";
  const timeStr = t.time ? `<span>${t.time}</span>` : "";
  return `<li class="item ${t.done ? "done" : ""}">
    <span class="check ${t.done ? "done" : ""}" data-toggle-todo="${t.id}"></span>
    <span class="item-text">${escapeHtml(t.text)}</span>
    <span class="item-meta">${timeStr}${tag}</span>
    <span class="item-actions">
      <button class="icon-btn" data-edit-todo="${t.id}" title="편집">✎</button>
      <button class="icon-btn" data-del-todo="${t.id}" title="삭제">✕</button>
    </span>
  </li>`;
}

function renderRoutineDailyItem(r, today) {
  const done = !!r.history?.[today];
  const b = r.businessId ? findBiz(r.businessId) : null;
  const tag = b ? `<span class="biz-tag"><span class="dot" style="background:${b.color}"></span>${escapeHtml(b.name)}</span>` : "";
  const timeStr = r.time ? `<span>${r.time}</span>` : "";
  const freq = r.frequency === "daily" ? "매일" : "매주";
  return `<li class="item ${done ? "done" : ""}">
    <span class="check ${done ? "done" : ""}" data-toggle-routine="${r.id}"></span>
    <span class="item-text">${escapeHtml(r.name)}</span>
    <span class="item-meta">${timeStr}<span class="biz-tag">${freq}</span>${tag}</span>
  </li>`;
}

function renderTodayTimeline() {
  const today = todayStr();
  const items = state.schedule.filter((s) => s.date === today);
  const el = $("#todayTimeline");

  if (items.length === 0) {
    el.innerHTML = `<div class="timeline-empty">오늘 등록된 일정이 없어요. + 일정 추가로 시간을 블록화 해보세요.</div>`;
    return;
  }

  const sorted = [...items].sort((a, b) => a.startTime.localeCompare(b.startTime));
  el.innerHTML = sorted.map((s) => {
    const b = s.businessId ? findBiz(s.businessId) : null;
    const color = b?.color || "#6366f1";
    const tag = b ? `<span class="biz-tag"><span class="dot" style="background:${color}"></span>${escapeHtml(b.name)}</span>` : "";
    return `<div class="tl-row">
      <div class="tl-time">${s.startTime}<br/>${s.endTime}</div>
      <div class="tl-block" style="border-left-color:${color}; background:${hexToRgba(color, 0.12)}" data-edit-schedule="${s.id}">
        <div class="tl-block-title">${escapeHtml(s.title)}</div>
        <div class="item-meta">${tag}</div>
      </div>
    </div>`;
  }).join("");
}

/* ----- BUSINESSES ----- */
function renderBusinesses() {
  const grid = $("#bizGrid");
  const cards = state.businesses.map((b) => {
    const doneMs = (b.milestones || []).filter((m) => m.done).length;
    const totalMs = (b.milestones || []).length;
    const statusKey = b.status || "active";
    return `<div class="biz-card" style="--biz-color:${b.color}" data-edit-biz="${b.id}">
      <div class="biz-card-head">
        <div class="biz-card-name">${escapeHtml(b.name)}</div>
        <span class="biz-card-status ${statusKey}">${STATUS_LABELS[statusKey] || statusKey}</span>
      </div>
      <div class="biz-progress-num">${b.progress || 0}<span>%</span></div>
      <div class="progress"><div class="progress-fill" style="width:${b.progress || 0}%"></div></div>
      <div class="biz-meta">
        <span>마일스톤 ${doneMs}/${totalMs}</span>
        <span>${countTodayTodosFor(b.id)} todo · ${countRoutinesFor(b.id)} 루틴</span>
      </div>
      ${b.note ? `<div class="biz-note">${escapeHtml(b.note)}</div>` : ""}
    </div>`;
  }).join("");

  const addCard = `<button class="biz-add-card" data-action="add-business">+ 사업 추가</button>`;
  grid.innerHTML = cards + addCard;
}

const countTodayTodosFor = (bid) => state.todos.filter((t) => t.businessId === bid && t.date === todayStr()).length;
const countRoutinesFor = (bid) => state.routines.filter((r) => r.businessId === bid).length;

/* ----- ROUTINES ----- */
function renderRoutines() {
  const list = $("#routineList");
  if (state.routines.length === 0) {
    list.innerHTML = `<li class="empty">매일·매주 반복할 일을 추가해보세요.</li>`;
    return;
  }
  list.innerHTML = state.routines.map((r) => {
    const b = r.businessId ? findBiz(r.businessId) : null;
    const tag = b ? `<span class="biz-tag"><span class="dot" style="background:${b.color}"></span>${escapeHtml(b.name)}</span>` : "";
    const freqText = r.frequency === "daily"
      ? "매일"
      : `매주 ${(r.weekdays || []).map((d) => "일월화수목금토"[d]).join(",")}`;
    const streak = computeStreak(r);
    return `<li class="item">
      <span class="item-text">${escapeHtml(r.name)}</span>
      <span class="item-meta">
        ${r.time ? `<span>${r.time}</span>` : ""}
        <span class="biz-tag">${freqText}</span>
        ${tag}
        <span class="biz-tag" title="연속 달성">🔥 ${streak}</span>
      </span>
      <span class="item-actions">
        <button class="icon-btn" data-edit-routine="${r.id}" title="편집">✎</button>
        <button class="icon-btn" data-del-routine="${r.id}" title="삭제">✕</button>
      </span>
    </li>`;
  }).join("");
}

function routineActiveOn(r, dateString) {
  if (r.frequency === "daily") return true;
  if (r.frequency === "weekly") return (r.weekdays || []).includes(dayOfWeek(dateString));
  return false;
}

function computeStreak(r) {
  let streak = 0;
  let cursor = new Date();
  const today = todayStr();
  for (let i = 0; i < 365; i++) {
    const ds = dateStr(cursor);
    if (routineActiveOn(r, ds)) {
      if (r.history?.[ds]) streak++;
      else if (ds !== today) break; // don't penalize an incomplete today
    }
    cursor = addDays(cursor, -1);
  }
  return streak;
}

/* ----- SCHEDULE ----- */
function renderSchedule() {
  const dates = getWeekDates(weekOffset);
  const today = todayStr();
  const HOURS_START = 6;
  const HOURS_END = 24; // exclusive

  $("#weekLabel").textContent = `${dates[0].getMonth() + 1}.${dates[0].getDate()} – ${dates[6].getMonth() + 1}.${dates[6].getDate()}`;

  const headers = ["", ...dates].map((d, i) => {
    if (i === 0) return `<div class="wg-cell wg-header"></div>`;
    const isToday = dateStr(d) === today;
    return `<div class="wg-cell wg-header ${isToday ? "today" : ""}">
      ${["일","월","화","수","목","금","토"][d.getDay()]}<span class="date-num">${d.getDate()}</span>
    </div>`;
  }).join("");

  let body = "";
  for (let h = HOURS_START; h < HOURS_END; h++) {
    body += `<div class="wg-cell wg-time">${pad(h)}:00</div>`;
    for (let i = 0; i < 7; i++) {
      const ds = dateStr(dates[i]);
      const blocks = state.schedule.filter((s) => {
        if (s.date !== ds) return false;
        const sh = parseInt(s.startTime.split(":")[0], 10);
        return sh === h;
      });
      const inner = blocks.map((s) => {
        const c = s.businessId ? bizColor(s.businessId) : "#6366f1";
        return `<div class="wg-block" style="background:${c}" data-edit-schedule="${s.id}" title="${escapeHtml(s.title)} (${s.startTime}–${s.endTime})">${escapeHtml(s.title)}</div>`;
      }).join("");
      body += `<div class="wg-cell" data-quickadd-date="${ds}" data-quickadd-hour="${pad(h)}:00">${inner}</div>`;
    }
  }

  $("#weekGrid").innerHTML = headers + body;
}

/* ----- STATS ----- */
function renderStats() {
  // bar chart: business progress
  const bar = $("#progressChart");
  if (state.businesses.length === 0) {
    bar.innerHTML = `<div class="empty muted small" style="padding:24px 0;text-align:center">사업을 추가하면 표시돼요.</div>`;
  } else {
    bar.innerHTML = state.businesses.map((b) => `
      <div class="bar-row">
        <span class="bar-name">${escapeHtml(b.name)}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${b.progress || 0}%; background:${b.color}"></div></div>
        <span class="bar-pct">${b.progress || 0}%</span>
      </div>
    `).join("");
  }

  // donut: this week's time allocation
  const dates = getWeekDates(0).map(dateStr);
  const minutesByBiz = {};
  let total = 0;
  for (const s of state.schedule) {
    if (!dates.includes(s.date)) continue;
    const mins = minutesBetween(s.startTime, s.endTime);
    const key = s.businessId || "__none__";
    minutesByBiz[key] = (minutesByBiz[key] || 0) + mins;
    total += mins;
  }

  const svg = $("#donut");
  const legend = $("#donutLegend");
  if (total === 0) {
    svg.innerHTML = `<circle cx="100" cy="100" r="70" fill="none" stroke="#1f2937" stroke-width="22"/>`;
    legend.innerHTML = `<li class="muted small">이번 주 일정이 없어요</li>`;
  } else {
    let acc = 0;
    const radius = 70;
    const circ = 2 * Math.PI * radius;
    let arcs = `<circle cx="100" cy="100" r="${radius}" fill="none" stroke="#1f2937" stroke-width="22"/>`;
    const legendItems = [];
    Object.entries(minutesByBiz).sort((a, b) => b[1] - a[1]).forEach(([key, mins]) => {
      const frac = mins / total;
      const color = key === "__none__" ? "#64748b" : bizColor(key);
      const name = key === "__none__" ? "미지정" : bizName(key);
      const dash = circ * frac;
      const gap = circ - dash;
      const offset = -circ * acc;
      arcs += `<circle cx="100" cy="100" r="${radius}" fill="none" stroke="${color}" stroke-width="22"
        stroke-dasharray="${dash} ${gap}" stroke-dashoffset="${offset}" transform="rotate(-90 100 100)"/>`;
      acc += frac;
      legendItems.push(`<li>
        <span class="dot" style="background:${color}"></span>
        <span>${escapeHtml(name)}</span>
        <span class="pct">${Math.round(frac * 100)}% · ${Math.round(mins / 60 * 10) / 10}h</span>
      </li>`);
    });
    svg.innerHTML = arcs + `<text x="100" y="96" text-anchor="middle" fill="#cbd5e1" font-size="11">이번 주 합계</text>
      <text x="100" y="116" text-anchor="middle" fill="#fff" font-size="20" font-weight="600">${Math.round(total / 60 * 10) / 10}h</text>`;
    legend.innerHTML = legendItems.join("");
  }

  // streaks
  const streakGrid = $("#streakGrid");
  if (state.routines.length === 0) {
    streakGrid.innerHTML = `<div class="empty muted small" style="padding:24px 0;text-align:center">루틴을 추가하면 표시돼요.</div>`;
  } else {
    const today = todayStr();
    streakGrid.innerHTML = state.routines.map((r) => {
      const cells = [];
      for (let i = 13; i >= 0; i--) {
        const d = addDays(new Date(), -i);
        const ds = dateStr(d);
        const on = !!r.history?.[ds];
        const isToday = ds === today;
        cells.push(`<div class="streak-cell ${on ? "on" : ""} ${isToday ? "today" : ""}" title="${ds}"></div>`);
      }
      return `<div class="streak-row">
        <span class="bar-name">${escapeHtml(r.name)}</span>
        <div class="streak-cells">${cells.join("")}</div>
        <span class="streak-count">🔥 ${computeStreak(r)}</span>
      </div>`;
    }).join("");
  }
}

function minutesBetween(start, end) {
  const [sh, sm] = start.split(":").map(Number);
  const [eh, em] = end.split(":").map(Number);
  return Math.max(0, eh * 60 + em - (sh * 60 + sm));
}

/* ===========================================================
   MODALS / FORMS
   =========================================================== */
let modalState = null;

function openModal(type, data = null) {
  modalState = { type, data };
  const titles = {
    business: data ? "사업 편집" : "사업 추가",
    todo: data ? "할 일 편집" : "할 일 추가",
    routine: data ? "루틴 편집" : "루틴 추가",
    schedule: data ? "일정 편집" : "일정 추가",
    quickAdd: "빠른 추가",
  };
  $("#modalTitle").textContent = titles[type];
  $("#modalBody").innerHTML = formHtml(type, data);
  $("#modal").classList.remove("hidden");

  // hook into color dots
  if (type === "business") {
    bindColorPicker(data?.color || COLORS[state.businesses.length % COLORS.length]);
    bindMilestoneEditor(data?.milestones || []);
  }
  if (type === "routine") {
    bindFrequencyToggle(data?.frequency || "daily");
  }
  if (type === "quickAdd") {
    bindQuickAdd();
  }
}

function closeModal() {
  $("#modal").classList.add("hidden");
  modalState = null;
}

function bizOptionsHtml(selectedId) {
  const blank = `<option value="">— 사업 미지정 —</option>`;
  return blank + state.businesses.map((b) =>
    `<option value="${b.id}" ${b.id === selectedId ? "selected" : ""}>${escapeHtml(b.name)}</option>`
  ).join("");
}

function formHtml(type, d) {
  if (type === "business") {
    const colors = COLORS.map((c) => `<span class="color-dot" data-color="${c}" style="background:${c}"></span>`).join("");
    return `
      <div class="field"><label>사업 이름</label><input type="text" id="f-name" value="${escapeAttr(d?.name || "")}" placeholder="예: 사업 A" /></div>
      <div class="field-row">
        <div class="field"><label>진행률 (%)</label><input type="number" id="f-progress" min="0" max="100" value="${d?.progress ?? 0}" /></div>
        <div class="field"><label>상태</label>
          <select id="f-status">
            <option value="active" ${d?.status === "active" ? "selected" : ""}>활발</option>
            <option value="paused" ${d?.status === "paused" ? "selected" : ""}>유지</option>
            <option value="risk" ${d?.status === "risk" ? "selected" : ""}>주의</option>
            <option value="idle" ${d?.status === "idle" ? "selected" : ""}>대기</option>
          </select>
        </div>
      </div>
      <div class="field"><label>컬러</label><div class="color-row" id="f-colors">${colors}</div></div>
      <div class="field"><label>한 줄 메모</label><textarea id="f-note" placeholder="현재 상황, 다음 단계 등">${escapeHtml(d?.note || "")}</textarea></div>
      <div class="field"><label>마일스톤</label><div class="milestones-edit" id="f-milestones"></div>
        <button type="button" class="ghost-btn" id="f-ms-add" style="margin-top:6px">+ 마일스톤 추가</button>
      </div>
      ${d ? `<button type="button" class="ghost-btn" id="f-delete" style="color:#f87171; border-color:#7f1d1d">삭제</button>` : ""}
    `;
  }

  if (type === "todo") {
    return `
      <div class="field"><label>할 일</label><input type="text" id="f-text" value="${escapeAttr(d?.text || "")}" placeholder="예: 사업 A 미팅 자료 준비" /></div>
      <div class="field-row">
        <div class="field"><label>날짜</label><input type="date" id="f-date" value="${d?.date || todayStr()}" /></div>
        <div class="field"><label>시간 (선택)</label><input type="time" id="f-time" value="${d?.time || ""}" /></div>
      </div>
      <div class="field"><label>관련 사업</label><select id="f-biz">${bizOptionsHtml(d?.businessId)}</select></div>
      ${d ? `<button type="button" class="ghost-btn" id="f-delete" style="color:#f87171; border-color:#7f1d1d">삭제</button>` : ""}
    `;
  }

  if (type === "routine") {
    const wd = d?.weekdays || [1, 2, 3, 4, 5];
    const wkBtns = ["일","월","화","수","목","금","토"].map((label, i) =>
      `<button type="button" class="ghost-btn weekday ${wd.includes(i) ? "selected" : ""}" data-wd="${i}" style="${wd.includes(i) ? "background:#6366f1;color:#fff;border-color:#6366f1" : ""}">${label}</button>`
    ).join("");
    return `
      <div class="field"><label>루틴 이름</label><input type="text" id="f-name" value="${escapeAttr(d?.name || "")}" placeholder="예: 매일 아침 보고 확인" /></div>
      <div class="field-row">
        <div class="field"><label>주기</label>
          <select id="f-freq">
            <option value="daily" ${d?.frequency === "daily" ? "selected" : ""}>매일</option>
            <option value="weekly" ${d?.frequency === "weekly" ? "selected" : ""}>매주 (요일 선택)</option>
          </select>
        </div>
        <div class="field"><label>시간 (선택)</label><input type="time" id="f-time" value="${d?.time || ""}" /></div>
      </div>
      <div class="field" id="f-weekdays-wrap" style="${d?.frequency === "weekly" ? "" : "display:none"}">
        <label>요일</label>
        <div class="color-row" id="f-weekdays">${wkBtns}</div>
      </div>
      <div class="field"><label>관련 사업</label><select id="f-biz">${bizOptionsHtml(d?.businessId)}</select></div>
      ${d ? `<button type="button" class="ghost-btn" id="f-delete" style="color:#f87171; border-color:#7f1d1d">삭제</button>` : ""}
    `;
  }

  if (type === "schedule") {
    return `
      <div class="field"><label>일정 제목</label><input type="text" id="f-title" value="${escapeAttr(d?.title || "")}" placeholder="예: 사업 A 회의" /></div>
      <div class="field"><label>날짜</label><input type="date" id="f-date" value="${d?.date || todayStr()}" /></div>
      <div class="field-row">
        <div class="field"><label>시작</label><input type="time" id="f-start" value="${d?.startTime || "09:00"}" /></div>
        <div class="field"><label>종료</label><input type="time" id="f-end" value="${d?.endTime || "10:00"}" /></div>
      </div>
      <div class="field"><label>관련 사업</label><select id="f-biz">${bizOptionsHtml(d?.businessId)}</select></div>
      ${d ? `<button type="button" class="ghost-btn" id="f-delete" style="color:#f87171; border-color:#7f1d1d">삭제</button>` : ""}
    `;
  }

  if (type === "quickAdd") {
    return `
      <div class="field"><label>무엇을 추가할까요?</label>
        <select id="qa-type">
          <option value="todo">오늘 할 일</option>
          <option value="schedule">일정 (시간 블록)</option>
          <option value="routine">반복 루틴</option>
          <option value="business">사업</option>
        </select>
      </div>
      <p class="muted small">선택 후 "다음"을 누르면 상세 입력 화면으로 이동해요.</p>
    `;
  }

  return "";
}

function bindColorPicker(selected) {
  const row = $("#f-colors");
  if (!row) return;
  const dots = $$(".color-dot", row);
  const mark = (c) => dots.forEach((d) => d.classList.toggle("selected", d.dataset.color === c));
  mark(selected);
  row.dataset.selected = selected;
  dots.forEach((d) => d.addEventListener("click", () => {
    row.dataset.selected = d.dataset.color;
    mark(d.dataset.color);
  }));
}

function bindMilestoneEditor(initial) {
  const wrap = $("#f-milestones");
  if (!wrap) return;
  let items = initial.map((m) => ({ ...m }));

  function render() {
    wrap.innerHTML = items.map((m, i) => `
      <div class="milestone-edit-row" data-i="${i}">
        <span class="check ${m.done ? "done" : ""}" data-ms-toggle="${i}"></span>
        <input type="text" data-ms-name="${i}" value="${escapeAttr(m.name)}" placeholder="마일스톤" />
        <button type="button" class="icon-btn" data-ms-del="${i}">✕</button>
      </div>
    `).join("");
    wrap._items = items;
  }
  render();

  wrap.addEventListener("click", (e) => {
    const tgt = e.target.closest("[data-ms-toggle], [data-ms-del]");
    if (!tgt) return;
    const idx = Number(tgt.dataset.msToggle ?? tgt.dataset.msDel);
    if (tgt.dataset.msToggle !== undefined) items[idx].done = !items[idx].done;
    if (tgt.dataset.msDel !== undefined) items.splice(idx, 1);
    render();
  });
  wrap.addEventListener("input", (e) => {
    const idx = e.target.dataset.msName;
    if (idx !== undefined) items[Number(idx)].name = e.target.value;
  });
  $("#f-ms-add").addEventListener("click", () => {
    items.push({ id: uid(), name: "", done: false });
    render();
  });
}

function bindFrequencyToggle(initial) {
  const freq = $("#f-freq");
  const wrap = $("#f-weekdays-wrap");
  freq.addEventListener("change", () => {
    wrap.style.display = freq.value === "weekly" ? "" : "none";
  });
  const wk = $("#f-weekdays");
  wk?.addEventListener("click", (e) => {
    const btn = e.target.closest(".weekday");
    if (!btn) return;
    btn.classList.toggle("selected");
    if (btn.classList.contains("selected")) {
      btn.style.background = "#6366f1";
      btn.style.color = "#fff";
      btn.style.borderColor = "#6366f1";
    } else {
      btn.style.background = "";
      btn.style.color = "";
      btn.style.borderColor = "";
    }
  });
}

function bindQuickAdd() {
  // handled in saveModal
}

/* ----- Save handlers ----- */
function saveModal() {
  const { type, data } = modalState || {};
  if (!type) return;

  if (type === "quickAdd") {
    const next = $("#qa-type").value;
    closeModal();
    openModal(next, null);
    return;
  }

  if (type === "business") {
    const name = $("#f-name").value.trim();
    if (!name) { toast("이름을 입력하세요"); return; }
    const color = $("#f-colors").dataset.selected || COLORS[0];
    const milestones = ($("#f-milestones")._items || []).filter((m) => m.name.trim());
    const payload = {
      id: data?.id || uid(),
      name,
      progress: clamp(Number($("#f-progress").value) || 0, 0, 100),
      status: $("#f-status").value,
      color,
      note: $("#f-note").value.trim(),
      milestones,
    };
    if (data) {
      const i = state.businesses.findIndex((b) => b.id === data.id);
      state.businesses[i] = payload;
    } else {
      state.businesses.push(payload);
    }
    saveState();
    toast(data ? "저장됨" : "사업이 추가되었어요");
  }

  if (type === "todo") {
    const text = $("#f-text").value.trim();
    if (!text) { toast("내용을 입력하세요"); return; }
    const payload = {
      id: data?.id || uid(),
      text,
      date: $("#f-date").value || todayStr(),
      time: $("#f-time").value || "",
      businessId: $("#f-biz").value || null,
      done: data?.done || false,
    };
    if (data) {
      const i = state.todos.findIndex((t) => t.id === data.id);
      state.todos[i] = payload;
    } else {
      state.todos.push(payload);
    }
    saveState();
    toast(data ? "저장됨" : "할 일이 추가되었어요");
  }

  if (type === "routine") {
    const name = $("#f-name").value.trim();
    if (!name) { toast("이름을 입력하세요"); return; }
    const freq = $("#f-freq").value;
    const weekdays = freq === "weekly"
      ? $$(".weekday.selected", $("#f-weekdays")).map((b) => Number(b.dataset.wd))
      : [];
    if (freq === "weekly" && weekdays.length === 0) { toast("요일을 선택하세요"); return; }
    const payload = {
      id: data?.id || uid(),
      name,
      frequency: freq,
      weekdays,
      time: $("#f-time").value || "",
      businessId: $("#f-biz").value || null,
      history: data?.history || {},
    };
    if (data) {
      const i = state.routines.findIndex((r) => r.id === data.id);
      state.routines[i] = payload;
    } else {
      state.routines.push(payload);
    }
    saveState();
    toast(data ? "저장됨" : "루틴이 추가되었어요");
  }

  if (type === "schedule") {
    const title = $("#f-title").value.trim();
    if (!title) { toast("제목을 입력하세요"); return; }
    const start = $("#f-start").value;
    const end = $("#f-end").value;
    if (!start || !end || end <= start) { toast("종료 시간은 시작 이후로"); return; }
    const payload = {
      id: data?.id || uid(),
      title,
      date: $("#f-date").value || todayStr(),
      startTime: start,
      endTime: end,
      businessId: $("#f-biz").value || null,
    };
    if (data) {
      const i = state.schedule.findIndex((s) => s.id === data.id);
      state.schedule[i] = payload;
    } else {
      state.schedule.push(payload);
    }
    saveState();
    toast(data ? "저장됨" : "일정이 추가되었어요");
  }

  closeModal();
  renderAll();
}

function deleteFromModal() {
  const { type, data } = modalState || {};
  if (!data) return;
  if (type === "business") state.businesses = state.businesses.filter((b) => b.id !== data.id);
  if (type === "todo") state.todos = state.todos.filter((t) => t.id !== data.id);
  if (type === "routine") state.routines = state.routines.filter((r) => r.id !== data.id);
  if (type === "schedule") state.schedule = state.schedule.filter((s) => s.id !== data.id);
  saveState();
  closeModal();
  toast("삭제되었어요");
  renderAll();
}

/* ===========================================================
   EVENT HANDLERS
   =========================================================== */
function bindEvents() {
  // Nav
  $$(".nav-item").forEach((n) => n.addEventListener("click", () => switchView(n.dataset.view)));

  // Quick add
  $("#quickAddBtn").addEventListener("click", () => openModal("quickAdd"));

  // Modal
  $("#modalClose").addEventListener("click", closeModal);
  $("#modalCancel").addEventListener("click", closeModal);
  $("#modalSave").addEventListener("click", saveModal);
  $("#modal").addEventListener("click", (e) => {
    if (e.target.id === "modal") closeModal();
    if (e.target.id === "f-delete") {
      if (confirm("정말 삭제하시겠어요?")) deleteFromModal();
    }
  });

  // Global click delegation
  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-action], [data-toggle-todo], [data-toggle-routine], [data-edit-todo], [data-del-todo], [data-edit-routine], [data-del-routine], [data-edit-schedule], [data-edit-biz], [data-quickadd-date]");
    if (!t) return;

    if (t.dataset.action === "add-business") openModal("business");
    if (t.dataset.action === "add-todo") openModal("todo");
    if (t.dataset.action === "add-routine") openModal("routine");
    if (t.dataset.action === "add-schedule") openModal("schedule");

    if (t.dataset.toggleTodo) {
      const todo = state.todos.find((x) => x.id === t.dataset.toggleTodo);
      if (todo) { todo.done = !todo.done; saveState(); renderAll(); }
    }
    if (t.dataset.toggleRoutine) {
      const r = state.routines.find((x) => x.id === t.dataset.toggleRoutine);
      if (r) {
        r.history = r.history || {};
        const ds = todayStr();
        if (r.history[ds]) delete r.history[ds];
        else r.history[ds] = true;
        saveState();
        renderAll();
      }
    }
    if (t.dataset.editTodo) {
      const todo = state.todos.find((x) => x.id === t.dataset.editTodo);
      if (todo) openModal("todo", todo);
    }
    if (t.dataset.delTodo) {
      if (confirm("삭제할까요?")) {
        state.todos = state.todos.filter((x) => x.id !== t.dataset.delTodo);
        saveState(); renderAll();
      }
    }
    if (t.dataset.editRoutine) {
      const r = state.routines.find((x) => x.id === t.dataset.editRoutine);
      if (r) openModal("routine", r);
    }
    if (t.dataset.delRoutine) {
      if (confirm("삭제할까요?")) {
        state.routines = state.routines.filter((x) => x.id !== t.dataset.delRoutine);
        saveState(); renderAll();
      }
    }
    if (t.dataset.editSchedule) {
      const s = state.schedule.find((x) => x.id === t.dataset.editSchedule);
      if (s) openModal("schedule", s);
    }
    if (t.dataset.editBiz) {
      const b = state.businesses.find((x) => x.id === t.dataset.editBiz);
      if (b) openModal("business", b);
    }
    if (t.dataset.quickaddDate) {
      // click empty week grid cell to quick-create
      openModal("schedule", null);
      setTimeout(() => {
        const date = $("#f-date"); if (date) date.value = t.dataset.quickaddDate;
        const start = $("#f-start"); if (start) start.value = t.dataset.quickaddHour;
        const end = $("#f-end");
        if (end) {
          const [h, m] = t.dataset.quickaddHour.split(":").map(Number);
          end.value = `${pad(h + 1)}:${pad(m)}`;
        }
      }, 0);
    }
  });

  // Week nav
  $("#weekPrev").addEventListener("click", () => { weekOffset--; renderSchedule(); });
  $("#weekNext").addEventListener("click", () => { weekOffset++; renderSchedule(); });
  $("#weekToday").addEventListener("click", () => { weekOffset = 0; renderSchedule(); });

  // Export / import
  $("#exportBtn").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `bizboard-${todayStr()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast("백업 파일을 받았어요");
  });
  $("#importBtn").addEventListener("click", () => $("#importFile").click());
  $("#importFile").addEventListener("change", async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    try {
      const txt = await f.text();
      const parsed = JSON.parse(txt);
      if (!parsed || typeof parsed !== "object") throw new Error("invalid");
      state = { businesses: [], todos: [], routines: [], schedule: [], ...parsed };
      saveState();
      renderAll();
      toast("불러왔어요");
    } catch (err) {
      toast("불러오기 실패");
    }
    e.target.value = "";
  });

  // ESC closes modal
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });
}

/* ===========================================================
   Helpers
   =========================================================== */
function escapeHtml(s) {
  if (s == null) return "";
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }
function clamp(n, min, max) { return Math.min(max, Math.max(min, n)); }

function hexToRgba(hex, a) {
  const h = hex.replace("#", "");
  const bigint = parseInt(h, 16);
  const r = (bigint >> 16) & 255;
  const g = (bigint >> 8) & 255;
  const b = bigint & 255;
  return `rgba(${r},${g},${b},${a})`;
}

/* ===========================================================
   INIT
   =========================================================== */
loadState();
bindEvents();
switchView("today");
