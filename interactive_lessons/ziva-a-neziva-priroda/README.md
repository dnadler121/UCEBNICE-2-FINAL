# Živá a neživá příroda – V17

Montessori · 6. ročník · Biologie

Opravy V17:
- v závěrečném testu je tlačítko „← Zpět do přehledu“,
- při vstupu do testu a po každé odpovědi se posílá testový stav na `{{ api_url("save") }}`,
- hlavní UČEBNICE díky tomu zapíše i nedokončený test do databáze jako „rozpracováno / přerušeno“,
- při návratu zpět, zavření karty nebo opuštění stránky se stav odešle ještě jednou pomocí sendBeacon,
- `{{ complete_url }}` se používá pouze po dokončení všech 15 otázek.
