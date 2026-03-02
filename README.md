# Lauateeninduse süsteemi prototüüp (Windows / Python)

## Autentimine

- Rakenduse avamisel küsitakse **4-kohalist koodi**.
- SUPER kood on **`0000`**.
- SUPER saab lisada uusi 4-kohalisi koode.
- Väljalogimisel küsitakse kohe uuesti autentimist.

## Laua ligipääs ja värvid

- Kui laud on **vaba** (tellimusi pole), on see **roheline**.
- Kui laud on valitud, on see **tumesinine**.
- Kui laual on tellimus ja see kuulub sinu koodile, on see **kollane**.
- Kui laud on teise koodi all, on see sulle **punane** ja sa ei saa seda avada.
- SUPER näeb teiste hõivatud laudu samuti **punasena**, kuid SUPER saab need avada.

## Uued visuaalsed muudatused

- Lauad ja istumiskohad on tehtud väiksemaks, et suurem kaart mahuks paremini ekraanile.
- Tellimuse akna vasakul küljel kuvatakse valitud laua eraldi detailvaade koos istekohtade ringidega.
- Detailvaates on istekoha ring vaikimisi **roheline**.
- Kui külalise ID-s olev number vastab istekoha numbrile, muutub see istekoha ring **kollaseks**.

## Tööpõhimõte

- Peaaken on kaart.
- Kui klikid lauda, avaneb kohe tellimuse aken.
- Dialoogaknad avatakse esiplaanile ning tekstiväljad saavad fookuse automaatselt (saab kohe kirjutada).

## Käivitamine

```bash
python restaurant_service_app.py
```

## Failid

- `restaurant_service_app.py` – rakenduse kood
- `table_layout.json` – laua paigutus
- `access_codes.json` – autentimiskoodid
