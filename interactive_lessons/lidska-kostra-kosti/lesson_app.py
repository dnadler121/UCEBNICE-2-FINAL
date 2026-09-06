TOTAL = 18
BONES = {'SKULL': {'cs': 'Lebka', 'en': 'Skull'}, 'MANDIBLE': {'cs': 'Dolní čelist', 'en': 'Mandible'}, 'CLAVICLE': {'cs': 'Klíční kost', 'en': 'Clavicle'}, 'SCAPULA': {'cs': 'Lopatka', 'en': 'Scapula'}, 'STERNUM': {'cs': 'Hrudní kost', 'en': 'Sternum'}, 'RIBS': {'cs': 'Žebra', 'en': 'Ribs'}, 'SPINE': {'cs': 'Páteř', 'en': 'Spine'}, 'HUMERUS': {'cs': 'Pažní kost', 'en': 'Humerus'}, 'RADIUS': {'cs': 'Vřetenní kost', 'en': 'Radius'}, 'ULNA': {'cs': 'Loketní kost', 'en': 'Ulna'}, 'HAND': {'cs': 'Kosti ruky', 'en': 'Hand bones'}, 'PELVIS': {'cs': 'Pánev', 'en': 'Pelvis'}, 'SACRUM': {'cs': 'Křížová kost', 'en': 'Sacrum'}, 'FEMUR': {'cs': 'Stehenní kost', 'en': 'Femur'}, 'PATELLA': {'cs': 'Čéška', 'en': 'Patella'}, 'TIBIA': {'cs': 'Holenní kost', 'en': 'Tibia'}, 'FIBULA': {'cs': 'Lýtková kost', 'en': 'Fibula'}, 'FOOT': {'cs': 'Kosti nohy', 'en': 'Foot bones'}}

def _key(user):
    return f"skeleton_bones_v1_{user['id']}"

def _fresh(mode):
    return {'mode': mode, 'placed': [], 'attempts': 0}

def _grade(percent):
    if percent >= 90: return 1
    if percent >= 75: return 2
    if percent >= 60: return 3
    if percent >= 40: return 4
    return 5

def _summary(state):
    placed=set(state.get('placed') or [])
    mode=state.get('mode','practice')
    completed=len(placed)
    percent=round(completed/TOTAL*100) if mode=='test' else None
    return {'mode':mode,'placed':sorted(placed),'completed':completed,'total':TOTAL,
            'score':completed if mode=='test' else TOTAL,'percent':percent,
            'grade':_grade(percent) if percent is not None else None,
            'done':completed>=TOTAL}

def handle(action, payload, session, user):
    key=_key(user)
    if action=='start':
        mode=str(payload.get('mode','practice')).lower()
        if mode not in ('practice','test'): raise ValueError('Neplatný režim.')
        state=_fresh(mode); session[key]=state
        out=_summary(state); out.update({'ok':True,'message':'Spuštěno.'}); return out
    if action=='status':
        state=session.get(key) or _fresh('practice'); session[key]=state
        out=_summary(state); out['ok']=True; return out
    if action=='restore':
        mode=str(payload.get('mode','test')).lower()
        placed=[str(x).upper().strip() for x in (payload.get('placed') or [])]
        placed=sorted({x for x in placed if x in BONES})
        state=_fresh(mode); state['placed']=placed; session[key]=state
        out=_summary(state); out.update({'ok':True,'message':'Rozpracovaná kostra byla obnovena.'}); return out
    if action=='reset':
        mode=str(payload.get('mode','practice')).lower()
        state=_fresh(mode); session[key]=state
        out=_summary(state); out.update({'ok':True,'message':'Kostra byla připravena znovu.'}); return out
    if action!='check': return {'ok':False,'message':'Neznámá akce.'}
    state=session.get(key) or _fresh(str(payload.get('mode','practice')).lower())
    outline=str(payload.get('outline_code','')).upper().strip()
    label=str(payload.get('label_code','')).upper().strip()
    if outline not in BONES or label not in BONES: raise ValueError('Neplatná kost.')
    placed=set(state.get('placed') or [])
    if outline in placed:
        out=_summary(state); out.update({'ok':True,'correct':True,'message':'Tato kost už je vyřešená.'}); return out
    state['attempts']=int(state.get('attempts') or 0)+1
    correct=(outline==label)
    if correct:
        placed.add(outline); state['placed']=sorted(placed); message='Správně!'
    else:
        message='Nesprávně. Zkus to znovu – můžeš pokračovat dál.'
    session[key]=state
    out=_summary(state); out.update({'ok':True,'correct':correct,'outline_code':outline,'message':message})
    if out['done']:
        out['message']='Kostra je kompletně doplněna.'
    return out
