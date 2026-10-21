// Legacy isolated-function tests must load both sides of a Stage 3 connection.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const ac={exports:{},module:{exports:{}}};ac.module.exports=ac.exports;
vm.runInNewContext(process.binding('natives')['internal/deps/acorn/acorn/dist/acorn'],ac);
exports.connectedFunctionSource=function(source,name){
 const nodes=[];function visit(n){if(!n||typeof n!=='object')return;if(n.type==='FunctionDeclaration'&&[name,'_arvexq_original_'+name].includes(n.id.name))nodes.push(n);for(const v of Object.values(n))if(Array.isArray(v))v.forEach(visit);else if(v&&typeof v==='object')visit(v)}
 visit(ac.exports.parse(source,{ecmaVersion:'latest'}));
 const publicNode=nodes.find(n=>n.id.name===name);if(!publicNode)throw Error('missing public entry '+name);
 const declaration=source.slice(publicNode.start,publicNode.end);
 const box=/(_arvexq_box_(\d+)_call)/.exec(declaration);
 const helper=box?fs.readFileSync(path.join(__dirname,'../arvexq/components/item_'+box[2]+'/routes.js'),'utf8'):'';
 return helper+'\n'+nodes.map(n=>source.slice(n.start,n.end)).join('\n');
};
