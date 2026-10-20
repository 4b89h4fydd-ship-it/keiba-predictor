function paceNarrativeCards(r,p){
  var stages=[
    ['start','スタート'],
    ['turn3','3コーナー'],
    ['turn4','4コーナー'],
    ['straight','ラスト']
  ];
  return '<div class="pace-text-timeline">'+stages.map(function(z){
    return '<section class="ai-stage-event" style="margin:10px 0;padding:13px 14px;border:1px solid rgba(120,170,255,.24);border-radius:12px;background:rgba(8,18,36,.50)">'
      +'<div style="font-size:16px;font-weight:900;color:#8de9ff;margin-bottom:8px">'+z[1]+'</div>'
      +'<div style="font-size:17px;line-height:1.75;font-weight:700">'+esc(paceStageNarrative(p,z[0]))+'</div>'
      +'</section>'
  }).join('')+'</div>'
}

var PACE_STAGE_PAGES=[
  {key:'start',visualKey:'first',label:'スタート',detail:'スタート直後'},
  {key:'turn3',visualKey:'turn3',label:'3C',detail:'3コーナー'},
  {key:'turn4',visualKey:'turn4',label:'4C',detail:'4コーナー'},
  {key:'straight',visualKey:'straight',label:'ラスト',detail:'直線・決着'}
];
