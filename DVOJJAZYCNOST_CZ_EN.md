# Dvojjazyčnost CZ / EN – první integrovaná verze

- Globální jazyk je uložen v session (`cs` / `en`).
- Přepínač CZ/EN je v horní liště celé aplikace.
- Přihlášení a hlavní portál jsou přeloženy do angličtiny.
- Překladový systém `t()` je dostupný ve všech Jinja šablonách, takže další systémové texty lze doplňovat bez kopírování stránek.
- Při zahájení studentské HTML lekce se jazyk uzamkne; po řádném dokončení závěrečného testu se znovu odemkne.
- Výsledky a databáze zůstávají společné pro oba jazyky.
- Obsah existujících lekcí se automaticky nepřekládá; pro plné EN lekce je potřeba doplnit anglický obsah/otázky. Tato verze záměrně nepoužívá automatický strojový překlad, aby neměnila odborný obsah bez kontroly učitele.
