const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
test('reliability stays concise, honest and leaves data unchanged',()=>{
 const source=fs.readFileSync(path.join(__dirname,'../app/web/operator.js'),'utf8');
 const code=source.slice(source.indexOf('const forecastReliabilityLabel ='),source.indexOf('const clampPercent ='));
 let label;
 const render=vm.runInNewContext(code+'\nrenderForecastAccuracyHistory;', {setText:(id,text)=>{label=text;}});
 for(const value of [null,{}, {state:'unavailable'}, {state:'unknown'}]) {
   render(value); assert.equal(label,'Forecast reliability: Unavailable');
 }
 for(const state of ['building','ready_for_calibration']) {
   const data={state,nightly:{completed_nights:100,horizons:[{count:100,review_ready:true,within_10:100}],nights:[{night:'private-date'}]}};
   const before=JSON.stringify(data); render(data);
   assert.equal(label,'Forecast reliability: Still being assessed');
   assert.equal(JSON.stringify(data),before);
   assert.doesNotMatch(label,/100|private-date|reliable|%|pending/i);
 }
});
