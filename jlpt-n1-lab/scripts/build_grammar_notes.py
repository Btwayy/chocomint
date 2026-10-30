"""Build display-only grammar notes; question hashes and study records stay unchanged."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
notes = {}
for line in (ROOT / 'data/curriculum/grammar-option-notes.tsv').read_text().splitlines():
    option, usage, example, translation = line.split('\t')
    if option in notes:
        raise ValueError(f'Duplicate option: {option}')
    notes[option] = dict(usage=usage, example=example, translation=translation)
questions = json.loads((ROOT / 'data/candidates.json').read_text())
options = {o for q in questions if q['kind'] == 'grammar' for o in q['options']}
assert options == notes.keys(), options ^ notes.keys()
(ROOT / 'web/grammar-notes.js').write_text(
    '// Display-only notes authored and checked by Codex; not official exam material.\n'
    'const grammarOptionNotes = ' + json.dumps(notes, ensure_ascii=False, indent=2) + ';\n')
print(f'Built notes for all {len(notes)} grammar options.')
