import puppeteer from 'puppeteer-core';
const [,,out] = process.argv;
const b = await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
const p = await b.newPage(); await p.setViewport({width:1100,height:900});
await p.goto('http://localhost:4173/',{waitUntil:'load'});
await p.waitForFunction(()=>window.__mwt,{timeout:90000});
await new Promise(r=>setTimeout(r,2500));
const cam=[[0,1.36,0.75],[0,1.30,0.1]];
for (const st of ['notch','peak']) {
  await p.evaluate((st,cam)=>{const m=window.__mwt;m.applyFabric('jacket_lapel','satin-black');m.setLapelStyle(st);m.camera.position.set(...cam[0]);m.controls.target.set(...cam[1]);m.controls.update();m.render();},st,cam);
  await new Promise(r=>setTimeout(r,700));
  await p.screenshot({path:out+'_'+st+'.png'});
}
// click the Peak button in the panel to test UI
await p.evaluate(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent==='Notch lapel');b&&b.click();});
await new Promise(r=>setTimeout(r,500));
const vis=await p.evaluate(()=>Object.entries(window.__mwt.meshes).map(([k,m])=>k+':'+m.visible).join(' '));
console.log(vis);
await p.screenshot({path:out+'_ui.png'});
await b.close();
