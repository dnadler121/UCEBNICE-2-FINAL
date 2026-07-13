import importlib.util
from pathlib import Path

_MODULE_FILE = Path(__file__).parent / "modules" / "zakladni_operace.py"
_SPEC = importlib.util.spec_from_file_location("zakladni_operace_interactive", _MODULE_FILE)
_MATH = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MATH)

TARGET_EXAMPLES = 10


def _state_key(user):
    return f"math_integer_operations_{user['id']}"


def _new_expression(payload):
    try:
        count = max(3, min(8, int(payload.get("count", 5))))
        max_number = max(5, min(100, int(payload.get("max_number", 20))))
    except (TypeError, ValueError):
        raise ValueError("Neplatné nastavení generátoru.")

    allowed = payload.get("operations", ["+", "-", "*", "/"])
    if isinstance(allowed, str):
        allowed = [allowed]
    allowed = [op for op in allowed if op in {"+", "-", "*", "/"}]
    if not allowed:
        raise ValueError("Vyber alespoň jednu početní operaci.")

    use_parentheses = bool(payload.get("use_parentheses", True))
    return _MATH.generate_expression(
        number_count=count,
        allowed_operations=allowed,
        max_number=max_number,
        use_parentheses=use_parentheses,
    )


def handle(action, payload, session, user):
    key = _state_key(user)
    state = session.get(key, {
        "tokens": None,
        "mistakes_current": 0,
        "steps_current": 0,
        "completed_examples": 0,
        "total_mistakes": 0,
    })

    if action == "new":
        state["tokens"] = _new_expression(payload)
        state["mistakes_current"] = 0
        state["steps_current"] = 0
        session[key] = state
        operation = _MATH.next_operation(state["tokens"])
        return {
            "ok": True,
            "expression": _MATH.format_expression(state["tokens"]),
            "operation": operation,
            "finished": operation is None,
            "completed_examples": state["completed_examples"],
            "target_examples": TARGET_EXAMPLES,
            "message": "Začni operací zvýrazněnou v příkladu.",
        }

    if action == "reset":
        session.pop(key, None)
        return {
            "ok": True,
            "completed_examples": 0,
            "target_examples": TARGET_EXAMPLES,
            "message": "Průběh této lekce byl vynulován.",
        }

    if action != "check":
        return {"ok": False, "message": "Neznámá akce."}

    tokens = state.get("tokens")
    if not tokens:
        return {"ok": False, "message": "Nejdříve vytvoř nový příklad."}

    try:
        answer = int(str(payload.get("answer", "")).strip())
    except ValueError:
        return {"ok": False, "message": "Zadej celé číslo."}

    operation = _MATH.next_operation(tokens)
    if operation is None:
        return {
            "ok": True,
            "finished": True,
            "expression": _MATH.format_expression(tokens),
            "message": "Tento příklad už je vypočítaný.",
            "completed_examples": state["completed_examples"],
            "target_examples": TARGET_EXAMPLES,
        }

    if answer != operation["result"]:
        state["mistakes_current"] += 1
        state["total_mistakes"] += 1
        session[key] = state
        return {
            "ok": True,
            "correct": False,
            "finished": False,
            "expression": _MATH.format_expression(tokens),
            "operation": operation,
            "mistakes": state["mistakes_current"],
            "completed_examples": state["completed_examples"],
            "target_examples": TARGET_EXAMPLES,
            "message": "To ještě není správně. Zkus zvýrazněnou operaci znovu.",
        }

    state["tokens"] = _MATH.apply_step(tokens, operation["index"])
    state["steps_current"] += 1
    following = _MATH.next_operation(state["tokens"])
    example_finished = following is None

    lesson_finished = False
    percent = None
    grade = None

    if example_finished:
        state["completed_examples"] += 1
        lesson_finished = state["completed_examples"] >= TARGET_EXAMPLES
        # Výsledek vychází z počtu chyb během celé série.
        percent = max(0, round(100 * TARGET_EXAMPLES / (TARGET_EXAMPLES + state["total_mistakes"])))
        if percent >= 90:
            grade = 1
        elif percent >= 80:
            grade = 2
        elif percent >= 70:
            grade = 3
        elif percent >= 60:
            grade = 4
        else:
            grade = 5

    session[key] = state

    return {
        "ok": True,
        "correct": True,
        "finished": example_finished,
        "lesson_finished": lesson_finished,
        "expression": _MATH.format_expression(state["tokens"]),
        "operation": following,
        "steps": state["steps_current"],
        "mistakes": state["mistakes_current"],
        "completed_examples": state["completed_examples"],
        "target_examples": TARGET_EXAMPLES,
        "percent": percent,
        "grade": grade,
        "message": (
            f"Výborně! Dokončil jsi všech {TARGET_EXAMPLES} příkladů."
            if lesson_finished
            else (
                f"Příklad je hotový. Splněno {state['completed_examples']} z {TARGET_EXAMPLES}."
                if example_finished
                else "Správně. Pokračuj další zvýrazněnou operací."
            )
        ),
    }
