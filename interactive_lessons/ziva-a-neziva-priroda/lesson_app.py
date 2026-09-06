def _grade(percent):
    if percent >= 90: return 1
    if percent >= 75: return 2
    if percent >= 60: return 3
    if percent >= 40: return 4
    return 5


def handle(action, payload, session, user):
    key = f"living_nonliving_v17_{user['id']}"
    if action == "start":
        session[key] = {"started": True}
        return {"ok": True}
    if action == "status":
        return {"ok": True, "state": session.get(key, {})}
    if action == "reset":
        session[key] = {}
        return {"ok": True}
    if action == "save":
        # Hlavní UČEBNICE zachytí testový payload tohoto API požadavku
        # a uloží průběžný/přerušený výsledek do InteractiveResult.
        st = session.get(key, {})
        st.update({
            "mode": payload.get("mode", "test"),
            "percent": int(payload.get("percent", 0) or 0),
            "score": int(payload.get("score", 0) or 0),
            "answered": int(payload.get("answered", 0) or 0),
            "total": int(payload.get("total", 15) or 15),
            "interrupted": bool(payload.get("interrupted", True)),
        })
        session[key] = st
        return {"ok": True, "saved": True, "state": st}
    if action == "grade":
        p = max(0, min(100, int(payload.get("percent", 0))))
        return {"ok": True, "percent": p, "grade": _grade(p)}
    return {"ok": False}
