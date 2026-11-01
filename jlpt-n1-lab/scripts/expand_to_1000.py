"""Materialize the explicitly authored 640-question supplement and preserve old IDs/hashes.
This script validates structure; it does not act as a language reviewer. The source
rows were written and reviewed by Codex in the user-authorized expansion session.
"""
import copy
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab

ROOT = lab.ROOT
SOURCE = lab.DATA / 'curriculum/expansion-1000'
REVIEW = 'codex-expansion-1000-v1'
COMMON = {'title':'OpenJLPT 固定版本知识点资料（非现成试题）','url':'https://github.com/evanclan/OpenJLPT/tree/0d1d3410bec90bd4098a7c72de820543cb4f707c'}
READING_REFS = {
 '愛想':{'title':'小学館等辞典：愛想（含あいそう）','url':'https://kotobank.jp/word/愛想-421457'},
 '共存':{'title':'小学館等辞典：共存（きょうそん／きょうぞん）','url':'https://kotobank.jp/word/共存-478601'},
 '重複':{'title':'小学館 日本国語大辞典：重複','url':'https://nikkoku-tomonokai.japanknowledge.jp/detail.php?id=158560'},
}
OTHER_READINGS = {'愛想':['あいそう'],'共存':['きょうそん'],'重複':['ちょうふく'],'一目':['ひとめ']}
EXTRA = {'区別':('くべつ','区别'),'審判':('しんぱん','裁判、判决'),'歓迎':('かんげい','欢迎'),'観客':('かんきゃく','观众'),'顧客':('こきゃく','客户'),'昇進':('しょうしん','升职')}

def read_rows(name, fields):
 rows=[line.split('|') for line in (SOURCE/name).read_text().splitlines() if line.strip()]
 assert all(len(r)==fields for r in rows), name
 return rows

def main():
 baseline_path=SOURCE/'original-360-hashes.json'
 if not baseline_path.exists():
  original=lab.annotate(lab.all_candidates())
  assert len(original)==360
  lab.write_json(baseline_path,{q['id']:q['content_hash'] for q in original})
 baseline=lab.read_json(baseline_path)
 targets=lab.read_json(lab.DATA/'targets.json');target_map={t['id']:t for t in targets}
 vocab={v['word']:v for v in lab.read_json(lab.DATA/'sources/vocab-n1.json')}
 grammar={g['id']:g for g in lab.read_json(lab.DATA/'sources/grammar-n1.json')}
 notes=lab.read_json(lab.DATA/'editorial-notes.json')
 table=lab.read_json(lab.DATA/'reading-distractors.json')
 vr=read_rows('vocabulary.tsv',9); gr=read_rows('grammar.tsv',7); gq=read_rows('grammar-questions.tsv',4)
 assert len(vr)==160 and len(gr)==40 and len(gq)==160
 gloss={t['label']:t['focus_zh'] for t in targets}
 gloss.update({r[0]:r[1] for r in vr});gloss.update({w:v[1] for w,v in EXTRA.items()})
 commit=lab.read_json(lab.DATA/'sources/manifest.json')['commit']
 added=[]
 def base(t):
  return {'target_id':t['id'],'target_label':t['label'],'level':'N1','focus_zh':t['focus_zh'],
   'source':{'project':'OpenJLPT','commit':commit,'source_id':t['source']['id'],'source_file':t['source_file'],'license':'CC-BY-SA-4.0'},
   'generation':{'model':'Codex（当前对话原创）','method':'authored_in_conversation','created_at':lab.now(),'curriculum_version':REVIEW},'review_status':'pending'}
 def keep(q,t):
  assert q['id'] not in baseline, q['id']
  errors=lab.structural_errors(q,t)
  assert not errors,(q['id'],errors)
  lab.shuffled(q)
  record={'question_id':q['id'],'content_hash':lab.question_hash(q),'decision':'reviewed','review_id':REVIEW,
   'reviewer':'Codex（当前对话中的 AI 编辑）',
   'method':'同一 AI 编写后的第二轮编辑复核：将四个选项代入完整句子，核对接续、语义唯一性、中译和解析；读音核对固定底库及异读。不是独立模型复答、真人审核或官方认证。',
   'note_zh':q['explanation_zh'],'options_checked':q['options'],'references':[COMMON]+([READING_REFS[t['label']]] if t['label'] in READING_REFS else []),
   'created_at':lab.now(),'limitations':'原创知识点巩固题，含接续辨析；未标定真实 N1 难度。读音题与该词第一道填空题共享句子，第二道填空题另设语境。'}
  existing=notes.get(q['id'])
  notes[q['id']]=existing if existing and existing['content_hash']==record['content_hash'] else record
  added.append(q);return q
 for word,meaning,s1,tr1,s2,tr2,wrong,read_wrong,why in vr:
  source=copy.deepcopy(vocab[word]);source['other_readings']=list(set(source.get('other_readings',[])+OTHER_READINGS.get(word,[])))
  tid='v-'+source['id'];wrongs=wrong.split(',');rw=read_wrong.split(',')
  assert len(set(wrongs))==3 and all(w in gloss for w in wrongs),word
  assert len(set(rw))==3 and not set(rw)&{source['reading'],*source['other_readings']},word
  t={'id':tid,'kind':'vocabulary','label':word,'reading':source['reading'],'focus_zh':meaning,'source':source,'source_file':'vocab-n1.json','distractors':wrongs}
  target_map[tid]=t;table[tid]=rw
  reading={**base(t),'id':tid+'-reading','kind':'reading','stem':s1.replace('（　）','【'+word+'】'),'options':[source['reading'],*rw],'answer_index':0,'translation_zh':tr1,
   'explanation_zh':f'「{word}」在本句中读「{source["reading"]}」，表示{meaning}。'+(' 注意该词有合法异读，其他语境或词典用法另见来源；异读未作为错误选项。' if source['other_readings'] else ''),
   'option_explanations_zh':[f'本句读「{source["reading"]}」。']+[f'本句不读「{r}」。' for r in rw]}
  qs=[keep(reading,t)]
  for i,(stem,tr) in enumerate([(s1,tr1),(s2,tr2)],1):
   q={**base(t),'id':tid+f'-cloze-{i}','kind':'vocabulary','stem':stem,'options':[word,*wrongs],'answer_index':0,'translation_zh':tr,
    'explanation_zh':why,'option_explanations_zh':[why]+[f'「{w}」表示{gloss[w]}。' for w in wrongs]}
   qs.append(keep(q,t))
  lab.write_json(lab.DATA/'batches'/(tid+'.json'),{'target_id':tid,'questions':qs})
 option_notes={}
 for gid,pattern,answer,wrong,focus,example,tr in gr:
  source=grammar[gid];tid='g-'+gid
  t={'id':tid,'kind':'grammar','label':source['pattern'],'focus_zh':focus,'source':source,'source_file':'grammar-n1.json','answer_pattern':re.escape(pattern)}
  target_map[tid]=t;rows=[r for r in gq if r[0]==gid];assert len(rows)==4,gid
  qs=[]
  for i,(_,stem,translation,why) in enumerate(rows,1):
   q={**base(t),'id':tid+'-'+str(i),'kind':'grammar','stem':stem,'options':[answer,*wrong.split(',')],'answer_index':0,'translation_zh':translation,
    'explanation_zh':why,'option_explanations_zh':[why]+[f'此处不选「{w}」；请对照其接续和例句，原句要求的是「{answer}」表达的关系。' for w in wrong.split(',')]}
   qs.append(keep(q,t))
  lab.write_json(lab.DATA/'batches'/(tid+'.json'),{'target_id':tid,'questions':qs})
  option_notes[answer]=[focus,example,tr]
 assert len(added)==640
 lab.write_json(lab.DATA/'targets.json',list(target_map.values()));lab.write_json(lab.DATA/'reading-distractors.json',table);lab.write_json(lab.DATA/'editorial-notes.json',notes)
 # Keep the existing option-note entries; append only newly introduced constructions.
 note_path=lab.DATA/'curriculum/grammar-option-notes.tsv';lines=note_path.read_text().splitlines();known={l.split('\t')[0] for l in lines}
 for option,values in option_notes.items():
  if option not in known:lines.append('\t'.join([option,*values]))
 note_path.write_text('\n'.join(lines)+'\n')
 # Existing display-only reading annotations are retained, including valid alternate readings.
 app_path=ROOT/'web/app.js';app=app_path.read_text();match=re.search(r'const optionReadings = (\{.*?\});',app,re.S);readings=json.loads(match.group(1))
 for q in added:
  if q['kind']=='vocabulary':
   for option in q['options']:
    if option not in readings:readings[option]=EXTRA[option][0] if option in EXTRA else vocab[option]['reading']
 for word in ['愛想','共存','重複']:readings[word]='／'.join([vocab[word]['reading'],*OTHER_READINGS[word]])
 app=app[:match.start(1)]+json.dumps(dict(sorted(readings.items())),ensure_ascii=False,indent=2)+app[match.end(1):];app_path.write_text(app)
 summary=lab.export();result=lab.read_json(lab.DATA/'candidates.json');by_id={q['id']:q for q in result}
 assert len(result)==1000 and len(by_id)==1000
 assert all(by_id[qid]['content_hash']==h for qid,h in baseline.items()),'Original content changed'
 assert all(q['structural_check']['passed'] and q.get('editorial_check',{}).get('decision')=='reviewed' for q in result)
 lab.write_json(ROOT/'reports/expansion-1000-validation.json',{'created_at':lab.now(),'total':1000,'added':640,'preserved_original_hashes':len(baseline),'new_vocabulary_targets':160,'new_grammar_targets':40,'kind_counts':summary['by_kind'],'structural_passed':1000,'editorial_records_hash_matched':1000,'independent_model_review':False,'teacher_review':False,'extra_model_api_calls':0,'method':'Explicitly authored source rows + same-agent editorial second pass + mechanical validation; no generated fake learning records.'})
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
