# Matematika V50 – skutečně náhodné varianty žáků

- Vstupní proměnné (`n1;n2;n3;...`) se při prvním otevření příkladu skutečně náhodně losují z nastaveného rozsahu.
- Každý náhodný kandidát musí splnit učitelovu matematickou podmínku a případné filtry výsledků.
- Engine se pokud možno vyhne stejné variantě, kterou už dostal jiný žák u stejného příkladu.
- Vylosovaná varianta se uloží do `MathAttempt.variant_json`, takže obnovení stránky ani nové přihlášení studentovi čísla nezmění.
- Pokud je platných variant méně než studentů, systém po vyčerpání možností dovolí opakování místo chyby.
- Starší lekce a zbytek matematického enginu zůstávají kompatibilní.
