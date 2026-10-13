const assert=require('node:assert/strict'),fs=require('node:fs');
const app=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const course=fs.readFileSync('scripts/arvexq_capture_course_revised_marks.js','utf8');
const boot="installNavigation();installEdgeBack();installPullRefresh();installPwaCache();evictRetiredRaceCaches();normalizeInitialAppLaunch();restoreLocation();setTimeout(load,0);";
assert(app.includes(boot));
assert(course.includes(boot));
assert(!course.includes('podium_axis_guard.js'),'deleted role guard must not be loaded');
assert(course.includes('vm.runInContext(source,'));
console.log('COURSE_MARK_CAPTURE_CURRENT_PREDICTOR_OK');
