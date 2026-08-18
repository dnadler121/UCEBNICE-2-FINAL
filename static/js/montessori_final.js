(function(){
 document.addEventListener('DOMContentLoaded',async()=>{
  const root=document.getElementById('montessoriFinal');if(!root)return;
  const lessonId=Number(root.dataset.lessonId),items=Array.from(document.querySelectorAll('#finalSequence .learning-item'));
  const label=document.getElementById('finalLabel'),count=document.getElementById('finalCount'),percent=document.getElementById('finalPercent'),grade=document.getElementById('finalGrade'),bar=document.getElementById('finalBar'),done=document.getElementById('finalDone');
  let progress={percent:0,grade:5,completed:0,total:items.length,label:'Začínám se orientovat'};
  function show(){
   const idx=items.findIndex(x=>x.dataset.completed!=='1');items.forEach((x,i)=>x.style.display=(i===idx?'':'none'));
   if(label)label.textContent=progress.label;if(count)count.textContent=`${progress.completed} / ${progress.total}`;if(percent)percent.textContent=`${progress.percent} %`;if(grade)grade.textContent=`známka ${progress.grade}`;if(bar)bar.style.width=`${progress.percent}%`;
   if(done)done.hidden=idx>=0;
  }
  const st=await fetch(`/api/final-status/${lessonId}`).then(r=>r.json()).catch(()=>null);
  if(st&&st.ok){progress=st.progress;(st.completed||[]).forEach(k=>{const el=items.find(x=>x.dataset.itemKey===k);if(el){el.dataset.completed='1';el.classList.add('completed-item')}});}
  show();
  async function checkQuestion(card,answer){
   const fb=card.querySelector('.feedback');const r=await fetch('/api/final-question-check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question_id:Number(card.dataset.questionId),answer})});const d=await r.json();fb.textContent=d.message||'';fb.className='feedback '+(d.ok?'ok':'bad');
   if(d.progress)progress=d.progress;if(d.ok){card.dataset.completed='1';card.classList.add('completed-item');setTimeout(show,450);}else show();
  }
  items.filter(x=>x.dataset.kind==='question').forEach(card=>{card.querySelectorAll('[data-answer]').forEach(b=>b.addEventListener('click',()=>checkQuestion(card,b.dataset.answer)));card.querySelector('.check-final-question')?.addEventListener('click',()=>checkQuestion(card,card.querySelector('.text-answer')?.value||''));});
  document.addEventListener('final-progress',e=>{if(e.detail){progress=e.detail;show();}});
  document.addEventListener('activity-completed',e=>{const card=e.target.closest('.learning-item');if(card&&card.dataset.context==='final'){card.dataset.completed='1';setTimeout(show,450);}});
 });
})();
