# Lauateeninduse süsteemi prototüüp (Windows / Python)

See on lihtne töölaua-rakendus (`tkinter`), mis demonstreerib lauateeninduse töövoogu:

- teenindaja näeb **laudade kaarti**;
- lauad on **ristkülikud**;
- lauda lisades küsitakse, mitu inimest istub igal küljel (üleval, paremal, all, vasakul);
- laua kuju ratio arvestab külgede istekohtade maksimumiga:
  - laius = `max(üleval, all)`
  - kõrgus = `max(vasakul, paremal)`
- istumiskohad kuvatakse väikeste ringidena numbritega **päripäeva**, alustades ülevalt vasakult suunalt;
- lisada tellimusi konkreetse **külalise** alla;
- kuvada **jagatud arve** või **ühise arve**;
- makstes näha külalise **tšeki formaati**;
- valida makseviis:
  - **sularaha**: sisestatakse antud summa;
  - **kaart**: avaneb eraldi "Sisesta kaart" aken ja kinnitusega märgitakse tasutuks;
- salvestada/laadida lauaplaani JSON-failina.

## Käivitamine (Windows)

1. Veendu, et Python 3.11+ on installitud.
2. Ava `cmd` või PowerShell kaustas, kus fail asub.
3. Käivita:

```bash
python restaurant_service_app.py
```

## Failid

- `restaurant_service_app.py` – rakenduse lähtekood.
- `table_layout.json` – tekib automaatselt, kui salvestad kaardi.

## Märkus

Tegu on prototüübiga. Päris maksete vastuvõtuks lisa turvaline makseintegratsioon (nt kaarditerminal või sertifitseeritud makseteenuse API).
