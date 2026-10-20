function smartTodayReturn(){
  if(!shouldShowTodayReturn())return '';
  return '<button type="button" class="smart-today-return" data-action="today-return" aria-label="今日のレースへ戻る"><span>↩</span><b>今日へ</b></button>'
}
