function horseCheckMap(r){try{var raw=localStorage.getItem(horseCheckKey(r));var obj=raw?JSON.parse(raw):{};return obj&&typeof obj==='object'?obj:{}}catch(e){return{}}}
