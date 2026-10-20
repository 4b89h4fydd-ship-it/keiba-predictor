function actualCornerCount(r){var f=r&&r.result&&r.result.finishers||[],m=0,i;for(i=0;i<f.length;i++)m=Math.max(m,(f[i].cornerPositions||[]).length);return m}
