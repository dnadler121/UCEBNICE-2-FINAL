def handle(action, payload, session, user):
    if action in ('start','status','reset'):
        return {'ok': True, 'message': 'Připraveno.'}
    return {'ok': True}
