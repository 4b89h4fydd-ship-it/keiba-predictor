function yieldFlex(h,r){var rs=historicalWindow(h,r),w=recencyWeights(rs.length),e=0,g=0,i,p,a,fin,ww;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];a=n(p[0]);fin=n(rs[i].finish);if(!a||a===1||a>5)continue;ww=w[i];e+=ww;if(fin>0&&fin<=4)g+=ww}return e?g/e:.45}

