const v=require('gltf-validator'),fs=require('fs');
const f=process.argv[2];
v.validateBytes(new Uint8Array(fs.readFileSync(f)),{maxIssues:200}).then(r=>{
 const s=r.issues;console.log(f.split('/').pop(),'errors',s.numErrors,'warnings',s.numWarnings,'infos',s.numInfos,'hints',s.numHints);
 const c={};for(const m of s.messages){const k=['E','W','I','H'][m.severity]+' '+m.code;c[k]=(c[k]||0)+1}console.log(c);});
