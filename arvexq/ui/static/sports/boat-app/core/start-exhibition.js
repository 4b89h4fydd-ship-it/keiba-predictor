// SMALL: strictly validate a verified start exhibition snapshot, without guessing course or ST.
export function validStartExhibition(race){
  const x=race&&race.startExhibition;
  if(!x||x.verified!==true||x.source!=="BOATRACE公式"||!Array.isArray(x.rows)||x.rows.length!==6)return null;
  if(!Number.isFinite(Date.parse(x.observedAt||"")))return null;
  const seenBoats=new Set(),seenCourses=new Set(),rows=[];
  for(const item of x.rows){
    const boat=Number(item&&item.boatNo),course=Number(item&&item.course);
    if(!Number.isInteger(boat)||boat<1||boat>6||!Number.isInteger(course)||course<1||course>6||
       seenBoats.has(boat)||seenCourses.has(course))return null;
    // Official timing texts include F.03 and .00. Do not turn F into a normal time.
    const st=String(item.st??"").trim().toUpperCase();
    if(!/^(?:F|L)?\.(?:\d{2})$/.test(st))return null;
    seenBoats.add(boat);seenCourses.add(course);
    rows.push({boatNo:boat,course,st});
  }
  return {rows:rows.sort((a,b)=>a.course-b.course),observedAt:x.observedAt,source:x.source};
}
