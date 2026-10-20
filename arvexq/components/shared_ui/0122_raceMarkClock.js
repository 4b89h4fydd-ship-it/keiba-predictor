function raceMarkClock(r){
  var date=String(r&&r.date||''),post=mins(r&&r.startTime),current=today(),
      status=String(r&&r.raceStatus||''),
      resultPublished=isFinal(r)||isFlash(r)||hasAnyResultData(r)||
        /^(?:発走済|発走中|発走$|進行中|確定|速報|終了)/.test(status);
  return {valid:!!date&&post<9999,
    started:resultPublished||!!date&&(date<current||(date===current&&post<9999&&nowMins()>=post)),
    remaining:date===current?post-nowMins():9999};
}
// Retired v345 device-only frozen marks are not loaded or written by this UI.
// Server-side pre-off receipts remain available for historical audit.
// Server archive is trusted only with evidence of a genuine pre-off capture.
