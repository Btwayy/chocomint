"""Loopback-only review/practice app. Start: python3 server.py"""
import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import lab
import study_plan


def state():
    questions = lab.annotate(lab.all_candidates())
    targets = lab.read_json(lab.DATA / "targets.json")
    order = {target["id"]: i for i, target in enumerate(targets)}
    questions.sort(key=lambda q: (order.get(q["target_id"], 9999), q["kind"] != "reading", q["id"]))
    with lab.connect() as db:
        reviews = {r["question_id"]: dict(r) for r in db.execute("SELECT * FROM reviews")}
        attempts = [dict(r) for r in db.execute("SELECT * FROM attempts ORDER BY id DESC")]
    for q in questions:
        review = reviews.get(q["id"])
        q["human_review"] = review if review and review["content_hash"] == q["content_hash"] else {"decision": "pending", "note": ""}
        q["review_status"] = q["human_review"]["decision"]
    return {"questions": questions, "attempts": attempts, "study_plan": study_plan.view(study_plan.read_plan(), questions, attempts), "targets": [{k: t[k] for k in ("id", "kind", "label", "focus_zh")} for t in targets],
            "summary": lab.read_json(lab.ROOT / "reports/summary.json") if (lab.ROOT / "reports/summary.json").exists() else {"generated": 0, "planned": 120}}


class Handler(BaseHTTPRequestHandler):
    server_version = "N1Lab/1.0"

    def send(self, status, data, content_type="application/json; charset=utf-8", filename=None):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def valid_host(self):
        return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def do_GET(self):
        if not self.valid_host():
            return self.send(403, {"error": "仅允许本机访问"})
        path = urlsplit(self.path).path
        if path == "/api/state":
            return self.send(200, state())
        if path == "/api/export/plan":
            plan = study_plan.read_plan()
            if not plan:
                return self.send(404, {"error": "尚无日期题单"})
            return self.send(200, json.dumps(plan, ensure_ascii=False, indent=2).encode(), filename="n1-study-plan.json")
        if path in ("/api/export/approved", "/api/export/candidates", "/api/export/reviewed"):
            lab.export()
            name = path.rsplit("/", 1)[1] + ".json"
            return self.send(200, (lab.DATA / name).read_bytes(), filename="n1-"+name)
        if path == "/api/export/records":
            with lab.connect() as db:
                data = {"reviews": [dict(r) for r in db.execute("SELECT * FROM reviews")], "attempts": [dict(r) for r in db.execute("SELECT * FROM attempts")], "study_plan": study_plan.read_plan(), "exported_at": lab.now()}
            return self.send(200, json.dumps(data, ensure_ascii=False, indent=2).encode(), filename="n1-records.json")
        files = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css", "/storage.js": "storage.js"}
        if path in files:
            file = lab.ROOT / "web" / files[path]
            mime = mimetypes.guess_type(str(file))[0] or "application/octet-stream"
            return self.send(200, file.read_bytes(), mime+"; charset=utf-8")
        return self.send(404, {"error": "页面不存在"})

    def do_POST(self):
        if not self.valid_host():
            return self.send(403, {"error": "仅允许本机访问"})
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}:
            return self.send(403, {"error": "请求来源不匹配"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send(415, {"error": "需要 JSON 请求"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > 16000:
                raise ValueError("请求大小不合法")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("请求格式不合法")
            questions = {q["id"]: q for q in lab.annotate(lab.all_candidates())}
            q = questions.get(body.get("question_id"))
            if not q:
                return self.send(404, {"error": "题目不存在"})
            if body.get("content_hash") != q["content_hash"]:
                return self.send(409, {"error": "题目已更新，请刷新后重试"})
            path = urlsplit(self.path).path
            if path == "/api/review":
                decision, note = body.get("decision"), body.get("note", "")
                if decision not in ("pending", "approved", "rejected") or not isinstance(note, str) or len(note) > 3000:
                    raise ValueError("审核内容不合法")
                if decision == "approved" and not q["structural_check"]["passed"]:
                    raise ValueError("结构检查失败的题目不能加入正式题库")
                with lab.connect() as db:
                    db.execute("INSERT INTO reviews(question_id,decision,note,updated_at,content_hash) VALUES(?,?,?,?,?) ON CONFLICT(question_id) DO UPDATE SET decision=excluded.decision,note=excluded.note,updated_at=excluded.updated_at,content_hash=excluded.content_hash",
                               (q["id"], decision, note, lab.now(), q["content_hash"]))
                lab.export()
                return self.send(200, {"saved": True, "decision": decision})
            if path == "/api/attempt":
                selected, confidence, elapsed = body.get("selected_index"), body.get("confidence"), body.get("elapsed_ms")
                if type(selected) is not int or selected not in range(4) or confidence not in ("sure", "unsure", "guess") or type(elapsed) is not int or elapsed < 0 or elapsed > 86400000:
                    raise ValueError("答题内容不合法")
                correct = selected == q["answer_index"]
                plan_date = body.get("plan_date")
                study_plan.validate_attempt(plan_date, q)
                with lab.connect() as db:
                    db.execute("INSERT INTO attempts(question_id,selected_index,correct,confidence,elapsed_ms,created_at,content_hash,plan_date) VALUES(?,?,?,?,?,?,?,?)",
                               (q["id"], selected, int(correct), confidence, elapsed, lab.now(), q["content_hash"], plan_date))
                return self.send(200, {"saved": True, "correct": correct})
            return self.send(404, {"error": "接口不存在"})
        except (ValueError, TypeError, KeyError) as exc:
            return self.send(400, {"error": str(exc)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    lab.connect().close()
    lab.export()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"N1 Lab: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
