def handle(action, payload, session, user):
    key = "ryby_stavba_tela"
    if action == "save":
        session[key] = {
            "score": int(payload.get("score", 0) or 0),
            "total": int(payload.get("total", 20) or 20),
            "lang": str(payload.get("lang", "cs")),
            "mode": str(payload.get("mode", "practice")),
        }
        return {"ok": True, "saved": session[key]}
    if action == "load":
        return {"ok": True, "state": session.get(key, {})}
    if action == "reset":
        session.pop(key, None)
        return {"ok": True}
    return {"ok": True}
