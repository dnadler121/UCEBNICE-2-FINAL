const mainCard = document.querySelector('.main-card[data-lesson]');
const lessonKey = mainCard ? `${mainCard.dataset.lesson}_step_${mainCard.dataset.step}` : 'lesson_step';
const correctQuestions = new Set();
const sectionAlreadyCompleted = mainCard && mainCard.dataset.completed === '1';

function updateLockState(){
  const cards = document.querySelectorAll('.q-card[data-q]');
  const activity = document.querySelector('#activityDone');
  const next = document.querySelector('#nextBtn');
  const msg = document.querySelector('#lockMsg');
  const testSwitch = document.querySelector('#testSwitch');
  const allQuestionsOk = correctQuestions.size === cards.length;
  const activityOk = !activity || activity.checked;
  const unlocked = allQuestionsOk && activityOk;
  if(next){
    next.classList.toggle('locked-next', !unlocked);
    next.setAttribute('aria-disabled', String(!unlocked));
  }
  if(testSwitch && testSwitch.classList.contains('locked-test')){
    testSwitch.setAttribute('aria-disabled', String(!unlocked));
    testSwitch.textContent = unlocked ? '⇄ Přepnout na test' : '🔒 Test je zamčený';
    testSwitch.classList.toggle('locked-test', !unlocked);
  }
  if(msg){
    if(unlocked){ msg.textContent = 'Hotovo, můžeš pokračovat dál. ✓'; msg.classList.add('ok'); }
    else { msg.textContent = 'Nejdřív odpověz správně na všechny otázky k výkladu a odškrtni aktivitu.'; msg.classList.remove('ok'); }
  }
  if(unlocked && mainCard){
    fetch('/api/section-complete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lesson_id:mainCard.dataset.lesson, step:mainCard.dataset.step})}).catch(()=>{});
  }
}

function markQuestion(card, ok){
  const cards = Array.from(document.querySelectorAll('.q-card[data-q]'));
  const idx = cards.indexOf(card);
  if(ok){ correctQuestions.add(idx); card.classList.add('answered-ok'); }
  else { correctQuestions.delete(idx); card.classList.remove('answered-ok'); }
  updateLockState();
}

document.querySelectorAll('.q-card[data-q]').forEach(card=>{
  const q=JSON.parse(card.dataset.q);
  const fb=card.querySelector('.feedback');
  card.querySelectorAll('[data-answer]').forEach(btn=>{
    btn.addEventListener('click',async()=>{
      card.querySelectorAll('[data-answer]').forEach(b=>b.classList.remove('selected'));
      btn.classList.add('selected');
      const r=await fetch('/api/check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,answer:btn.dataset.answer})});
      const j=await r.json();
      fb.textContent=j.ok?'✓ Správně, můžeš pokračovat.':'Zkus to ještě jednou. Odpověď najdeš ve výkladu.';
      fb.className='feedback '+(j.ok?'ok':'bad');
      markQuestion(card, j.ok);
    });
  });
  const check=card.querySelector('.check-text');
  if(check){check.addEventListener('click',async()=>{
    const ans=card.querySelector('.text-answer').value;
    const r=await fetch('/api/check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,answer:ans})});
    const j=await r.json();
    fb.textContent=j.ok?'✓ Správně, můžeš pokračovat.':'Zkus odpověď doplnit. Hledej přímo ve výkladu.';
    fb.className='feedback '+(j.ok?'ok':'bad');
    markQuestion(card, j.ok);
  })}
});

if(sectionAlreadyCompleted){
  document.querySelectorAll('.q-card[data-q]').forEach((card, idx)=>{ correctQuestions.add(idx); card.classList.add('answered-ok'); });
  const done = document.querySelector('#activityDone');
  if(done) done.checked = true;
}
const activity = document.querySelector('#activityDone');
if(activity){
  activity.addEventListener('change', updateLockState);
}
const next = document.querySelector('#nextBtn');
function scrollToMissing(){
  const firstBad = document.querySelector('.q-card[data-q]:not(.answered-ok)') || document.querySelector('#activityDone');
  if(firstBad) firstBad.scrollIntoView({behavior:'smooth', block:'center'});
}
if(next){
  next.addEventListener('click', e=>{
    if(next.classList.contains('locked-next')){
      e.preventDefault();
      scrollToMissing();
    }
  });
}
const testSwitch = document.querySelector('#testSwitch');
if(testSwitch){
  testSwitch.addEventListener('click', e=>{
    if(testSwitch.classList.contains('locked-test')){
      e.preventDefault();
      scrollToMissing();
      const msg=document.querySelector('#lockMsg');
      if(msg) msg.textContent='Test se odemkne až po správných otázkách a splněné aktivitě.';
    }
  });
}
updateLockState();

// Jedna otázka po druhé + náhodné pořadí pro výkladové otázky i závěrečný test
function setupOneByOne(containerSelector, cardSelector){
  const container = document.querySelector(containerSelector);
  if(!container) return;
  let cards = Array.from(container.querySelectorAll(cardSelector));
  if(cards.length <= 1) return;
  cards.sort(()=>Math.random()-0.5);
  cards.forEach(c=>container.insertBefore(c, container.querySelector('.submit') || null));
  let index = 0;
  const info = document.createElement('div');
  info.className = 'question-progress';
  container.insertBefore(info, cards[0]);
  function show(){
    cards.forEach((c,i)=>c.style.display = i===index ? '' : 'none');
    info.textContent = `Otázka ${index+1} / ${cards.length}`;
  }
  show();
  cards.forEach((card,i)=>{
    card.addEventListener('click', e=>{
      if(card.classList.contains('answered-ok') && i===index){
        setTimeout(()=>{ if(index < cards.length-1){ index++; show(); } }, 500);
      }
    });
  });
}
setupOneByOne('.question-grid.vertical', '.q-card[data-q]');

(function setupFinalOneByOne(){
  const form = document.querySelector('.final-form');
  if(!form) return;
  const cards = Array.from(form.querySelectorAll('.final-one'));
  if(cards.length <= 1) return;
  cards.sort(()=>Math.random()-0.5);
  const submit = form.querySelector('.submit');
  cards.forEach(c=>form.insertBefore(c, submit));
  let index=0;
  const info=document.createElement('div');
  info.className='question-progress';
  form.insertBefore(info, cards[0]);
  const next=document.createElement('button');
  next.type='button'; next.className='testbtn'; next.textContent='Další otázka →';
  form.insertBefore(next, submit);
  submit.style.display='none';
  function answered(card){ return !!card.querySelector('input:checked, input.text-answer:not(:placeholder-shown)'); }
  function show(){
    cards.forEach((c,i)=>c.style.display=i===index?'':'none');
    info.textContent=`Závěrečný test: otázka ${index+1} / ${cards.length}`;
    next.style.display=index<cards.length-1?'':'none';
    submit.style.display=index===cards.length-1?'':'none';
  }
  next.addEventListener('click',()=>{
    if(!answered(cards[index])){ alert('Nejdřív odpověz na otázku. Výklad máš vedle.'); return; }
    index++; show();
  });
  form.addEventListener('submit', e=>{ if(!answered(cards[index])){ e.preventDefault(); alert('Nejdřív odpověz na poslední otázku.'); } });
  show();
})();
