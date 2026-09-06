TOTAL = 15
ITEMS = {'BRAIN': {'cs': 'Mozek', 'en': 'Brain'}, 'THYROID': {'cs': 'Štítná žláza', 'en': 'Thyroid gland'}, 'TRACHEA': {'cs': 'Průdušnice', 'en': 'Trachea'}, 'LUNG_L': {'cs': 'Levá plíce', 'en': 'Left lung'}, 'LUNG_R': {'cs': 'Pravá plíce', 'en': 'Right lung'}, 'HEART': {'cs': 'Srdce', 'en': 'Heart'}, 'LIVER': {'cs': 'Játra', 'en': 'Liver'}, 'STOMACH': {'cs': 'Žaludek', 'en': 'Stomach'}, 'PANCREAS': {'cs': 'Slinivka břišní', 'en': 'Pancreas'}, 'SPLEEN': {'cs': 'Slezina', 'en': 'Spleen'}, 'KIDNEY_L': {'cs': 'Levá ledvina', 'en': 'Left kidney'}, 'KIDNEY_R': {'cs': 'Pravá ledvina', 'en': 'Right kidney'}, 'SMALL_INTESTINE': {'cs': 'Tenké střevo', 'en': 'Small intestine'}, 'LARGE_INTESTINE': {'cs': 'Tlusté střevo', 'en': 'Large intestine'}, 'BLADDER': {'cs': 'Močový měchýř', 'en': 'Urinary bladder'}}

def _key(user): return f"human_organs_v1_{user['id']}"
def _fresh(mode): return {'mode':mode,'placed':[],'attempts':0}
def _grade(p):
    if p>=90:return 1
    if p>=75:return 2
    if p>=60:return 3
    if p>=40:return 4
    return 5
def _summary(s):
    placed=set(s.get('placed') or []); mode=s.get('mode','practice'); c=len(placed); p=round(c/TOTAL*100) if mode=='test' else None
    return {'mode':mode,'placed':sorted(placed),'completed':c,'total':TOTAL,'score':c if mode=='test' else TOTAL,'percent':p,'grade':_grade(p) if p is not None else None,'done':c>=TOTAL}
def handle(action,payload,session,user):
    key=_key(user)
    if action=='start':
        mode=str(payload.get('mode','practice')).lower(); mode=mode if mode in ('practice','test') else 'practice'; s=_fresh(mode); session[key]=s; o=_summary(s); o.update({'ok':True,'message':'Spuštěno.'}); return o
    if action=='status':
        s=session.get(key) or _fresh('practice'); session[key]=s; o=_summary(s); o['ok']=True; return o
    if action=='restore':
        mode=str(payload.get('mode','test')).lower(); placed=sorted({str(x).upper().strip() for x in (payload.get('placed') or []) if str(x).upper().strip() in ITEMS}); s=_fresh(mode); s['placed']=placed; session[key]=s; o=_summary(s); o.update({'ok':True,'message':'Rozpracovaná práce byla obnovena.'}); return o
    if action=='reset':
        s=_fresh(str(payload.get('mode','practice')).lower()); session[key]=s; o=_summary(s); o.update({'ok':True,'message':'Připraveno znovu.'}); return o
    if action!='check': return {'ok':False,'message':'Neznámá akce.'}
    s=session.get(key) or _fresh(str(payload.get('mode','practice')).lower()); outline=str(payload.get('outline_code','')).upper().strip(); label=str(payload.get('label_code','')).upper().strip()
    if outline not in ITEMS or label not in ITEMS: raise ValueError('Neplatná položka.')
    placed=set(s.get('placed') or []); correct=outline==label; s['attempts']=int(s.get('attempts') or 0)+1
    if correct: placed.add(outline); s['placed']=sorted(placed)
    session[key]=s; o=_summary(s); o.update({'ok':True,'correct':correct,'outline_code':outline,'message':'Správně!' if correct else 'Nesprávně. Zkus to znovu – můžeš pokračovat dál.'}); return o
