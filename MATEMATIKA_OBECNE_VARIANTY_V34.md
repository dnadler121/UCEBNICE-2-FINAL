# Matematika V34 – obecné náhodné varianty s podmínkami

Stávající matematický generátor zůstává zachovaný. U každého příkladu lze nově volitelně zapnout **Obecné náhodné varianty pro každého žáka**.

## Použití

1. Zadání a správné kroky napiš normálně pomocí čísel, stejně jako dosud.
2. Zapni obecné náhodné varianty.
3. Do pole **Čísla ze vzoru, která se mají měnit** napiš čísla oddělená středníkem, např. `3; 4; 5`.
4. Aplikace jim automaticky přiřadí názvy `n1`, `n2`, `n3`.
5. Nastav rozsah a krok náhodných hodnot.
6. Volitelně zadej podmínku, např. `n1**2 + n2**2 == n3**2`.

Podmínka není navázána na goniometrii ani trojúhelníky. Je to obecný matematický filtr. Lze použít např.:

- `n1 < n2`
- `n1 % n2 == 0`
- `n1 + n2 < 100`
- `n1**2 + n2**2 == n3**2`
- `sqrt(n1) == n2`
- více podmínek: `n1 < n2 and n2 < n3`

Stejné hodnoty se po vygenerování nahradí v **zadání, instrukci, správném stavu/odpovědi i nápovědě**. Matematická forma textu se zachová.

Pokud obecné varianty nejsou zapnuté, aplikace se chová stejně jako před touto změnou, včetně původního generátoru jednoduchých lineárních rovnic.
