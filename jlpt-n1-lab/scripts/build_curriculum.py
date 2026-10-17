"""Materialize explicitly authored, reviewed questions; no model/API calls.
The TSV rows are written and checked in the Codex conversation, not inferred
by this script. Mechanical checks are an additional gate, never a language judge.
"""
import copy
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import lab

REVIEW='codex-52days-v1'
COMMON={'title':'OpenJLPT 固定版本知识点资料（非现成试题）','url':'https://github.com/evanclan/OpenJLPT/tree/0d1d3410bec90bd4098a7c72de820543cb4f707c'}
REFERENCES={
'ni-taru':{'title':'Bunpro：に足る（核对接续与意义）','url':'https://cdn.bunpro.jp/grammar_points/に足る'},
'katagata':{'title':'Bunpro：かたがた（核对接续与意义）','url':'https://bunpro.jp/grammar_points/948'},
'zu-ni-wa-sumanai-nai-de-wa-sumanai':{'title':'Bunpro：ずにはすまない（核对接续与意义）','url':'https://bunpro.jp/grammar_points/ずにはすまない'},
'ikan-de-ikan-ni-yorazu':{'title':'Bunpro：いかん〜ず（核对不问条件的用法）','url':'https://bunpro.jp/grammar_points/いかん-ず'},
}

def main():
 targets=lab.read_json(lab.DATA/'targets.json');target_map={t['id']:t for t in targets}
 vocab={v['word']:v for v in lab.read_json(lab.DATA/'sources/vocab-n1.json')}
 grammar={g['id']:g for g in lab.read_json(lab.DATA/'sources/grammar-n1.json')}
 rows=[r.split('|') for r in (lab.DATA/'curriculum/vocabulary.tsv').read_text().splitlines() if r]
 gloss={q['target_label']:q['focus_zh'] for q in lab.all_candidates()}
 gloss.update({r[0]:r[1] for r in rows})
 gloss.update({'極端':'极端','たやすい':'容易','好ましい':'可喜、理想','滅多に':'很少（通常与否定呼应）','決して':'绝不（通常与否定呼应）','一概に':'一概、不加区分地','一概':'一概、笼统','脆い':'脆、易碎'})
 notes=lab.read_json(lab.DATA/'editorial-notes.json')
 reading_table=lab.read_json(lab.DATA/'reading-distractors.json')
 commit=lab.read_json(lab.DATA/'sources/manifest.json')['commit']
 new=[]
 def base(t):
  return {'target_id':t['id'],'target_label':t['label'],'level':'N1','focus_zh':t['focus_zh'],
   'source':{'project':'OpenJLPT','commit':commit,'source_id':t['source']['id'],'source_file':t['source_file'],'license':'CC-BY-SA-4.0'},
   'generation':{'model':'Codex（当前对话原创）','method':'authored_in_conversation','created_at':lab.now(),'curriculum_version':REVIEW},'review_status':'pending'}
 def keep(q,t,note,refs):
  errors=lab.structural_errors(q,t)
  if errors:raise ValueError((q['id'],errors))
  lab.shuffled(q)
  existing=notes.get(q['id'])
  if existing and existing.get('content_hash')!=lab.question_hash(q):
   archive=lab.DATA/'revisions'/REVIEW/(q['id']+'-previous.json')
   old=next((x for x in lab.all_candidates() if x['id']==q['id']),None)
   if old and not archive.exists():lab.write_json(archive,old)
  record={'question_id':q['id'],'content_hash':lab.question_hash(q),'decision':'reviewed','review_id':REVIEW,
   'reviewer':'Codex（当前对话中的 AI 编辑）','method':'逐题将四个选项代入完整句子，复核语义、接续、唯一性、中文解析；读音与固定版本词典数据核对。不是独立真人复审。',
   'note_zh':note,'options_checked':q['options'],'references':refs,'created_at':lab.now(),
   'limitations':'原创知识点练习，非官方真题；AI 编辑仍可能漏错，未作真实 N1 难度标定。'}
  if existing and existing.get('content_hash')==record['content_hash']:record=existing
  notes[q['id']]=record;new.append(q)
 for row in rows:
  if len(row)!=7:raise ValueError(row)
  word,meaning,stem,translation,distractors,wrong,why=row
  source=vocab[word];tid='v-'+source['id']
  if word==source['reading']:raise ValueError('Kana-only word cannot be a meaningful reading question: '+word)
  wrongs=wrong.split(',');valid={source['reading'],*source.get('other_readings',[])}
  if len(set(wrongs))!=3 or any(w in valid for w in wrongs):raise ValueError((word,'invalid reading distractors',wrongs))
  reading_table[tid]=wrongs
  t={'id':tid,'kind':'vocabulary','label':word,'reading':source['reading'],'focus_zh':meaning,'source':source,'source_file':'vocab-n1.json','distractors':distractors.split(',')}
  target_map[tid]=t
  opts=[word,*t['distractors']]
  q={**base(t),'id':tid+'-cloze','kind':'vocabulary','stem':stem,'options':opts,'answer_index':0,'translation_zh':translation,
   'explanation_zh':why,'option_explanations_zh':[why]+[f'「{d}」表示{gloss[d]}；不符合本题已经限定的句意或接续。' for d in t['distractors']]}
  r={**base(t),'id':tid+'-reading','kind':'reading','stem':stem.replace('（　）','【'+word+'】'),'options':[source['reading'],*wrongs], 'answer_index':0,'translation_zh':translation,
   'explanation_zh':f'「{word}」本题读「{source["reading"]}」，句中表示{meaning}。',
   'option_explanations_zh':[f'正确：本题标记词读「{source["reading"]}」。']+[f'不是本题标记词的正确读音；这里应选「{source["reading"]}」。' for _ in range(3)]}
  keep(r,t,r['explanation_zh'],[COMMON]);keep(q,t,why,[COMMON])
  lab.write_json(lab.DATA/'batches'/(tid+'.json'),{'target_id':tid,'questions':[r,q]})
 for row in (lab.DATA/'curriculum/grammar.tsv').read_text().splitlines():
  gid,pattern,focus,answer,wrong,s1,tr1,s2,tr2,why,exclusion=row.split('|')
  source=grammar[gid];tid='g-'+gid
  t={'id':tid,'kind':'grammar','label':source['pattern'],'focus_zh':focus,'source':source,'source_file':'grammar-n1.json','answer_pattern':pattern}
  target_map[tid]=t;qs=[]
  for i,(stem,translation) in enumerate([(s1,tr1),(s2,tr2)],1):
   q={**base(t),'id':tid+'-'+str(i),'kind':'grammar','stem':stem,'options':[answer,*wrong.split(',')],'answer_index':0,'translation_zh':translation,
    'explanation_zh':focus+' '+why,'option_explanations_zh':['正确。'+why]+[f'本题不选「{d}」。'+exclusion for d in wrong.split(',')]}
   keep(q,t,q['explanation_zh'],[COMMON]+([REFERENCES[gid]] if gid in REFERENCES else []));qs.append(q)
  lab.write_json(lab.DATA/'batches'/(tid+'.json'),{'target_id':tid,'questions':qs})
 lab.write_json(lab.DATA/'targets.json',list(target_map.values()))
 lab.write_json(lab.DATA/'reading-distractors.json',reading_table)
 lab.write_json(lab.DATA/'editorial-notes.json',notes)
 # Discarded alternatives are a trace of specific rejected drafts, not questions
 # that a learner must adjudicate.
 lab.write_json(lab.DATA/'curriculum/discarded-drafts.json',[
  {'target':'寄贈','draft':'干扰项误含合法异读「きそう」','reason':'原组读音选项废弃；移除合法异读后重新检查。'},
  {'target':'公認','draft':'读音干扰项误含「こうにん」','reason':'与正确读音相同，整组读音选项废弃；替换后重新检查。'},
  {'target':'煩わしい','draft':'重复输入作业＋たやすい 选项','reason':'重复操作也可能容易，缺乏唯一性；废弃该题干与选项组合。'},
  {'target':'ともなると','draft':'决赛语境＋に先立って 选项','reason':'赛前采访的读法也可能成立；不收录这个选项组合。'}])
 summary=lab.export()
 lab.write_json(lab.ROOT/'reports/curriculum-generation.json',{'created_at':lab.now(),'new_questions':len(new),'new_vocabulary_targets':len(rows),'new_grammar_targets':20,'discarded_drafts':4,'method':'Codex 在当前对话中编写并逐题复核；脚本只落盘、打乱选项及做结构校验，无额外本地或付费模型 API 调用。','total':summary['generated'],'language_quality_note':'含读音与词汇题共享例句；这是知识点巩固题库，并非 360 个不同情景的真题。'})
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
