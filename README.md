# Lauateeninduse süsteemi prototüüp (Windows / Python)

## Uued põhimõtted

- Rakenduse avamisel küsitakse **autentimiskoodi**.
- Kood `0000` on **SUPER**:
  - saab lisada/muuta kaarti (uued lauad);
  - saab lisada uusi teenindaja koode;
  - näeb ja avab kõiki laudu.
- Teised koodid on teenindajad:
  - saavad võtta vaba laua enda kasutusse;
  - lauda näevad/saad avada seni ainult nemad ja SUPER, kuni kõik on makstud.

## Laua värvid kaardil

- **Roheline** – laud on vaba.
- **Sinine** – laud on sinu kasutuses.
- **Tumesinine** – sinu valitud laud.
- **Punane** – laud on teise teenindaja kasutuses (sulle lukus).

## UI struktuur

- **Peaaken** näitab ainult kaarti + ülemist tööriistariba.
- Tellimused avanevad eraldi aknas (**"Ava tellimuse aken"**).
- Kõik alamdialoogid (tellimus, makse jne) avatakse esiplaanis, et need ei jääks peaakna taha.

## Lauad

- Lauad on ristkülikud.
- Laua lisamisel küsitakse istekohtade arv 4 küljel (üleval, paremal, all, vasakul).
- Proportsioon:
  - laius = `max(üleval, all)`
  - kõrgus = `max(vasakul, paremal)`
- Istekohad kuvatakse väikeste ringidena, nummerdatud päripäeva.

## Käivitamine (Windows)

```bash
python restaurant_service_app.py
```

## Failid

- `restaurant_service_app.py` – rakenduse kood.
- `table_layout.json` – kaardipaigutus.
- `access_codes.json` – autentimiskoodid.
