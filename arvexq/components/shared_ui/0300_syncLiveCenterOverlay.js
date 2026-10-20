function syncLiveCenterOverlay(){
  var existing=document.querySelector('body > .live-center-overlay');
  if(!liveCenterOpen){if(existing)existing.remove();return}
  var key='direct';
  if(existing&&existing.getAttribute('data-live-key')===key)return; // keep the LIVE menu state alive
  if(existing)existing.remove();
  var box=document.createElement('div');box.innerHTML=liveCenterModal();
  var node=box.firstElementChild;if(node)document.body.appendChild(node)
}
