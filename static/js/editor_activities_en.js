(function(){
  const state=Array.isArray(window.initialActivitiesEn)?window.initialActivitiesEn:[];
  const hidden=document.getElementById('activities_json_en'), builder=document.getElementById('activityBuilderEn'), list=document.getElementById('activityListEn'), bucket=document.getElementById('activityFileBucketEn');
  if(!hidden||!builder||!list)return;
  let selectedType=''; let fileCounter=0;
  const typeNames={cards:'🧩 Kartičky',video_find:'🎥 Zastav a ukaž',video_observe:'🎬 Pozoruj video',find_image:'🔎 Najdi na obrázku',real_world:'🌱 Skutečná mise'};
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const sync=()=>hidden.value=JSON.stringify(state);
  const mediaUrl=ref=>!ref?'':(String(ref).startsWith('blob:')?ref:`/uploads/${encodeURIComponent(ref)}`);
  function newFileInput(kind,accept){const name=`pa_en_${kind}_${Date.now()}_${fileCounter++}`;const i=document.createElement('input');i.type='file';i.name=name;i.accept=accept;return i;}
  function moveFile(i){if(i&&i.files&&i.files.length){if(!i.name){i.name=`pa_en_media_${Date.now()}_${fileCounter++}`;}const d=document.createElement('div');d.style.display='none';d.appendChild(i);bucket.appendChild(d);return `__file__:${i.name}`;}return '';}
  function renderList(){list.innerHTML='';state.forEach((a,i)=>{const c=document.createElement('div');c.className='factory-qcard activity-summary';c.innerHTML=`<span class="badge-muted">${typeNames[a.type]||a.type}</span><b>${esc(a.title||'Praktická aktivita')}</b><p>${esc(a.prompt||'')}</p><small>${a.include_final?'Použije se i v „Teď to zkus sám“.':'Jen v průchodu lekcí.'}</small><button type="button" class="link-button danger">🗑️ Smazat</button>`;c.querySelector('button').onclick=()=>{state.splice(i,1);renderList();sync()};list.appendChild(c)});sync();}
  function baseFields(extra=''){builder.innerHTML=`<div class="activity-builder-grid"><label>Název aktivity<input id="paTitleEn" placeholder="např. Najdi skřele"></label><label class="wide">Zadání pro studenta<textarea id="paPromptEn" rows="3" placeholder="Co má student udělat?"></textarea></label>${extra}<label class="checkline wide"><input type="checkbox" id="paFinalEn" checked> Použít tuto aktivitu také v závěrečném „Teď to zkus sám“</label><div class="wide"><button type="button" class="savebtn" id="saveActivityEn">+ Přidat aktivitu</button></div></div>`;}
  function setupZoneStage(imgInput, savedRef=''){
    const host=document.getElementById('zoneHostEn'); if(!host)return null;
    host.innerHTML='<div class="teacher-zone-stage"><img id="zoneImageEn"><div id="zoneBoxEn" class="teacher-zone-box" hidden></div></div><p class="helpText">Myší táhni přes oblast, kterou má student trefit. Záměrně ji označ trochu větší.</p>';
    const stage=host.querySelector('.teacher-zone-stage'),img=host.querySelector('img'),box=host.querySelector('#zoneBoxEn');let zone=null,start=null;
    if(savedRef)img.src=mediaUrl(savedRef);
    if(imgInput)imgInput.addEventListener('change',()=>{if(imgInput.files[0])img.src=URL.createObjectURL(imgInput.files[0])});
    stage.addEventListener('pointerdown',e=>{if(!img.src)return;const r=stage.getBoundingClientRect();start={x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height};stage.setPointerCapture(e.pointerId);});
    stage.addEventListener('pointerup',e=>{if(!start)return;const r=stage.getBoundingClientRect();const end={x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height};zone={shape:document.getElementById('zoneShapeEn')?.value||'rect',x:Math.max(0,Math.min(start.x,end.x)),y:Math.max(0,Math.min(start.y,end.y)),w:Math.abs(end.x-start.x),h:Math.abs(end.y-start.y)};box.hidden=false;box.style.left=`${zone.x*100}%`;box.style.top=`${zone.y*100}%`;box.style.width=`${zone.w*100}%`;box.style.height=`${zone.h*100}%`;box.style.borderRadius=zone.shape==='oval'?'50%':'10px';start=null;});
    return ()=>zone;
  }
  function buildFindImage(){
    baseFields(`<label>Obrázek<input id="paImageSlotEn" type="file" accept="image/*"></label><label>Tvar správné oblasti<select id="zoneShapeEn"><option value="rect">Obdélník</option><option value="oval">Kruh / ovál</option></select></label><div class="wide image-zone-actions"><button type="button" id="showImageForZone" class="secondary-action">🖼️ 1. Zobrazit obrázek</button><button type="button" id="startImageZone" class="primary-action" hidden>✏️ 2. Označit správnou oblast</button></div><div class="wide" id="zoneHostEn"></div>`);
    const inp=document.getElementById('paImageSlotEn'), host=document.getElementById('zoneHostEn'), startBtn=document.getElementById('startImageZone');
    let stage=null,box=null,zone=null,drawing=false,start=null;
    function paintZone(z){if(!box||!z)return;box.hidden=false;Object.assign(box.style,{left:`${z.x*100}%`,top:`${z.y*100}%`,width:`${z.w*100}%`,height:`${z.h*100}%`,borderRadius:z.shape==='oval'?'50%':'10px'});}
    function enableDrawing(){if(!stage)return;drawing=true;stage.classList.add('zone-drawing-active');startBtn.textContent=zone?'✏️ Označit oblast znovu':'✏️ Táhni myší přes správné místo';const st=host.querySelector('.zone-status');if(st)st.textContent='Drž levé tlačítko myši, táhni přes správné místo a pusť.';}
    document.getElementById('showImageForZone').onclick=()=>{
      if(!inp.files[0])return alert('Nejdřív vyber obrázek.');
      host.innerHTML='<div class="teacher-zone-stage"><img id="zoneImageEn"><div id="zoneBoxEn" class="teacher-zone-box" hidden></div></div><p class="helpText zone-status">Obrázek je připravený. Klikni na „Označit správnou oblast“.</p>';
      stage=host.querySelector('.teacher-zone-stage');box=host.querySelector('#zoneBoxEn');const img=host.querySelector('img');img.src=URL.createObjectURL(inp.files[0]);zone=null;drawing=false;start=null;startBtn.hidden=false;startBtn.textContent='✏️ 2. Označit správnou oblast';
      stage.onpointerdown=e=>{if(!drawing)return;e.preventDefault();const r=stage.getBoundingClientRect();start={x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height};};
      stage.onpointerup=e=>{if(!drawing||!start)return;e.preventDefault();const r=stage.getBoundingClientRect(),end={x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height};zone={shape:zoneShapeEn.value,x:Math.min(start.x,end.x),y:Math.min(start.y,end.y),w:Math.abs(end.x-start.x),h:Math.abs(end.y-start.y)};start=null;drawing=false;stage.classList.remove('zone-drawing-active');paintZone(zone);startBtn.textContent='✏️ Označit oblast znovu';const st=host.querySelector('.zone-status');if(st)st.textContent='✓ Správná oblast je označená. Student zelený rámeček neuvidí.';};
    };
    startBtn.onclick=enableDrawing;
    document.getElementById('saveActivityEn').onclick=()=>{if(!inp.files[0]||!zone)return alert('Vyber obrázek, zobraz ho a tlačítkem „Označit správnou oblast“ vyznač místo, které má student najít.');state.push({type:'find_image',title:paTitleEn.value,prompt:paPromptEn.value,image:moveFile(inp),video:'',config:{zone},include_final:paFinalEn.checked});renderList();buildFindImage();};
  }
  function buildVideoFind(){
    baseFields(`<label>Video MP4<input id="paVideoSlotEn" type="file" accept="video/*"></label><label>Čas ve videu (sekundy)<input id="videoTimeEn" type="number" min="0" step="0.1" value="8"></label><label>Tolerance času ± s<input id="videoTolEn" type="number" min="0.2" step="0.1" value="0.8"></label><label>Tvar správné oblasti<select id="zoneShapeEn"><option value="rect">Obdélník</option><option value="oval">Kruh / ovál</option></select></label><div class="wide video-zone-actions"><button type="button" id="captureVideoEn" class="secondary-action">📸 1. Zobrazit snímek v nastaveném čase</button><button type="button" id="startVideoZone" class="primary-action" hidden>✏️ 2. Označit správnou oblast</button></div><div class="wide" id="zoneHostEn"></div>`);
    const inp=document.getElementById('paVideoSlotEn');
    const host=document.getElementById('zoneHostEn');
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

    document.getElementById('captureVideoEn').onclick=()=>{
      if(!inp.files[0])return alert('Nejdřív vyber video.');
      const v=document.createElement('video');
      v.src=URL.createObjectURL(inp.files[0]);v.muted=true;
      v.addEventListener('loadedmetadata',()=>{v.currentTime=Math.min(Number(videoTimeEn.value||0),Math.max(0,v.duration-.05))});
      v.addEventListener('seeked',()=>{
        const c=document.createElement('canvas');c.width=v.videoWidth||640;c.height=v.videoHeight||360;c.getContext('2d').drawImage(v,0,0,c.width,c.height);
        const url=c.toDataURL('image/png');
        host.innerHTML='<div class="teacher-zone-stage"><img id="zoneImageEn"><div id="zoneBoxEn" class="teacher-zone-box" hidden></div></div><p class="helpText zone-status">Snímek je připravený. Klikni na „Označit správnou oblast“.</p>';
        stage=host.querySelector('.teacher-zone-stage');box=host.querySelector('#zoneBoxEn');
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
          zone={shape:zoneShapeEn.value,x:Math.min(start.x,end.x),y:Math.min(start.y,end.y),w:Math.abs(end.x-start.x),h:Math.abs(end.y-start.y)};
          start=null;drawing=false;stage.classList.remove('zone-drawing-active');paintZone(zone);
          startBtn.textContent='✏️ Označit oblast znovu';
          const status=host.querySelector('.zone-status');
          if(status)status.textContent='✓ Správná oblast je označená. Student zelený rámeček neuvidí.';
        };
        getZone=()=>zone;
      });
    };
    startBtn.onclick=enableDrawing;
    document.getElementById('saveActivityEn').onclick=()=>{
      const z=getZone();
      if(!inp.files[0]||!z)return alert('Vyber video, zobraz snímek a tlačítkem „Označit správnou oblast“ vyznač místo, které má student najít.');
      state.push({type:'video_find',title:paTitleEn.value,prompt:paPromptEn.value,image:'',video:moveFile(inp),config:{time:Number(videoTimeEn.value||0),tolerance:Number(videoTolEn.value||.8),zone:z},include_final:paFinalEn.checked});
      renderList();buildVideoFind();
    };
  }
  function buildVideoObserve(){baseFields(`<label>Video<input id="paVideoSlotEn" type="file" accept="video/*"></label><label class="wide">Možnosti odpovědi – každá na nový řádek<textarea id="observeOptionsEn" rows="5"></textarea></label><label>Číslo správné odpovědi<input id="observeCorrectEn" type="number" min="1" value="1"></label>`);const inp=document.getElementById('paVideoSlotEn');document.getElementById('saveActivityEn').onclick=()=>{const ops=observeOptionsEn.value.split('\n').map(x=>x.trim()).filter(Boolean);if(!inp.files[0]||ops.length<2)return alert('Vyber video a napiš alespoň dvě možnosti.');state.push({type:'video_observe',title:paTitleEn.value,prompt:paPromptEn.value,image:'',video:moveFile(inp),config:{options:ops,correct:Math.max(0,Number(observeCorrectEn.value||1)-1)},include_final:paFinalEn.checked});renderList();buildVideoObserve();};}
  function buildSort(){baseFields(`<label class="wide">Kategorie – odděl čárkou<input id="sortCatsEn" placeholder="Živé, Neživé"></label><label class="wide">Položky – každý řádek ve tvaru položka | kategorie<textarea id="sortItemsEn" rows="7" placeholder="strom | Živé\nkámen | Neživé"></textarea></label>`);document.getElementById('saveActivityEn').onclick=()=>{const cats=sortCatsEn.value.split(',').map(x=>x.trim()).filter(Boolean);const rows=sortItemsEn.value.split('\n').map(x=>x.trim()).filter(Boolean);const items=[];for(const r of rows){const [label,cat]=r.split('|').map(x=>x.trim());const idx=cats.findIndex(x=>x.toLowerCase()===String(cat).toLowerCase());if(label&&idx>=0)items.push({label,category:idx});}if(cats.length<2||items.length<2)return alert('Doplň alespoň dvě kategorie a položky se správnou kategorií.');state.push({type:'sort',title:paTitleEn.value,prompt:paPromptEn.value,image:'',video:'',config:{categories:cats,items},include_final:paFinalEn.checked});renderList();buildSort();};}
  function buildMission(){baseFields(`<label>Kolik různých znaků musí napsat<input id="missionMinEn" type="number" min="1" value="3"></label><label class="wide">Uznávané významy – každý znak na nový řádek, podobné kořeny odděl |<textarea id="missionConceptsEn" rows="7" placeholder="rost|růst|zvětš\ndych|dých\nživin|výživ|vodu\nreag|světlo\nrozmnož"></textarea></label>`);document.getElementById('saveActivityEn').onclick=()=>{const concepts=missionConceptsEn.value.split('\n').map(x=>x.split('|').map(y=>y.trim()).filter(Boolean)).filter(x=>x.length);const min=Number(missionMinEn.value||3);if(concepts.length<min)return alert('Doplň alespoň tolik různých uznávaných znaků, kolik má student napsat.');state.push({type:'real_world',title:paTitleEn.value,prompt:paPromptEn.value,image:'',video:'',config:{min_items:min,concepts},include_final:paFinalEn.checked});renderList();buildMission();};}
  function buildCards(){
    baseFields(`<label class="wide">Typ kartiček<select id="cardModeEn"><option value="categories">Textové kartičky do kategorií</option><option value="images">Obrázky k očíslovaným názvům</option></select></label><div class="wide" id="cardModeEnFields"></div>`);
    const host=document.getElementById('cardModeEnFields');
    function categoriesMode(){
      host.innerHTML=`<label class="wide">Kategorie – odděl čárkou<input id="cardCatsEn" placeholder="Znaky života, Není znak života"></label><label class="wide">Kartičky – každý řádek ve tvaru kartička | kategorie<textarea id="cardCatItemsEn" rows="9" placeholder="Roste a vyvíjí se | Znaky života\nMusí být zelené | Není znak života"></textarea></label><p class="helpText wide">Student přetahuje textové kartičky do správných kategorií. Samostatné „Roztřiď“ už není potřeba.</p>`;
      document.getElementById('saveActivityEn').onclick=()=>{
        const cats=cardCatsEn.value.split(',').map(x=>x.trim()).filter(Boolean);
        const rows=cardCatItemsEn.value.split('\n').map(x=>x.trim()).filter(Boolean),items=[];
        for(const r of rows){const parts=r.split('|').map(x=>x.trim()),label=parts[0],cat=parts[1];const idx=cats.findIndex(x=>x.toLowerCase()===String(cat||'').toLowerCase());if(label&&idx>=0)items.push({label,category:idx});}
        if(cats.length<2||items.length<2)return alert('Doplň alespoň dvě kategorie a kartičky ve tvaru kartička | kategorie.');
        state.push({type:'cards',title:paTitleEn.value,prompt:paPromptEn.value,image:'',video:'',config:{mode:'categories',categories:cats,items},include_final:paFinalEn.checked});renderList();buildCards();
      };
    }
    function imagesMode(){
      host.innerHTML=`<div class="wide image-pair-help"><b>Obrázková skládačka</b><p>Nahraj 2–12 obrázků. Aplikace je očísluje podle pořadí. Ke každému napiš název cíle, např. „1 – živočišná buňka“. Student uvidí obrázky zamíchané a očíslované obdélníky s názvy.</p></div><label>Počet obrázků<input id="imageCardCountEn" type="number" min="2" max="12" value="6"></label><div class="wide"><button type="button" id="prepareImageCardsEn" class="secondary-action">🖼️ Připravit obrázky</button></div><div class="wide" id="imageCardRowsEn"></div>`;
      const rowsHost=document.getElementById('imageCardRowsEn'); let inputs=[];
      function prepare(){
        const n=Math.max(2,Math.min(12,Number(document.getElementById('imageCardCountEn').value||6))); rowsHost.innerHTML='';inputs=[];
        for(let i=0;i<n;i++){
          const row=document.createElement('div');row.className='image-card-editor-row';
          const num=document.createElement('b');num.textContent=`${i+1}.`;
          const fi=newFileInput(`cardimg${i}`,'image/*'); fi.className='image-card-file';
          const name=document.createElement('input');name.type='text';name.className='image-card-name';name.placeholder=i===0?'např. živočišná buňka':'Název obrázku / cíle';
          const prev=document.createElement('div');prev.className='image-card-preview';prev.textContent='Náhled';
          fi.addEventListener('change',()=>{prev.innerHTML='';if(fi.files[0]){const im=document.createElement('img');im.src=URL.createObjectURL(fi.files[0]);prev.appendChild(im);}});
          row.append(num,fi,name,prev);rowsHost.appendChild(row);inputs.push({fi,name});
        }
      }
      document.getElementById('prepareImageCardsEn').onclick=prepare;prepare();
      document.getElementById('saveActivityEn').onclick=()=>{
        if(inputs.length<2)return alert('Připrav alespoň dva obrázky.');
        const cards=[];
        for(let i=0;i<inputs.length;i++){
          const {fi,name}=inputs[i];const label=name.value.trim();
          if(!fi.files[0]||!label)return alert(`Doplň obrázek i název u položky ${i+1}.`);
          cards.push({label,number:i+1,image:moveFile(fi)});
        }
        state.push({type:'cards',title:paTitleEn.value,prompt:paPromptEn.value,image:'',video:'',config:{mode:'images',cards},include_final:paFinalEn.checked});renderList();buildCards();
      };
    }
    cardModeEn.onchange=()=>cardModeEn.value==='images'?imagesMode():categoriesMode(); categoriesMode();
  }
  function build(type){selectedType=type;if(type==='find_image')buildFindImage();else if(type==='video_find')buildVideoFind();else if(type==='video_observe')buildVideoObserve();else if(type==='real_world')buildMission();else if(type==='cards')buildCards();}
  document.querySelectorAll('[data-activity-type-en]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-activity-type-en]').forEach(x=>x.classList.remove('sel'));b.classList.add('sel');build(b.dataset.activityTypeEn)}));
  document.getElementById('lessonEditorForm')?.addEventListener('submit',sync);
  renderList();
})();
