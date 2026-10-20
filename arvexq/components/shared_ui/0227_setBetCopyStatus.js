function setBetCopyStatus(msg){var el=document.getElementById('bet-copy-status');if(el){el.textContent=msg;el.classList.add('show');setTimeout(function(){if(el)el.classList.remove('show')},1800)}}
