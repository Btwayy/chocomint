"""A precomputed dated study plan. No inference or external services."""
import argparse
import collections
import datetime as dt
import hashlib
import json
import random
from zoneinfo import ZoneInfo
import lab

START='2026-10-17'
END='2026-12-07'
FILE='study-plan.json'

def tokyo_today():
    return dt.datetime.now(ZoneInfo('Asia/Tokyo')).date().isoformat()

def make_plan(questions,daily=30,start=START,end=END):
    start_date,end_date=dt.date.fromisoformat(start),dt.date.fromisoformat(end)
    days=(end_date-start_date).days+1
    if daily<1 or days<8:raise ValueError('Invalid daily count or date range')
    candidates=[q for q in questions if lab.practice_allowed(q)]
    if len(candidates)<daily:raise ValueError('Not enough unique reviewed questions for the first day')
    if len({q['target_id'] for q in candidates})<daily:raise ValueError('Not enough distinct targets for the first day')
    learning_days=days-7
    if len(candidates)>learning_days*daily:raise ValueError('Not enough study slots for every new question')
    pools={k:[q for q in candidates if q['kind']==k] for k in ['reading','vocabulary','grammar']}
    rng=random.Random(20261017)
    for pool in pools.values():rng.shuffle(pool)
    deck=[]
    while any(pools.values()):
        for kind in ['reading','vocabulary','grammar','reading','vocabulary']:
            if pools[kind]:deck.append(pools[kind].pop())
    remaining=len(deck)-daily
    base,extra=divmod(remaining,learning_days-1)
    quotas=[daily]+[base+(i<extra) for i in range(learning_days-1)]+[0]*7
    history={};daily_rows=[];first_dates={}
    intervals=[1,3,7,14,21]
    by_id={q['id']:q for q in candidates}
    for n,quota in enumerate(quotas):
        date=(start_date+dt.timedelta(days=n)).isoformat()
        chosen=[];targets=set()
        for _ in range(quota):
            idx=next((i for i,q in enumerate(deck) if q['target_id'] not in targets),None)
            if idx is None:raise ValueError('Cannot avoid duplicate targets on '+date)
            q=deck.pop(idx);targets.add(q['target_id']);first_dates[q['id']]=date
            chosen.append({'question_id':q['id'],'content_hash':q['content_hash'],'role':'new'})
        def priority(qid):
            appearances=history[qid];gap=intervals[min(len(appearances)-1,len(intervals)-1)]
            return (appearances[-1]+gap-n,len(appearances),lab.seed_for(date+qid))
        for qid in sorted(history,key=priority):
            if len(chosen)>=daily:break
            q=by_id[qid]
            if q['target_id'] in targets:continue
            chosen.append({'question_id':qid,'content_hash':q['content_hash'],'role':'review'})
            targets.add(q['target_id'])
        if len(chosen)!=daily:raise ValueError(f'{date}: only {len(chosen)} available')
        random.Random(lab.seed_for(date)).shuffle(chosen)
        for entry in chosen:history.setdefault(entry['question_id'],[]).append(n)
        daily_rows.append({'date':date,'day_number':n+1,'phase':'consolidation' if n>=learning_days else 'learning',
                           'new_count':quota,'review_count':daily-quota,'items':chosen})
    if deck:raise ValueError('Unscheduled new questions')
    payload=json.dumps([(q['id'],q['content_hash']) for q in candidates],sort_keys=True).encode()
    return {'version':'study-52days-v1','created_at':lab.now(),'timezone':'Asia/Tokyo','start_date':start,'end_date':end,
            'days_count':days,'daily_count':daily,'total_slots':days*daily,'unique_questions':len(candidates),
            'new_slots':sum(quotas),'review_slots':days*daily-sum(quotas),'learning_days':learning_days,
            'consolidation_days':7,'bank_hash':hashlib.sha256(payload).hexdigest(),'first_dates':first_dates,
            'review_policy':'固定题单，优先安排距上次练习约 1、3、7、14、21 天的旧题；受每日容量影响，不保证每个间隔精确命中。不是随作答自动调整的算法。',
            'content_scope':'词汇读音、语境填空、语法；不含听力、长篇阅读或完整模拟卷。读音与词汇题可能共享例句。',
            'days':daily_rows}

def read_plan():
    path=lab.DATA/FILE
    return lab.read_json(path) if path.exists() else None

def view(plan,questions,attempts,today=None):
    if not plan:return None
    by_id={q['id']:q for q in questions}
    done={(a.get('plan_date'),a['question_id'],a['content_hash']) for a in attempts if a.get('plan_date')}
    result={k:v for k,v in plan.items() if k not in ('first_dates','days')}
    rows=[]
    for day in plan['days']:
        entries=[]
        for entry in day['items']:
            q=by_id.get(entry['question_id'])
            available=bool(q and q['content_hash']==entry['content_hash'] and lab.practice_allowed(q))
            entries.append({**entry,'available':available,'done':(day['date'],entry['question_id'],entry['content_hash']) in done})
        rows.append({**day,'items':entries,'completed_count':sum(e['done'] for e in entries),'unavailable_count':sum(not e['available'] for e in entries)})
    result['days']=rows;result['today']=today or tokyo_today()
    result['completed_slots']=sum(d['completed_count'] for d in rows)
    return result

def validate_attempt(date,q):
    if date is None:return
    if not isinstance(date,str):raise ValueError('练习日期不合法')
    plan=read_plan()
    if not plan:raise ValueError('尚未生成日期题单')
    day=next((d for d in plan['days'] if d['date']==date),None)
    if not day or not any(e['question_id']==q['id'] and e['content_hash']==q['content_hash'] for e in day['items']):
        raise ValueError('此题不属于所选日期的当前版本题单')
    if not lab.practice_allowed(q):raise ValueError('此题已暂停或复核失效，请刷新')

def save_plan(plan,questions):
    path=lab.DATA/FILE
    old=lab.read_json(path) if path.exists() else None
    if old and any(old.get(k)!=plan[k] for k in ('bank_hash','daily_count','start_date','end_date')):
        lab.write_json(lab.DATA/'plan-history'/('before-'+lab.now().replace(':','-')+'.json'),old)
    lab.write_json(path,plan)
    by_id={q['id']:q for q in questions}
    for day in plan['days']:
        lab.write_json(lab.DATA/'daily'/(day['date']+'.json'),{k:v for k,v in day.items() if k!='items'}|{'questions':[{**by_id[e['question_id']],'plan_role':e['role'],'plan_date':day['date']} for e in day['items']]})
    lines=['# 52 天本地练习计划','',f"{plan['start_date']} 至 {plan['end_date']}，含首尾共 {plan['days_count']} 天，每天 {plan['daily_count']} 题。",'',
           f"共 {plan['total_slots']} 次作答：{plan['unique_questions']} 道不同题目首次练习 + {plan['review_slots']} 次间隔复习。不是 {plan['total_slots']} 道互不相同的新题。",'',
           '题库覆盖 150 个词汇和 30 个语法点。延续原有 120 题，新编并复核 240 题。所有题目已保存，无需每日生成或启动 Ollama。', '',
           '11 月 30 日前完成新题，12 月 1 日至 7 日只做复习。由于首日没有旧题，首日 30 题都是新题。以后每天 7–8 道新题搭配 22–23 道复习题。','',
           plan['review_policy'],'',plan['content_scope'],'',
           '审核：当前对话中的 Codex 逐题编辑复核，仍可能漏错，不是教师认证。4 组有问题的草稿组合已废弃；具体记录在 `data/curriculum/discarded-drafts.json`。不会要求学习者审核。','',
           '新增题目由当前 Codex 对话编写；没有新增 Ollama 请求或额外模型 API 调用。当前 Codex 对话的使用成本不在旧本机推理统计中。','',
           '每日日进度按日期、题目 ID 和内容版本去重；同题重复作答不会重复增加当日完成数。旧题库中无日期标记的作答记录保留，但不计作某一天的完成。', '',
           '## 每日题单','', '| 日期 | 第几天 | 新题 | 复习 | 合计 |','|---|---:|---:|---:|---:|']
    for day in plan['days']:lines.append(f"| {day['date']} | {day['day_number']} | {day['new_count']} | {day['review_count']} | {len(day['items'])} |")
    (lab.ROOT/'reports/study-plan.md').write_text('\n'.join(lines)+'\n')
    return plan

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--daily',type=int,default=30);args=parser.parse_args()
    questions=lab.annotate(lab.all_candidates())
    plan=save_plan(make_plan(questions,daily=args.daily),questions)
    print(json.dumps({k:v for k,v in plan.items() if k not in ('days','first_dates')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
