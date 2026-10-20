function resultFinish(r,no){var f=r&&r.result&&r.result.finishers||[];for(var i=0;i<f.length;i++)if(n(f[i].horseNumber)===n(no))return n(f[i].finish);return 0}
