/* Node tools use the same ordered source manifest as runtime and static builds. */
'use strict';
const fs=require('node:fs'),path=require('node:path');
const root=path.join(__dirname,'static');
function readAppSource(){
 const names=JSON.parse(fs.readFileSync(path.join(root,'app_sources.json'),'utf8'));
 return names.map(name=>{
  const target=path.resolve(root,name);
  if(!target.startsWith(root+path.sep))throw Error('invalid app source path');
  return fs.readFileSync(target,'utf8');
 }).join('\n');
}
module.exports={readAppSource};
