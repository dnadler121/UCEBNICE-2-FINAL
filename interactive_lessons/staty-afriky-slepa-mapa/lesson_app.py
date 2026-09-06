TOTAL = 54
ITEMS = {'DZA': {'cs': 'Alžírsko', 'en': 'Algeria'}, 'AGO': {'cs': 'Angola', 'en': 'Angola'}, 'BEN': {'cs': 'Benin', 'en': 'Benin'}, 'BWA': {'cs': 'Botswana', 'en': 'Botswana'}, 'BFA': {'cs': 'Burkina Faso', 'en': 'Burkina Faso'}, 'BDI': {'cs': 'Burundi', 'en': 'Burundi'}, 'CPV': {'cs': 'Kapverdy', 'en': 'Cabo Verde'}, 'CMR': {'cs': 'Kamerun', 'en': 'Cameroon'}, 'CAF': {'cs': 'Středoafrická republika', 'en': 'Central African Republic'}, 'TCD': {'cs': 'Čad', 'en': 'Chad'}, 'COM': {'cs': 'Komory', 'en': 'Comoros'}, 'COD': {'cs': 'DR Kongo', 'en': 'DR Congo'}, 'COG': {'cs': 'Kongo', 'en': 'Republic of the Congo'}, 'CIV': {'cs': 'Pobřeží slonoviny', 'en': 'Côte d’Ivoire'}, 'DJI': {'cs': 'Džibutsko', 'en': 'Djibouti'}, 'EGY': {'cs': 'Egypt', 'en': 'Egypt'}, 'GNQ': {'cs': 'Rovníková Guinea', 'en': 'Equatorial Guinea'}, 'ERI': {'cs': 'Eritrea', 'en': 'Eritrea'}, 'SWZ': {'cs': 'Eswatini', 'en': 'Eswatini'}, 'ETH': {'cs': 'Etiopie', 'en': 'Ethiopia'}, 'GAB': {'cs': 'Gabon', 'en': 'Gabon'}, 'GMB': {'cs': 'Gambie', 'en': 'Gambia'}, 'GHA': {'cs': 'Ghana', 'en': 'Ghana'}, 'GIN': {'cs': 'Guinea', 'en': 'Guinea'}, 'GNB': {'cs': 'Guinea-Bissau', 'en': 'Guinea-Bissau'}, 'KEN': {'cs': 'Keňa', 'en': 'Kenya'}, 'LSO': {'cs': 'Lesotho', 'en': 'Lesotho'}, 'LBR': {'cs': 'Libérie', 'en': 'Liberia'}, 'LBY': {'cs': 'Libye', 'en': 'Libya'}, 'MDG': {'cs': 'Madagaskar', 'en': 'Madagascar'}, 'MWI': {'cs': 'Malawi', 'en': 'Malawi'}, 'MLI': {'cs': 'Mali', 'en': 'Mali'}, 'MRT': {'cs': 'Mauritánie', 'en': 'Mauritania'}, 'MUS': {'cs': 'Mauricius', 'en': 'Mauritius'}, 'MAR': {'cs': 'Maroko', 'en': 'Morocco'}, 'MOZ': {'cs': 'Mosambik', 'en': 'Mozambique'}, 'NAM': {'cs': 'Namibie', 'en': 'Namibia'}, 'NER': {'cs': 'Niger', 'en': 'Niger'}, 'NGA': {'cs': 'Nigérie', 'en': 'Nigeria'}, 'RWA': {'cs': 'Rwanda', 'en': 'Rwanda'}, 'STP': {'cs': 'Svatý Tomáš a Princův ostrov', 'en': 'São Tomé and Príncipe'}, 'SEN': {'cs': 'Senegal', 'en': 'Senegal'}, 'SYC': {'cs': 'Seychely', 'en': 'Seychelles'}, 'SLE': {'cs': 'Sierra Leone', 'en': 'Sierra Leone'}, 'SOM': {'cs': 'Somálsko', 'en': 'Somalia'}, 'ZAF': {'cs': 'Jihoafrická republika', 'en': 'South Africa'}, 'SSD': {'cs': 'Jižní Súdán', 'en': 'South Sudan'}, 'SDN': {'cs': 'Súdán', 'en': 'Sudan'}, 'TZA': {'cs': 'Tanzanie', 'en': 'Tanzania'}, 'TGO': {'cs': 'Togo', 'en': 'Togo'}, 'TUN': {'cs': 'Tunisko', 'en': 'Tunisia'}, 'UGA': {'cs': 'Uganda', 'en': 'Uganda'}, 'ZMB': {'cs': 'Zambie', 'en': 'Zambia'}, 'ZWE': {'cs': 'Zimbabwe', 'en': 'Zimbabwe'}}

def _key(user): return f"africa_map_v1_{user['id']}"
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
