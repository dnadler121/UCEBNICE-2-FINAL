# Matematika V41 – obecný strukturovaný výstup a filtr výsledků

## Co je nové

### 1. Strukturovaný studentský výstup
U jednoduchých konečných výsledků aplikace pozná strukturu odpovědi.

Příklady:
- `x=2` → student vidí pevné `x =` a doplní hodnotu.
- `y=-1.5` → student vidí pevné `y =` a doplní `-1.5` po znacích.
- `alpha=36.87deg` → student vidí pevné `α =` a `°`, doplní pouze číslo.

U algebraických mezikroků, např. `x=y+2`, zůstává původní režim po znacích, aby aplikace studentovi nepředvyplnila samotný algebraický postup.

### 2. Obecná pravidla pro vygenerované výsledky
U obecné náhodné varianty lze nastavit:
- typ výsledku: bez omezení / celá čísla,
- znaménko: bez omezení / nezáporné / kladné,
- minimum výsledku,
- maximum výsledku,
- maximální počet desetinných míst (`-1` = bez omezení).

Generátor variantu použije až tehdy, když všechny výsledky vypočítané pomocí polí „Vzorec / vzorce pro přepočet výsledku“ tato pravidla splní.

Tento filtr není navázaný na soustavy rovnic. Funguje stejně pro goniometrii, geometrii, logaritmy, fyziku a další témata.

## Doporučené nastavení pro náhodnou soustavu
Pro soustavu se dvěma výsledky `x`, `y`:
- Typ výsledku: **Celá čísla**
- Znaménko: podle potřeby
- Max. desetinných míst: `-1` (u celých čísel není třeba)

Pak generátor odmítne variantu, pokud vypočtené `x` nebo `y` není celé číslo, a zkusí další náhodná čísla.
