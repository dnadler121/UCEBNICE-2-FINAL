# UČEBNICE 2.0 – spuštění

## 1. Lokální přihlášení učitele

Zkopíruj `.env.example` jako `.env` a doplň své heslo.

```powershell
Copy-Item .env.example .env
```

Soubor `.env` se na GitHub neodesílá.

## 2. Instalace a spuštění

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Otevři `http://127.0.0.1:5000`.

## 3. Dva druhy lekcí
  python app.py
### Biologie a občanská výchova

V administraci klikni na **Nová HTML lekce**. Povinně vyplníš:

- předmět,
- školu a ročník,
- téma,
- název lekce.

Podle těchto údajů se lekce automaticky zařadí.

### Matematika a informatika

Klikni na **Import aplikace** a nahraj ZIP s povinným `lesson.json`.

```json
{
  "subject": "matematika",
  "school": "Střední škola",
  "grade": "1. ročník",
  "topic": "Početní operace",
  "title": "Hierarchie početních operací",
  "slug": "hierarchie-pocetnich-operaci",
  "icon": "➗"
}
```

Nová škola, ročník nebo téma se vytvoří automaticky z údajů v JSON.

## 4. Výsledky

- Biologie a občanka: výsledek závěrečného testu.
- Matematika a informatika: dokončení interaktivní lekce.
- Ukládá se student, předmět, škola/ročník, téma, lekce, procenta, známka a datum dokončení.
- Jednotlivé nebo všechny výsledky lze smazat.
- Smazání výsledků nesmaže studenty ani jejich trvalý pokrok.

## 5. Render

Na Renderu ponech stejné proměnné prostředí. `.env` se používá pouze lokálně.
