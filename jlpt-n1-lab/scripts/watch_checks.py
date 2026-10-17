"""Process completed candidates while the generation job is running."""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import lab

while True:
    subprocess.run([sys.executable, str(ROOT / "lab.py"), "rebuild-readings"], cwd=ROOT, check=True)
    questions = lab.annotate(lab.all_candidates())
    pending = [q for q in questions if q["kind"] != "reading" and q["structural_check"]["passed"] and not q.get("blind_check")]
    print(f"CHECK QUEUE generated={len(questions)} pending={len(pending)}", flush=True)
    if pending:
        subprocess.run([sys.executable, str(ROOT / "lab.py"), "blind-check", "--model", "qwen3.5:9b-q4_K_M", "--limit", "8"], cwd=ROOT, check=True)
    elif len(questions) == 120:
        subprocess.run([sys.executable, str(ROOT / "lab.py"), "export"], cwd=ROOT, check=True)
        print("ALL CANDIDATES CHECKED", flush=True)
        break
    else:
        time.sleep(5)
