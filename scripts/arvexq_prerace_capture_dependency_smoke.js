const assert=require('node:assert/strict'),fs=require('node:fs');
const app=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const boot="installNavigation();installEdgeBack();installPullRefresh();installPwaCache();evictRetiredRaceCaches();normalizeInitialAppLaunch();restoreLocation();setTimeout(load,0);";
assert(app.includes(boot),'current boot anchor must be checked');
for(const file of ['scripts/arvexq_capture_prerace_bet.js','scripts/arvexq_capture_course_revised_marks.js']){
 const script=fs.readFileSync(file,'utf8');
 assert(script.includes(boot),file+' uses retired boot');
 for(const old of ['podium_axis_guard.js','legacy_v213_order_model.js','three_way_engine.js']){
  assert(!script.includes(old),file+' still loads retired '+old);
 }
}
assert(app.includes('function assignPredictionMarks('));
assert(app.includes('function buildAiBetPlan('));
console.log('PRESALE_CAPTURE_CURRENT_MODULES_OK');
