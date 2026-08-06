# Matematika V38 – víceřádkové matematické vzory

V38 rozšiřuje V37 o podporu více matematických řádků v poli **Matematický vzor pro engine**.

## Soustava rovnic
Do pole lze nyní přímo napsat například:

```text
2x+y=7
x-y=2
```

Každý řádek je validován samostatně. Podporován je libovolný počet řádků. Pro zpětnou kompatibilitu dál fungují i jednořádkové vzory a seznamy přiřazení jako `a=3,b=4,c=5`.

Více matematických výrazů lze technicky oddělit také středníkem, ale pro přehlednost je doporučeno používat nový řádek.

Na náhledu se zalomení řádků zachovává.

## Slovní zadání a soustava
Pokud chceš, aby student viděl rovnice pod sebou přímo v zadání, napiš je také do pole **Slovní zadání pro žáka** na samostatné řádky. V38 zachová zalomení řádků i ve studentské verzi. Matematický vzor zůstává technickým podkladem enginu.
