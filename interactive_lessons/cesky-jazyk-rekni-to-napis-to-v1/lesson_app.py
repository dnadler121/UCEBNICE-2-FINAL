def handle(action, payload, session, user):
    key = f"cesky_jazyk_rekni_napis_v1_{user['id']}"
    if action == 'start':
        session[key] = {'started': True, 'completed': 0, 'score': 0}
        return {'ok': True}
    if action == 'status':
        return {'ok': True, 'state': session.get(key, {})}
    if action == 'reset':
        session[key] = {}
        return {'ok': True}
    if action == 'progress':
        state = session.get(key, {})
        state['completed'] = max(0, min(8, int(payload.get('completed', 0))))
        state['score'] = max(0, int(payload.get('score', 0)))
        session[key] = state
        return {'ok': True, 'state': state}
    return {'ok': False, 'message': 'Neznámá akce.'}
