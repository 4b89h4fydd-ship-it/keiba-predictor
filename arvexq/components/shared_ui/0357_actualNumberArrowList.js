function actualNumberArrowList(r,items){return (items||[]).map(function(it){var x=it&&it.x?it.x:it,h=horseByNo(r,x.horseNumber)||x;return badge(h)}).join('<i>→</i>')}
