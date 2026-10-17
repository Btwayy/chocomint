import copy
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab
import server


def fixture():
    return {"id": "v-test-cloze", "target_id": "v-test", "target_label": "把握", "kind": "vocabulary", "level": "N1",
            "stem": "状況を（　）する。", "options": ["把握", "補足", "配慮", "排除"], "answer_index": 0,
            "explanation_zh": "掌握情况。", "translation_zh": "掌握情况。",
            "option_explanations_zh": ["正确。", "补充。", "顾及。", "排除。"],
            "generation": {"model": "test-model"}, "source": {"commit": "abc", "license": "CC-BY-SA-4.0"}}


class ValidationTests(unittest.TestCase):
    def test_normalized_duplicates(self):
        q = fixture(); q["options"][1] = " 把握　"
        self.assertIn("duplicate_options", lab.structural_errors(q))

    def test_bad_answers_never_crash_or_pass(self):
        for invalid in [None, True, -1, 4, "0", []]:
            q = fixture(); q["answer_index"] = invalid
            self.assertIn("invalid_answer_index", lab.structural_errors(q))

    def test_blank_and_target_mismatch(self):
        q = fixture(); q["stem"] = "状況を理解する。"
        self.assertIn("exactly_one_blank_required", lab.structural_errors(q))
        q = fixture(); q["answer_index"] = 1
        self.assertIn("vocabulary_answer_differs_from_target", lab.structural_errors(q))

    def test_shuffling_keeps_explanations_aligned(self):
        q = fixture(); before = dict(zip(q["options"], q["option_explanations_zh"]))
        a = lab.shuffled(copy.deepcopy(q)); b = lab.shuffled(copy.deepcopy(q))
        self.assertEqual(a, b)
        self.assertEqual(a["options"][a["answer_index"]], "把握")
        self.assertEqual(dict(zip(a["options"], a["option_explanations_zh"])), before)

    def test_known_valid_readings_cannot_be_distractors(self):
        q = fixture(); q.update(kind="reading", target_label="明日", stem="【明日】出発する。", options=["あす", "あした", "あず", "あしだ"])
        target = {"reading": "あす", "source": {"other_readings": ["あした"]}}
        self.assertIn("valid_reading_used_as_distractor", lab.structural_errors(q, target))

    def test_hash_invalidates_changed_explanation(self):
        q = fixture(); h = lab.question_hash(q)
        q["explanation_zh"] = "更正后的说明"
        self.assertNotEqual(h, lab.question_hash(q))
        h = lab.question_hash(q)
        q["focus_zh"] = "修正后的考点"
        self.assertNotEqual(h, lab.question_hash(q))

    def test_grammar_must_test_the_selected_pattern(self):
        q = fixture(); q["kind"] = "grammar"
        self.assertIn("grammar_target_not_present_in_completed_sentence", lab.structural_errors(q, {"answer_pattern": "がてら"}))
        q.update(stem="仕事のかたわら、（　）を続ける。", options=["音楽", "料理", "研究", "読書"])
        self.assertIn("grammar_target_not_tested_by_blank", lab.structural_errors(q, {"answer_pattern": "かたわら"}))

    def test_all_selected_readings_have_four_unique_choices(self):
        for t in lab.read_json(lab.DATA / "targets.json"):
            if t["kind"] == "vocabulary":
                opts = lab.reading_options(t, t["id"])
                self.assertEqual(len(set(opts)), 4, t["label"])
                self.assertEqual(opts[0], t["reading"])


class PersistenceTests(unittest.TestCase):
    def test_codex_review_expires_after_content_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            lab.write_json(data / "targets.json", [])
            q = fixture()
            lab.write_json(data / "editorial-notes.json", {q["id"]: {"content_hash": lab.question_hash(q), "decision": "reviewed"}})
            with patch.object(lab, "DATA", data):
                checked = lab.annotate([q])[0]
                self.assertTrue(lab.practice_allowed(checked))
                self.assertEqual(checked["quality_status"], "codex_reviewed")
                checked["explanation_zh"] = "变更解析"
                checked["blind_check"] = {"passed": True}
                stale = lab.annotate([checked])[0]
                self.assertNotIn("editorial_check", stale)
                self.assertNotIn("blind_check", stale)
                self.assertFalse(lab.practice_allowed(stale))

    def test_feedback_excludes_reviewed_practice_without_faking_approval(self):
        q = fixture()
        q.update(content_hash=lab.question_hash(q), structural_check={"passed": True}, editorial_check={"decision": "reviewed"})
        self.assertTrue(lab.practice_allowed(q))
        self.assertNotIn("human_review", q)
        q["human_review"] = {"decision": "rejected", "content_hash": q["content_hash"]}
        self.assertFalse(lab.practice_allowed(q))
        q["human_review"]["content_hash"] = "old-version"
        self.assertTrue(lab.practice_allowed(q))

    def test_reviewed_export_is_separate_from_user_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); data = root / "data"
            (root / "reports").mkdir()
            q = fixture(); h = lab.question_hash(q)
            lab.write_json(data / "targets.json", [])
            lab.write_json(data / "batches/test.json", {"questions": [q]})
            lab.write_json(data / "editorial-notes.json", {q["id"]: {"content_hash": h, "decision": "reviewed"}})
            with patch.object(lab, "DATA", data), patch.object(lab, "ROOT", root):
                summary = lab.export()
                self.assertEqual(summary["practice_available"], 1)
                self.assertEqual(summary["human_approved"], 0)
                self.assertEqual(len(lab.read_json(data / "reviewed.json")), 1)
                with lab.connect() as db:
                    db.execute("INSERT INTO reviews VALUES(?,?,?,?,?)", (q["id"], "rejected", "有疑问", lab.now(), h))
                self.assertEqual(lab.export()["practice_available"], 0)

    def test_readings_use_dictionary_and_editorial_flags_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            lab.write_json(data / "targets.json", [{"id": "v-test", "label": "把握", "reading": "はあく", "source": {}}])
            q = fixture(); q.update(kind="reading", stem="状況を【把握】した。", options=["はあく", "はく", "ばあく", "はあぐ"])
            h = lab.question_hash(q)
            lab.write_json(data / "audits" / (q["id"]+".json"), {"content_hash": h, "passed": False})
            with patch.object(lab, "DATA", data):
                result = lab.annotate([copy.deepcopy(q)])[0]
                self.assertEqual(result["quality_status"], "dictionary_checked")
                self.assertNotIn("blind_check", result)
                lab.write_json(data / "editorial-notes.json", {q["id"]: {"content_hash": h, "decision": "flagged", "note_zh": "语境需修改"}})
                self.assertEqual(lab.annotate([copy.deepcopy(q)])[0]["quality_status"], "editorial_flagged")

    def test_only_matching_user_approvals_export(self):
        original_data = lab.DATA
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); data = root / "data"
            (data / "batches").mkdir(parents=True)
            (root / "reports").mkdir()
            lab.write_json(data / "targets.json", [{"id": "v-test", "reading": "はあく", "source": {}}])
            q = fixture()
            lab.write_json(data / "batches/test.json", {"questions": [q]})
            with patch.object(lab, "DATA", data), patch.object(lab, "ROOT", root):
                self.assertEqual(lab.export()["human_approved"], 0)
                with lab.connect() as db:
                    db.execute("INSERT INTO reviews VALUES(?,?,?,?,?)", (q["id"], "approved", "checked", lab.now(), lab.question_hash(q)))
                self.assertEqual(lab.export()["human_approved"], 1)
                self.assertEqual(lab.read_json(data / "approved.json")[0]["review_status"], "approved")
                q["options"][1] = "促進"
                lab.write_json(data / "batches/test.json", {"questions": [q]})
                self.assertEqual(lab.export()["human_approved"], 0)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(); cls.data = Path(cls.temp.name)
        cls.db_patch = patch.object(lab, "DATA", cls.data); cls.db_patch.start()
        cls.server = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start()
        cls.url = "http://127.0.0.1:"+str(cls.server.server_port)
        cls.q = fixture(); cls.q["content_hash"] = lab.question_hash(cls.q); cls.q["structural_check"] = {"passed": True}

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.db_patch.stop(); cls.temp.cleanup()

    def request(self, body, origin=None, path="/api/review"):
        headers = {"Content-Type": "application/json"}
        if origin: headers["Origin"] = origin
        req = urllib.request.Request(self.url+path, data=json.dumps(body).encode(), headers=headers)
        with patch.object(lab, "all_candidates", return_value=[self.q]), patch.object(lab, "annotate", side_effect=lambda x:x), patch.object(lab, "export"):
            try:
                with urllib.request.urlopen(req) as r: return r.status, json.load(r)
            except urllib.error.HTTPError as exc:
                with exc:
                    return exc.code, json.load(exc)

    def test_stale_review_is_rejected(self):
        status, _ = self.request({"question_id": self.q["id"], "content_hash": "stale", "decision": "approved"})
        self.assertEqual(status, 409)

    def test_foreign_origin_cannot_write(self):
        status, _ = self.request({}, "https://example.com")
        self.assertEqual(status, 403)

    def test_valid_approval_persists(self):
        status, body = self.request({"question_id": self.q["id"], "content_hash": self.q["content_hash"], "decision": "approved", "note": "测试笔记"})
        self.assertEqual(status, 200)
        with lab.connect() as db:
            row = db.execute("SELECT * FROM reviews WHERE question_id=?", (self.q["id"],)).fetchone()
        self.assertEqual(row["note"], "测试笔记")

    def test_attempt_persists_confidence_and_rejects_negative_time(self):
        body = {"question_id": self.q["id"], "content_hash": self.q["content_hash"], "selected_index": 0, "confidence": "guess", "elapsed_ms": 1240}
        status, _ = self.request(body, path="/api/attempt")
        self.assertEqual(status, 200)
        with lab.connect() as db:
            row = db.execute("SELECT * FROM attempts ORDER BY id DESC LIMIT 1").fetchone()
        self.assertEqual(row["confidence"], "guess")
        self.assertEqual(row["correct"], 1)
        body["elapsed_ms"] = -1
        self.assertEqual(self.request(body, path="/api/attempt")[0], 400)


if __name__ == "__main__":
    unittest.main()
