"""Live shared integer maths classroom, persistent SQLite polling (no websocket dependency)."""
import io, json, secrets, sqlite3, time
from flask import request, jsonify, render_template_string, send_file, redirect

TEACHER = '''<!doctype html><html lang="cs"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Živá matematika – učitel</title><style>body{font:17px system-ui;background:#eef4fb;color:#142d50;margin:0}main{max-width:1080px;margin:auto;padding:24px}.card{background:white;padding:22px;margin:15px 0;border-radius:18px;box-shadow:0 4px 16px #142d5015}button,input,select{font:inherit;padding:11px;border:1px solid #bbcde3;border-radius:10px;margin:4px}button{background:#1267c6;color:white;cursor:pointer}h1{margin:0}.row{display:flex;flex-wrap:wrap;gap:16px;align-items:center}.pin{font-size:40px;font-weight:800;letter-spacing:6px}.small{color:#536b89}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid #dce6f2}#qr{width:190px;height:190px}#answer{font-size:24px;font-weight:bold}.hidden{display:none}</style><main><h1>🔴🔵 Živá matematika – učitel</h1><p><a href="/teacher">← Zpět do Učebnice FINAL</a></p><div class="card"><button onclick="createRoom()">Založit novou hodinu</button><span id="msg" class="small"></span><div id="room" class="hidden"><div class="row"><div><p>PIN pro žáky</p><div class="pin" id="pin"></div><p>Adresa: <a id="joinLink" target="_blank"></a></p><button onclick="navigator.clipboard.writeText(document.getElementById('joinLink').href)">Kopírovat odkaz</button></div><img id="qr" alt="QR kód pro připojení žáků"></div></div></div><div id="control" class="card hidden"><h2>Společný příklad</h2><div class="row"><label>Operace <select id="op"><option value="+">Sčítání +</option><option value="-">Odčítání −</option><option value="*">Násobení ×</option><option value="/">Dělení ÷</option></select></label><label>První číslo <input id="a" type="number" value="-6" style="width:95px"></label><label>Druhé číslo <input id="b" type="number" value="3" style="width:95px"></label><button onclick="publish()">Zadat všem žákům</button><button onclick="reveal()">Ukázat řešení</button></div><p id="current" class="small">Zatím žádný příklad.</p><p id="answer"></p><p class="small">Při dělení zadávej příklady s celočíselným výsledkem. Výsledky se obnovují automaticky.</p></div><div id="students" class="card hidden"><h2>Žáci a živé odpovědi</h2><p id="count"></p><table><thead><tr><th>Žák</th><th>Odpověď</th><th>Stav</th><th>Úspěšnost</th></tr></thead><tbody id="rows"></tbody></table></div></main><script>
let pin=localStorage.getItem('liveMathTeacherPin')||'';let lastQ=0;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,body){let r=await fetch('/live-math/api/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});let j=await r.json();if(!r.ok)throw Error(j.error||'Chyba');return j}
function show(){document.getElementById('room').classList.remove('hidden');document.getElementById('control').classList.remove('hidden');document.getElementById('students').classList.remove('hidden');document.getElementById('pin').textContent=pin;let url=location.origin+'/live-math/join?pin='+pin;let a=document.getElementById('joinLink');a.href=url;a.textContent=url;document.getElementById('qr').src='/live-math/qr/'+pin}
async function createRoom(){try{let j=await api('create',{});pin=j.pin;localStorage.setItem('liveMathTeacherPin',pin);show();poll()}catch(e){document.getElementById('msg').textContent=e.message}}
async function publish(){try{await api('question',{pin,a:+document.getElementById('a').value,b:+document.getElementById('b').value,op:document.getElementById('op').value});poll()}catch(e){alert(e.message)}}
async function reveal(){try{await api('reveal',{pin});poll()}catch(e){alert(e.message)}}
async function poll(){if(!pin)return;try{let r=await fetch('/live-math/api/state?pin='+encodeURIComponent(pin));let j=await r.json();if(!r.ok){localStorage.removeItem('liveMathTeacherPin');pin='';return}show();let q=j.question;if(q){document.getElementById('current').textContent='Příklad č. '+q.id+': '+q.a+' '+({'*':'×','/':'÷'}[q.op]||q.op)+' '+q.b+' = ?';document.getElementById('answer').textContent=q.revealed?'Správný výsledek: '+q.answer:''}else{document.getElementById('current').textContent='Zatím žádný příklad.'}document.getElementById('count').textContent='Připojeno: '+j.students.length;document.getElementById('rows').innerHTML=j.students.map(s=>'<tr><td>'+esc(s.name)+'</td><td>'+esc(s.response??'—')+'</td><td>'+esc(s.status)+'</td><td>'+s.correct+'/'+s.total+' ('+(s.total?Math.round(100*s.correct/s.total):0)+' %)</td></tr>').join('')}catch(e){document.getElementById('msg').textContent='Spojení přerušeno: '+e.message}}
if(pin){show();poll()}setInterval(poll,2500);
</script></html>'''
STUDENT = '''<!doctype html><html lang="cs"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Matematika – žák</title><style>body{font:18px system-ui;background:#edf4ff;color:#153153;margin:0}main{max-width:650px;margin:auto;padding:20px}.card{background:white;border-radius:18px;padding:23px;margin:15px 0;box-shadow:0 4px 15px #1232}input,button{font:inherit;padding:12px;border:1px solid #b4c7e3;border-radius:10px;max-width:100%;margin:4px}button{background:#1269cb;color:white;font-weight:bold;cursor:pointer}.balls{display:flex;gap:5px;flex-wrap:wrap;min-height:30px;margin:10px 0}.ball{height:21px;width:21px;border-radius:50%;background:#347bd7}.neg{background:#e44e50}.muted{color:#586e89}.hidden{display:none}.big{font-size:35px;font-weight:800}</style><main><h1>🔴🔵 Matematika – celá čísla</h1><div id="login" class="card"><h2>Připoj se k hodině</h2><input id="pin" placeholder="Šestimístný PIN" inputmode="numeric" maxlength="6" value="{{ pin }}"><input id="name" placeholder="Tvoje jméno" maxlength="40"><button onclick="join()">Připojit se</button><p id="error" style="color:#b32626"></p></div><div id="lesson" class="card hidden"><h2 id="hello"></h2><p class="muted" id="wait">Čekej, až učitel zadá příklad.</p><div id="exercise" class="hidden"><p class="big" id="expression"></p><p class="muted">Modré kuličky = kladné číslo, červené = záporné číslo.</p><div id="balls" class="balls"></div><input id="answer" type="number" step="1" placeholder="Tvůj výsledek" style="width:180px"><button onclick="submitAnswer()">Odeslat odpověď</button><p id="feedback"></p></div><p id="score"></p></div></main><script>
let token=sessionStorage.getItem('liveMathStudentToken')||'',name=sessionStorage.getItem('liveMathStudentName')||'',qid=0,answered=0;
async function join(){try{let p=document.getElementById('pin').value.trim(),n=document.getElementById('name').value.trim();let r=await fetch('/live-math/api/join',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin:p,name:n})});let j=await r.json();if(!r.ok)throw Error(j.error);token=j.token;name=n;sessionStorage.setItem('liveMathStudentToken',token);sessionStorage.setItem('liveMathStudentName',name);display();poll()}catch(e){document.getElementById('error').textContent=e.message}}
function display(){document.getElementById('login').classList.add('hidden');document.getElementById('lesson').classList.remove('hidden');document.getElementById('hello').textContent='Ahoj, '+name+'!'}
function balls(n){let abs=Math.min(Math.abs(n),30);return Array.from({length:abs},()=>'<i class="ball '+(n<0?'neg':'')+'"></i>').join('')+(Math.abs(n)>30?' …':'')}
async function poll(){if(!token)return;try{let r=await fetch('/live-math/api/student-state?token='+encodeURIComponent(token));let j=await r.json();if(!r.ok){document.getElementById('wait').textContent=j.error||'Spojení vypršelo';return}display();document.getElementById('score').textContent='Správné odpovědi: '+j.correct+' / '+j.total;let q=j.question;if(!q){document.getElementById('exercise').classList.add('hidden');return}document.getElementById('exercise').classList.remove('hidden');document.getElementById('wait').textContent='Vypočítej příklad a odešli odpověď.';if(q.id!==qid){qid=q.id;document.getElementById('answer').value='';document.getElementById('feedback').textContent=''}document.getElementById('expression').textContent=q.a+' '+({'*':'×','/':'÷'}[q.op]||q.op)+' '+q.b+' = ?';document.getElementById('balls').innerHTML=balls(q.a)+'<span style="padding:0 10px">'+({'*':'×','/':'÷'}[q.op]||q.op)+'</span>'+balls(q.b);if(j.response!==null){document.getElementById('feedback').textContent='Odesláno: '+j.response+(q.revealed?' — '+(j.response===q.answer?'Správně!':'Správný výsledek: '+q.answer):' — čekáme na učitele')}else if(q.revealed){document.getElementById('feedback').textContent='Správný výsledek: '+q.answer}}
catch(e){document.getElementById('wait').textContent='Čekám na spojení…'}}
async function submitAnswer(){let value=document.getElementById('answer').value;if(value===''||!Number.isInteger(+value))return alert('Zadej celé číslo');let r=await fetch('/live-math/api/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,question_id:qid,answer:+value})});let j=await r.json();if(!r.ok)alert(j.error);poll()}
if(token){display();poll()}setInterval(poll,2500);
</script></html>'''

def register(app, data_dir, require_teacher):
    dbfile=str(data_dir/'live_math.sqlite3')
    def connect():
        c=sqlite3.connect(dbfile,timeout=10)
        c.row_factory=sqlite3.Row
        c.execute('PRAGMA busy_timeout=10000')
        c.executescript('''CREATE TABLE IF NOT EXISTS rooms(pin TEXT PRIMARY KEY, created INTEGER, question_id INTEGER DEFAULT 0, a INTEGER, b INTEGER, op TEXT, answer INTEGER, revealed INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS pupils(token TEXT PRIMARY KEY,pin TEXT,name TEXT,joined INTEGER,last_seen INTEGER);
        CREATE TABLE IF NOT EXISTS answers(token TEXT,pin TEXT,qid INTEGER,response INTEGER,correct INTEGER,PRIMARY KEY(token,qid));''')
        return c
    def error(message,code=400):return jsonify(error=message),code
    def room(c,pin):return c.execute('SELECT * FROM rooms WHERE pin=?',(pin,)).fetchone()
    def pupil(c,token):return c.execute('SELECT * FROM pupils WHERE token=?',(token,)).fetchone()
    def question(r):return dict(id=r['question_id'],a=r['a'],b=r['b'],op=r['op'],answer=r['answer'],revealed=bool(r['revealed'])) if r['question_id'] else None
    @app.route('/live-math')
    def live_math_teacher():
        auth=require_teacher()
        if auth:return auth
        return render_template_string(TEACHER)
    @app.route('/live-math/join')
    def live_math_join():return render_template_string(STUDENT,pin=request.args.get('pin',''))
    @app.route('/live-math/qr/<pin>')
    def live_math_qr(pin):
        with connect() as c:
            if not room(c,pin):return 'Nenalezeno',404
        import qrcode
        img=qrcode.make(request.url_root.rstrip('/')+'/live-math/join?pin='+pin)
        buf=io.BytesIO();img.save(buf,format='PNG');buf.seek(0)
        return send_file(buf,mimetype='image/png',max_age=0)
    @app.route('/live-math/api/create',methods=['POST'])
    def live_math_create():
        auth=require_teacher()
        if auth:return error('Pouze učitel',403)
        with connect() as c:
            for _ in range(30):
                pin=str(secrets.randbelow(900000)+100000)
                if not room(c,pin):break
            else:return error('Nelze vytvořit PIN',500)
            c.execute('INSERT INTO rooms(pin,created) VALUES (?,?)',(pin,int(time.time())))
        return jsonify(pin=pin)
    @app.route('/live-math/api/question',methods=['POST'])
    def live_math_question():
        auth=require_teacher()
        if auth:return error('Pouze učitel',403)
        d=request.get_json(silent=True) or {};pin=str(d.get('pin',''));op=d.get('op')
        try:a=int(d['a']);b=int(d['b'])
        except (KeyError,ValueError,TypeError):return error('Zadej celá čísla')
        if op not in ('+','-','*','/'):return error('Neplatná operace')
        if abs(a)>100 or abs(b)>100:return error('Použij čísla od −100 do 100')
        if op=='/' and (b==0 or a%b!=0):return error('Dělení musí mít celočíselný výsledek a nenulového dělitele')
        answer={'+':lambda:a+b,'-':lambda:a-b,'*':lambda:a*b,'/':lambda:a//b}[op]()
        with connect() as c:
            if not room(c,pin):return error('Hodina nenalezena',404)
            c.execute('UPDATE rooms SET question_id=question_id+1,a=?,b=?,op=?,answer=?,revealed=0 WHERE pin=?',(a,b,op,answer,pin))
        return jsonify(ok=True)
    @app.route('/live-math/api/reveal',methods=['POST'])
    def live_math_reveal():
        auth=require_teacher()
        if auth:return error('Pouze učitel',403)
        pin=str((request.get_json(silent=True) or {}).get('pin',''))
        with connect() as c:
            if not room(c,pin):return error('Hodina nenalezena',404)
            c.execute('UPDATE rooms SET revealed=1 WHERE pin=?',(pin,))
        return jsonify(ok=True)
    @app.route('/live-math/api/join',methods=['POST'])
    def live_math_join_api():
        d=request.get_json(silent=True) or {};pin=str(d.get('pin','')).strip();name=str(d.get('name','')).strip()[:40]
        if not name:return error('Zadej své jméno')
        with connect() as c:
            if not room(c,pin):return error('Nesprávný PIN',404)
            token=secrets.token_urlsafe(32);now=int(time.time())
            c.execute('INSERT INTO pupils(token,pin,name,joined,last_seen) VALUES (?,?,?,?,?)',(token,pin,name,now,now))
        return jsonify(token=token)
    @app.route('/live-math/api/answer',methods=['POST'])
    def live_math_answer():
        d=request.get_json(silent=True) or {};token=str(d.get('token',''))
        try:qid=int(d['question_id']);response=int(d['answer'])
        except (KeyError,ValueError,TypeError):return error('Odpověď musí být celé číslo')
        with connect() as c:
            p=pupil(c,token)
            if not p:return error('Neplatné připojení',403)
            r=room(c,p['pin'])
            if not r or r['question_id']!=qid or r['revealed']:return error('Tato otázka už není aktivní')
            c.execute('INSERT OR IGNORE INTO answers(token,pin,qid,response,correct) VALUES (?,?,?,?,?)',(token,p['pin'],qid,response,int(response==r['answer'])))
        return jsonify(ok=True)
    @app.route('/live-math/api/student-state')
    def live_math_student_state():
        token=request.args.get('token','')
        with connect() as c:
            p=pupil(c,token)
            if not p:return error('Neplatné připojení',403)
            c.execute('UPDATE pupils SET last_seen=? WHERE token=?',(int(time.time()),token))
            r=room(c,p['pin']);q=question(r) if r else None
            a=c.execute('SELECT response FROM answers WHERE token=? AND qid=?',(token,r['question_id'])).fetchone() if q else None
            totals=c.execute('SELECT COUNT(*) total,COALESCE(SUM(correct),0) correct FROM answers WHERE token=?',(token,)).fetchone()
        if q and not q['revealed']:q.pop('answer')
        return jsonify(question=q,response=a['response'] if a else None,total=totals['total'],correct=totals['correct'])
    @app.route('/live-math/api/state')
    def live_math_state():
        auth=require_teacher()
        if auth:return error('Pouze učitel',403)
        pin=request.args.get('pin','')
        with connect() as c:
            r=room(c,pin)
            if not r:return error('Hodina nenalezena',404)
            students=[]
            for p in c.execute('SELECT * FROM pupils WHERE pin=? AND last_seen>? ORDER BY joined',(pin,int(time.time())-60)):
                a=c.execute('SELECT response,correct FROM answers WHERE token=? AND qid=?',(p['token'],r['question_id'])).fetchone()
                totals=c.execute('SELECT COUNT(*) total,COALESCE(SUM(correct),0) correct FROM answers WHERE token=?',(p['token'],)).fetchone()
                students.append(dict(name=p['name'],response=a['response'] if a else None,status=('Správně' if a['correct'] else 'Chybně') if a else 'Čeká na odpověď',total=totals['total'],correct=totals['correct']))
        return jsonify(question=question(r),students=students)
