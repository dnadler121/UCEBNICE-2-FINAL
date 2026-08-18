(function(){
  const state=Array.isArray(window.initialActivities)?window.initialActivities:[];
  const hidden=document.getElementById('activities_json'), builder=document.getElementById('activityBuilder'), list=document.getElementById('activityList'), bucket=document.getElementById('activityFileBucket');
  if(!hidden||!builder||!list)return;
  let selectedType=''; let fileCounter=0;
  const typeNames={cards:'🧩 Kartičky',video_find:'🎥 Zastav a ukaž',video_observe:'🎬 Pozoruj video',find_image:'🔎 Najdi na obrázku',sort:'↔️ Roztřiď',real_world:'🌱 Skutečná mise'};
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const sync=()=>hidden.value=JSON.stringify(state);
  const mediaUrl=ref=>!ref?'':(String(ref).startsWith('blob:')?ref:`/uploads/${encodeURIComponent(ref)}`);
  function newFileInput(kind,accept){const name=`pa_${kind}_${Date.now()}_${fileCounter++}`;const i=document.createElement('input');i.type='file';i.name=name;i.accept=accept;return i;}
  function moveFile(i){if(i&&i.files&&i.files.length){const d=document.createElement('div');d.style.display='none';d.appendChild(i);bucket.appendChild(d);return `__file__:${i.name}`;}return '';}
  function renderList(){list.innerHTML='';state.forEach((a,i)=>{const c=document.createElement('div');c.className='factory-qcard activity-summary';c.innerHTML=`<span class="badge-muted">${typeNames[a.type]||a.type}</span><b>${esc(a.title||'Praktická aktivita')}</b><p>${esc(a.prompt||'')}</p><small>${a.include_final?'Použije se i v „Teď to zkus sám“.':'Jen v průchodu lekcí.'}</small><button type="button" class="link-button danger">🗑️ Smazat</button>`;c.querySelector('button').onclick=()=>{state.splice(i,1);renderList();sync()};list.appendChild(c)});sync();}
  function baseFields(extra=''){builder.innerHTML=`<div class="activity-builder-grid"><label>Název aktivity<input id="paTitle" placeholder="např. Najdi skřele"></label><label class="wide">Zadání pro studenta<textarea id="paPrompt" rows="3" placeholder="Co má student udělat?"></textarea></label>${extra}<label class="checkline wide"><input type="checkbox" id="paFinal" checked> Použít tuto aktivitu také v závěrečném „Teď to zkus sám“</label><div class="wide"><button type="button" class="savebtn" id="saveActivity">+ Přidat aktivitu</button></div></div>`;}
  function setupZoneStage(imgInput, savedRef=''){
    const host=document.getElementById('zoneHost'); if(!host)return null;
    host.innerHTML='<div class="teacher-zone-stage"><img id="zoneImage"><div id="zoneBox" class="teacher-zone-box" hidden></div></div><p class="helpText">Myší táhni přes oblast, kterou má student trefit. Záměrně ji označ trochu větší.</p>';
    const stage=host.querySelector('.teacher-zone-stage'),img=host.querySelector('img'),box=host.querySelector('#zoneBox');let zone=null,start=null;
    if(savedRef)img.src=mediaUrl(savedRef);
    if(imgInput)imgInput.addEventListener('change',()=>{if(imgInput.files[0])img.src=URL.createObjectURL(imgInput.files[0])});
    stage.addEventListener('pointerdown',e=>{if(!img.src)return;const r=stage.getBoundingClientRect();start={x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height};stage.setPointerCapture(e.pointerId);});
    stage.addEventListener('pointerup',e=>{if(!start)return;const r=stage.getBoundingClientRect();const end={x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height};zone={shape:document.getElementById('zoneShape')?.value||'rect',x:Math.max(0,Math.min(start.x,end.x)),y:Math.max(0,Math.min(start.y,end.y)),w:Math.abs(end.x-start.x),h:Math.abs(end.y-start.y)};box.hidden=false;box.style.left=`${zone.x*100}%`;box.style.top=`${zone.y*100}%`;box.style.width=`${zone.w*100}%`;box.style.height=`${zone.h*100}%`;box.style.borderRadius=zone.shape==='oval'?'50%':'10px';start=null;});
    return ()=>zone;
  }
  function buildFindImage(){baseFields(`<label>Obrázek<input id="paImageSlot" type="file" accept="image/*"></label><label>Tvar správné oblasti<select id="zoneShape"><option value="rect">Obdélník</option><option value="oval">Kruh / ovál</option></select></label><div class="wide" id="zoneHost"></div>`);const inp=document.getElementById('paImageSlot');const getZone=setupZoneStage(inp);document.getElementById('saveActivity').onclick=()=>{const z=getZone();if(!inp.files[0]||!z)return alert('Nahraj obrázek a označ správnou oblast.');state.push({type:'find_image',title:paTitle.value,prompt:paPrompt.value,image:moveFile(inp),video:'',config:{zone:z},include_final:paFinal.checked});renderList();buildFindImage();};}
  function buildVideoFind(){
    baseFields(`<label>Video MP4<input id="paVideoSlot" type="file" accept="video/*"></label><label>Čas ve videu (sekundy)<input id="videoTime" type="number" min="0" step="0.1" value="8"></label><label>Tolerance času ± s<input id="videoTol" type="number" min="0.2" step="0.1" value="0.8"></label><label>Tvar správné oblasti<select id="zoneShape"><option value="rect">Obdélník</option><option value="oval">Kruh / ovál</option></select></label><div class="wide video-zone-actions"><button type="button" id="captureVideo" class="secondary-action">📸 1. Zobrazit snímek v nastaveném čase</button><button type="button" id="startVideoZone" class="primary-action" hidden>✏️ 2. Označit správnou oblast</button></div><div class="wide" id="zoneHost"></div>`);
    const inp=document.getElementById('paVideoSlot');
    const host=document.getElementById('zoneHost');
    const startBtn=document.getElementById('startVideoZone');
    let getZone=()=>null, stage=null, box=null, zone=null, drawing=false, start=null;

    function paintZone(z){
      if(!box||!z)return;
      box.hidden=false;
      Object.assign(box.style,{left:`${z.x*100}%`,top:`${z.y*100}%`,width:`${z.w*100}%`,height:`${z.h*100}%`,borderRadius:z.shape==='oval'?'50%':'10px'});
    }
    function enableDrawing(){
      if(!stage)return;
      drawing=true;
      stage.classList.add('zone-drawing-active');
      startBtn.textContent=zone?'✏️ Označit oblast znovu':'✏️ Táhni myší přes správné místo';
      const status=host.querySelector('.zone-status');
      if(status)status.textContent='Drž levé tlačítko myši, táhni přes správné místo a pusť.';
    }

    document.getElementById('captureVideo').onclick=()=>{
      if(!inp.files[0])return alert('Nejdřív vyber video.');
      const v=document.createElement('video');
      v.src=URL.createObjectURL(inp.files[0]);v.muted=true;
      v.addEventListener('loadedmetadata',()=>{v.currentTime=Math.min(Number(videoTime.value||0),Math.max(0,v.duration-.05))});
      v.addEventListener('seeked',()=>{
        const c=document.createElement('canvas');c.width=v.videoWidth||640;c.height=v.videoHeight||360;c.getContext('2d').drawImage(v,0,0,c.width,c.height);
        const url=c.toDataURL('image/png');
        host.innerHTML='<div class="teacher-zone-stage"><img id="zoneImage"><div id="zoneBox" class="teacher-zone-box" hidden></div></div><p class="helpText zone-status">Snímek je připravený. Klikni na „Označit správnou oblast“.</p>';
        stage=host.querySelector('.teacher-zone-stage');box=host.querySelector('#zoneBox');
        const img=host.querySelector('img');img.src=url;zone=null;drawing=false;start=null;
        startBtn.hidden=false;startBtn.textContent='✏️ 2. Označit správnou oblast';
        stage.onpointerdown=e=>{
          if(!drawing)return;
          e.preventDefault();
          const r=stage.getBoundingClientRect();
          start={x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height};
        };
        stage.onpointerup=e=>{
          if(!drawing||!start)return;
          e.preventDefault();
          const r=stage.getBoundingClientRect(),end={x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height};
          zone={shape:zoneShape.value,x:Math.min(start.x,end.x),y:Math.min(start.y,end.y),w:Math.abs(end.x-start.x),h:Math.abs(end.y-start.y)};
          start=null;drawing=false;stage.classList.remove('zone-drawing-active');paintZone(zone);
          startBtn.textContent='✏️ Označit oblast znovu';
          const status=host.querySelector('.zone-status');
          if(status)status.textContent='✓ Správná oblast je označená. Student zelený rámeček neuvidí.';
        };
        getZone=()=>zone;
      });
    };
    startBtn.onclick=enableDrawing;
    document.getElementById('saveActivity').onclick=()=>{
      const z=getZone();
      if(!inp.files[0]||!z)return alert('Vyber video, zobraz snímek a tlačítkem „Označit správnou oblast“ vyznač místo, které má student najít.');
      state.push({type:'video_find',title:paTitle.value,prompt:paPrompt.value,image:'',video:moveFile(inp),config:{time:Number(videoTime.value||0),tolerance:Number(videoTol.value||.8),zone:z},include_final:paFinal.checked});
      renderList();buildVideoFind();
    };
  }
  function buildVideoObserve(){baseFields(`<label>Video<input id="paVideoSlot" type="file" accept="video/*"></label><label class="wide">Možnosti odpovědi – každá na nový řádek<textarea id="observeOptions" rows="5"></textarea></label><label>Číslo správné odpovědi<input id="observeCorrect" type="number" min="1" value="1"></label>`);const inp=document.getElementById('paVideoSlot');document.getElementById('saveActivity').onclick=()=>{const ops=observeOptions.value.split('\n').map(x=>x.trim()).filter(Boolean);if(!inp.files[0]||ops.length<2)return alert('Vyber video a napiš alespoň dvě možnosti.');state.push({type:'video_observe',title:paTitle.value,prompt:paPrompt.value,image:'',video:moveFile(inp),config:{options:ops,correct:Math.max(0,Number(observeCorrect.value||1)-1)},include_final:paFinal.checked});renderList();buildVideoObserve();};}
  function buildSort(){baseFields(`<label class="wide">Kategorie – odděl čárkou<input id="sortCats" placeholder="Živé, Neživé"></label><label class="wide">Položky – každý řádek ve tvaru položka | kategorie<textarea id="sortItems" rows="7" placeholder="strom | Živé\nkámen | Neživé"></textarea></label>`);document.getElementById('saveActivity').onclick=()=>{const cats=sortCats.value.split(',').map(x=>x.trim()).filter(Boolean);const rows=sortItems.value.split('\n').map(x=>x.trim()).filter(Boolean);const items=[];for(const r of rows){const [label,cat]=r.split('|').map(x=>x.trim());const idx=cats.findIndex(x=>x.toLowerCase()===String(cat).toLowerCase());if(label&&idx>=0)items.push({label,category:idx});}if(cats.length<2||items.length<2)return alert('Doplň alespoň dvě kategorie a položky se správnou kategorií.');state.push({type:'sort',title:paTitle.value,prompt:paPrompt.value,image:'',video:'',config:{categories:cats,items},include_final:paFinal.checked});renderList();buildSort();};}
  function buildMission(){baseFields(`<label>Kolik různých znaků musí napsat<input id="missionMin" type="number" min="1" value="3"></label><label class="wide">Uznávané významy – každý znak na nový řádek, podobné kořeny odděl |<textarea id="missionConcepts" rows="7" placeholder="rost|růst|zvětš\ndych|dých\nživin|výživ|vodu\nreag|světlo\nrozmnož"></textarea></label>`);document.getElementById('saveActivity').onclick=()=>{const concepts=missionConcepts.value.split('\n').map(x=>x.split('|').map(y=>y.trim()).filter(Boolean)).filter(x=>x.length);const min=Number(missionMin.value||3);if(concepts.length<min)return alert('Doplň alespoň tolik různých uznávaných znaků, kolik má student napsat.');state.push({type:'real_world',title:paTitle.value,prompt:paPrompt.value,image:'',video:'',config:{min_items:min,concepts},include_final:paFinal.checked});renderList();buildMission();};}
  function buildCards(){
    baseFields(`<label class="wide">Typ kartiček<select id="cardMode"><option value="categories">Přetahování do kategorií (bez obrázku)</option><option value="image">Skládání do obrázku</option></select></label><div class="wide" id="cardModeFields"></div>`);
    const host=document.getElementById('cardModeFields');
    function categoriesMode(){
      host.innerHTML=`<label class="wide">Kategorie – odděl čárkou<input id="cardCats" placeholder="Znaky života, Není znak života"></label><label class="wide">Kartičky – každý řádek ve tvaru kartička | kategorie<textarea id="cardCatItems" rows="9" placeholder="Roste a vyvíjí se | Znaky života\nMusí být zelené | Není znak života"></textarea></label><p class="helpText wide">Obrázek není potřeba. Student přetahuje kartičky do správných oblastí.</p>`;
      document.getElementById('saveActivity').onclick=()=>{
        const cats=cardCats.value.split(',').map(x=>x.trim()).filter(Boolean);
        const rows=cardCatItems.value.split('\n').map(x=>x.trim()).filter(Boolean),items=[];
        for(const r of rows){const parts=r.split('|').map(x=>x.trim()),label=parts[0],cat=parts[1];const idx=cats.findIndex(x=>x.toLowerCase()===String(cat||'').toLowerCase());if(label&&idx>=0)items.push({label,category:idx});}
        if(cats.length<2||items.length<2)return alert('Doplň alespoň dvě kategorie a kartičky ve tvaru kartička | kategorie.');
        state.push({type:'cards',title:paTitle.value,prompt:paPrompt.value,image:'',video:'',config:{mode:'categories',categories:cats,items},include_final:paFinal.checked});renderList();buildCards();
      };
    }
    function imageMode(){
      host.innerHTML=`<label>Podkladový obrázek<input id="paImageSlot" type="file" accept="image/*"></label><label class="wide">Názvy kartiček – odděl čárkou<input id="cardLabels" placeholder="jádro, membrána, cytoplazma"></label><div class="wide"><button type="button" id="prepareCards" class="secondary-action">Připravit označování míst</button></div><label>Právě označuji<select id="cardSelect"></select></label><label>Tvar oblasti<select id="zoneShape"><option value="rect">Obdélník</option><option value="oval">Kruh / ovál</option></select></label><div class="wide" id="zoneHost"></div>`;
      const inp=document.getElementById('paImageSlot'),zones={};
      document.getElementById('prepareCards').onclick=()=>{const labels=cardLabels.value.split(',').map(x=>x.trim()).filter(Boolean);if(!inp.files[0]||!labels.length)return alert('Vyber obrázek a napiš názvy kartiček.');cardSelect.innerHTML=labels.map((x,i)=>`<option value="${i}">${esc(x)}</option>`).join('');const zh=document.getElementById('zoneHost');zh.innerHTML='<div class="teacher-zone-stage"><img><div class="teacher-zone-box" hidden></div></div><p class="helpText">Vyber kartičku nahoře a myší označ její správné místo. Postupně označ všechny.</p>';const stage=zh.querySelector('.teacher-zone-stage'),img=zh.querySelector('img'),box=zh.querySelector('.teacher-zone-box');img.src=URL.createObjectURL(inp.files[0]);let start=null;stage.onpointerdown=e=>{const r=stage.getBoundingClientRect();start={x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height}};stage.onpointerup=e=>{if(!start)return;const r=stage.getBoundingClientRect(),end={x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height};const z={shape:zoneShape.value,x:Math.min(start.x,end.x),y:Math.min(start.y,end.y),w:Math.abs(end.x-start.x),h:Math.abs(end.y-start.y)};zones[cardSelect.value]=z;box.hidden=false;Object.assign(box.style,{left:`${z.x*100}%`,top:`${z.y*100}%`,width:`${z.w*100}%`,height:`${z.h*100}%`,borderRadius:z.shape==='oval'?'50%':'10px'});};cardSelect.onchange=()=>{const z=zones[cardSelect.value];box.hidden=!z;if(z)Object.assign(box.style,{left:`${z.x*100}%`,top:`${z.y*100}%`,width:`${z.w*100}%`,height:`${z.h*100}%`,borderRadius:z.shape==='oval'?'50%':'10px'});};};
      document.getElementById('saveActivity').onclick=()=>{const labels=cardLabels.value.split(',').map(x=>x.trim()).filter(Boolean);if(!inp.files[0]||!labels.length||labels.some((_,i)=>!zones[i]))return alert('Nahraj obrázek a označ správné místo pro každou kartičku.');state.push({type:'cards',title:paTitle.value,prompt:paPrompt.value,image:moveFile(inp),video:'',config:{mode:'image',cards:labels.map((label,i)=>({label,zone:zones[i]}))},include_final:paFinal.checked});renderList();buildCards();};
    }
    cardMode.onchange=()=>cardMode.value==='image'?imageMode():categoriesMode(); categoriesMode();
  }
  function build(type){selectedType=type;if(type==='find_image')buildFindImage();else if(type==='video_find')buildVideoFind();else if(type==='video_observe')buildVideoObserve();else if(type==='sort')buildSort();else if(type==='real_world')buildMission();else if(type==='cards')buildCards();}
  document.querySelectorAll('[data-activity-type]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-activity-type]').forEach(x=>x.classList.remove('sel'));b.classList.add('sel');build(b.dataset.activityType)}));
  document.getElementById('lessonEditorForm')?.addEventListener('submit',sync);
  document.getElementById('downloadAiBrief')?.addEventListener('click',()=>{
    const form=document.getElementById('lessonEditorForm');const val=n=>form.querySelector(`[name="${n}"]`)?.value||'';
    const rows=[['field','value'],['subject',val('subject')],['grade',val('grade')],['topic',val('block')],['lesson_title',val('title')],['questions',document.getElementById('briefQuestions')?.value||0]];
    document.querySelectorAll('[data-brief]').forEach(i=>rows.push([`activity_${i.dataset.brief}`,i.value||0]));
    const csv=rows.map(r=>r.map(v=>`"${String(v).replace(/"/g,'""')}"`).join(',')).join('\n');const blob=new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`zadani_lekce_${(val('title')||'nova').replace(/[^a-z0-9ěščřžýáíéúůďťň-]+/gi,'_')}.csv`;a.click();URL.revokeObjectURL(a.href);
  });
  renderList();
})();
