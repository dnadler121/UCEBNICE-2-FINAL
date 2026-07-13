# Import matematických a informatických lekcí

V administraci otevři **Import matematika / informatika** a nahraj ZIP.

Každý balíček musí obsahovat:

```text
nazev-lekce/
├── lesson.json
├── lesson_app.py
├── templates/
│   └── index.html
└── static/
```

Povinné údaje v `lesson.json`:

- `subject`: `matematika` nebo `informatika`
- `school`
- `grade`
- `topic`
- `title`
- `slug`

Nová škola, ročník nebo téma se vytvoří automaticky podle údajů v JSON.
Po dokončení lekce se přes `complete_url` uloží procenta, známka a datum dokončení.
