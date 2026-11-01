/* Derive the daily recap from saved attempts; never write learning records. */
(function(root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.JLPTDaySummary = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function() {
  "use strict";
  function build(day, questions, attempts, notes = {}) {
    const result = {date:day?.date, total:day?.items.length || 0, completed:0, ready:false, groups:[], unavailable:0};
    if (!day || !result.total) return result;
    const records = new Map();
    for (const a of attempts) {
      if (a.plan_date !== day.date) continue;
      const key = `${a.question_id}:${a.content_hash}`;
      if (!records.has(key)) records.set(key, []);
      records.get(key).push(a);
    }
    result.completed = day.items.filter(e => records.has(`${e.question_id}:${e.content_hash}`)).length;
    result.ready = result.completed === result.total;
    // Do not expose today's grammar answers before the complete daily set is done.
    if (!result.ready) return result;
    const bank = new Map(questions.map(q => [q.id,q])), groups = new Map();
    for (const entry of day.items) {
      const q = bank.get(entry.question_id);
      if (!q || q.content_hash !== entry.content_hash || !q.structural_check?.passed ||
          q.editorial_check?.decision !== "reviewed" || q.editorial_check.content_hash !== q.content_hash ||
          q.human_review?.decision === "rejected" || entry.available === false) {
        result.unavailable++; continue;
      }
      if (q.kind !== "grammar") continue;
      const answer = q.options[q.answer_index], note = notes[answer];
      const patternNote = notes[q.target_label.replace(/^[〜～~]/, "")] || note;
      const key = q.target_id || q.target_label;
      if (!groups.has(key)) groups.set(key, {id:key, title:q.target_label, usage:patternNote?.usage || q.focus_zh,
        examples:[], questions:[], wrong:false, uncertain:false});
      const group = groups.get(key), saved = records.get(`${q.id}:${q.content_hash}`) || [];
      // Any mistake or uncertainty remains worth revisiting, even after a later correct retry.
      const wrong = saved.some(a => a.selected_index !== q.answer_index);
      const uncertain = saved.some(a => a.confidence === "unsure" || a.confidence === "guess");
      group.wrong ||= wrong; group.uncertain ||= uncertain;
      if (note && !group.examples.some(e => e.example === note.example)) group.examples.push(note);
      group.questions.push({id:q.id, stem:q.stem.replace(/（(?:\s|\\u3000)*）/, `【${answer}】`),
        translation:q.translation_zh, explanation:q.explanation_zh, wrong, uncertain});
    }
    result.groups = Array.from(groups.values()).sort((a,b) =>
      Number(b.wrong)*2 + Number(b.uncertain) - Number(a.wrong)*2 - Number(a.uncertain));
    return result;
  }
  return {build};
});
