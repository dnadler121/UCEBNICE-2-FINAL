# Matematika V36 – přepočet výsledku + zachování formuláře

## 1. Obecný přepočet výsledku
U kroku lze při zapnutých „Obecných náhodných variantách“ vyplnit nové pole **Vzorec pro přepočet výsledku**.

Příklad pro pravoúhlý trojúhelník 3–4–5, kde je strana 3 proti úhlu alfa a 5 je přepona:

- Slovní zadání: `V pravoúhlém trojúhelníku jsou strany 3 cm, 4 cm a 5 cm. Urči úhel alpha.`
- Matematický vzor: `a=3,b=4,c=5`
- Čísla ze vzoru: `3;4;5`
- Podmínka: `n1**2+n2**2==n3**2`
- Správný stav / odpověď: `alpha=36.87deg`
- Vzorec pro přepočet výsledku: `degrees(asin(n1/n3))`
- Zaokrouhlení: `2`

Aplikace při ukládání ověří, že vzorec pro původní hodnoty skutečně dává 36,87. Pro každého studenta pak po vygenerování nových hodnot dopočítá nový správný úhel a zachová tvar odpovědi `alpha=...deg`.

Vzorec je obecný. Povolené funkce zahrnují například `sqrt`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `degrees`, `radians`, `log`, `ln`, `exp`, `abs`, `min`, `max`, `round`; konstanty `pi` a `e`.

## 2. Chyba při tvorbě lekce
Při chybě matematického vzoru, podmínky generování, rozsahu, správné odpovědi nebo vzorce výsledku se stránka už nepřesměruje na prázdný formulář.

- dosud vyplněné textové údaje zůstanou,
- chybné pole se zvýrazní červeně,
- nahoře se zobrazí konkrétní chybová zpráva,
- stránka se posune k chybnému poli.

Poznámka: webové prohlížeče z bezpečnostních důvodů neumějí po neúspěšném odeslání automaticky znovu vyplnit lokální `<input type=file>`. Textová a matematická pole však zůstávají zachována.

## 3. Zpětná kompatibilita
Staré lekce fungují dál. Nový vzorec výsledku je nepovinný. Pokud není vyplněn, generátor se chová stejně jako ve V35.
