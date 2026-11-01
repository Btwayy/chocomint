"""Explicit migration: preserve all daily sets through 2026-11-01, including online users'."""
import collections
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import lab
import study_plan

if __name__=='__main__':
    old=study_plan.read_plan()
    before=lab.DATA/'plan-history/pre-expansion-360.json'
    if not before.exists():lab.write_json(before,old)
    baseline=lab.read_json(before)
    questions=lab.annotate(lab.all_candidates())
    plan=study_plan.extend_plan(baseline,questions,'2026-11-01')
    assert plan['days'][:16]==baseline['days'][:16]
    ids={q['id'] for q in questions};seen=set();new=collections.Counter()
    for day in plan['days']:
        assert len(day['items'])==30
        for entry in day['items']:
            if entry['role']=='new':
                assert entry['question_id'] not in seen
                new[entry['question_id']]+=1
            else:assert entry['question_id'] in seen
            seen.add(entry['question_id'])
    assert seen==ids and set(new.values())=={1} and len(new)==1000
    study_plan.save_plan(plan,questions)
    lab.write_json(lab.ROOT/'reports/expanded-plan-validation.json',{
        'bank_questions':1000,'days':52,'total_slots':1560,'new_slots':plan['new_slots'],'review_slots':plan['review_slots'],
        'preserved_through':plan['preserved_through'],'preserved_days':16,'all_1000_questions_scheduled_once_as_new':True,
        'last_new_date':max(plan['first_dates'].values()),'future_learning_quotas':dict(collections.Counter(d['new_count'] for d in plan['days'][16:-7]))})
    print(json.dumps(lab.read_json(lab.ROOT/'reports/expanded-plan-validation.json'),ensure_ascii=False,indent=2))
