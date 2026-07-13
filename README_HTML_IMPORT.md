# Import HTML výkladu

Výklad se vkládá jako hotový HTML soubor.

Postup:
1. Připrav výklad mimo aplikaci.
2. Převeď ho na HTML.
3. V editoru vyber hlavní `.html` / `.htm` soubor.
4. Do pole „Obrázky k HTML“ vyber obrázky, které patří k danému HTML.
5. Klikni na „Uložit lekci“.

Aplikace zkopíruje obrázky do `static/uploads` a opraví cesty v HTML podle názvů souborů.

Doporučený převod přes pandoc:

```bash
pandoc "vyklad.docx" -o vyklad.html --extract-media=media
```

Potom vyber `vyklad.html` a obrázky ze složky `media`.
