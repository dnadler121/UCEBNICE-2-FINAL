
const sequence = [
  "multiply",
  "divide",
  "powerPower",
  "productPower",
  "negative",
  "multiply",
  "divide",
  "powerPower",
  "factor",
  "productPower",
  "negative",
  "factor"
];

let index=0, ex=null, phase="", errors=0, pending=null;

const expression=document.getElementById("expression");
const workspace=document.getElementById("workspace");
const teacher=document.getElementById("teacher");
const teacherText=document.getElementById("teacherText");
const continueBtn=document.getElementById("continueBtn");
const nextBtn=document.getElementById("nextBtn");
const returnBtn=document.getElementById("returnBtn");
function gradeFromPercent(percent) {
  if (percent >= 95) return 1;
  if (percent >= 90) return 2;
  if (percent >= 85) return 3;
  if (percent >= 80) return 4;
  return 5;
}

returnBtn.onclick=async()=>{
  const completed=index+(phase==="done"?1:0);
  const percent=Math.round((completed/sequence.length)*100);
  const grade=gradeFromPercent(percent);
  returnBtn.disabled=true;
  returnBtn.textContent="Ukládám výsledek…";
  try{
    const response=await fetch(window.LESSON_URLS.completeLesson,{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({percent,grade})
    });
    const data=await response.json();
    if(!response.ok||!data.ok)throw new Error(data.error||"Výsledek se nepodařilo uložit.");
    window.location.href=window.LESSON_URLS.portal;
  }catch(error){
    returnBtn.disabled=false;
    returnBtn.textContent="← Ukončit a uložit výsledek";
    say(error.message||"Výsledek se nepodařilo uložit.","bad");
  }
};

function rnd(min,max){return min+Math.floor(Math.random()*(max-min+1))}
function pow(base,exp){
  return `<span class="pow"><span class="base">${base}</span><span class="exp">${exp}</span></span>`;
}
function frac(top,bottom){
  return `<span class="frac"><span class="top">${top}</span><span class="bottom">${bottom}</span></span>`;
}
function say(text,kind=""){teacher.className="teacher"+(kind?" "+kind:"");teacherText.textContent=text}
function bump(messages){errors++;say(messages[Math.min(errors-1,messages.length-1)],"error")}
function hideContinue(){pending=null;continueBtn.classList.add("hidden")}
function offerContinue(text,cb){pending=cb;continueBtn.classList.remove("hidden");say(text,"good")}
continueBtn.onclick=()=>{if(!pending)return;const cb=pending;hideContinue();cb()};

function makeExample(type){
  if(type==="multiply"){
    const base=rnd(2,12), a=rnd(2,8), b=rnd(1,7), third=Math.random()<.4?rnd(1,5):null;
    return {type,base,a,b,third,result:a+b+(third||0)};
  }
  if(type==="divide"){
    const base=rnd(2,12), b=rnd(1,6), result=rnd(1,7), a=b+result;
    return {type,base,a,b,result};
  }
  if(type==="powerPower"){
    const base=rnd(2,10), a=rnd(2,6), b=rnd(2,6);
    return {type,base,a,b,result:a*b};
  }
  if(type==="productPower"){
    return {type,a:rnd(2,9),b:rnd(2,9),exp:rnd(2,6)};
  }
  if(type==="negative"){
    const base=rnd(2,10), exp=rnd(2,9);
    return {type,base,exp,positive:exp%2===0};
  }
  const k=rnd(2,7);
  return {type,k};
}

function label(type){
  return ({
    multiply:"Násobení mocnin se stejným základem",
    divide:"Dělení mocnin se stejným základem",
    powerPower:"Mocnina mocniny",
    productPower:"Mocnina součinu",
    negative:"Záporný základ",
    factor:"Vytýkání společné mocniny"
  })[type];
}

function renderOriginal(){
  const t=ex.type;
  if(t==="multiply"){
    expression.innerHTML=`${pow(ex.base,ex.a)}<span class="op">·</span>${pow(ex.base,ex.b)}`
      +(ex.third?`<span class="op">·</span>${pow(ex.base,ex.third)}`:"");
  }
  if(t==="divide"){
    expression.innerHTML=frac(pow(ex.base,ex.a),pow(ex.base,ex.b));
  }
  if(t==="powerPower"){
    expression.innerHTML=`(${pow(ex.base,ex.a)})${pow("",ex.b)}`;
  }
  if(t==="productPower"){
    expression.innerHTML=pow(`(${ex.a} · ${ex.b})`,ex.exp);
  }
  if(t==="negative"){
    expression.innerHTML=pow(`(−${ex.base})`,ex.exp);
  }
  if(t==="factor"){
    expression.innerHTML=`${pow(100,3)}<span class="op">−</span>${pow(ex.k*100,2)}`;
  }
}

function startRule(){
  phase="rule"; errors=0;
  let choices=[];
  if(ex.type==="multiply")choices=[["add","Mocnitele sečtu"],["sub","Mocnitele odečtu"],["mul","Mocnitele vynásobím"]];
  if(ex.type==="divide")choices=[["sub","Mocnitele odečtu"],["add","Mocnitele sečtu"],["mul","Mocnitele vynásobím"]];
  if(ex.type==="powerPower")choices=[["mul","Mocnitele vynásobím"],["add","Mocnitele sečtu"],["sub","Mocnitele odečtu"]];
  if(ex.type==="productPower")choices=[["split","Stejný mocnitel rozdělím na oba činitele"],["first","Umocním jen první činitel"],["sum","Činitele sečtu"]];
  if(ex.type==="negative")choices=[["parity","Nejdřív určím, zda je mocnitel sudý nebo lichý"],["plus","Výsledek je vždy kladný"],["minus","Výsledek je vždy záporný"]];
  if(ex.type==="factor")choices=[["rewrite","Přepíšu druhý člen pomocí 100 a hledám společnou mocninu"],["calc","Všechno hned dopočítám"],["subexp","Odečtu mocnitele"]];

  workspace.innerHTML=`<section class="panel">
    <h2>1. Vyber správné pravidlo</h2>
    <div class="choice-grid">${choices.map(([id,text])=>`<button class="choice" onclick="chooseRule('${id}')">${text}</button>`).join("")}</div>
  </section>`;
  say("Nejdřív rozhodni, jaké pravidlo se v tomto výrazu používá.");
  document.getElementById("stage").textContent="Pravidlo";
}

window.chooseRule=function(choice){
  const correct=({
    multiply:"add",
    divide:"sub",
    powerPower:"mul",
    productPower:"split",
    negative:"parity",
    factor:"rewrite"
  })[ex.type];

  if(choice!==correct){
    bump([
      "Toto pravidlo sem nepatří. Podívej se na operaci a na základy mocnin.",
      ex.type==="multiply"?"Při násobení stejných základů mocnitele sčítáme.":
      ex.type==="divide"?"Při dělení stejných základů mocnitele odečítáme.":
      ex.type==="powerPower"?"U mocniny mocniny mocnitele násobíme.":
      ex.type==="productPower"?"Mocnina součinu patří ke každému činiteli.":
      ex.type==="negative"?"Znaménko závisí na sudosti nebo lichosti mocnitele.":
      "Přepiš druhý člen tak, aby byla vidět společná mocnina 100."
    ]);
    return;
  }
  offerContinue("Správně. Klikni na Pokračovat a uprav výraz.",startTransform);
};

function startTransform(){
  errors=0;
  document.getElementById("stage").textContent="Úprava výrazu";

  if(ex.type==="multiply"){
    const text=ex.third?`${ex.a} + ${ex.b} + ${ex.third}`:`${ex.a} + ${ex.b}`;
    expression.innerHTML=pow(ex.base,text);
    workspace.innerHTML=`<section class="panel"><h2>2. Sečti mocnitele</h2>
      <div class="math-line">${pow(ex.base,'<input id="expInput">')}</div>
      <div class="math-line"><button onclick="checkExponent()">Zkontrolovat</button></div></section>`;
    say("Základ zůstává stejný. Sečti pouze mocnitele.");
  }

  if(ex.type==="divide"){
    expression.innerHTML=pow(ex.base,`${ex.a} − ${ex.b}`);
    workspace.innerHTML=`<section class="panel"><h2>2. Odečti mocnitele</h2>
      <div class="math-line">${pow(ex.base,'<input id="expInput">')}</div>
      <div class="math-line"><button onclick="checkExponent()">Zkontrolovat</button></div></section>`;
    say("Od horního mocnitele odečti dolní.");
  }

  if(ex.type==="powerPower"){
    expression.innerHTML=pow(ex.base,`${ex.a} · ${ex.b}`);
    workspace.innerHTML=`<section class="panel"><h2>2. Vynásob mocnitele</h2>
      <div class="math-line">${pow(ex.base,'<input id="expInput">')}</div>
      <div class="math-line"><button onclick="checkExponent()">Zkontrolovat</button></div></section>`;
    say("Základ zůstává stejný. Mocnitele se násobí.");
  }

  if(ex.type==="productPower"){
    expression.innerHTML=`${pow(ex.a,ex.exp)}<span class="op">·</span>${pow(ex.b,ex.exp)}`;
    workspace.innerHTML=`<section class="panel"><h2>2. Doplň mocnitele</h2>
      <div class="math-line">${pow(ex.a,'<input id="expA">')} · ${pow(ex.b,'<input id="expB">')}</div>
      <div class="math-line"><button onclick="checkProductPower()">Zkontrolovat</button></div></section>`;
    say("Stejný mocnitel patří k oběma činitelům.");
  }

  if(ex.type==="negative"){
    workspace.innerHTML=`<section class="panel"><h2>2. Urči znaménko</h2>
      <div class="choice-grid">
        <button class="choice" onclick="checkNegative(true)">Výraz bude kladný</button>
        <button class="choice" onclick="checkNegative(false)">Výraz bude záporný</button>
      </div>
      <div class="rule-box">Sudý mocnitel → kladný výraz. Lichý mocnitel → záporný výraz.</div>
    </section>`;
    say("Rozhodni podle toho, zda je mocnitel sudý nebo lichý.");
  }

  if(ex.type==="factor"){
    expression.innerHTML=`${pow(100,3)} − (${ex.k} · 100)${pow("",2)}`;
    workspace.innerHTML=`<section class="panel"><h2>2. Rozděl mocninu součinu</h2>
      <div class="math-line">${pow(100,3)} − ${pow(ex.k,'<input id="kExp">')} · ${pow(100,'<input id="hExp">')}</div>
      <div class="math-line"><button onclick="checkFactorRewrite()">Zkontrolovat</button></div></section>`;
    say("Dvojka patří k číslu "+ex.k+" i k číslu 100.");
  }
}

window.checkExponent=function(){
  if(+expInput.value!==ex.result){
    bump([
      "Výsledný mocnitel není správný.",
      ex.type==="multiply"?"Sečti všechny mocnitele.":ex.type==="divide"?"Odečti dolní mocnitel od horního.":"Vynásob oba mocnitele."
    ]);
    return;
  }
  expression.innerHTML=pow(ex.base,ex.result);
  complete();
};

window.checkProductPower=function(){
  if(+expA.value!==ex.exp || +expB.value!==ex.exp){
    bump(["Mocnitel musí být u obou činitelů stejný.",`Ke každému činiteli patří mocnitel ${ex.exp}.`]);
    return;
  }
  expression.innerHTML=`${pow(ex.a,ex.exp)}<span class="op">·</span>${pow(ex.b,ex.exp)}`;
  complete();
};

window.checkNegative=function(isPositive){
  if(isPositive!==ex.positive){
    bump([
      "Znaménko není správně.",
      ex.positive?"Mocnitel je sudý, proto je výraz kladný.":"Mocnitel je lichý, proto je výraz záporný."
    ]);
    return;
  }
  expression.innerHTML=ex.positive?pow(ex.base,ex.exp):`−${pow(ex.base,ex.exp)}`;
  complete();
};

window.checkFactorRewrite=function(){
  if(+kExp.value!==2 || +hExp.value!==2){
    bump(["Mocnina součinu není rozdělena správně.",`Dvojka musí být u ${ex.k} i u 100.`]);
    return;
  }
  offerContinue("Přepis je správný. Klikni na Pokračovat a vytkni společnou mocninu.",showFactoring);
};

function showFactoring(){
  expression.innerHTML=`100 · ${pow(100,2)} − ${pow(ex.k,2)} · ${pow(100,2)}`;
  workspace.innerHTML=`<section class="panel"><h2>3. Vytkni společný činitel</h2>
    <div class="math-line">${pow(100,2)} · ( <input id="insideA"> − ${pow(ex.k,2)} )</div>
    <div class="math-line"><button onclick="checkFactoring()">Zkontrolovat</button></div></section>`;
  say("Společný činitel je 100². Z prvního členu zůstane číslo 100.");
  document.getElementById("stage").textContent="Vytýkání";
}

window.checkFactoring=function(){
  if(+insideA.value!==100){
    bump(["Číslo v závorce není správné.","Po vytknutí 100² z prvního členu zůstane 100."]);
    return;
  }
  expression.innerHTML=`${pow(100,2)} · (100 − ${pow(ex.k,2)})`;
  complete();
};

function complete(){
  hideContinue();
  phase="done";
  workspace.innerHTML=`<div class="success">Hotovo. Výraz je upraven do nejjednoduššího tvaru ✓</div>`;
  say("Výborně. Nic dalšího už není potřeba dopočítávat.","good");
  nextBtn.disabled=false;
  document.getElementById("fill").style.width=((index+1)/sequence.length*100)+"%";
  document.getElementById("stage").textContent="Hotovo";
}

document.getElementById("hintBtn").onclick=()=>{
  if(phase==="rule"){say("Podívej se na operaci a na to, zda mají mocniny stejný základ.");return}
  if(phase==="done"){say("Příklad je hotový. Můžeš pokračovat na další.");return}
  say("Použij pravidlo, které je právě zobrazené. Cílem není číslo dopočítat, ale upravit výraz.");
};

nextBtn.onclick=()=>{
  if(nextBtn.disabled)return;
  index++;
  if(index>=sequence.length){
    workspace.innerHTML=`<div class="success">Celá lekce je dokončena ✓</div>`;
    expression.innerHTML="";
    say("Zvládl jsi všech dvanáct příkladů.","good");
    nextBtn.disabled=true;
    document.getElementById("fill").style.width="100%";
    document.getElementById("counter").textContent=`Dokončeno ${sequence.length} / ${sequence.length}`;
    document.getElementById("stage").textContent="Lekce dokončena";

    // Výsledek se ukládá pouze podle míry dokončení, nikoli podle počtu chyb.
    // Dokončená celá lekce = 100 % = známka 1.
    // Tlačítko se zobrazí okamžitě a nezávisí na výsledku ukládání.
    fetch(window.LESSON_URLS.completeLesson,{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({percent:100,grade:1})
    }).catch(()=>{});
    return;
  }
  start();
};

function start(){
  hideContinue();
  nextBtn.disabled=true;
  errors=0;
  ex=makeExample(sequence[index]);
  document.getElementById("counter").textContent=`Příklad ${index+1} / ${sequence.length}`;
  document.getElementById("badge").textContent=label(ex.type);
  renderOriginal();
  startRule();
}

start();
