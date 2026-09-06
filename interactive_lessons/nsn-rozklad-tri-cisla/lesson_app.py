import random
from collections import Counter
from math import prod

DIVISORS = [2, 3, 5, 7, 11]
TARGET_EXAMPLES = 10


def _key(user):
    return f"nsn_three_{user['id']}"


def _prime(n):
    if n < 2: return False
    d = 2
    while d*d <= n:
        if n % d == 0: return False
        d += 1
    return True


def _factor(n):
    out=[]; d=2
    while n > 1:
        while n % d == 0:
            out.append(d); n//=d
        d += 1
    return out


def _lcm3(nums):
    mx = Counter()
    for n in nums:
        c = Counter(_factor(n))
        for p,k in c.items(): mx[p] = max(mx[p], k)
    return prod(p**k for p,k in mx.items())


def _new_numbers():
    # Složená, různá čísla; rozsah je didakticky přehledný pro ruční rozklad.
    candidates=[n for n in range(12,61) if not _prime(n)]
    while True:
        nums=random.sample(candidates,3)
        # Alespoň jeden společný prvočinitel, aby škrtání mělo smysl.
        fs=[set(_factor(n)) for n in nums]
        if (fs[0]&fs[1]) or (fs[0]&fs[2]) or (fs[1]&fs[2]):
            return nums


def _fresh_state(done=0, mistakes=0):
    nums=_new_numbers()
    rows=[]; next_id=1
    for n in nums:
        rows.append([{"id":next_id,"value":n,"crossed":False}]); next_id+=1
    return {"numbers":nums,"rows":rows,"next_id":next_id,"phase":"factor",
            "completed":done,"mistakes":mistakes,"example_mistakes":0}


def _public(st, message=""):
    return {"ok":True,"numbers":st["numbers"],"rows":st["rows"],"phase":st["phase"],
            "divisors":DIVISORS,"completed":st["completed"],"target":TARGET_EXAMPLES,
            "mistakes":st["example_mistakes"],"message":message}


def _all_prime(rows):
    return all(_prime(x["value"]) for row in rows for x in row)


def _expected_crossable(st, row_idx, value):
    # Kolik výskytů value má být v daném řádku vyškrtnuto proti dosavadnímu sjednocení maxima.
    prev_max=0
    for r in range(row_idx):
        prev_max=max(prev_max, sum(1 for x in st["rows"][r] if x["value"]==value and not x["crossed"]))
    # Po předchozím škrtání reprezentuje součet nepřeškrtnutých předchozích řádků právě union maxima.
    prev_union=sum(1 for r in range(row_idx) for x in st["rows"][r] if x["value"]==value and not x["crossed"])
    crossed_here=sum(1 for x in st["rows"][row_idx] if x["value"]==value and x["crossed"])
    return crossed_here < prev_union


def handle(action, payload, session, user):
    key=_key(user)
    st=session.get(key)
    if action in ("new","reset") or not st:
        done=0 if action=="reset" or not st else st.get("completed",0)
        mistakes=0 if action=="reset" or not st else st.get("mistakes",0)
        st=_fresh_state(done,mistakes); session[key]=st
        return _public(st,"Rozlož postupně všechna tři čísla. Začni nejmenším prvočíslem, kterým lze vybrané číslo dělit.")

    if action=="split":
        try: row=int(payload.get("row")); item_id=int(payload.get("item")); divisor=int(payload.get("divisor"))
        except: raise ValueError("Vyber číslo a prvočíselného dělitele.")
        if st["phase"]!="factor": raise ValueError("Rozklad už je dokončen.")
        if divisor not in DIVISORS: raise ValueError("Použij nabídnutý prvočíselný dělitel.")
        target=next((x for x in st["rows"][row] if x["id"]==item_id),None)
        if not target: raise ValueError("Vyber číslo, které chceš rozložit.")
        v=target["value"]
        if _prime(v):
            st["example_mistakes"]+=1; st["mistakes"]+=1; session[key]=st
            return {**_public(st,"Toto číslo je už prvočíslo."),"correct":False}
        # vyžadujeme nejmenší prvočíselný dělitel – přesně nácvik 2, pak 3, 5...
        smallest=next(d for d in DIVISORS if v%d==0)
        if divisor!=smallest:
            st["example_mistakes"]+=1; st["mistakes"]+=1; session[key]=st
            return {**_public(st,f"Tudy ne. Zkoušej prvočísla postupně od nejmenšího."),"correct":False}
        st["rows"][row].remove(target)
        for val in (divisor, v//divisor):
            if val!=1:
                st["rows"][row].append({"id":st["next_id"],"value":val,"crossed":False}); st["next_id"]+=1
        if _all_prime(st["rows"]): st["phase"]="cross"
        session[key]=st
        msg="Správně. Pokračuj v rozkladu." if st["phase"]=="factor" else "Výborně. Všechna čísla jsou rozložena. Teď vyškrtej opakující se činitele ve 2. a 3. řádku."
        return {**_public(st,msg),"correct":True}

    if action=="cross":
        if st["phase"]!="cross": raise ValueError("Nejdříve dokonči rozklad.")
        try: row=int(payload.get("row")); item_id=int(payload.get("item"))
        except: raise ValueError("Vyber činitel ke škrtnutí.")
        if row not in (1,2): raise ValueError("V prvním řádku nic neškrtáme.")
        item=next((x for x in st["rows"][row] if x["id"]==item_id),None)
        if not item or item["crossed"]: raise ValueError("Vyber nevyškrtnutý činitel.")
        if not _expected_crossable(st,row,item["value"]):
            st["example_mistakes"]+=1; st["mistakes"]+=1; session[key]=st
            return {**_public(st,"Tento činitel už v dosavadním součinu nemá odpovídající dvojici."),"correct":False}
        item["crossed"]=True; session[key]=st
        return {**_public(st,"Správně vyškrtnuto. Hledej další dvojici, nebo pokračuj k součinu."),"correct":True}

    if action=="to_product":
        if st["phase"]!="cross": raise ValueError("Ještě nejsi ve fázi škrtání.")
        # Ověř, že už nezůstala žádná povinně škrtatelná položka.
        for r in (1,2):
            for x in st["rows"][r]:
                if not x["crossed"] and _expected_crossable(st,r,x["value"]):
                    st["example_mistakes"]+=1; st["mistakes"]+=1; session[key]=st
                    return {**_public(st,"Ještě lze vyškrtnout alespoň jednu dvojici."),"correct":False}
        st["phase"]="product"; session[key]=st
        return {**_public(st,"Vynásob všechny nevyškrtnuté prvočinitele."),"correct":True,
                "factors":[x["value"] for row in st["rows"] for x in row if not x["crossed"]]}

    if action=="answer":
        if st["phase"]!="product": raise ValueError("Nejdříve dokonči škrtání.")
        try: answer=int(payload.get("answer"))
        except: raise ValueError("Zadej celé číslo.")
        result=_lcm3(st["numbers"])
        if answer!=result:
            st["example_mistakes"]+=1; st["mistakes"]+=1; session[key]=st
            return {**_public(st,"Výsledek ještě nesouhlasí. Zkontroluj součin nevyškrtnutých prvočinitelů."),"correct":False,
                    "factors":[x["value"] for row in st["rows"] for x in row if not x["crossed"]]}
        st["completed"]+=1
        percent=max(0,round(100*st["completed"]/(st["completed"]+st["mistakes"])))
        grade=1 if percent>=90 else 2 if percent>=75 else 3 if percent>=60 else 4 if percent>=40 else 5
        finished=st["completed"]>=TARGET_EXAMPLES
        done=st["completed"]; totalmist=st["mistakes"]
        session[key]=st
        return {**_public(st,"Správně! NSN je vypočítán."),"correct":True,"example_done":True,"lesson_finished":finished,
                "result":result,"percent":percent,"grade":grade,"completed":done,"total_mistakes":totalmist}

    raise ValueError("Neznámá akce.")
