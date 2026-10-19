const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {createStore,KEY}=require('../web/storage.js');
const bank=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/candidates.json')));
const plan=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/study-plan.json')));
function setup({storageError=false,backend=false}={}){
 const values=new Map(),calls=[];
 const storage={getItem:key=>values.get(key)||null,setItem:(key,value)=>{if(storageError)throw new Error('quota');values.set(key,value);}};
 const options={baseURL:'https://example.test/nested/jlpt-n1-lab/web/',backend,getStorage:()=>storage,now:()=>new Date('2026-10-18T16:00:00Z'),fetch:async(url,init)=>{
  calls.push([String(url),init]);
  if(backend)return {ok:true,json:async()=>init?{saved:true}:{questions:[],attempts:[]}};
  const data=String(url).endsWith('candidates.json')?bank:plan;
  return {ok:true,json:async()=>JSON.parse(JSON.stringify(data))};
 }};
 return {values,calls,options,store:createStore(options)};
}
function attemptFor(state,date='2026-10-19'){
 const entry=state.study_plan.days.find(d=>d.date===date).items[0];
 const q=state.questions.find(q=>q.id===entry.question_id);
 return {question_id:q.id,content_hash:q.content_hash,selected_index:q.answer_index,confidence:'sure',elapsed_ms:4000,plan_date:date};
}
test('nested static URLs load the full bank without /api requests and use Tokyo date',async()=>{
 const x=setup(),s=await x.store.load();
 assert.equal(s.questions.length,360);assert.equal(s.study_plan.today,'2026-10-19');
 assert.deepEqual(x.calls.map(x=>x[0]),['https://example.test/nested/jlpt-n1-lab/data/candidates.json','https://example.test/nested/jlpt-n1-lab/data/study-plan.json']);
 assert.equal(s.study_plan.days[0].items.length,30);
});
test('attempts survive a new store instance, duplicate answers count once per date',async()=>{
 const x=setup(),s=await x.store.load(),a=attemptFor(s);
 await x.store.post('/api/attempt',a);await x.store.post('/api/attempt',a);
 const after=await createStore(x.options).load();
 assert.equal(after.attempts.length,2);assert.equal(after.study_plan.completed_slots,1);
 assert.equal(after.study_plan.days.find(d=>d.date===a.plan_date).completed_count,1);
 assert.equal(after.attempts[0].correct,1);
});
test('wrong version, unrelated date and invalid choice are rejected without saving',async()=>{
 const x=setup(),s=await x.store.load(),a=attemptFor(s);
 await assert.rejects(x.store.post('/api/attempt',{...a,content_hash:'old'}));
 await assert.rejects(x.store.post('/api/attempt',{...a,plan_date:'2026-12-08'}));
 await assert.rejects(x.store.post('/api/attempt',{...a,selected_index:4}));
 assert.equal(x.values.size,0);
});
test('feedback excludes a question, then reset restores it, without losing attempts',async()=>{
 const x=setup(),s=await x.store.load(),a=attemptFor(s);
 await x.store.post('/api/attempt',a);
 await x.store.post('/api/review',{...a,decision:'rejected',note:'测试疑问'});
 const rejected=await createStore(x.options).load();
 const day=rejected.study_plan.days.find(d=>d.date===a.plan_date);
 assert.equal(day.items.find(e=>e.question_id===a.question_id).available,false);
 await assert.rejects(x.store.post('/api/attempt',a));
 await x.store.post('/api/review',{...a,decision:'pending',note:''});
 const restored=await x.store.load();
 assert.equal(restored.study_plan.days.find(d=>d.date===a.plan_date).unavailable_count,0);
 assert.equal(restored.attempts.length,1);
});
test('old reviews do not approve changed content; records exports preserve learning data',async()=>{
 const x=setup(),s=await x.store.load(),a=attemptFor(s);
 await x.store.post('/api/attempt',a);
 await x.store.post('/api/review',{...a,decision:'approved',note:'收藏'});
 assert.equal((await x.store.exportData('approved')).data.length,1);
 const backup=await x.store.exportData('records');
 assert.equal(backup.data.reviews[0].note,'收藏');assert.equal(backup.data.attempts.length,1);
 const records=JSON.parse(x.values.get(KEY));records.reviews[a.question_id].content_hash='old';x.values.set(KEY,JSON.stringify(records));
 assert.equal((await x.store.exportData('approved')).data.length,0);
 assert.equal((await x.store.exportData('plan')).data.days.length,52);
 assert.equal((await x.store.exportData('reviewed')).data.length,360);
});
test('storage failures are surfaced and never pretend the attempt was saved',async()=>{
 const x=setup({storageError:true}),s=await x.store.load();
 await assert.rejects(x.store.post('/api/attempt',attemptFor(s)),/未能保存/);
 assert.equal(x.values.size,0);
 x.values.set(KEY,'broken-json');await assert.rejects(x.store.load(),/无法读取/);
});
test('localhost backend keeps using Python API and ignores browser records',async()=>{
 const x=setup({backend:true});
 assert.equal((await x.store.load()).storage_mode,'server');
 await x.store.post('/api/attempt',{question_id:'x'});
 await x.store.exportData('records');
 assert.deepEqual(x.calls.map(c=>c[0]),['/api/state','/api/attempt','/api/export/records']);
 assert.equal(x.values.size,0);
});
