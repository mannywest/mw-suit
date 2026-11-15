import puppeteer from 'puppeteer-core';
const [,,out,jacket,lapel,views] = process.argv;
const b = await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
const p = await b.newPage(); await p.setViewport({width:1100,height:900});
await p.goto('http://localhost:4173/',{waitUntil:'load'});
await p.waitForFunction(()=>window.__mwt,{timeout:90000});
await new Promise(r=>setTimeout(r,2500));
await p.evaluate((j,l)=>{const m=window.__mwt; if(j!=='-') m.applyFabric('jacket_body',j); if(l!=='-') m.applyFabric('jacket_lapel',l); m.setVisible&&0;},jacket,lapel);
const V={front:[[0,1.36,0.75],[0,1.30,0.1]],back:[[0,1.45,-0.45],[0,1.38,-0.02]],q:[[0.40,1.45,0.45],[0,1.34,0.05]],side:[[0.6,1.35,0.1],[0,1.33,0.02]],full:[[0,1.0,2.6],[0,0.9,0]]};
for (const v of views.split(',')){const [pos,tgt]=V[v];
 await p.evaluate((pos,tgt)=>{const m=window.__mwt;m.camera.position.set(...pos);m.controls.target.set(...tgt);m.controls.update();m.render&&m.render();},pos,tgt);
 await new Promise(r=>setTimeout(r,700));
 await p.screenshot({path:out+'_'+v+'.png',clip:{x:0,y:0,width:700,height:900}});}
await b.close();
