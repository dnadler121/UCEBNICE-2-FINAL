(function(){
  document.addEventListener('DOMContentLoaded',()=>{
    const root=document.getElementById('montessoriLesson'); if(!root)return;
    const items=Array.from(document.querySelectorAll('#learningSequence .learning-item'));
    const studyScroll=document.getElementById('studyScroll');
    let readComplete=root.dataset.readComplete==='1';
    const reviewMode=root.dataset.review==='1';
    let current=0;
    let sectionSaving=false, sectionSaved=root.dataset.sectionCompleted==='1';
    const nextBtn=document.getElementById('nextBtn'), topTestBtn=document.getElementById('topTestBtn'), lockMsg=document.getElementById('lockMsg'), doneBox=document.getElementById('sequenceDone');
    const counter=document.getElementById('journeyCounter'),bar=document.getElementById('journeyBar');

    async function markRead(){
      if(readComplete)return; readComplete=true;
      await fetch('/api/section-read',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lesson_id:Number(root.dataset.lessonId),step:Number(root.dataset.step)})}).catch(()=>{});
      refresh();
    }
    if(studyScroll){
      const testEnd=()=>{if(studyScroll.scrollTop+studyScroll.clientHeight>=studyScroll.scrollHeight-24)markRead();};
      studyScroll.addEventListener('scroll',testEnd); setTimeout(testEnd,150);
    }
    function firstIncomplete(){const idx=items.findIndex(x=>x.dataset.completed!=='1');return idx<0?items.length:idx;}
    function refresh(){
      current=firstIncomplete();
      if(reviewMode){
        // Po prvním dokončení může student jedním kliknutím znovu otevřít
        // všechny otázky a praktické aktivity. Splnění se tím nemaže.
        items.forEach(it=>{it.style.display='';});
      }else{
        items.forEach((it,i)=>{it.style.display=(i===current?'':'none');});
      }
      const total=Math.max(items.length,1), completed=items.filter(x=>x.dataset.completed==='1').length;
      if(counter)counter.textContent=`${Math.min(completed+1,total)} / ${total}`;
      if(bar)bar.style.width=`${Math.round(completed/total*100)}%`;
      const allItems=completed===items.length; const requirementsMet=allItems&&readComplete;
      const unlocked=requirementsMet&&sectionSaved;
      if(doneBox)doneBox.hidden=reviewMode || !allItems;
      if(nextBtn){nextBtn.classList.toggle('locked-next',!unlocked);nextBtn.setAttribute('aria-disabled',String(!unlocked));}
      // Horní tlačítko bylo dříve vyrenderované jako zamčený <span> a po
      // dokončení poslední části se už bez reloadu neumělo změnit. Držíme ho
      // jako odkaz a odemykáme ho současně se spodním tlačítkem.
      if(topTestBtn){
        topTestBtn.classList.toggle('locked-test',!unlocked);
        topTestBtn.setAttribute('aria-disabled',String(!unlocked));
        topTestBtn.textContent=unlocked ? (topTestBtn.dataset.readyLabel||'🧠 Teď to zkus sám') : (topTestBtn.dataset.lockedLabel||'🔒 Ověření se odemkne po lekci');
      }
      if(lockMsg){
        const text=reviewMode?'📖 Režim opakování: výklad, otázky i aktivity máš znovu otevřené. Výsledek se tím nezhorší.'
          :(unlocked?'Hotovo. Můžeš pokračovat. ✓'
          :(requirementsMet?'Ukládám dokončení lekce…'
          :(!readComplete?'Projdi jednou celý studijní materiál vlevo a dokonči aktuální krok.':'Dokonči aktuální otázku nebo praktickou aktivitu.')));
        lockMsg.textContent=text; lockMsg.classList.toggle('ok',unlocked||reviewMode);
      }
      if(requirementsMet&&!sectionSaved&&!sectionSaving){
        sectionSaving=true;
        fetch('/api/section-complete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lesson_id:Number(root.dataset.lessonId),step:Number(root.dataset.step)})})
          .then(r=>r.json().then(data=>({ok:r.ok,data})))
          .then(({ok,data})=>{
            sectionSaving=false;
            if(ok&&data.ok){sectionSaved=true;refresh();}
            else{if(lockMsg)lockMsg.textContent=data.message||'Dokončení se nepodařilo uložit. Zkus to znovu.';setTimeout(refresh,1200);}
          })
          .catch(()=>{sectionSaving=false;if(lockMsg)lockMsg.textContent='Dokončení se nepodařilo uložit. Zkouším znovu…';setTimeout(refresh,1200);});
      }
    }
    async function checkQuestion(card,answer){
      const fb=card.querySelector('.feedback');
      const res=await fetch('/api/study-question-check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question_id:Number(card.dataset.questionId),answer})});
      const data=await res.json(); fb.textContent=data.message||'';fb.className='feedback '+(data.ok?'ok':'bad');
      if(data.ok){card.dataset.completed='1';card.classList.add('completed-item');setTimeout(refresh,450);}
    }
    items.filter(x=>x.dataset.kind==='question').forEach(card=>{
      card.querySelectorAll('[data-answer]').forEach(btn=>btn.addEventListener('click',()=>checkQuestion(card,btn.dataset.answer)));
      card.querySelector('.check-study-question')?.addEventListener('click',()=>checkQuestion(card,card.querySelector('.text-answer')?.value||''));
    });
    document.addEventListener('activity-completed',()=>setTimeout(refresh,450));
    nextBtn?.addEventListener('click',e=>{if(nextBtn.classList.contains('locked-next')){e.preventDefault();const visible=items.find(x=>x.style.display!=='none');visible?.scrollIntoView({behavior:'smooth',block:'center'});}});
    topTestBtn?.addEventListener('click',e=>{if(topTestBtn.classList.contains('locked-test')){e.preventDefault();const visible=items.find(x=>x.style.display!=='none');visible?.scrollIntoView({behavior:'smooth',block:'center'});}});
    if(items.length===1&&items[0].dataset.kind==='read'&&readComplete){items[0].dataset.completed='1';}
    refresh();
  });
})();
