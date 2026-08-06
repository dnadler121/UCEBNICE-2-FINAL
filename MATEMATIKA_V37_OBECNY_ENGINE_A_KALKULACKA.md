# MATEMATIKA V37 – obecné výsledky a studentská kalkulačka

## Co zůstává beze změny
- Stávající matematický engine a staré lekce zůstávají funkční.
- Speciální matematické konstrukce jsou ve studentském vstupu pevné: např. α, znak °, odmocnina, log/ln, sin/cos/tan, inverzní goniometrické funkce, π, integrál, derivace, absolutní hodnota, závorky a zlomková čára.
- Student doplňuje pouze připravená políčka pro číslice, proměnné a běžné operátory.

## Náhodné varianty
Učitel zadá vzorová čísla jako n1, n2, ... a volitelnou podmínku.
Příklad pravoúhlého trojúhelníku:
- vzor: a=3,b=4,c=5
- čísla: 3;4;5
- podmínka: n1**2+n2**2==n3**2

## Přepočet jednoho výsledku
Správná odpověď vzoru:
alpha=36.87deg

Vzorec pro přepočet:
degrees(asin(n1/n3))

## Více vypočtených výsledků
Do pole „Vzorec / vzorce pro přepočet výsledku“ lze zadat více vzorců, každý na nový řádek nebo oddělený středníkem. Engine výsledky dosadí do správné odpovědi ve stejném pořadí.

Příklad:
Správná odpověď:
x=2,y=3

Vzorce:
n1+n2
n3-n4

V praxi lze stejným principem zadat obecné vzorce pro řešení soustavy podle koeficientů n1, n2, ...

## Studentská vědecká kalkulačka
Na stránce matematické lekce je tlačítko „Otevřít kalkulačku“. Kalkulačka je uvnitř aplikace a nevyvolá ochranu proti opuštění stránky.

Obsahuje:
- +, −, ×, ÷, mocniny, závorky
- odmocninu
- sin, cos, tan
- sin⁻¹, cos⁻¹, tan⁻¹
- log, ln
- π
- režim DEG/RAD (výchozí DEG)

Kalkulačka pouze počítá číselné výrazy. Neřeší celé rovnice ani soustavy automaticky.

## Inverzní funkce ve studentském zápisu
Učitelský zápis asin(...), acos(...), atan(...) se studentovi vizuálně zobrazí jako sin⁻¹(...), cos⁻¹(...), tan⁻¹(...). Funkce je pevná konstrukce a student doplňuje pouze její argument.
