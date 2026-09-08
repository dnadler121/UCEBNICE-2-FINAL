def handle(action, payload, session, user):
    key = f"cesky_jazyk_rozhovor_naslouchani_v1_{user['id']}"
    if action == 'start':
        session[key] = {'started': True, 'completed': 0}
        return {'ok': True}
    if action == 'status':
        return {'ok': True, 'state': session.get(key, {})}
    if action == 'reset':
        session[key] = {}
        return {'ok': True}
    if action == 'progress':
        state = session.get(key, {})
        state['completed'] = max(0, min(6, int(payload.get('completed', 0))))
        session[key] = state
        return {'ok': True, 'state': state}
    return {'ok': False, 'message': 'Neznámá akce.'}
