import importlib.util
from pathlib import Path

_MODULE_FILE = Path(__file__).parent / "modules" / "course_data.py"
_SPEC = importlib.util.spec_from_file_location("decimal_course_data", _MODULE_FILE)
_DATA = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_DATA)
COURSE = _DATA.COURSE


def handle(action, payload, session, user):
    if action == "course":
        return {"ok": True, "course": COURSE}
    return {"ok": False, "message": "Neznámá akce."}
