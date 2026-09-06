
const sequence=["add","subtract","multiply","divide","add","multiply","subtract","divide","add","multiply","subtract","divide"];
let index=0, ex=null, phase="", selected=null, errors=0;
const workspace=document.getElementById("workspace");
const teacher=document.getElementById("teacher");
const teacherText=document.getElementById("teacherText");
const nextBtn=document.getElementById("nextBtn");
const returnBtn=document.getElementById("returnBtn");

function gradeFromPercent(percent){
 if(percent>=95)return 1;
 if(percent>=90)return 2;
 if(percent>=85)return 3;
 if(percent>=80)return 4;
 return 5;
}

async function saveAndReturn(){
 const completed=index+(phase==="done"?1:0);
 const percent=Math.round((completed/sequence.length)*100);
 const grade=gradeFromPercent(percent);
 returnBtn.disabled=true;
 returnBtn.textContent="Ukládám výsledek…";
 try{
  const response=await fetch(window.LESSON_URLS.completeLesson,{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify({percent,grade})
  });
  const data=await response.json();
  if(!response.ok||!data.ok)throw new Error(data.error||"Výsledek se nepodařilo uložit.");
  window.location.href=window.LESSON_URLS.portal;
 }catch(error){
  returnBtn.disabled=false;
  returnBtn.textContent="← Ukončit a uložit výsledek";
  say(error.message||"Výsledek se nepodařilo uložit.","error");
 }
}
returnBtn.onclick=saveAndReturn;

function rand(){return 1+Math.floor(Math.random()*9)}
function gcd(a,b){while(b){[a,b]=[b,a%b]}return Math.abs(a)}
function lcm(a,b){return Math.abs(a*b)/gcd(a,b)}
function isPrime(n){if(n<2)return false;for(let i=2;i*i<=n;i++)if(n%i===0)return false;return true}
function token(value,group){return{id:crypto.randomUUID(),value,group,used:false,removed:false}}
function makeGroup(value,name){return{name,tokens:[token(value,name)]}}
function frac(top,bottom){return `<span class="frac"><span class="top">${top}</span><span class="bottom">${bottom}</span></span>`}
function say(msg,kind=""){teacher.className="teacher"+(kind?" "+kind:"");teacherText.textContent=msg}
function bump(msgs){errors++;say(msgs[Math.min(errors-1,msgs.length-1)],"error")}
function visible(g){return g.tokens.filter(t=>!t.removed)}
function product(g){return visible(g).reduce((p,t)=>p*t.value,1)}
function allPrime(groups){return groups.every(g=>g.tokens.every(t=>t.removed||t.value===1||isPrime(t.value)))}
function label(type){return({add:"Sčítání zlomků",subtract:"Odčítání zlomků",multiply:"Násobení zlomků",divide:"Dělení zlomků"})[type]}
function sign(type){return({add:"+",subtract:"−",multiply:"·",divide:":"})[type]}

function makeExample(type){
 let a=rand(),b=2+Math.floor(Math.random()*8),c=rand(),d=2+Math.floor(Math.random()*8);
 if(type==="subtract"){
   while(a/b<=c/d){a=rand();b=2+Math.floor(Math.random()*8);c=rand();d=2+Math.floor(Math.random()*8)}
 }
 return{
   type,a,b,c,d,
   an:makeGroup(a,"an"), ad:makeGroup(b,"ad"),
   bn:makeGroup(c,"bn"), bd:makeGroup(d,"bd")
 };
}
function originalTop(){
 document.getElementById("mainExample").innerHTML=
   `${frac(ex.a,ex.b)}<span class="op">${sign(ex.type)}</span>${frac(ex.c,ex.d)}`;
}
function renderToken(t){
 return `<span class="factor ${t.used?"used":""} ${selected&&selected.id===t.id?"selected":""}" data-id="${t.id}">${t.value}</span>`;
}
function renderGroup(g){
 const v=visible(g);
 if(!v.length)return `<span class="factor used">1</span>`;
 return v.map(renderToken).join("<span>·</span>");
}
function findToken(id){
 for(const g of [ex.an,ex.ad,ex.bn,ex.bd]){
   const t=g.tokens.find(x=>x.id===id);if(t)return{t,g};
 }
}
function bindTokens(){
 document.querySelectorAll(".factor[data-id]").forEach(el=>el.onclick=()=>tokenClick(el.dataset.id));
}
function splitButtonsFor(t,targetId){
 const ds=[2,3,5,7].filter(d=>t.value%d===0&&t.value!==d);
 document.getElementById(targetId).innerHTML=ds.map(d=>`<button onclick="splitSelected(${d})">${t.value} = ${d} · ${t.value/d}</button>`).join("");
}
window.splitSelected=function(d){
 const f=findToken(selected.id),t=f.t,g=f.g,idx=g.tokens.indexOf(t);
 g.tokens.splice(idx,1,token(d,g.name),token(t.value/d,g.name));
 selected=null;errors=0;
 if(ex.type==="add"||ex.type==="subtract")renderNSN();
 else renderMulDiv();
}

function tokenClick(id){
 const f=findToken(id),t=f.t;
 if(t.used){say("Tento prvočinitel už byl použit a nelze ho použít znovu.","error");return}
 if(phase==="nsnSplit"||phase==="mulSplit"){
   if(t.value===1||isPrime(t.value)){say(`${t.value} je prvočíslo nebo jednička. Dál ho rozkládat nelze.`,"error");return}
   selected=t;
   if(phase==="nsnSplit")renderNSN();else renderMulDiv();
   splitButtonsFor(t,"splitButtons");
   say(`Vybral jsi ${t.value}. Rozlož ho prvočíslem.`);
   return;
 }
 if(phase==="nsnPair")pairNSN(t);
 if(phase==="cancel")cancelPair(t);
}

function startAddSub(){
 phase="nsnSplit";selected=null;errors=0;
 renderNSN();
 say("Nejdříve rozlož oba jmenovatele na prvočísla.");
}
function renderNSN(){
 workspace.innerHTML=`
 <section class="panel">
  <h2>1. Urči NSN jmenovatelů</h2>
  <div class="factor-lines">
   <div class="factor-line"><b>${ex.b} =</b><div class="factors">${renderGroup(ex.ad)}</div></div>
   <div class="factor-line"><b>${ex.d} =</b><div class="factors">${renderGroup(ex.bd)}</div></div>
  </div>
  <div id="splitButtons" class="buttons"></div>
  <div id="nsnInputArea" class="answer-box"></div>
 </section>`;
 bindTokens();
 if(allPrime([ex.ad,ex.bd])&&phase==="nsnSplit"){
   phase="nsnPair";selected=null;renderNSN();
   say("Rozklad je hotový. Spojuj stejné prvočinitele. Z dvojice jedno číslo zmizí a druhé zčervená.","good");
 }
 if(phase==="nsnPair"&&!hasNSNPair())showNSNInput();
}
function hasNSNPair(){
 const A=visible(ex.ad).filter(t=>!t.used),B=visible(ex.bd).filter(t=>!t.used);
 return A.some(a=>B.some(b=>a.value===b.value));
}
function pairNSN(t){
 if(!selected){selected=t;renderNSN();say(t.group==="ad"?"Vyber stejné číslo ve druhém jmenovateli.":"Vyber stejné číslo v prvním jmenovateli.");return}
 if(selected.group===t.group){selected=t;renderNSN();say("Druhé číslo musí být z druhého jmenovatele.","error");return}
 if(selected.value!==t.value){selected=null;renderNSN();bump(["Spojit lze jen stejná prvočísla.","Obě čísla musí mít stejnou hodnotu.","Najdi například dvojici 2 a 2 nebo 3 a 3."]);return}
 const keep=selected.group==="ad"?selected:t;
 const remove=selected.group==="bd"?selected:t;
 keep.used=true;remove.removed=true;selected=null;renderNSN();
 say("Správně. Jedno číslo zmizelo a druhé je už použité.","good");
}
function showNSNInput(){
 const area=document.getElementById("nsnInputArea");
 area.innerHTML=`NSN = <input id="nsnValue"><button onclick="checkNSN()">Zkontrolovat</button>`;
 say("Vynásob všechna čísla, která zůstala. Tím získáš NSN.","good");
 phase="nsnAnswer";
}
window.checkNSN=function(){
 const n=lcm(ex.b,ex.d);
 if(+document.getElementById("nsnValue").value!==n){bump(["NSN není správně.","Vynásob prvočinitele, které zůstaly po spojování.","Společný prvočinitel použij jen jednou."]);return}
 ex.nsn=n;ex.left=ex.a*(n/ex.b);ex.right=ex.c*(n/ex.d);
 phase="expand";errors=0;
 workspace.innerHTML=`<section class="panel"><h2>2. Rozšiř oba zlomky</h2>
 <div class="main-example">${frac('<input id="leftN">',n)}<span class="op">${sign(ex.type)}</span>${frac('<input id="rightN">',n)}</div>
 <div class="answer-box"><button onclick="checkExpand()">Zkontrolovat čitatele</button></div></section>`;
 say("Doplň nové čitatele. Zjisti, čím se každý jmenovatel násobil, a stejným číslem vynásob čitatel.","good");
 document.getElementById("stage").textContent="Rozšíření zlomků";
}
window.checkExpand=function(){
 if(+leftN.value!==ex.left||+rightN.value!==ex.right){bump(["Nové čitatele nejsou správné.","Vyděl NSN původním jmenovatelem.","Stejným číslem potom vynásob původní čitatel."]);return}
 ex.raw=ex.type==="add"?ex.left+ex.right:ex.left-ex.right;
 phase="addResult";errors=0;
 workspace.innerHTML=`<section class="panel"><h2>3. ${ex.type==="add"?"Sečti":"Odečti"} čitatele</h2>
 <div class="main-example">${frac(ex.left,ex.nsn)}<span class="op">${sign(ex.type)}</span>${frac(ex.right,ex.nsn)}
 <span class="equals">=</span>${frac('<input id="rawN">',ex.nsn)}</div>
 <div class="answer-box"><button onclick="checkAddResult()">Zkontrolovat</button></div></section>`;
 say("Jmenovatel zůstává stejný. Vypočítej pouze čitatele.","good");
 document.getElementById("stage").textContent="Výpočet čitatele";
}
window.checkAddResult=function(){
 if(+rawN.value!==ex.raw){bump(["Čitatel není správně.","Počítej pouze čísla nahoře.","Zkontroluj znaménko mezi zlomky."]);return}
 if(gcd(ex.raw,ex.nsn)===1){complete(ex.raw,ex.nsn);return}
 setupFinalReduction(ex.raw,ex.nsn);
}

function startMulDiv(){
 phase="mulSplit";selected=null;errors=0;
 if(ex.type==="divide"){
   [ex.bn,ex.bd]=[ex.bd,ex.bn];
   [ex.c,ex.d]=[ex.d,ex.c];
   document.getElementById("mainExample").innerHTML=
     `${frac(ex.a,ex.b)}<span class="op">·</span>${frac(ex.c,ex.d)}`;
   say("Při dělení jsme druhý zlomek převrátili. Teď pokračujeme jako při násobení.","good");
 }else say("Nejdříve rozlož všechna čtyři čísla na prvočísla.");
 renderMulDiv();
}
function renderMulDiv(){
 workspace.innerHTML=`<section class="panel"><h2>1. Rozlož čísla na prvočísla</h2>
 <div class="main-example">${frac(renderGroup(ex.an),renderGroup(ex.ad))}<span class="op">·</span>${frac(renderGroup(ex.bn),renderGroup(ex.bd))}</div>
 <div id="splitButtons" class="buttons"></div></section>`;
 bindTokens();
 if(allPrime([ex.an,ex.ad,ex.bn,ex.bd])&&phase==="mulSplit"){
   phase="cancel";selected=null;renderMulDiv();
   say("Rozklad je hotový. Teď kracuj napříč celým součinem: stejné prvočíslo nahoře a dole po kliknutí zmizí.","good");
   document.getElementById("stage").textContent="Krácení před násobením";
 }
 if(phase==="cancel"&&!hasCancelPair())finishMulCancellation();
}
function numeratorGroups(){return [ex.an,ex.bn]}
function denominatorGroups(){return [ex.ad,ex.bd]}
function inGroups(t,groups){return groups.some(g=>g.name===t.group)}
function hasCancelPair(){
 const N=numeratorGroups().flatMap(g=>visible(g));
 const D=denominatorGroups().flatMap(g=>visible(g));
 return N.some(n=>D.some(d=>n.value===d.value&&n.value!==1));
}
function cancelPair(t){
 if(!selected){selected=t;renderMulDiv();say(inGroups(t,numeratorGroups())?"Teď vyber stejné číslo dole.":"Teď vyber stejné číslo nahoře.");return}
 const first=selected;
 if(inGroups(first,numeratorGroups())===inGroups(t,numeratorGroups())){
   selected=t;renderMulDiv();say("Musíš vybrat jedno číslo z čitatele a jedno ze jmenovatele.","error");return
 }
 if(first.value!==t.value){selected=null;renderMulDiv();bump(["Krátit lze jen stejnými prvočiniteli.","Obě označená čísla musí mít stejnou hodnotu.","Najdi například 2 nahoře a 2 dole."]);return}
 first.removed=true;t.removed=true;selected=null;renderMulDiv();
 say("Správně. Obě čísla zmizela. Pokračuj, dokud už žádná společná dvojice nezůstane.","good");
}
function finishMulCancellation(){
 phase="multiplyFinal";errors=0;
 const n=numeratorGroups().reduce((p,g)=>p*product(g),1);
 const d=denominatorGroups().reduce((p,g)=>p*product(g),1);
 ex.finalN=n;ex.finalD=d;
 workspace.innerHTML=`<section class="panel"><h2>2. Vynásob čísla, která zůstala</h2>
 <div class="main-example">
 ${frac(numeratorGroups().map(renderGroup).join(" · "),denominatorGroups().map(renderGroup).join(" · "))}
 <span class="equals">=</span>${frac('<input id="finalN">','<input id="finalD">')}
 </div>
 <div class="answer-box"><button onclick="checkMulFinal()">Dokončit příklad</button></div></section>`;
 say("Všechno možné je vykráceno. Teď vynásob pouze čísla, která zůstala.","good");
 document.getElementById("stage").textContent="Násobení zbylých čísel";
}
window.checkMulFinal=function(){
 if(+finalN.value!==ex.finalN||+finalD.value!==ex.finalD){bump(["Výsledek není správný.","Vynásob pouze čísla, která po krácení zůstala.","Zmizelá čísla už do výsledku nepatří."]);return}
 complete(ex.finalN,ex.finalD);
}

function setupFinalReduction(n,d){
 ex.an=makeGroup(n,"an");ex.ad=makeGroup(d,"ad");ex.bn=makeGroup(1,"bn");ex.bd=makeGroup(1,"bd");
 phase="mulSplit";selected=null;errors=0;
 document.getElementById("mainExample").innerHTML=frac(n,d);
 renderMulDiv();
 say("Výsledek ještě lze krátit. Rozlož čitatele a jmenovatele a potom stejné prvočinitele nech zmizet.","good");
}
function complete(n,d){
 phase="done";
 workspace.innerHTML=`<div class="success">Hotovo: ${frac(n,d)}</div><div class="note">Celý příklad je dokončen. Odemklo se tlačítko Další příklad.</div>`;
 say("Výborně. Dokončil jsi celý postup správně.","good");
 nextBtn.disabled=false;
 document.getElementById("bar").style.width=((index+1)/sequence.length*100)+"%";
 document.getElementById("stage").textContent="Příklad dokončen";
}
document.getElementById("hintBtn").onclick=()=>{
 const hints={
  nsnSplit:"Klikni na složený jmenovatel a rozlož ho nejmenším prvočíslem.",
  nsnPair:"Hledej stejné prvočíslo v obou jmenovatelích.",
  nsnAnswer:"Vynásob prvočinitele, které po spojování zůstaly.",
  expand:"Vyděl NSN původním jmenovatelem a tímto číslem vynásob čitatel.",
  addResult:"Počítej pouze čitatele. Společný jmenovatel se nemění.",
  mulSplit:"Klikni na složené číslo přímo ve zlomku a postupně ho rozlož.",
  cancel:"Hledej stejné prvočíslo kdekoliv nahoře a kdekoliv dole.",
  multiplyFinal:"Vynásob pouze čísla, která po krácení zůstala."
 };
 say(hints[phase]||"Dokonči právě zobrazený krok.");
}
nextBtn.onclick=()=>{if(nextBtn.disabled)return;index++;if(index>=sequence.length){
 say("Lekce je dokončena.","good");
 nextBtn.disabled=true;
 document.getElementById("bar").style.width="100%";
 document.getElementById("counter").textContent=`Dokončeno ${sequence.length} / ${sequence.length}`;
 document.getElementById("stage").textContent="Lekce dokončena";
 fetch(window.LESSON_URLS.completeLesson,{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({percent:100,grade:1})
 }).catch(()=>{});
 return
}start()}
function start(){
 ex=makeExample(sequence[index]);phase="";selected=null;errors=0;nextBtn.disabled=true;
 document.getElementById("counter").textContent=`Příklad ${index+1} / ${sequence.length}`;
 document.getElementById("stage").textContent="Začínáme";
 document.getElementById("operationBadge").textContent=label(ex.type);
 originalTop();
 if(ex.type==="add"||ex.type==="subtract")startAddSub();else startMulDiv();
}
start();
