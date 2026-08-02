"""Jednoduchý testovací program pro lekci informatiky."""

def spocitej_celkem(ceny):
    return sum(ceny)

jidla = {
    "Svíčková": 189,
    "Kuřecí řízek": 169,
    "Špagety": 149,
}

print("NABÍDKA RESTAURACE")
for jidlo, cena in jidla.items():
    print(f"{jidlo}: {cena} Kč")

celkem = spocitej_celkem(list(jidla.values()))
print(f"Součet cen: {celkem} Kč")

if celkem > 500:
    print("Součet cen je vyšší než 500 Kč.")
else:
    print("Součet cen je nejvýše 500 Kč.")
