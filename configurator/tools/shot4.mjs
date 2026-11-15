import puppeteer from 'puppeteer-core';
const [,,out,lapelFab,styleArg='peak'] = process.argv;
const b = await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
const p = await b.newPage(); await p.setViewport({width:1100,height:900});
await p.goto('http://localhost:4173/',{waitUntil:'load'});
await p.waitForFunction(()=>window.__mwt,{timeout:90000});
await new Promise(r=>setTimeout(r,2500));
await p.evaluate((f,st)=>{const m=window.__mwt;m.applyFabric('jacket_lapel',f);m.setLapelStyle(st);},lapelFab,styleArg);
const V={
 front:[[0,1.30,1.0],[0,1.25,0.1]],
 q:[[0.45,1.42,0.45],[0,1.34,0.05]],
 peakL:[[-0.20,1.46,0.30],[-0.12,1.40,0.06]],
 peakR:[[0.20,1.46,0.30],[0.12,1.40,0.06]],
 over:[[0,1.95,0.12],[0,1.35,0.04]],
 backhi:[[0.12,1.62,-0.42],[0,1.38,0.0]],
 side:[[0.55,1.40,0.12],[0,1.36,0.06]],
 full:[[0,1.0,2.7],[0,0.9,0]],
};
for (const v of Object.keys(V)){const [pos,tgt]=V[v];
 await p.evaluate((pos,tgt)=>{const m=window.__mwt;m.camera.position.set(...pos);m.controls.target.set(...tgt);m.controls.update();m.render();},pos,tgt);
 await new Promise(r=>setTimeout(r,600));
 await p.screenshot({path:out+'_'+v+'.png',clip:{x:0,y:0,width:780,height:900}});}
await b.close();
