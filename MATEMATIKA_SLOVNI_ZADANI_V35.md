# Matematika V35 – slovní zadání + matematický vzor

V35 odděluje text, který čte žák, od technického matematického vzoru enginu.

Příklad:
- Slovní zadání: `V pravoúhlém trojúhelníku jsou strany 3 cm, 4 cm a 5 cm. Urči sin α.`
- Matematický vzor: `a=3,b=4,c=5`
- Obecné varianty: zapnuto
- Čísla z matematického vzoru: `3; 4; 5`
- Podmínka: `n1**2 + n2**2 == n3**2`
- Správná odpověď kroku: `sin(alpha)=3/5`

Engine vytvoří stabilní variantu pro konkrétního žáka a stejnou náhradu použije ve slovním zadání, matematickém vzoru, instrukci, správné odpovědi a nápovědě.

Zpětná kompatibilita: staré lekce bez slovního zadání používají původní pole `problem` a zobrazují se stejně jako dříve. Databázový sloupec `prose_problem` se při startu aplikace doplní automaticky.
