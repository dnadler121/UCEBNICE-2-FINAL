const C=window.NSN; let S=null;
async function call(a,p={}){let r=await fetch(C.api[a],{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});let d=await r.json();if(!d.ok&&d.error) throw Error(d.error);S=d;render();return d}
function el(id){return document.getElementById(id)}
function render(){if(!S)return;el('numbers').textContent=S.numbers.join(' , ');el('progress').textContent=`${S.completed} z ${S.target} příkladů`;el('bar').style.width=`${100*S.completed/S.target}%`;el('mistakes').textContent=S.mistakes;el('msg').textContent=S.message||'';
 el('rows').innerHTML=S.rows.map((row,ri)=>`<div class="row"><b>${S.numbers[ri]} =</b> ${row.map(x=>`<button class="factor ${x.crossed?'crossed':''}" ${x.crossed?'disabled':''} onclick="pick(${ri},${x.id},${x.value})">${x.value}</button>`).join(' × ')}</div>`).join('');
 let c=el('controls');
 if(S.phase==='factor') c.innerHTML=`<h3>Rozklad</h3><p>Klikni na složené číslo v řádku a potom vyber nejmenšího prvočíselného dělitele.</p><div id="chosen">Nejdříve vyber číslo.</div><div class="divs">${S.divisors.map(d=>`<button disabled data-div="${d}">${d}</button>`).join('')}</div>`;
 if(S.phase==='cross') c.innerHTML=`<h3>Škrtání dvojic</h3><p>Klikej na činitele ve <b>2. a 3. řádku</b>, které už jsou zastoupené v předchozích řádcích.</p><button class="primary" onclick="call('to_product')">Mám vyškrtnuto – pokračovat</button>`;
 if(S.phase==='product'){let f=S.factors||S.rows.flat().filter(x=>!x.crossed).map(x=>x.value);c.innerHTML=`<h3>Součin pro NSN</h3><div class="product">${f.join(' × ')}</div><div class="answer"><input id="ans" type="number" placeholder="Výsledek"><button class="primary" onclick="answer()">Zkontrolovat</button></div>`;}
}
window.pick=function(row,id,value){if(!S)return;if(S.phase==='factor'){el('chosen').innerHTML=`Rozkládám <b>${value}</b>. Vyber dělitele:`;document.querySelectorAll('[data-div]').forEach(b=>{b.disabled=false;b.onclick=()=>call('split',{row,item:id,divisor:+b.dataset.div})})}else if(S.phase==='cross'){if(row===0){el('msg').textContent='V prvním řádku nic neškrtáme.';return}call('cross',{row,item:id})}}
window.answer=async function(){let d=await call('answer',{answer:el('ans').value});if(d.example_done){if(d.lesson_finished){await fetch(C.complete,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({percent:d.percent,grade:d.grade})});el('controls').innerHTML=`<div class="finish"><h2>Hotovo 🎉</h2><p>Výsledek série: ${d.percent} % · známka ${d.grade}</p></div>`;el('msg').textContent='Výsledek lekce byl uložen.'}else{el('controls').innerHTML=`<div class="finish"><h3>Správně: NSN = ${d.result}</h3><button class="primary" onclick="call('new')">Další příklad</button></div>`}}}
el('new').onclick=()=>call('new');call('new').catch(e=>el('msg').textContent=e.message);


// Stejná studentská vědecká kalkulačka jako v běžných matematických lekcích UČEBNICE 2.0.
let calculatorAngleMode='DEG';
function toggleCalculator(){
 const panel=document.getElementById('student-calculator'), btn=document.getElementById('calc-toggle');
 if(!panel||!btn)return;
 panel.hidden=!panel.hidden; btn.textContent=panel.hidden?'Otevřít kalkulačku':'Skrýt kalkulačku';
 if(!panel.hidden) document.getElementById('calc-expression').focus();
}
function toggleAngleMode(){ calculatorAngleMode=calculatorAngleMode==='DEG'?'RAD':'DEG'; document.getElementById('calc-angle-mode').textContent=calculatorAngleMode; }
function calcInsert(txt){ const e=document.getElementById('calc-expression'); const a=e.selectionStart??e.value.length,b=e.selectionEnd??e.value.length; e.value=e.value.slice(0,a)+txt+e.value.slice(b); const p=a+txt.length; e.focus(); e.setSelectionRange(p,p); }
function calcClear(){ document.getElementById('calc-expression').value=''; const r=document.getElementById('calc-result'); r.textContent='0'; r.classList.remove('calc-error'); }
function calcEvaluate(){
 const input=document.getElementById('calc-expression'), out=document.getElementById('calc-result');
 try{
   let src=input.value.trim().replace(/,/g,'.').replace(/\^/g,'**');
   if(!src) throw new Error('Zadej výpočet');
   if(!/^[0-9A-Za-z_+\-*/().\s]+$/.test(src)) throw new Error('Nepovolený znak');
   const names=(src.match(/[A-Za-z_]+/g)||[]);
   const allowed=new Set(['sin','cos','tan','asin','acos','atan','sqrt','log','ln','abs','pi','e']);
   if(names.some(n=>!allowed.has(n))) throw new Error('Nepovolená funkce');
   const toRad=x=>calculatorAngleMode==='DEG'?x*Math.PI/180:x;
   const fromRad=x=>calculatorAngleMode==='DEG'?x*180/Math.PI:x;
   const funcs={sin:x=>Math.sin(toRad(x)),cos:x=>Math.cos(toRad(x)),tan:x=>Math.tan(toRad(x)),asin:x=>fromRad(Math.asin(x)),acos:x=>fromRad(Math.acos(x)),atan:x=>fromRad(Math.atan(x)),sqrt:Math.sqrt,log:Math.log10,ln:Math.log,abs:Math.abs,pi:Math.PI,e:Math.E};
   const fn=new Function(...Object.keys(funcs),'"use strict"; return ('+src+');');
   const value=fn(...Object.values(funcs));
   if(typeof value!=='number'||!Number.isFinite(value)) throw new Error('Výsledek není platné číslo');
   out.textContent=Number(value.toPrecision(12)).toString().replace('.',','); out.classList.remove('calc-error');
 }catch(e){ out.textContent='Chyba: '+e.message; out.classList.add('calc-error'); }
}
document.addEventListener('DOMContentLoaded',()=>{ const c=document.getElementById('calc-expression'); if(c)c.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();calcEvaluate();}}); });
