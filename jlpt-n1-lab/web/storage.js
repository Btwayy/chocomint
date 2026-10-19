/* Shared UI transport: Python/SQLite at localhost root, browser records on static hosts. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.JLPTStorage = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const KEY = "jlpt-n1-lab.records.v1";
  const clone = value => JSON.parse(JSON.stringify(value));
  const pending = () => ({ decision: "pending", note: "" });
  function reviewed(q) {
    return Boolean(q.structural_check?.passed && q.editorial_check?.decision === "reviewed" && q.editorial_check.content_hash === q.content_hash);
  }
  function available(q) { return reviewed(q) && q.human_review?.decision !== "rejected"; }
  function tokyoDate(now) {
    const parts = new Intl.DateTimeFormat("en", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(now);
    const value = name => parts.find(p => p.type === name).value;
    return `${value("year")}-${value("month")}-${value("day")}`;
  }
  function planView(plan, questions, attempts, today) {
    const byId = new Map(questions.map(q => [q.id, q]));
    const done = new Set(attempts.map(a => JSON.stringify([a.plan_date, a.question_id, a.content_hash])));
    const result = clone(plan);
    delete result.first_dates;
    result.today = today;
    result.completed_slots = 0;
    result.days = plan.days.map(day => {
      const items = day.items.map(entry => {
        const q = byId.get(entry.question_id);
        return { ...entry, available: Boolean(q && q.content_hash === entry.content_hash && available(q)), done: done.has(JSON.stringify([day.date, entry.question_id, entry.content_hash])) };
      });
      const completed_count = items.filter(e => e.done).length;
      result.completed_slots += completed_count;
      return { ...day, items, completed_count, unavailable_count: items.filter(e => !e.available).length };
    });
    return result;
  }
  function createStore({ fetch, baseURL, getStorage, backend = false, now = () => new Date() }) {
    let bank = null, plan = null;
    async function json(url, options) {
      const response = await fetch(url, options);
      if (!response.ok) throw new Error(`题库请求失败（${response.status}），请刷新重试。`);
      return response.json();
    }
    function readRecords() {
      try {
        const raw = getStorage().getItem(KEY);
        if (!raw) return { version: 1, attempts: [], reviews: {} };
        const records = JSON.parse(raw);
        if (records.version !== 1 || !Array.isArray(records.attempts) || !records.reviews || typeof records.reviews !== "object" || Array.isArray(records.reviews)) throw new Error("Unsupported records");
        return records;
      } catch (_) { throw new Error("无法读取浏览器学习记录。请保留原数据，并检查浏览器是否允许本站存储。"); }
    }
    function writeRecords(records) {
      try { getStorage().setItem(KEY, JSON.stringify(records)); }
      catch (_) { throw new Error("未能保存到浏览器，可能已满或被禁用。本次记录未保存，请导出备份后重试。"); }
    }
    function currentState() {
      const records = readRecords();
      const questions = bank.map(original => {
        const q = clone(original), review = records.reviews[q.id];
        q.human_review = review?.content_hash === q.content_hash ? clone(review) : pending();
        q.review_status = q.human_review.decision;
        return q;
      });
      return { questions, attempts: clone(records.attempts), study_plan: planView(plan, questions, records.attempts, tokyoDate(now())),
        summary: { planned: questions.length, generated: questions.length }, storage_mode: "browser" };
    }
    async function load() {
      if (backend) return { ...await json("/api/state"), storage_mode: "server" };
      const data = await Promise.all([
        json(new URL("../data/candidates.json", baseURL).href),
        json(new URL("../data/study-plan.json", baseURL).href)
      ]);
      if (!Array.isArray(data[0]) || !Array.isArray(data[1]?.days)) throw new Error("题库或日期计划格式不正确。");
      bank = data[0]; plan = data[1];
      return currentState();
    }
    async function post(path, body) {
      if (backend) return json(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (!bank || !plan) throw new Error("题库尚未加载。");
      const state = currentState(), q = state.questions.find(q => q.id === body.question_id);
      if (!q || body.content_hash !== q.content_hash) throw new Error("题目版本已变化，请刷新后重试。");
      const records = readRecords();
      if (path === "/api/attempt") {
        if (!Number.isInteger(body.selected_index) || body.selected_index < 0 || body.selected_index > 3 || !["sure", "unsure", "guess"].includes(body.confidence) || !Number.isInteger(body.elapsed_ms) || body.elapsed_ms < 0 || body.elapsed_ms > 86400000) throw new Error("答题内容不合法。");
        if (!available(q)) throw new Error("此题已暂停或复核失效。");
        if (body.plan_date !== null && body.plan_date !== undefined) {
          const day = plan.days.find(d => d.date === body.plan_date);
          if (!day?.items.some(e => e.question_id === q.id && e.content_hash === q.content_hash)) throw new Error("此题不属于所选日期的当前题单。");
        }
        const correct = body.selected_index === q.answer_index;
        records.attempts.unshift({ ...body, correct: Number(correct), created_at: now().toISOString() });
        writeRecords(records);
        return { saved: true, correct };
      }
      if (path === "/api/review") {
        if (!["pending", "approved", "rejected"].includes(body.decision) || typeof body.note !== "string" || body.note.length > 3000 || (body.decision === "approved" && !q.structural_check.passed)) throw new Error("收藏或疑问内容不合法。");
        records.reviews[q.id] = { question_id: q.id, content_hash: q.content_hash, decision: body.decision, note: body.note, updated_at: now().toISOString() };
        writeRecords(records);
        return { saved: true, decision: body.decision };
      }
      throw new Error("不支持的保存操作。");
    }
    async function exportData(kind) {
      if (!["plan", "candidates", "reviewed", "approved", "records"].includes(kind)) throw new Error("导出类型不合法。");
      let data;
      if (backend) data = await json(`/api/export/${kind}`);
      else {
        if (!bank || !plan) throw new Error("题库尚未加载。");
        const state = currentState(), records = readRecords();
        if (kind === "plan") data = clone(plan);
        else if (kind === "records") data = { version: 1, reviews: Object.values(records.reviews), attempts: records.attempts, study_plan: clone(plan), exported_at: now().toISOString(), storage_mode: "browser" };
        else if (kind === "reviewed") data = state.questions.filter(available);
        else if (kind === "approved") data = state.questions.filter(q => q.structural_check.passed && q.human_review.decision === "approved");
        else data = state.questions;
      }
      return { filename: `n1-${kind}.json`, data };
    }
    return { load, post, exportData, mode: backend ? "server" : "browser" };
  }
  return { createStore, planView, tokyoDate, KEY };
});
