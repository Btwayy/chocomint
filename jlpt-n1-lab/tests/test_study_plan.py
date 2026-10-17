import collections
import copy
import datetime as dt
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import lab
import study_plan

class StudyPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions=lab.annotate(lab.all_candidates())
        cls.plan=study_plan.make_plan(cls.questions)

    def test_full_date_range_and_every_question_has_one_first_day(self):
        p=self.plan
        self.assertEqual(p['days_count'],52)
        self.assertEqual(p['total_slots'],1560)
        self.assertEqual(p['days'][0]['date'],'2026-10-17')
        self.assertEqual(p['days'][-1]['date'],'2026-12-07')
        self.assertEqual(p['new_slots'],360)
        seen=set();by_id={q['id']:q for q in self.questions};new=collections.Counter()
        for day in p['days']:
            entries=day['items'];ids=[e['question_id'] for e in entries]
            self.assertEqual(len(ids),30)
            self.assertEqual(len(set(ids)),30)
            self.assertEqual(len({by_id[qid]['target_id'] for qid in ids}),30)
            for e in entries:
                if e['role']=='new':
                    self.assertNotIn(e['question_id'],seen);new[e['question_id']]+=1
                else:self.assertIn(e['question_id'],seen)
            seen.update(ids)
        self.assertEqual(set(seen),set(by_id))
        self.assertEqual(set(new.values()),{1})
        self.assertTrue(all(d['new_count']==0 for d in p['days'][-7:]))

    def test_progress_deduplicates_date_and_version_not_raw_attempt_count(self):
        p=self.plan;e=p['days'][0]['items'][0];date=p['days'][0]['date']
        attempt={'question_id':e['question_id'],'content_hash':e['content_hash'],'plan_date':date}
        attempts=[attempt,copy.deepcopy(attempt),attempt|{'plan_date':None},attempt|{'content_hash':'old'}]
        view=study_plan.view(p,self.questions,attempts,today=date)
        self.assertEqual(view['days'][0]['completed_count'],1)
        self.assertEqual(view['completed_slots'],1)

    def test_modified_or_withdrawn_questions_are_unavailable(self):
        qs=copy.deepcopy(self.questions);e=self.plan['days'][0]['items'][0]
        q=next(q for q in qs if q['id']==e['question_id'])
        q['content_hash']='changed'
        view=study_plan.view(self.plan,qs,[])
        self.assertFalse(next(i for i in view['days'][0]['items'] if i['question_id']==q['id'])['available'])

    def test_unscheduled_attempt_is_rejected(self):
        day=self.plan['days'][0];by_id={q['id']:q for q in self.questions}
        with patch.object(study_plan,'read_plan',return_value=self.plan):
            study_plan.validate_attempt(day['date'],by_id[day['items'][0]['question_id']])
            outsider=next(q for q in self.questions if q['id'] not in {e['question_id'] for e in day['items']})
            with self.assertRaises(ValueError):study_plan.validate_attempt(day['date'],outsider)
            with self.assertRaises(ValueError):study_plan.validate_attempt('2026-12-08',outsider)

    def test_existing_database_migration_preserves_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'old.sqlite'
            db=sqlite3.connect(path)
            db.execute('CREATE TABLE attempts (id INTEGER PRIMARY KEY AUTOINCREMENT,question_id TEXT,selected_index INTEGER,correct INTEGER,confidence TEXT,elapsed_ms INTEGER,created_at TEXT,content_hash TEXT)')
            db.execute('INSERT INTO attempts(question_id,selected_index,correct,confidence,elapsed_ms,created_at,content_hash) VALUES(?,?,?,?,?,?,?)',('existing',0,1,'sure',10,'old','old-hash'))
            db.commit();db.close()
            with lab.connect(path) as migrated:
                row=dict(migrated.execute('SELECT * FROM attempts').fetchone())
            self.assertEqual(row['question_id'],'existing')
            self.assertEqual(row['content_hash'],'old-hash')
            self.assertIsNone(row['plan_date'])

if __name__=='__main__':unittest.main()
