import collections
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import lab
import study_plan

class ExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions=lab.annotate(lab.all_candidates())
        cls.baseline=lab.read_json(lab.DATA/'curriculum/expansion-1000/original-360-hashes.json')
        cls.old_plan=lab.read_json(lab.DATA/'plan-history/pre-expansion-360.json')
        cls.plan=study_plan.read_plan()

    def test_exact_count_distinct_questions_and_original_content_unchanged(self):
        by_id={q['id']:q for q in self.questions}
        self.assertEqual(len(self.questions),1000)
        self.assertEqual(len(by_id),1000)
        self.assertEqual(len({lab.question_hash(q) for q in self.questions}),1000)
        self.assertEqual(len({lab.normalized(q['stem']) for q in self.questions}),1000)
        self.assertEqual(len(self.baseline),360)
        for qid,content_hash in self.baseline.items():
            self.assertEqual(by_id[qid]['content_hash'],content_hash)
        self.assertEqual(collections.Counter(q['kind'] for q in self.questions),{'reading':310,'vocabulary':470,'grammar':220})

    def test_every_question_has_structure_and_content_bound_editorial_record(self):
        for q in self.questions:
            self.assertTrue(q['structural_check']['passed'],q['id'])
            self.assertEqual(q['editorial_check']['content_hash'],q['content_hash'])
            self.assertEqual(q['editorial_check']['decision'],'reviewed')
            self.assertTrue(lab.practice_allowed(q))

    def test_extension_preserves_issued_dates_and_schedules_every_question(self):
        self.assertEqual(self.plan['days'][:16],self.old_plan['days'][:16])
        by_id={q['id']:q for q in self.questions};seen=set();first=collections.Counter()
        for day in self.plan['days']:
            ids=[e['question_id'] for e in day['items']]
            self.assertEqual(len(set(ids)),30)
            self.assertEqual(len({by_id[qid]['target_id'] for qid in ids}),30)
            for e in day['items']:
                self.assertEqual(e['content_hash'],by_id[e['question_id']]['content_hash'])
                if e['role']=='new':
                    self.assertNotIn(e['question_id'],seen);first[e['question_id']]+=1
                else:self.assertIn(e['question_id'],seen)
                seen.add(e['question_id'])
        self.assertEqual(seen,set(by_id));self.assertEqual(set(first.values()),{1})
        self.assertEqual(self.plan['new_slots'],1000);self.assertEqual(self.plan['review_slots'],560)
        self.assertEqual(max(self.plan['first_dates'].values()),'2026-11-30')
        self.assertTrue(all(d['new_count']==0 for d in self.plan['days'][-7:]))
        for q in self.questions:
            if q['id']not in self.baseline:self.assertGreater(self.plan['first_dates'][q['id']],'2026-11-01')

    def test_short_reading_uses_stored_curated_distractors(self):
        t=next(t for t in lab.read_json(lab.DATA/'targets.json')if t['label']=='縁')
        expected=lab.read_json(lab.DATA/'reading-distractors.json')[t['id']]
        self.assertEqual(lab.reading_options(t,'anything'),[t['reading'],*expected])
