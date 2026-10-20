function smartLiveRaceSection(){
  if(state.date!==today())return'';
  var now=nowMins(),central=smartLiveCircuitGroup('中央','中央',now),local=smartLiveCircuitGroup('地方','地方',now),body=central+local;
  return '<section class="smart-live-section"><div class="smart-live-heading"><b>リアルタイム</b><small>各会場から1レース</small></div>'+
    (body||'<div class="smart-live-empty">現在の対象レースはありません</div>')+
  '</section>'
}
var ARVEXQ_LOCAL_LIVE_SLUG={"帯広":"obihiro","門別":"monbetsu","盛岡":"morioka","水沢":"mizusawa","浦和":"urawa","船橋":"funabashi","大井":"ooi","川崎":"kawasaki","金沢":"kanazawa","笠松":"kasamatsu","名古屋":"nagoya","園田":"sonoda","姫路":"himeji","高知":"kouchi","佐賀":"saga"};
var ARVEXQ_JRA_YOUTUBE_CHANNEL='UCj6AKkCWS6FJqf0o5wP45eQ';
