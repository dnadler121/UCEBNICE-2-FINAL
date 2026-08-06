# Matematika V47 – přísný obecný generátor

Generování variant nyní probíhá výhradně v pořadí: **vygenerovat vstupy → vypočítat všechny výsledky → aplikovat obecný filtr → teprve potom vykreslit studentovi**.

- filtr není specifický pro soustavy rovnic; používá `result_formula` libovolného matematického příkladu,
- při filtru „Celá čísla“ musí všechny vypočtené výsledky být celá čísla,
- před návratem varianty probíhá druhá nezávislá kontrola,
- při aktivním filtru je zakázán tichý fallback na neověřenou variantu.
