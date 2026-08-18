(function(){
  function pctPoint(ev, stage){
    const r=stage.getBoundingClientRect();
    return {x:(ev.clientX-r.left)/r.width, y:(ev.clientY-r.top)/r.height};
  }
  async function check(card, answer){
    const fb=card.querySelector('.activity-feedback');
    const res=await fetch('/api/activity-check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({activity_id:Number(card.dataset.activityId),context:card.dataset.context||'study',answer})});
    const data=await res.json();
    fb.textContent=data.message || (data.ok?'Správně.':'Ještě ne.');
    fb.className='feedback activity-feedback '+(data.ok?'ok':'bad');
    if(data.ok){
      card.dataset.completed='1'; card.classList.add('completed-item');
      card.dispatchEvent(new CustomEvent('activity-completed',{bubbles:true,detail:data}));
    }
    if(data.progress) document.dispatchEvent(new CustomEvent('final-progress',{detail:data.progress}));
    return data;
  }
  function initFindImage(card){
    const stage=card.querySelector('.image-stage'); const layer=stage?.querySelector('.click-layer');
    if(!stage||!layer) return;
    layer.addEventListener('click',ev=>{const p=pctPoint(ev,stage); check(card,p);});
  }
  function initVideoFind(card,cfg){
    const video=card.querySelector('video'); const freeze=card.querySelector('.freeze-video'); const stage=card.querySelector('.video-freeze-stage'); const canvas=stage?.querySelector('canvas'); const layer=stage?.querySelector('.click-layer');
    const hint=card.querySelector('.target-time'); if(hint) hint.textContent=new Date((Number(cfg.time||0))*1000).toISOString().substring(14,19);
    if(!video||!freeze||!stage||!canvas||!layer) return;
    freeze.addEventListener('click',()=>{
      video.pause(); const w=video.videoWidth||640,h=video.videoHeight||360; canvas.width=w;canvas.height=h; canvas.getContext('2d').drawImage(video,0,0,w,h); stage.hidden=false;
    });
    layer.addEventListener('click',ev=>{const p=pctPoint(ev,stage); check(card,{time:video.currentTime,x:p.x,y:p.y});});
  }
  function initVideoObserve(card,cfg){
    const box=card.querySelector('.observe-options'); if(!box) return;
    (cfg.options||[]).forEach((op,i)=>{const b=document.createElement('button');b.type='button';b.className='observe-option';b.textContent=op;b.onclick=()=>check(card,{selected:i});box.appendChild(b);});
  }
  function initSort(card,cfg){
    const bank=card.querySelector('.sort-bank'), zones=card.querySelector('.sort-zones'); if(!bank||!zones) return;
    const assignments={};
    (cfg.categories||[]).forEach((name,idx)=>{const z=document.createElement('div');z.className='sort-zone';z.dataset.category=idx;z.innerHTML=`<h3>${name}</h3><div class="sort-drop"></div>`;zones.appendChild(z);});
    (cfg.items||[]).forEach((it,idx)=>{const b=document.createElement('button');b.type='button';b.className='sort-chip';b.textContent=it.label||it;b.draggable=true;b.dataset.item=idx;b.addEventListener('dragstart',e=>e.dataTransfer.setData('text/plain',String(idx)));bank.appendChild(b);});
    card.querySelectorAll('.sort-zone').forEach(z=>{z.addEventListener('dragover',e=>e.preventDefault());z.addEventListener('drop',e=>{e.preventDefault();const idx=e.dataTransfer.getData('text/plain');const chip=card.querySelector(`.sort-chip[data-item="${idx}"]`);if(chip){z.querySelector('.sort-drop').appendChild(chip);assignments[idx]=Number(z.dataset.category);}});});
    card.querySelector('.check-activity')?.addEventListener('click',()=>check(card,{assignments}));
  }
  function initCards(card,cfg){
    const bank=card.querySelector('.cards-bank'),stage=card.querySelector('.cards-image-stage'),overlay=card.querySelector('.card-drop-overlay'); if(!bank||!stage||!overlay)return;
    const placements={};
    (cfg.cards||[]).forEach((it,idx)=>{const b=document.createElement('button');b.type='button';b.className='drag-card';b.textContent=it.label||`Kartička ${idx+1}`;b.draggable=true;b.dataset.card=idx;b.addEventListener('dragstart',e=>e.dataTransfer.setData('text/plain',String(idx)));bank.appendChild(b);});
    stage.addEventListener('dragover',e=>e.preventDefault());stage.addEventListener('drop',e=>{e.preventDefault();const idx=e.dataTransfer.getData('text/plain');const p=pctPoint(e,stage);placements[idx]=p;const old=overlay.querySelector(`[data-placement="${idx}"]`);if(old)old.remove();const tag=document.createElement('span');tag.className='placed-card';tag.dataset.placement=idx;tag.textContent=(cfg.cards?.[Number(idx)]?.label)||'';tag.style.left=`${p.x*100}%`;tag.style.top=`${p.y*100}%`;overlay.appendChild(tag);});
    card.querySelector('.check-activity')?.addEventListener('click',()=>check(card,{placements}));
  }
  function initMission(card,cfg){
    const box=card.querySelector('.mission-answers'); if(!box)return; const n=Math.max(1,Number(cfg.min_items||3));
    for(let i=0;i<n;i++){const inp=document.createElement('textarea');inp.rows=2;inp.placeholder=`${i+1}. znak / zjištění`;box.appendChild(inp);}
    card.querySelector('.check-activity')?.addEventListener('click',()=>check(card,{answers:Array.from(box.querySelectorAll('textarea')).map(x=>x.value)}));
  }
  function init(card){
    let cfg={};try{cfg=JSON.parse(card.dataset.config||'{}')}catch(e){}
    const typ=card.dataset.activityType;
    if(typ==='find_image')initFindImage(card,cfg); else if(typ==='video_find')initVideoFind(card,cfg); else if(typ==='video_observe')initVideoObserve(card,cfg); else if(typ==='sort')initSort(card,cfg); else if(typ==='cards')initCards(card,cfg); else if(typ==='real_world')initMission(card,cfg);
  }
  document.addEventListener('DOMContentLoaded',()=>document.querySelectorAll('.practical-card').forEach(init));
})();
