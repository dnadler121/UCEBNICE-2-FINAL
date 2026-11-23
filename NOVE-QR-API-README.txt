NOVY SPOLECNY SYSTEM QR / VYSLEDKY

Trvala verejna adresa lekce: https://VAS-WEB/join/<slug>
Pro nove ZIP lekce pouzijte ve skriptu volani:
POST /join/<slug>/api/join {"name":"Adela"}
POST /join/<slug>/api/progress {"answered":1,"correct":1,"total":40}
GET  /join/<slug>/api/status
POST /join/<slug>/api/restart {}

Ucitelsky prehled: /teacher/public-progress
V databazi je odkaz na tento prehled. Kazdy pokus ma vlastni zaznam.

POZOR: Stare ZIP lekce maji vlastni API, nektere vyzaduji PIN nebo
vlastni start hodiny. Samotna nova infrastruktura jejich vnitrni
HTML/JavaScript automaticky neprepisuje. Aby fungovaly bez PIN, je
nutne upravit jejich balicky na toto spolecne API.

Pred nasazenim zalohujte produkcni databazi. Provozni test na Renderu
nebyl proveden.
