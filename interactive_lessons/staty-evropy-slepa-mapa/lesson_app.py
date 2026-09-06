TOTAL = 47
COUNTRIES = {
    'ALB': {'cs': 'Albánie', 'en': 'Albania'},
    'AND': {'cs': 'Andorra', 'en': 'Andorra'},
    'AUT': {'cs': 'Rakousko', 'en': 'Austria'},
    'BLR': {'cs': 'Bělorusko', 'en': 'Belarus'},
    'BEL': {'cs': 'Belgie', 'en': 'Belgium'},
    'BIH': {'cs': 'Bosna a Hercegovina', 'en': 'Bosnia and Herzegovina'},
    'BGR': {'cs': 'Bulharsko', 'en': 'Bulgaria'},
    'HRV': {'cs': 'Chorvatsko', 'en': 'Croatia'},
    'CYP': {'cs': 'Kypr', 'en': 'Cyprus'},
    'CZE': {'cs': 'Česko', 'en': 'Czechia'},
    'DNK': {'cs': 'Dánsko', 'en': 'Denmark'},
    'EST': {'cs': 'Estonsko', 'en': 'Estonia'},
    'FIN': {'cs': 'Finsko', 'en': 'Finland'},
    'FRA': {'cs': 'Francie', 'en': 'France'},
    'DEU': {'cs': 'Německo', 'en': 'Germany'},
    'GRC': {'cs': 'Řecko', 'en': 'Greece'},
    'HUN': {'cs': 'Maďarsko', 'en': 'Hungary'},
    'ISL': {'cs': 'Island', 'en': 'Iceland'},
    'IRL': {'cs': 'Irsko', 'en': 'Ireland'},
    'ITA': {'cs': 'Itálie', 'en': 'Italy'},
    'XKX': {'cs': 'Kosovo', 'en': 'Kosovo'},
    'LVA': {'cs': 'Lotyšsko', 'en': 'Latvia'},
    'LIE': {'cs': 'Lichtenštejnsko', 'en': 'Liechtenstein'},
    'LTU': {'cs': 'Litva', 'en': 'Lithuania'},
    'LUX': {'cs': 'Lucembursko', 'en': 'Luxembourg'},
    'MLT': {'cs': 'Malta', 'en': 'Malta'},
    'MDA': {'cs': 'Moldavsko', 'en': 'Moldova'},
    'MCO': {'cs': 'Monako', 'en': 'Monaco'},
    'MNE': {'cs': 'Černá Hora', 'en': 'Montenegro'},
    'NLD': {'cs': 'Nizozemsko', 'en': 'Netherlands'},
    'MKD': {'cs': 'Severní Makedonie', 'en': 'North Macedonia'},
    'NOR': {'cs': 'Norsko', 'en': 'Norway'},
    'POL': {'cs': 'Polsko', 'en': 'Poland'},
    'PRT': {'cs': 'Portugalsko', 'en': 'Portugal'},
    'ROU': {'cs': 'Rumunsko', 'en': 'Romania'},
    'RUS': {'cs': 'Rusko', 'en': 'Russia'},
    'SMR': {'cs': 'San Marino', 'en': 'San Marino'},
    'SRB': {'cs': 'Srbsko', 'en': 'Serbia'},
    'SVK': {'cs': 'Slovensko', 'en': 'Slovakia'},
    'SVN': {'cs': 'Slovinsko', 'en': 'Slovenia'},
    'ESP': {'cs': 'Španělsko', 'en': 'Spain'},
    'SWE': {'cs': 'Švédsko', 'en': 'Sweden'},
    'CHE': {'cs': 'Švýcarsko', 'en': 'Switzerland'},
    'TUR': {'cs': 'Turecko', 'en': 'Turkey'},
    'UKR': {'cs': 'Ukrajina', 'en': 'Ukraine'},
    'GBR': {'cs': 'Spojené království', 'en': 'United Kingdom'},
    'VAT': {'cs': 'Vatikán', 'en': 'Vatican City'},
}

def _key(user):
    return f"europe_map_v1_{user['id']}"

def _fresh(mode):
    return {
        'mode': mode,
        'placed': [],
        'attempts': 0,
    }

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
    return {
        'mode':mode,'placed':sorted(placed),'completed':completed, 'total':TOTAL,
        'score':completed if mode=='test' else TOTAL,'percent':percent,
        'grade':_grade(percent) if percent is not None else None,
        'done':completed>=TOTAL,
    }

def handle(action, payload, session, user):
    key=_key(user)
    if action=='start':
        mode=str(payload.get('mode','practice')).lower()
        if mode not in ('practice','test'):
            raise ValueError('Neplatný režim.')
        state=_fresh(mode)
        session[key]=state
        out=_summary(state); out.update({'ok':True,'message':'Procvičování spuštěno.' if mode=='practice' else 'Test spuštěn. Hodně štěstí!'}); return out
    if action=='status':
        state=session.get(key) or _fresh('practice')
        session[key]=state
        out=_summary(state); out['ok']=True; return out
    if action=='restore':
        mode=str(payload.get('mode','test')).lower()
        if mode not in ('practice','test'): mode='test'
        placed=[str(x).upper().strip() for x in (payload.get('placed') or [])]
        placed=sorted({x for x in placed if x in COUNTRIES})
        state=_fresh(mode)
        state['placed']=placed
        session[key]=state
        out=_summary(state); out.update({'ok':True,'message':'Rozpracovaná mapa byla obnovena.'}); return out
    if action=='reset':
        mode=str(payload.get('mode','practice')).lower()
        if mode not in ('practice','test'): mode='practice'
        state=_fresh(mode); session[key]=state
        out=_summary(state); out.update({'ok':True,'message':'Mapa byla připravena znovu.'}); return out
    if action!='check':
        return {'ok':False,'message':'Neznámá akce.'}
    state=session.get(key)
    if not state:
        state=_fresh(str(payload.get('mode','practice')).lower())
    outline=str(payload.get('outline_code','')).upper().strip()
    label=str(payload.get('label_code','')).upper().strip()
    if outline not in COUNTRIES or label not in COUNTRIES:
        raise ValueError('Neplatný stát.')
    placed=set(state.get('placed') or [])
    if outline in placed:
        out=_summary(state); out.update({'ok':True,'correct':True,'message':'Tento stát už je vyřešený.'}); return out
    state['attempts']=int(state.get('attempts') or 0)+1
    correct=(outline==label)
    if correct:
        placed.add(outline); state['placed']=sorted(placed)
        message='Správně!'
    else:
        if state.get('mode')=='test':
            message='Nesprávně. Zkus to znovu – můžeš pokračovat, chyba procenta nesnižuje.'
        else:
            message='To není správně. Zkus to znovu – při procvičování se chyba nepočítá.'
    session[key]=state
    out=_summary(state)
    out.update({'ok':True,'correct':correct,'outline_code':outline,'message':message})
    if out['done']:
        if state.get('mode')=='test':
            out['message']=f"Test dokončen: {out['score']} z {TOTAL} bodů = {out['percent']} %."
        else:
            out['message']='Výborně! Procvičování celé Evropy je dokončeno.'
    return out
