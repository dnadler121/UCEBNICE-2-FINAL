function gradeFromPercent(percent) {
  if (percent >= 95) return 1;
  if (percent >= 90) return 2;
  if (percent >= 85) return 3;
  if (percent >= 80) return 4;
  return 5;
}

let course=null;
const order=['addition','multiplication','division','algebra'];
const labels={addition:'Sčítání pod sebe',multiplication:'Násobení pod sebe',division:'Dělení pod sebe',algebra:'Úprava výrazů'};
let section=0, task=0, solved=false;
const norm=s=>String(s??'').toLowerCase().replaceAll(' ','').replace('.',',').replaceAll('−','-').replaceAll('*','');
const plain=s=>String(s).replace(',','');
const decimals=s=>(String(s).split(',')[1]||'').length;
const toNum=s=>Number(String(s).replace(',','.'));
function fb(msg,ok=false){const e=document.getElementById('feedback');e.textContent=msg;e.className='feedback '+(ok?'ok':'bad')}
function unlock(msg){solved=true;document.getElementById('continue').disabled=false;fb(msg,true)}
function totalTasks(){return order.reduce((n,k)=>n+course[k].length,0)}
function doneTasks(){let n=0;for(let i=0;i<section;i++)n+=course[order[i]].length;return n+task}
function updateProgress(){const pct=Math.round(doneTasks()/totalTasks()*100);document.getElementById('progress-bar').style.width=pct+'%';document.getElementById('progress-text').textContent=`Úkol ${doneTasks()+1} z ${totalTasks()}`;document.getElementById('section-name').textContent=labels[order[section]];order.forEach((k,i)=>{const el=document.getElementById('road-'+k);el.className=i<section?'done':i===section?'active':''})}
function setup(title,instruction){solved=false;document.getElementById('continue').disabled=true;document.getElementById('title').textContent=title;document.getElementById('instruction').textContent=instruction;document.getElementById('work').innerHTML='';updateProgress()}
function cell(ch,editable=false){
  if(editable && ch===''){
    const d=document.createElement('div');
    d.className='math-cell spacer';
    d.setAttribute('aria-hidden','true');
    return d;
  }
  if(!editable){
    const d=document.createElement('div');
    d.className='math-cell fixed '+(ch===','?'comma':'')+(ch===''?' spacer':'');
    d.textContent=ch;
    return d;
  }
  const i=document.createElement('input');
  i.className='math-cell '+(ch===','?'comma':'');
  i.maxLength=1;
  i.inputMode=ch===','?'text':'numeric';
  i.dataset.expected=ch;
  return i
}
function makeRow(chars,editable=false,extra=''){const r=document.createElement('div');r.className='math-row '+extra;chars.forEach(ch=>r.appendChild(cell(ch,editable)));return r}
function checkSequential(inputs,fromRight,onDone,hint){const list=[...inputs],seq=fromRight?[...list].reverse():list;list.forEach(x=>x.disabled=true);if(!seq.length){onDone();return}seq[0].disabled=false;seq[0].focus();seq.forEach((inp,idx)=>inp.addEventListener('input',()=>{const v=norm(inp.value);if(!v)return;if(v!==norm(inp.dataset.expected)){inp.value='';fb(inp.dataset.expected===','?'Sem patří desetinná čárka. Zkontroluj její polohu.':hint(inp,idx));return}inp.disabled=true;inp.classList.add('locked');const next=seq[idx+1];if(next){next.disabled=false;next.focus();fb('Správně. Pokračuj další číslicí.',true)}else onDone()}))}
function alignStrings(a,b){const [ai,ad='']=a.split(','),[bi,bd='']=b.split(',');const left=Math.max(ai.length,bi.length),right=Math.max(ad.length,bd.length);const pad=s=>{let [i,d='']=s.split(',');return i.padStart(left,' ') + ',' + d.padEnd(right,'0')};return {a:pad(a),b:pad(b),cols:left+1+right}}
function boardRow(text, editable=false, operator=''){const wrap=document.createElement('div');wrap.className='board-line';const op=document.createElement('div');op.className='board-op';op.textContent=operator;wrap.appendChild(op);wrap.appendChild(makeRow([...text].map(x=>x===' '?'':x),editable));return wrap}
function renderAddition(d){setup(`Sčítání pod sebe – příklad ${task+1}`,'První číslo je už zapsané. Doplň druhé číslo přesně pod něj, včetně potřebných nul. Potom sčítej zprava po jednotlivých sloupcích.');const w=document.getElementById('work'),al=alignStrings(d.a,d.b);w.innerHTML=`<div class="exercise">${d.a} + ${d.b}</div><div class="step"><b>Krok 1:</b> Zapiš druhý sčítanec pod první. Nuly doplňujeme proto, aby byly stejné řády přesně pod sebou.</div>`;const board=document.createElement('div');board.className='stack-board';board.appendChild(boardRow(al.a,false,''));const second=boardRow(al.b,true,'+');board.appendChild(second);w.appendChild(board);const feedback=document.createElement('div');feedback.id='feedback';feedback.className='feedback';feedback.textContent='Začni zleva. Porovnávej jednotky, desetiny, setiny a další řády.';w.appendChild(feedback);checkSequential(second.querySelectorAll('input'),false,()=>additionResult(d,w,al),()=> 'Tento znak není ve správném sloupci. Podívej se na první číslo a zarovnej desetinné čárky.')}
function additionResult(d,w,al){const s=document.createElement('div');s.className='step';s.innerHTML='<b>Krok 2:</b> Teď sčítej zprava. Výsledek zapisuj přesně pod odpovídající sloupce.';w.insertBefore(s,document.getElementById('feedback'));const result=d.result.padStart(al.cols,' ');const board=document.querySelector('.stack-board');board.classList.add('with-rule');const row=boardRow(result,true,'');row.classList.add('result-line');board.appendChild(row);checkSequential(row.querySelectorAll('input'),true,()=>unlock(`Výborně. ${d.a} + ${d.b} = ${d.result}`),()=> 'Výsledek v tomto sloupci nesedí. Sečti číslice v tomto sloupci a nezapomeň na přenos.')}
function mulData(d){const A=plain(d.a),B=plain(d.b),partials=[...B].reverse().map((ch,i)=>String(Number(A)*Number(ch))+'0'.repeat(i));const places=decimals(d.a)+decimals(d.b);let res=(toNum(d.a)*toNum(d.b)).toFixed(places).replace('.',',');return {A,B,partials,res}}
function padLeft(s,n){return String(s).padStart(n,' ')}
function renderMultiplication(d){setup(`Násobení pod sebe – příklad ${task+1}`,'Činitele jsou správně pod sebou. Vypočítej mezivýsledky po řádcích; každý další řádek je posunut o jedno místo doleva. Nakonec je sečti ve správných sloupcích.');const w=document.getElementById('work'),m=mulData(d);const width=Math.max(m.A.length,m.B.length+1,...m.partials.map(x=>x.length),m.res.length);w.innerHTML=`<div class="exercise">${d.a} × ${d.b}</div><div class="step"><b>Krok 1:</b> Pro násobení dočasně pracujeme bez desetinných čárek: ${m.A} × ${m.B}.</div>`;const board=document.createElement('div');board.className='stack-board with-rule';board.appendChild(boardRow(padLeft(m.A,width),false,''));board.appendChild(boardRow(padLeft(m.B,width),false,'×'));w.appendChild(board);const feedback=document.createElement('div');feedback.id='feedback';feedback.className='feedback';feedback.textContent='Vyplň první mezivýsledek zprava doleva.';w.appendChild(feedback);let i=0;function nextPartial(){if(i>=m.partials.length){finalMul();return}const expected=padLeft(m.partials[i],width);const row=boardRow(expected,true,i?' +':'');row.classList.add('partial-line');board.appendChild(row);checkSequential(row.querySelectorAll('input'),true,()=>{i++;fb('Mezivýsledek je správně a je ve správných sloupcích.',true);setTimeout(nextPartial,180)},()=> 'Číslice nebo její sloupec nesedí. Každý další mezivýsledek musí být posunut o jedno místo doleva.')}function finalMul(){const st=document.createElement('div');st.className='step';st.innerHTML=`<b>Krok 2:</b> Sečti mezivýsledky po sloupcích. Potom umísti desetinnou čárku tak, aby výsledek měl <b>${decimals(d.a)+decimals(d.b)}</b> desetinných míst.`;w.insertBefore(st,feedback);board.classList.add('double-rule');const row=boardRow(padLeft(m.res,width),true,'');row.classList.add('result-line');board.appendChild(row);checkSequential(row.querySelectorAll('input'),true,()=>unlock(`Správně. ${d.a} × ${d.b} = ${m.res}`),()=> 'Zkontroluj součet ve sloupci, přenos a počet desetinných míst.')}nextPartial()}
function textInput(expected, cls='long-input'){const i=document.createElement('input');i.className=cls;i.dataset.expected=expected;i.autocomplete='off';return i}
function checkWhole(input,onDone,hint){input.addEventListener('change',()=>{if(norm(input.value)===norm(input.dataset.expected)){input.disabled=true;input.classList.add('locked');onDone()}else{input.value='';fb(hint);input.focus()}});input.focus()}
function renderDivision(d){
  setup(`Dělení pod sebe – příklad ${task+1}`,'Nejprve odstraníme desetinnou čárku z dělitele tím, že dělenec i dělitel vynásobíme stejným číslem. Potom dělíme klasicky pod sebe.');
  const w=document.getElementById('work');
  const originalParts=d.original.split(':').map(x=>x.trim());
  const factor='1'+'0'.repeat(d.moves);
  w.innerHTML=`<div class="exercise">${d.original}</div>
    <div class="step"><b>Krok 1:</b> Dělitel <b>${originalParts[1]}</b> má ${d.moves} desetinná ${d.moves===1?'místo':'místa'}. Proto obě čísla vynásobíme <b>${factor}</b>. Hodnota podílu se tím nezmění.</div>
    <div class="division-transform">
      <div class="transform-row"><span>${originalParts[0]}</span><span>:</span><span>${originalParts[1]}</span></div>
      <div class="transform-row factor"><span>× ${factor}</span><span></span><span>× ${factor}</span></div>
      <div class="transform-rule"></div>
      <div class="transform-row result"><span>${d.dividend}</span><span>:</span><span>${d.divisor}</span></div>
    </div>
    <button id="start-division" class="action start-division">Pokračovat k dělení pod sebe</button>
    <div id="feedback" class="feedback">Zkontroluj, že jsme obě čísla vynásobili stejným číslem.</div>`;
  document.getElementById('start-division').onclick=()=>{
    document.getElementById('start-division').disabled=true;
    fb(`Správně. Nyní dělíme ${d.dividend} : ${d.divisor}.`,true);
    startLongDivision(d,w);
  };
}
function startLongDivision(d,w){
  if(document.querySelector('.long-division'))return;
  const shift=document.querySelector('.decimal-shift'); if(shift) shift.querySelectorAll('button').forEach(b=>b.disabled=true);
  const step=document.createElement('div');step.className='step';step.innerHTML=`<b>Krok 2:</b> Dělíme <b>${d.dividend} : ${d.divisor}</b>. Doplň vždy jen právě požadovaný krok. ${d.note||''}`;
  w.insertBefore(step,document.getElementById('feedback'));
  const box=document.createElement('div');box.className='long-division';box.innerHTML=`<div class="division-head"><span class="dividend">${d.dividend}</span><span class="colon">:</span><span class="divisor">${d.divisor}</span><span>=</span><span id="quotient"></span></div><div id="division-work" class="division-work"></div>`;
  w.insertBefore(box,document.getElementById('feedback'));
  let idx=0;
  function next(){
    if(idx>=d.steps.length){unlock(`Výborně. ${d.original} = ${d.quotient}${d.note?' (na tři desetinná místa)':''}`);return}
    const s=d.steps[idx],q=document.getElementById('quotient');
    if(s.decimal&&!q.textContent.includes(','))q.append(',');
    const qin=cell(s.q,true);qin.classList.add('q-cell');q.appendChild(qin);
    fb(`Kolikrát se ${d.divisor} vejde do čísla ${s.part}? Zapiš další číslici podílu.`);
    checkSequential([qin],false,()=>productStep(s),()=>`Zkus odhadnout, kolikrát se ${d.divisor} vejde do ${s.part}, aniž by součin byl větší.`)
  }
  function productStep(s){
    const work=document.getElementById('division-work'),block=document.createElement('div');block.className='division-step';block.innerHTML=`<div class="division-caption">${d.divisor} × ${s.q} =</div>`;
    const p=textInput(s.product,'step-input');block.appendChild(p);work.appendChild(block);fb('Napiš násobek, který budeme odečítat.');
    checkWhole(p,()=>remainderStep(s,block),`Vynásob ${d.divisor} číslicí ${s.q}.`)
  }
  function remainderStep(s,block){
    block.insertAdjacentHTML('beforeend','<span class="minus-sign">−</span>');const r=textInput(s.remainder,'step-input');block.appendChild(r);fb(`Odečti ${s.part} − ${s.product}.`);
    checkWhole(r,()=>{if(s.bring!==''){const br=document.createElement('div');br.className='bring-down';br.textContent=`Zbytek ${s.remainder}; připíšeme další číslici ${s.bring} → ${s.remainder}${s.bring}`;block.appendChild(br)}idx++;fb('Tento krok je správně.',true);setTimeout(next,180)},`Zkontroluj odečtení ${s.part} − ${s.product}.`)
  }
  next();
}
function renderAlgebra(d){
  setup(`Úprava výrazů – příklad ${task+1}`,'Označ všechny členy stejného druhu. Musí mít stejné proměnné i stejné exponenty. Čísla bez proměnných lze spojovat jen s dalšími čísly.');
  const w=document.getElementById('work');
  w.innerHTML=`<div class="exercise expression-live" id="expression-live"></div>
    <div class="step"><b>Postup:</b> Označ dva nebo více stejných členů. Potom se objeví políčko, do kterého napíšeš jejich součet.</div>
    <div class="terms" id="terms"></div>
    <div class="answer-line hidden" id="merge-line"><input id="alg-answer" class="algebra-input" placeholder="Napiš jejich součet"><button id="merge" class="action">Nahradit součtem</button></div>
    <div id="feedback" class="feedback">Najdi členy se stejnou proměnnou částí a stejnými mocninami.</div>`;
  const terms=document.getElementById('terms'), live=document.getElementById('expression-live'), mergeLine=document.getElementById('merge-line');
  let active=d.products.map((text,id)=>({id,text}));
  let completed=new Set();
  function draw(){
    terms.innerHTML='';
    active.forEach((t,pos)=>{const b=document.createElement('button');b.className='term';b.textContent=t.text;b.dataset.id=t.id;b.onclick=()=>{b.classList.toggle('selected');const n=document.querySelectorAll('.term.selected').length;mergeLine.classList.toggle('hidden',n<2);if(n>=2)fb(`Označeno ${n} členů. Napiš jejich společný součet.`)};terms.appendChild(b)});
    live.textContent=active.map((t,i)=>{if(i===0)return t.text;return t.text.startsWith('-')?'− '+t.text.slice(1):'+ '+t.text}).join(' ');
  }
  draw();
  document.getElementById('merge').onclick=()=>{
    const selected=[...document.querySelectorAll('.term.selected')].map(x=>Number(x.dataset.id));
    if(selected.length<2){fb('Označ alespoň dva členy.');return}
    const match=d.groups.findIndex((g,idx)=>!completed.has(idx)&&g.length===selected.length&&g.every(id=>selected.includes(id)));
    if(match<0){fb('Tyto členy nelze spojit. Musí mít úplně stejné proměnné a stejné exponenty.');return}
    const answer=d.group_answers[match];
    if(norm(document.getElementById('alg-answer').value)!==norm(answer)){fb('Výběr je správný, ale součet koeficientů nesedí. Znaménka počítej velmi pečlivě.');return}
    const positions=active.map((x,i)=>selected.includes(x.id)?i:-1).filter(i=>i>=0), first=Math.min(...positions);
    active=active.filter(x=>!selected.includes(x.id));
    active.splice(first,0,{id:1000+match,text:answer});
    completed.add(match);document.getElementById('alg-answer').value='';mergeLine.classList.add('hidden');draw();
    if(completed.size===d.groups.length)unlock(`Správně. Výraz se upravil na: ${d.final}`);else fb('Správně. Původní členy se ve výrazu nahradily jejich součtem. Najdi další skupinu.',true)
  }
}
function render(){const kind=order[section],d=course[kind][task];({addition:renderAddition,multiplication:renderMultiplication,division:renderDivision,algebra:renderAlgebra})[kind](d)}
document.getElementById('continue').onclick=()=>{if(!solved)return;task++;const kind=order[section];if(task>=course[kind].length){section++;task=0}if(section>=order.length){document.getElementById('progress-bar').style.width='100%';document.querySelectorAll('.roadmap span').forEach(x=>x.className='done');document.getElementById('progress-text').textContent='Lekce dokončena';document.getElementById('section-name').textContent='Hotovo';document.querySelector('.panel').innerHTML='<div class="finished"><h2>Výborně, celá lekce je dokončena!</h2><p>Prošel jsi sčítání, násobení, dělení i úpravy výrazů krok za krokem.</p></div>';fetch(window.LESSON_URLS.completeLesson,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({percent:100,grade:1})}).catch(()=>{});return}render()}
const exitLessonBtn=document.getElementById("exitLessonBtn");
exitLessonBtn.onclick=async()=>{
  const kinds=["addition","multiplication","division","algebra"];
  let completed=0;
  for(let i=0;i<section;i++)completed+=course[kinds[i]].length;
  completed+=task;
  if(solved)completed+=1;
  const total=kinds.reduce((sum,k)=>sum+course[k].length,0);
  const percent=Math.round((completed/total)*100);
  const grade=gradeFromPercent(percent);
  exitLessonBtn.disabled=true;
  exitLessonBtn.textContent="Ukládám výsledek…";
  try{
    const response=await fetch(window.LESSON_URLS.completeLesson,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({percent,grade})});
    const data=await response.json();
    if(!response.ok||!data.ok)throw new Error(data.error||"Výsledek se nepodařilo uložit.");
    window.location.href=window.LESSON_URLS.portal;
  }catch(error){
    exitLessonBtn.disabled=false;
    exitLessonBtn.textContent="← Ukončit a uložit výsledek";
    alert(error.message||"Výsledek se nepodařilo uložit.");
  }
};

fetch(window.LESSON_URLS.course)
  .then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json()})
  .then(d=>{course=d.course||d;if(!course||!course.addition)throw new Error('Data lekce nemají správný formát.');render()})
  .catch(err=>{document.getElementById('title').textContent='Lekci se nepodařilo načíst';document.getElementById('instruction').textContent='Chyba při načítání dat lekce: '+err.message;document.getElementById('work').innerHTML='<div class="feedback bad">Obnov stránku. Pokud chyba zůstane, balíček nebyl správně importován.</div>';console.error(err)});
