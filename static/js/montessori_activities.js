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
    const video=card.querySelector('video');
    const freeze=card.querySelector('.freeze-video');
    const stage=card.querySelector('.video-freeze-stage');
    const canvas=stage?.querySelector('canvas');
    const layer=stage?.querySelector('.click-layer');
    const hint=card.querySelector('.target-time');
    const targetTime=Math.max(0,Number(cfg.time||0));
    let frameReady=false;

    if(hint) hint.textContent=new Date(targetTime*1000).toISOString().substring(14,19);
    if(!video||!freeze||!stage||!canvas||!layer) return;

    function clearMarker(){
      stage.querySelectorAll('.video-click-marker').forEach(el=>el.remove());
    }

    function showMarker(p){
      clearMarker();
      const marker=document.createElement('span');
      marker.className='video-click-marker';
      marker.style.left=`${p.x*100}%`;
      marker.style.top=`${p.y*100}%`;
      stage.appendChild(marker);
    }

    function captureTeacherFrame(){
      const w=video.videoWidth||640, h=video.videoHeight||360;
      canvas.width=w; canvas.height=h;
      canvas.getContext('2d').drawImage(video,0,0,w,h);
      stage.hidden=false;
      frameReady=true;
      layer.disabled=false;
      freeze.disabled=false;
      freeze.textContent='↻ Zobrazit snímek znovu';
    }

    function seekAndFreeze(){
      frameReady=false;
      layer.disabled=true;
      freeze.disabled=true;
      freeze.textContent='⏳ Připravuji snímek…';
      clearMarker();
      video.pause();

      const maxTime=Number.isFinite(video.duration) && video.duration>0
        ? Math.max(0,Math.min(targetTime,Math.max(0,video.duration-0.01)))
        : targetTime;

      const finish=()=>{
        video.pause();
        captureTeacherFrame();
      };

      // Pokud jsme už přesně na požadovaném čase, seeked se nemusí vyvolat.
      if(Math.abs(video.currentTime-maxTime)<0.015 && video.readyState>=2){
        finish();
        return;
      }

      video.addEventListener('seeked',finish,{once:true});
      // currentTime použijeme záměrně místo fastSeek: potřebujeme co nejpřesnější snímek,
      // ne pouze nejbližší keyframe videa.
      video.currentTime=maxTime;
    }

    freeze.addEventListener('click',()=>{
      if(video.readyState<1){
        freeze.disabled=true;
        freeze.textContent='⏳ Načítám video…';
        video.addEventListener('loadedmetadata',seekAndFreeze,{once:true});
        return;
      }
      seekAndFreeze();
    });

    layer.addEventListener('click',ev=>{
      if(!frameReady) return;
      const p=pctPoint(ev,stage);
      showMarker(p);
      // Kontrola vždy používá přesný čas nastavený učitelem, ne náhodný čas přehrávače.
      check(card,{time:targetTime,x:p.x,y:p.y});
    });
  }
  function initVideoObserve(card,cfg){
    const box=card.querySelector('.observe-options'); if(!box) return;
    (cfg.options||[]).forEach((op,i)=>{const b=document.createElement('button');b.type='button';b.className='observe-option';b.textContent=op;b.onclick=()=>check(card,{selected:i});box.appendChild(b);});
  }
  function initCards(card,cfg){
    const bank=card.querySelector('.cards-bank'); if(!bank)return;
    if(cfg.mode==='categories'){
      const zones=card.querySelector('.cards-category-zones'),assignments={}; if(!zones)return;
      (cfg.categories||[]).forEach((name,idx)=>{const z=document.createElement('div');z.className='sort-zone';z.dataset.category=idx;z.innerHTML=`<h3>${name}</h3><div class="sort-drop"></div>`;zones.appendChild(z);});
      (cfg.items||[]).forEach((it,idx)=>{const b=document.createElement('button');b.type='button';b.className='drag-card';b.textContent=it.label||it;b.draggable=true;b.dataset.card=idx;b.addEventListener('dragstart',e=>e.dataTransfer.setData('text/plain',String(idx)));bank.appendChild(b);});
      card.querySelectorAll('.sort-zone').forEach(z=>{z.addEventListener('dragover',e=>e.preventDefault());z.addEventListener('drop',e=>{e.preventDefault();const idx=e.dataTransfer.getData('text/plain'),chip=card.querySelector(`.drag-card[data-card="${idx}"]`);if(chip){z.querySelector('.sort-drop').appendChild(chip);assignments[idx]=Number(z.dataset.category);}});});
      card.querySelector('.check-activity')?.addEventListener('click',()=>check(card,{assignments})); return;
    }
    const targets=card.querySelector('.image-card-targets'); if(!targets)return;
    const assignments={};
    const items=(cfg.cards||[]).map((it,idx)=>({it,idx}));
    // Zamícháme pouze nabídku obrázků; cíle zůstávají očíslované 1..N.
    items.sort(()=>Math.random()-.5).forEach(({it,idx})=>{
      const tile=document.createElement('div');tile.className='image-drag-card';tile.draggable=true;tile.dataset.card=idx;
      const img=document.createElement('img');img.alt='Obrázek k přiřazení';img.src=`/activity-media/${encodeURIComponent(card.dataset.activityId)}/card/${idx}`;tile.appendChild(img);
      tile.addEventListener('dragstart',e=>e.dataTransfer.setData('text/plain',String(idx)));bank.appendChild(tile);
    });
    (cfg.cards||[]).forEach((it,idx)=>{
      const z=document.createElement('div');z.className='image-card-target';z.dataset.target=idx;
      z.innerHTML=`<div class="image-target-title"><span class="image-target-number">${idx+1}</span><b>${it.label||''}</b></div><div class="image-target-drop">Sem přetáhni obrázek</div>`;targets.appendChild(z);
      z.addEventListener('dragover',e=>e.preventDefault());z.addEventListener('drop',e=>{
        e.preventDefault();const cardIdx=Number(e.dataTransfer.getData('text/plain'));const tile=card.querySelector(`.image-drag-card[data-card="${cardIdx}"]`);if(!tile)return;
        if(cardIdx!==idx){z.classList.add('wrong-drop');setTimeout(()=>z.classList.remove('wrong-drop'),650);return;}
        z.querySelector('.image-target-drop').innerHTML='';z.querySelector('.image-target-drop').appendChild(tile);z.classList.add('correct-drop');assignments[String(cardIdx)]=idx;
      });
    });
    card.querySelector('.check-activity')?.addEventListener('click',()=>check(card,{assignments}));
  }
  function initMission(card,cfg){
    const box=card.querySelector('.mission-answers'); if(!box)return; const n=Math.max(1,Number(cfg.min_items||3));
    for(let i=0;i<n;i++){const inp=document.createElement('textarea');inp.rows=2;inp.placeholder=`${i+1}. znak / zjištění`;box.appendChild(inp);}
    card.querySelector('.check-activity')?.addEventListener('click',()=>check(card,{answers:Array.from(box.querySelectorAll('textarea')).map(x=>x.value)}));
  }
  function init(card){
    let cfg={};try{cfg=JSON.parse(card.dataset.config||'{}')}catch(e){}
    const typ=card.dataset.activityType;
    if(typ==='find_image')initFindImage(card,cfg); else if(typ==='video_find')initVideoFind(card,cfg); else if(typ==='video_observe')initVideoObserve(card,cfg); else if(typ==='cards')initCards(card,cfg); else if(typ==='real_world')initMission(card,cfg);
  }
  document.addEventListener('DOMContentLoaded',()=>document.querySelectorAll('.practical-card').forEach(init));
})();
