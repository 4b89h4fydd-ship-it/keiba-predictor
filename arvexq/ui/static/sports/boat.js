/* Isolated boat UI. Real race data is required before forecasts appear. */
(function(){
  "use strict";
  var venues=["桐生","戸田","江戸川","平和島","多摩川","浜名湖","蒲郡","常滑","津","三国","びわこ","住之江","尼崎","鳴門","丸亀","児島","宮島","徳山","下関","若松","芦屋","福岡","唐津","大村"];
  var grid=document.getElementById("boat-venue-grid"),output=document.getElementById("boat-workspace");
  if(!grid||!output)return;
  var selected="";
  function render(){
    grid.replaceChildren();
    venues.forEach(function(name){
      var button=document.createElement("button");
      button.type="button";button.textContent=name;
      button.className=selected===name?"selected":"";
      button.setAttribute("aria-pressed",String(selected===name));
      button.addEventListener("click",function(){selected=name;render()});
      grid.appendChild(button);
    });
    output.replaceChildren();
    var head=document.createElement("div");head.className="boat-workspace-title";
    var title=document.createElement("h2");title.textContent=selected?selected+"｜競艇予想":"競艇予想";
    var status=document.createElement("span");status.className="boat-status";status.textContent="データ未接続";
    head.append(title,status);
    var note=document.createElement("p");
    note.textContent=selected?"現在、"+selected+"の検証済み出走表・展示・結果は未接続です。接続後に予想印と3連単（最大6点）を表示します。":"会場を選択してください。実データが確認できるまで架空のレース、印、買い目は表示しません。";
    output.append(head,note);
  }
  render();
})();
