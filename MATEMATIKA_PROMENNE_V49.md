# Matematika – proměnný engine V49

Nový doporučený způsob tvorby náhodných příkladů:

1. Zapni „Obecné náhodné varianty“.
2. Do „Vstupní proměnné“ napiš pouze `n1;n2;n3;...`.
3. Nastav rozsah a případnou podmínku, např. `n1**2+n2**2==n3**2`.
4. Ve slovním zadání používej `{n1}`, `{n2}`, `{n3}`.
5. V matematickém zápisu a správných stavech používej přímo `n1`, `n2`, `n3` – žádná vzorová čísla nejsou potřeba.
6. V kroku lze vytvořit pomocnou proměnnou, např. `d=degrees(asin(n1/n3))`; další kroky ji mohou použít.
7. Když je správný stav `alpha=d` a `d` vzniká přes `degrees(...)`, studentovi se vykreslí `α = [hodnota]°`; α, = a ° jsou pevné.

Příklad sinus:
- vstupy: `n1;n2;n3`
- podmínka: `n1**2+n2**2==n3**2`
- krok 1 správný stav: `sin(alpha)=n1/n3`
- krok 2 správný stav: `alpha=d`
- krok 2 výpočet: `d=degrees(asin(n1/n3))`

Staré lekce s číselnými vzory zůstávají v backendu podporované.
