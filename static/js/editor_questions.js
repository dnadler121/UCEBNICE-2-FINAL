(function(){
  const state = {questions: window.initialQuestions?.questions || []};
  const types = {questions:'choice'};
  let fileCounter = 0;

  function esc(s){return String(s||'').replace(/[&<>\"]/g, m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));}
  function imgUrl(name){
    if(!name) return '';
    if(String(name).startsWith('blob:')) return name;
    return `/uploads/${encodeURIComponent(name)}`;
  }
  function sync(){ const el=document.getElementById('questions_json'); if(el) el.value = JSON.stringify(state.questions.map(q=>{ const x={...q}; delete x.preview; delete x.previews; return x; })); }
  function newField(){ fileCounter += 1; return `qimg_${Date.now()}_${fileCounter}`; }

  function firstValue(obj, names){
    for(const name of names){
      if(obj && obj[name] !== undefined && obj[name] !== null) return obj[name];
    }
    return undefined;
  }

  function normalizeRoots(value){
    if(Array.isArray(value)) return value.map(x=>String(x).trim()).filter(Boolean);
    if(typeof value === 'string') return value.split(/[,;|]/).map(x=>x.trim()).filter(Boolean);
    return [];
  }

  function normalizeImportedQuestion(item){
    if(!item || typeof item !== 'object') throw new Error('Položka otázky není objekt.');
    const question=String(firstValue(item,['question','otazka','prompt','text']) || '').trim();
    if(!question) throw new Error('U otázky chybí text otázky.');

    const rawType=String(firstValue(item,['type','typ','qtype']) || '').trim().toLowerCase();
    const roots=normalizeRoots(firstValue(item,['roots','koreny','root','koren','answer_roots','correct_roots']));
    const answer=firstValue(item,['answer','odpoved','correct_answer','spravna_odpoved']);
    if(!roots.length && answer !== undefined && !Array.isArray(answer)) roots.push(String(answer).trim());

    const optionsRaw=firstValue(item,['options','moznosti','answers','odpovedi']);
    const options=Array.isArray(optionsRaw) ? optionsRaw.map(x=>String(x).trim()).filter(Boolean) : [];
    const isText=['text','short','short_answer','kratka_odpoved','jedna_odpoved'].includes(rawType) || (roots.length && !options.length);
    const isChoice=['choice','multiple_choice','vyber','4_moznosti','four_options'].includes(rawType) || options.length;

    if(isText){
      if(!roots.length) throw new Error(`Otázka „${question}“ nemá kořen odpovědi.`);
      return {type:'text', question, roots, image:''};
    }
    if(isChoice){
      if(options.length < 2) throw new Error(`Otázka „${question}“ musí mít alespoň 2 možnosti.`);
      let correctRaw=firstValue(item,['correct','spravna','correct_index','spravna_moznost','correct_answer']);
      let correct=0;
      if(typeof correctRaw === 'string' && !/^\d+$/.test(correctRaw.trim())){
        const found=options.findIndex(x=>x.toLowerCase()===correctRaw.trim().toLowerCase());
        if(found >= 0) correct=found;
      }else if(correctRaw !== undefined){
        const n=Number(correctRaw);
        if(Number.isFinite(n)) correct=(n >= 1 && n <= options.length) ? n-1 : n;
      }
      correct=Math.max(0,Math.min(options.length-1,Math.trunc(correct || 0)));
      return {type:'choice', question, options, correct};
    }
    throw new Error(`U otázky „${question}“ nelze určit typ.`);
  }

  function setupJsonImport(){
    const input=document.getElementById('questionsJsonFile');
    const status=document.getElementById('questionsJsonStatus');
    const box=document.querySelector('.question-factory[data-target="questions"]');
    if(!input || !box) return;
    input.addEventListener('change', async()=>{
      status.textContent='';
      const file=input.files && input.files[0];
      if(!file) return;
      try{
        const parsed=JSON.parse(await file.text());
        const source=Array.isArray(parsed) ? parsed : firstValue(parsed,['questions','otazky','items']);
        if(!Array.isArray(source)) throw new Error('JSON musí obsahovat pole otázek nebo objekt s položkou „questions“ / „otazky“.');
        const imported=source.map(normalizeImportedQuestion);
        state.questions.push(...imported);
        renderList(box);
        sync();
        status.textContent=`Načteno ${imported.length} otázek. Ručně vytvořené otázky zůstaly zachované.`;
        input.value='';
      }catch(err){
        status.textContent=`Chyba JSON: ${err.message || err}`;
        input.value='';
      }
    });
  }

  function previewFile(input, target){
    const box = typeof target === 'string' ? document.getElementById(target) : target;
    if(!box) return;
    const file = input.files && input.files[0];
    if(!file){ box.innerHTML = '<span>Náhled obrázku</span>'; return; }
    const url = URL.createObjectURL(file);
    box.innerHTML = `<img src="${esc(url)}"><span>${esc(file.name)}</span>`;
    box.dataset.previewUrl = url;
  }

  function setupGeneralPreviews(){
    document.querySelectorAll('.preview-input').forEach(input=>{
      input.addEventListener('change',()=>previewFile(input, input.dataset.preview));
    });
  }

  function makeQuestionImageInput(label, existing=''){
    const field = newField();
    const wrap = document.createElement('div');
    wrap.className = 'question-image-picker';
    wrap.dataset.ref = existing || '';
    wrap.innerHTML = `
      <div class="image-preview question-preview">${existing ? `<img src="${esc(imgUrl(existing))}"><span>Aktuální obrázek</span>` : '<span>Náhled obrázku</span>'}</div>
      <label class="image-pick-btn">🖼 ${esc(label)}<input type="file" name="${field}" accept="image/*"></label>
    `;
    const input = wrap.querySelector('input[type=file]');
    input.addEventListener('change',()=>{
      if(input.files && input.files[0]){
        wrap.dataset.ref = `__file__:${input.name}`;
        previewFile(input, wrap.querySelector('.question-preview'));
      }
    });
    return wrap;
  }

  function renderDynamic(box){
    const target=box.dataset.target || 'questions';
    const dyn=box.querySelector('.factory-dynamic');
    if(types[target] === 'text'){
      dyn.innerHTML = `<label>Obrázek k otázce (volitelné)</label><div class="inline-picker-holder"></div><label>Kořeny správné odpovědi <input class="roots" placeholder="např. bun, rost, rozmno"></label><p class="helpText">Aplikace uzná odpověď, pokud odpověď obsahuje některý kořen slova.</p>`;
      dyn.querySelector('.inline-picker-holder').appendChild(makeQuestionImageInput('Vložit obrázek k otázce'));
    }else if(types[target] === 'image_choice'){
      dyn.innerHTML = `<label>Vlož 4 obrázky přímo z počítače</label><div class="image-slot-grid direct"></div><label>Správný obrázek <select class="correct"><option value="0">1</option><option value="1">2</option><option value="2">3</option><option value="3">4</option></select></label><p class="helpText">U každého obrázku vidíš náhled. Správný obrázek pak vybereš číslem 1–4.</p>`;
      const grid = dyn.querySelector('.image-slot-grid');
      for(let i=0;i<4;i++){
        const item = makeQuestionImageInput(`Obrázek ${i+1}`);
        item.classList.add('slot-picker');
        item.dataset.slot = i;
        grid.appendChild(item);
      }
    }else{
      dyn.innerHTML = `<label>Odpovědi</label><div class="grid4"><input class="opt" placeholder="A"><input class="opt" placeholder="B"><input class="opt" placeholder="C"><input class="opt" placeholder="D"></div><label>Správná odpověď <select class="correct"><option value="0">1</option><option value="1">2</option><option value="2">3</option><option value="3">4</option></select></label>`;
    }
  }

  function moveInputsToBucket(container){
    const bucket = document.getElementById('questionFileBucket');
    if(!bucket || !container) return;
    container.querySelectorAll('input[type=file]').forEach(inp=>{
      if(inp.files && inp.files.length){
        const hidden = document.createElement('div');
        hidden.style.display='none';
        hidden.appendChild(inp);
        bucket.appendChild(hidden);
      }
    });
  }

  function renderList(box){
    const target=box.dataset.target || 'questions'; const list=box.querySelector('.question-list'); list.innerHTML='';
    state[target].forEach((q,i)=>{
      const card=document.createElement('div'); card.className='factory-qcard';
      let tag='Výběr odpovědi', detail='';
      if(q.type==='text'){
        tag='Krátká odpověď';
        const url = q.preview || imgUrl(q.image);
        detail = `${q.image?`<div class="qcard-images"><span class="mini-img right"><img src="${esc(url)}"><small>obrázek</small></span></div>`:''}Kořeny: ${(q.roots||[]).map(esc).join(', ')}`;
      }else if(q.type==='image_choice'){
        tag='4 obrázky'; detail=`<div class="qcard-images">${(q.images||[]).map((im,idx)=>`<span class="mini-img ${Number(q.correct||0)===idx?'right':''}"><img src="${esc((q.previews&&q.previews[idx]) || imgUrl(im))}"><small>${idx+1}</small></span>`).join('')}</div>`;
      }else{
        detail=`Možnosti: ${(q.options||[]).map(esc).join(' | ')} · správně ${Number(q.correct||0)+1}`;
      }
      card.innerHTML=`<span class="badge-muted">${tag}</span><b>${i+1}. ${esc(q.question)}</b><p>${detail}</p><button type="button" class="link-button danger">🗑️ Smazat</button>`;
      card.querySelector('button').onclick=()=>{ state[target].splice(i,1); renderList(box); sync(); };
      list.appendChild(card);
    });
    sync();
  }

  function addQuestion(box){
    const target=box.dataset.target || 'questions'; const question=box.querySelector('.factory-question').value.trim();
    if(!question){ alert('Napiš otázku.'); return; }
    const dyn = box.querySelector('.factory-dynamic');
    if(types[target]==='text'){
      const roots=(box.querySelector('.roots')?.value||'').split(',').map(x=>x.trim()).filter(Boolean);
      if(!roots.length){ alert('Napiš alespoň jeden kořen správné odpovědi.'); return; }
      const picker = dyn.querySelector('.question-image-picker');
      const image = picker?.dataset.ref || '';
      const preview = picker?.querySelector('.question-preview')?.dataset.previewUrl || '';
      state[target].push({type:'text', question, roots, image, preview});
      moveInputsToBucket(dyn);
    }else if(types[target]==='image_choice'){
      const pickers=Array.from(dyn.querySelectorAll('.question-image-picker'));
      const images=pickers.map(p=>p.dataset.ref || '');
      if(images.some(x=>!x)){ alert('Vyber všechny 4 obrázky.'); return; }
      const previews=pickers.map(p=>p.querySelector('.question-preview')?.dataset.previewUrl || '');
      const correct=parseInt(box.querySelector('.correct').value || '0');
      state[target].push({type:'image_choice', question, images, previews, correct});
      moveInputsToBucket(dyn);
    }else{
      const options=Array.from(box.querySelectorAll('.opt')).map(x=>x.value.trim()).filter(Boolean);
      if(options.length<2){ alert('Napiš alespoň dvě odpovědi.'); return; }
      const correct=parseInt(box.querySelector('.correct').value || '0');
      state[target].push({type:'choice', question, options, correct});
    }
    box.querySelector('.factory-question').value=''; box.querySelectorAll('.opt,.roots').forEach(i=>i.value=''); renderDynamic(box); renderList(box);
  }

  document.querySelectorAll('.question-factory').forEach(box=>{
    renderDynamic(box); renderList(box);
    box.querySelectorAll('.factory-tabs button').forEach(btn=>btn.addEventListener('click',()=>{ box.querySelectorAll('.factory-tabs button').forEach(b=>b.classList.remove('sel')); btn.classList.add('sel'); types[box.dataset.target]=btn.dataset.type; renderDynamic(box); }));
    box.querySelector('.add-question').addEventListener('click',()=>addQuestion(box));
  });
  setupGeneralPreviews();
  setupJsonImport();
  const form=document.getElementById('lessonEditorForm'); if(form){ form.addEventListener('submit',()=>sync()); }
})();
