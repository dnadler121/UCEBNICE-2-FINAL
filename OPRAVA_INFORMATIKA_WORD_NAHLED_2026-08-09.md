# Oprava Informatiky – Word náhled a rozložení

Opraveno 2026-08-09:

1. HTML výklad na stránce informatického úkolu se nyní zobrazuje v odděleném `iframe`.
   CSS uvnitř učitelského HTML tak už nemůže změnit šířku nebo vzhled celé studentské stránky.
2. Stránka jednotlivého informatického úkolu používá jeden široký hlavní sloupec.
3. Náhled učitelského Word/Excel/PowerPoint souboru stále přednostně používá PDF z LibreOffice.
4. Pokud LibreOffice na serveru není dostupný, aplikace už neukáže chybu `No such file or directory: libreoffice`.
   Místo toho vytvoří interní HTML náhled přímo v Pythonu.
5. Word fallback zachovává základní typografii, zarovnání, tabulky a vložené obrázky; Excel zobrazí listy jako tabulku a PowerPoint jednotlivé snímky.
