import json, time, secrets, io, base64
from flask import current_app
from sqlalchemy import text

TABLES = [
 "CREATE TABLE IF NOT EXISTS geo901_rooms (pin TEXT PRIMARY KEY, teacher_id INTEGER NOT NULL, question INTEGER NOT NULL DEFAULT -1, revealed INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL)",
 "CREATE TABLE IF NOT EXISTS geo901_answers (pin TEXT NOT NULL, question INTEGER NOT NULL, user_id INTEGER NOT NULL, student TEXT NOT NULL, answer INTEGER NOT NULL, correct INTEGER NOT NULL, created REAL NOT NULL, PRIMARY KEY(pin,question,user_id))"
]

def handle(action, payload, session, user):
    db=current_app.extensions['sqlalchemy']
    uid=int(user['id'])
    with db.session.begin_nested():
        for sql in TABLES: db.session.execute(text(sql))
    db.session.commit()
    role = user.get('role') if uid < 0 else db.session.execute(text('SELECT role FROM user WHERE id=:id'),{'id':uid}).scalar()
    is_teacher=role in ('teacher','admin')
    pin=str(payload.get('pin','')).strip()
    def room():
        r=db.session.execute(text('SELECT pin,teacher_id,question,revealed FROM geo901_rooms WHERE pin=:p'),{'p':pin}).mappings().first()
        if not r: raise ValueError('Hodina s tímto PINem nebyla nalezena.')
        return r
    if action=='create':
        if not is_teacher: raise ValueError('Hodinu smí založit jen učitel.')
        for _ in range(15):
            pin=str(secrets.randbelow(900000)+100000)
            if not db.session.execute(text('SELECT 1 FROM geo901_rooms WHERE pin=:p'),{'p':pin}).first(): break
        db.session.execute(text('INSERT INTO geo901_rooms(pin,teacher_id,question,revealed,created) VALUES(:p,:u,-1,0,:t)'),{'p':pin,'u':uid,'t':time.time()});db.session.commit()
        return {'ok':True,'pin':pin}
    if action=='qr':
        r=room()
        import qrcode
        from flask import request
        url=request.url_root.rstrip('/')+'/live-geo901?pin='+pin
        buf=io.BytesIO();qrcode.make(url).save(buf,format='PNG')
        return {'ok':True,'image':'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()}
    if action=='publish':
        r=room()
        if not is_teacher or r['teacher_id']!=uid: raise ValueError('Pouze zakládající učitel může řídit hodinu.')
        q=int(payload.get('question',-1))
        if not 0<=q<40: raise ValueError('Neplatné číslo otázky.')
        db.session.execute(text('UPDATE geo901_rooms SET question=:q,revealed=0 WHERE pin=:p'),{'q':q,'p':pin});db.session.commit()
        return {'ok':True}
    if action=='reveal':
        r=room()
        if not is_teacher or r['teacher_id']!=uid: raise ValueError('Pouze učitel může odhalit řešení.')
        db.session.execute(text('UPDATE geo901_rooms SET revealed=1 WHERE pin=:p'),{'p':pin});db.session.commit()
        return {'ok':True}
    if action=='join':
        r=room()
        if is_teacher: raise ValueError('Učitel se připojuje jako učitel.')
        name=str(payload.get('name','')).strip()
        if len(name)<2 or len(name)>60: raise ValueError('Zadej své jméno (2–60 znaků).')
        session['geo901_name_'+pin]=name
        return {'ok':True}
    if action=='submit':
        r=room()
        if is_teacher: raise ValueError('Odpovědi odesílají žáci.')
        q=int(payload.get('question',-1)); a=int(payload.get('answer',-1));correct=int(payload.get('correct',-1))
        if q!=r['question'] or r['revealed']: raise ValueError('Tato otázka už není otevřená.')
        if not 0<=a<5 or correct not in (0,1): raise ValueError('Neplatná odpověď.')
        if not session.get('geo901_name_'+pin): raise ValueError('Nejdřív zadej PIN a své jméno.')
        # Correctness is verified from teacher-authored answer key below, never trusted from browser.
        expected=ANSWERS[q]
        correct=int(a==expected)
        db.session.execute(text('INSERT OR IGNORE INTO geo901_answers(pin,question,user_id,student,answer,correct,created) VALUES(:p,:q,:u,:s,:a,:c,:t)'),{'p':pin,'q':q,'u':uid,'s':session['geo901_name_'+pin],'a':a,'c':correct,'t':time.time()});db.session.commit()
        return {'ok':True}
    if action=='status':
        r=room()
        if not is_teacher and not session.get('geo901_name_'+pin): raise ValueError('Nejdřív zadej PIN a své jméno.')
        is_owner=is_teacher and r['teacher_id']==uid
        answers=db.session.execute(text('SELECT user_id,student,question,answer,correct FROM geo901_answers WHERE pin=:p ORDER BY student,question'),{'p':pin}).mappings().all()
        byuser={}
        for a in answers:
            d=byuser.setdefault(a['user_id'],{'name':a['student'],'correct':0,'total':0,'current':None})
            d['total']+=1;d['correct']+=a['correct']
            if a['question']==r['question']:d['current']={'answer':a['answer'],'correct':bool(a['correct'])}
        if is_owner:
            return {'ok':True,'question':r['question'],'revealed':bool(r['revealed']),'students':list(byuser.values()),'count':sum(1 for d in byuser.values() if d['current'])}
        d=byuser.get(uid,{'correct':0,'total':0,'current':None})
        return {'ok':True,'question':r['question'],'revealed':bool(r['revealed']),'correct':d['correct'],'total':d['total'],'current':d['current']}
    raise ValueError('Neznámá akce.')

ANSWERS = [2, 1, 0, 2, 1, 0, 2, 1, 0, 2, 1, 0, 2, 1, 0, 2, 1, 0, 2, 1, 0, 2, 1, 0, 2, 1, 0, 2, 1, 0, 2, 1, 0, 2, 1, 0, 2, 1, 0, 2]
