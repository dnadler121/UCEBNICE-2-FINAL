def _grade(percent):
    if percent >= 90: return 1
    if percent >= 75: return 2
    if percent >= 60: return 3
    if percent >= 40: return 4
    return 5

def handle(action, payload, session, user):
    key = f"globalizace_montessori_9_v1_{user['id']}"
    if action == 'start':
        session[key] = {'started': True}
        return {'ok': True, 'message': 'Spuštěno.'}
    if action == 'status': return {'ok': True, 'state': session.get(key, {})}
    if action == 'reset':
        session[key] = {}
        return {'ok': True, 'message': 'Aktivita byla připravena znovu.'}
    if action == 'grade':
        percent=max(0,min(100,int(payload.get('percent',0))))
        return {'ok':True,'percent':percent,'grade':_grade(percent)}
    return {'ok':False,'message':'Neznámá akce.'}
