"use strict";
const $ = (id) => document.getElementById(id);
const labels = { reading: "汉字读音", vocabulary: "词汇填空", grammar: "语法选择" };
let app = { data: null, mode: "daily", date: null, kind: "all", status: "all", search: "", list: [], index: 0, choice: null, revealed: false, busy: false, started: performance.now() };
function el(tag, text, className) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (className) n.className = className; return n; }
function toast(text) { $("toast").textContent = text; $("toast").hidden = false; setTimeout(() => $("toast").hidden = true, 4000); }
function current() { return app.list[app.index]; }
async function post(path, body) { const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); const d = await r.json(); if (!r.ok) throw new Error(d.error || "保存失败"); return d; }
function reviewDecision(q) { return q.human_review?.decision || "pending"; }
function practiceAvailable(q) { return q.structural_check.passed && q.editorial_check?.decision === "reviewed" && reviewDecision(q) !== "rejected"; }
function day() { return app.data?.study_plan?.days.find(d => d.date === app.date); }
function doneOnDate(q, date = app.date) { return app.data.attempts.some(a => a.plan_date === date && a.question_id === q.id && a.content_hash === q.content_hash); }
function renderDay() {
  const plan = app.data.study_plan, d = day();
  $("study-card").hidden = app.mode !== "daily" || !plan;
  if (!d) return;
  const completed = d.items.filter(e => app.data.attempts.some(a => a.plan_date === d.date && a.question_id === e.question_id && a.content_hash === e.content_hash)).length;
  const unavailable = d.items.filter(e => !e.available || !app.data.questions.some(q => q.id === e.question_id && practiceAvailable(q))).length;
  $("study-date").min=plan.start_date; $("study-date").max=plan.end_date; $("study-date").value=d.date;
  $("day-title").textContent = `第 ${d.day_number} / ${plan.days_count} 天 · ${d.phase === "consolidation" ? "集中复习" : "新题与间隔复习"}`;
  $("day-description").textContent = `${d.date} · 新题 ${d.new_count} 道 + 复习 ${d.review_count} 道。52 天共 ${plan.total_slots.toLocaleString()} 次练习，${plan.unique_questions} 道不同题目。`;
  $("day-progress").textContent = `${completed} / ${d.items.length} 已完成`;
  $("day-progress-bar").style.width=`${completed/d.items.length*100}%`;
  $("day-message").textContent = unavailable ? `${unavailable} 道题因版本变化或疑问反馈已暂停；不会显示未经复核的新版本。` : completed === d.items.length ? "今天这份题单已完成。可以回看解析，或到自由练习中巩固。" : "已预先备好，无需每日生成。新题和复习题都会标明；完成数按不同题目去重。";
  $("date-previous").disabled=d.day_number===1; $("date-next").disabled=d.day_number===plan.days_count;
}
function filter(reset = true, keepId) {
  const entries = new Map((day()?.items || []).map((e,i) => [e.question_id,{...e,index:i}]));
  app.list = app.data.questions.filter(q => (app.mode === "candidate" || practiceAvailable(q)) && (app.mode !== "daily" || (entries.get(q.id)?.available && entries.get(q.id).content_hash === q.content_hash)) && (app.kind === "all" || app.kind === q.kind) && (!app.search || `${q.target_label} ${q.stem}`.toLowerCase().includes(app.search.toLowerCase())) && (app.status === "all" || (app.status === "flagged" && ["model_flagged", "structural_failed", "editorial_flagged"].includes(q.quality_status)) || (app.status === "screened" && q.quality_status === "codex_reviewed") || app.status === reviewDecision(q)));
  if (app.mode === "daily") app.list.sort((a,b) => entries.get(a.id).index-entries.get(b.id).index);
  if (keepId && app.list.some(q => q.id === keepId)) app.index = app.list.findIndex(q => q.id === keepId);
  else if (reset) app.index = app.mode === "daily" ? Math.max(0,app.list.findIndex(q=>!doneOnDate(q))) : 0;
  app.index = Math.max(0, Math.min(app.index, app.list.length - 1));
  renderDay(); renderQuestion();
}
function renderStats() {
  const qs = app.data.questions, approved = qs.filter(practiceAvailable).length;
  $("candidate-count").textContent = qs.length;
  $("overview-count").textContent = qs.filter(q=>q.quality_status === "codex_reviewed").length;
  $("approved-count").textContent = approved;
  const planned = app.data.summary.planned || qs.length;
  $("stat-generated").replaceChildren(document.createTextNode(qs.length), el("small", ` / ${planned}`));
  $("progress-bar").style.width = `${Math.min(100, qs.length / planned * 100)}%`;
  $("stat-screened").textContent = qs.filter(q => q.quality_status === "codex_reviewed").length;
  $("stat-flagged").textContent = qs.filter(q => !practiceAvailable(q)).length;
  $("stat-approved").textContent = approved;
  $("daily-count").textContent = app.data.study_plan?.daily_count || "—";
}
function renderStem(text) {
  const parts = text.split(/(【[^【】]+】)/g);
  $("stem").replaceChildren(...parts.map(t => t.startsWith("【") ? el("mark", t.slice(1, -1)) : document.createTextNode(t)));
}
function renderOptions() {
  const q = current(); if (!q) return;
  $("options").replaceChildren(...q.options.map((text, i) => {
    const n = el("button", undefined, "option"); n.lang = "ja"; n.append(el("span", String(i + 1), "option-index"), el("span", text));
    n.setAttribute("aria-pressed", String(app.choice === i));
    if (app.choice === i) n.classList.add("selected");
    if (app.revealed && i === q.answer_index) n.classList.add("correct");
    if (app.revealed && i === app.choice && i !== q.answer_index) n.classList.add("wrong");
    n.disabled = app.revealed || app.busy;
    n.onclick = () => { app.choice = i; renderOptions(); $("reveal").disabled = false; };
    return n;
  }));
}
function renderQuality() {
  const q = current();
  const tags = [];
  tags.push(el("span", q.structural_check.passed ? "✓ 结构检查通过" : "! 结构检查失败", `quality-tag ${q.structural_check.passed ? "" : "bad"}`));
  if (q.kind === "reading") tags.push(el("span", "✓ 读音已与底库核对", "quality-tag"));
  else if (q.blind_check) tags.push(el("span", q.blind_check.passed ? "✓ 本版本模型复答一致" : "! 模型建议复核", "quality-tag"));
  if (q.editorial_check?.decision === "flagged") tags.push(el("span", "! 内容抽查发现问题", "quality-tag warn"));
  const decision = reviewDecision(q);
  tags.push(el("span", q.editorial_check?.decision === "reviewed" ? "✓ 经 Codex 逐题复核（AI）" : "○ 等待编辑复核", "quality-tag"));
  if (decision !== "pending") tags.push(el("span", {approved:"✓ 已加入个人收藏", rejected:"! 你已报告疑问 · 暂停练习"}[decision], `quality-tag ${decision === "rejected" ? "bad" : ""}`));
  $("quality-badges").replaceChildren(...tags);
  $("blind-note").textContent = !app.revealed ? "先作答，再看解析与复核说明。无需你审核后才能练习。" : q.editorial_check?.note_zh || "尚未复核，暂不进入复核练习。";
  if (app.revealed && q.editorial_check) $("blind-note").textContent += " 这是 AI 编辑复核，用于知识点巩固，未经真实 N1 难度标定。";
  if (!q.structural_check.passed && app.revealed) $("blind-note").textContent += ` 结构问题：${q.structural_check.errors.join("、")}`;
  $("source-details").replaceChildren();
  for (const [k, v] of [["知识点", app.revealed ? q.target_label : "查看解析后显示"], ["出题模型", q.generation.model], ["题目 ID", q.id], ["底库", `OpenJLPT · ${q.source.commit.slice(0, 10)}`], ["许可", q.source.license], ...(q.editorial_revision ? [["内容修订", q.editorial_revision.actor]] : [])]) { $("source-details").append(el("dt", k), el("dd", v)); }
  if (app.revealed) for (const ref of q.editorial_check?.references || []) { const a = el("a", ref.title); a.href = ref.url; a.target = "_blank"; a.rel = "noreferrer"; const dd=el("dd");dd.append(a);$("source-details").append(el("dt","核对资料"),dd); }
  $("review-state").textContent = decision === "pending" ? "可直接练习；收藏和反馈均为可选" : decision === "approved" ? "已保存到个人收藏" : "疑问已保存，本题暂时移出练习";
  $("approve").disabled = !app.revealed || !q.structural_check.passed || app.busy;
}
function renderQuestion() {
  app.choice = null; app.revealed = false; app.started = performance.now(); app.busy = false;
  $("workspace").hidden = app.list.length === 0; $("empty").hidden = app.list.length !== 0;
  if (!app.list.length) {
    $("empty-title").textContent = "没有符合筛选的题目";
    $("empty-description").textContent = "试试切换题型或清空搜索。尚未复核或你报告有疑问的题目可在全部题目中查看。";
    return;
  }
  const q = current();
  $("question-type").textContent = labels[q.kind];
  const entry=day()?.items.find(e=>e.question_id===q.id);
  $("candidate-badge").textContent = app.mode === "daily" ? `${entry?.role === "new" ? "新题" : "间隔复习"}${doneOnDate(q) ? " · 今日已做" : ""} · AI 已复核` : practiceAvailable(q) ? "AI 复核练习" : "待复核 · 仅供查看";
  $("position").textContent = `${String(app.index + 1).padStart(2, "0")} / ${app.list.length}`;
  $("instruction").textContent = q.kind === "reading" ? "【　】の言葉の読み方として、最もよいものを一つ選びなさい。" : "（　）に入れるのに最もよいものを、一つ選びなさい。";
  $("review-note").value = q.human_review?.note || "";
  renderStem(q.stem); renderOptions(); renderQuality();
  $("answer").hidden = true; $("reveal").disabled = true; $("reveal").textContent = "查看答案与解析"; $("save-state").textContent = ""; $("target-after").textContent = "";
  $("previous").disabled = app.index === 0; $("next").disabled = app.index >= app.list.length - 1;
  document.querySelectorAll('input[name="confidence"]').forEach(n => { n.disabled = false; n.checked = n.value === "unsure"; });
}
async function reveal() {
  const q = current(); if (!q || app.choice === null || app.busy || app.revealed) return;
  app.busy = true; $("reveal").disabled = true; $("save-state").textContent = "保存答题记录…"; renderOptions();
  try {
    const attempt={question_id:q.id,content_hash:q.content_hash,selected_index:app.choice,confidence:document.querySelector('input[name="confidence"]:checked').value,elapsed_ms:Math.min(86400000,Math.round(performance.now()-app.started)),plan_date:app.mode === "daily" ? app.date : null};
    await post("/api/attempt", attempt);
    app.data.attempts.unshift(attempt); renderDay();
    app.revealed = true; $("answer").hidden = false; $("save-state").textContent = "已保存到本机"; $("reveal").textContent = "已展开解析";
    const correct = app.choice === q.answer_index;
    $("result").textContent = `${correct ? "回答正确" : "本题答案"} · ${q.answer_index+1}. ${q.options[q.answer_index]}`;
    $("result").className = "result"+(correct ? "" : " wrong");
    $("translation").textContent = q.translation_zh; $("focus").textContent = `考点：${q.focus_zh}`; $("explanation").textContent = q.explanation_zh;
    $("option-explanations").replaceChildren(...q.option_explanations_zh.map((text,i) => { const d=el("div"); d.append(el("b",String(i+1)),el("span",`${q.options[i]}：${text}`));return d; }));
    $("target-after").textContent = q.target_label;
    document.querySelectorAll('input[name="confidence"]').forEach(n => n.disabled=true);
  } catch(e) { toast(e.message); $("save-state").textContent = "保存失败，可重试"; $("reveal").disabled = false; }
  finally { app.busy = false; renderOptions(); renderQuality(); }
}
async function review(decision) {
  const q = current(); if (!q || app.busy || (decision === "approved" && !app.revealed)) return;
  app.busy = true;
  try {
    const note = $("review-note").value;
    await post("/api/review",{question_id:q.id,content_hash:q.content_hash,decision,note});
    q.human_review = {decision,note,content_hash:q.content_hash}; renderStats(); toast({approved:"已加入个人收藏",rejected:"疑问已保存，本题暂时移出练习",pending:"已清除个人标记"}[decision]);
    // Reapply filters so a decision immediately removes items from incompatible views.
    const stillMatches = (app.mode === "candidate" || practiceAvailable(q)) && (!["pending","approved","rejected"].includes(app.status) || app.status === decision);
    renderDay();
    if (!stillMatches) filter(false); else renderQuality();
  } catch(e) { toast(e.message); }
  finally { app.busy = false; if(current()) $("approve").disabled = !app.revealed || !current().structural_check.passed; }
}
async function load(initial = false) {
  $("refresh").disabled = true;
  try { const r = await fetch("/api/state"); if(!r.ok) throw new Error("题库读取失败"); const data = await r.json(); const id = current()?.id; app.data = data; if(data.study_plan && !app.date) app.date=[data.study_plan.start_date,data.study_plan.today,data.study_plan.end_date].sort()[1]; renderStats(); filter(initial,id); if(!initial) toast("题库进度已刷新"); }
  catch(e) { toast(e.message); }
  finally { $("refresh").disabled = false; }
}
document.querySelectorAll("[data-mode]").forEach(n => n.onclick = () => { app.mode = n.dataset.mode; app.status="all"; $("status-filter").value="all"; document.querySelectorAll("[data-mode]").forEach(b => b.classList.toggle("active",b===n)); $("page-title").textContent=app.mode==="candidate"?"查看题目与复核记录。":app.mode==="daily"?"每天三十题，循序巩固。":"留一点时间，巩固理解。";$("page-description").textContent=app.mode==="candidate"?"可查看未复核或已提出疑问的题目；不需要你承担审核工作。":"10 月 17 日至 12 月 7 日 · 题目已预先备好并经 AI 编辑复核，不需要你审核。";if(app.data)filter(); });
function changeDate(date) { if (!app.data.study_plan?.days.some(d=>d.date===date)) return; app.date=date; app.kind="all"; app.search=""; app.status="all"; $("search").value=""; $("status-filter").value="all"; document.querySelectorAll("[data-kind]").forEach(b=>b.classList.toggle("active",b.dataset.kind==="all")); filter(); }
$("study-date").onchange=e=>changeDate(e.target.value);
$("date-previous").onclick=()=>changeDate(app.data.study_plan.days[day().day_number-2]?.date);
$("date-next").onclick=()=>changeDate(app.data.study_plan.days[day().day_number]?.date);
$("date-today").onclick=()=>{const p=app.data.study_plan;changeDate([p.start_date,p.today,p.end_date].sort()[1]);};
document.querySelectorAll("[data-kind]").forEach(n => n.onclick = () => {app.kind=n.dataset.kind;document.querySelectorAll("[data-kind]").forEach(b=>b.classList.toggle("active",b===n));if(app.data)filter();});
$("status-filter").onchange=e=>{app.status=e.target.value;if(app.data)filter();};
$("search").oninput=e=>{app.search=e.target.value;if(app.data)filter();};
$("previous").onclick=()=>{if(app.index>0){app.index--;renderQuestion();}};
$("next").onclick=()=>{if(app.index<app.list.length-1){app.index++;renderQuestion();}};
$("reveal").onclick=reveal;$("refresh").onclick=()=>load();$("approve").onclick=()=>review("approved");$("reject").onclick=()=>review("rejected");$("reset-review").onclick=()=>review("pending");
const mobileOverview=window.matchMedia("(max-width:700px)");
$("bank-overview").open=!mobileOverview.matches;
mobileOverview.addEventListener("change",e=>$("bank-overview").open=!e.matches);
load(true);
