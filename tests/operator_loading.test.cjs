const {test} = require('node:test');
const assert = require('node:assert/strict');
const {createLoadCoordinator} = require('../app/web/loading.js');
test('stages follow responses, including out-of-order and partial failures', async () => {
  let snapshot;
  const loader = createLoadCoordinator(run => snapshot = {...run.stages});
  const run=loader.begin({Plan:'waiting', History:'waiting'});
  let finish;
  const plan=run.request('Plan',()=>new Promise(resolve=>finish=resolve));
  await assert.rejects(run.request('History',()=>Promise.reject(new Error('Unavailable'))));
  assert.deepEqual(snapshot,{Plan:'loading',History:'error'});
  finish(42); assert.equal(await plan,42);
  assert.deepEqual(snapshot,{Plan:'done',History:'error'});
});
test('retry aborts old work and ignores late completion', async () => {
  let snapshot, finish;
  const loader=createLoadCoordinator(run=>snapshot={...run.stages});
  const old=loader.begin({Plan:'waiting'});
  const pending=old.request('Plan',()=>new Promise(resolve=>finish=resolve));
  const rejection=assert.rejects(pending);
  const next=loader.begin({Plan:'waiting'},true);
  await rejection;
  finish('old');
  assert.equal(old.current(),false);
  assert.deepEqual(snapshot,{Plan:'waiting'});
  assert.equal(next.retained,true);
});
test('timeout bounds a hung request and allows retry', async()=>{
  const loader=createLoadCoordinator(()=>{},10);
  const run=loader.begin({Plan:'waiting'});
  await assert.rejects(run.request('Plan',()=>new Promise(()=>{})),/try again/);
  assert.equal(run.stages.Plan,'error');
  const next=loader.begin({Plan:'waiting'});
  assert.equal(await next.request('Plan',async()=>23),23);
});
test('cancel prevents updates after sign-out', async()=>{
  let count=0;
  const loader=createLoadCoordinator(()=>count++);
  const run=loader.begin({Plan:'waiting'});
  loader.cancel();
  run.finish('failure'); run.update('Plan','done');
  assert.equal(count,1);
});
