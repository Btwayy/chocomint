const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {build}=require('../web/day-summary.js');
function fixture(){
 const questions=[1,2,3].map((n)=>({id:`q${n}`,content_hash:`h${n}`,kind:n===3?'reading':'grammar',target_id:'same',target_label:'〜がてら',focus_zh:'顺便做另一件事',stem:'散歩（　）、買い物をする。',options:['がてら','ながら'],answer_index:0,translation_zh:'散步时顺便购物。',explanation_zh:'顺便做另一件事。',structural_check:{passed:true},editorial_check:{decision:'reviewed',content_hash:`h${n}`}}));
 const day={date:'2026-11-01',items:questions.map(q=>({question_id:q.id,content_hash:q.content_hash,available:true}))};
 const attempts=questions.map(q=>({question_id:q.id,content_hash:q.content_hash,plan_date:day.date,selected_index:0,confidence:'sure'}));
 const notes={'がてら':{usage:'接续',example:'散歩がてら買い物をする。',translation:'顺便购物。'}};
 return {questions,day,attempts,notes};
}
test('no early answers; duplicates, free practice and other dates cannot unlock recap',()=>{
 const f=fixture(),a=f.attempts[0];
 const r=build(f.day,f.questions,[a,a,{...f.attempts[1],plan_date:null},{...f.attempts[2],plan_date:'2026-11-02'}],f.notes);
 assert.equal(r.completed,1);assert.equal(r.ready,false);assert.deepEqual(r.groups,[]);
});
test('completed recap groups same grammar, excludes reading and keeps past mistakes after retry',()=>{
 const f=fixture();f.attempts.push({...f.attempts[0],selected_index:1,confidence:'guess'});
 const r=build(f.day,f.questions,f.attempts,f.notes);
 assert.equal(r.completed,3);assert.equal(r.ready,true);assert.equal(r.groups.length,1);
 assert.equal(r.groups[0].questions.length,2);assert.equal(r.groups[0].examples.length,1);
 assert.equal(r.groups[0].wrong,true);assert.equal(r.groups[0].uncertain,true);
 assert.equal(r.groups[0].questions[0].stem,'散歩【がてら】、買い物をする。');
});
test('old versions do not unlock recap; changed or flagged content is not summarized',()=>{
 const f=fixture();const old=build(f.day,f.questions,f.attempts.map(a=>({...a,content_hash:'old'})),f.notes);
 assert.equal(old.completed,0);
 f.questions[0].human_review={decision:'rejected'};f.questions[1].content_hash='changed';
 const r=build(f.day,f.questions,f.attempts,f.notes);
 assert.equal(r.ready,true);assert.equal(r.unavailable,2);assert.deepEqual(r.groups,[]);
});
test('mistakes rank first, then uncertainty; current notes are optional',()=>{
 const f=fixture();f.questions[1].target_id='second';f.attempts[1].selected_index=1;
 const r=build(f.day,f.questions,f.attempts);
 assert.equal(r.groups[0].id,'second');assert.equal(r.groups[1].id,'same');assert.deepEqual(r.groups[0].examples,[]);
});
test('all 52 real days recap exactly their assigned grammar after completion',()=>{
 const root=path.join(__dirname,'../data');const bank=JSON.parse(fs.readFileSync(path.join(root,'candidates.json')));
 const plan=JSON.parse(fs.readFileSync(path.join(root,'study-plan.json')));const questions=new Map(bank.map(q=>[q.id,q]));
 for(const day of plan.days){
  const attempts=day.items.map(e=>({question_id:e.question_id,content_hash:e.content_hash,plan_date:day.date,selected_index:questions.get(e.question_id).answer_index,confidence:'sure'}));
  const r=build(day,bank,attempts);
  const expected=day.items.map(e=>questions.get(e.question_id)).filter(q=>q.kind==='grammar');
  assert.equal(r.ready,true);assert.equal(r.completed,30);assert.equal(r.unavailable,0);
  assert.equal(r.groups.length,new Set(expected.map(q=>q.target_id)).size);
  assert.equal(r.groups.reduce((sum,g)=>sum+g.questions.length,0),expected.length);
 }
});
test('empty or missing plan does not claim completion',()=>{
 assert.equal(build(null,[],[]).ready,false);assert.equal(build({date:'2026-11-01',items:[]},[],[]).ready,false);
});
