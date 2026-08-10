# CLAUDE.md — Lern-Loop-Workspace: «FACH»

> Generalisiertes Lern-Loop-Muster (Prototyp: Math DS 2). Diese Datei wurde von
> `lernen --init` in den Materialordner gestempelt. Beim Bootstrap füllt eine
> Claude-Instanz die «Platzhalter» aus dem vorhandenen Material aus.
> Gestartet wird der Loop über `lernen «dieser Ordner»` (eigenes Desktop-Icon möglich).

## Eckdaten (beim Init ausfüllen)

| | |
|---|---|
| **Fach** | «FACH» |
| **Klausur** | «Datum, Uhrzeit, Ort» |
| **Modus** | «schriftlich \| mündlich» |
| **Bestehen ab** | «z.B. 50 %» |
| **Hilfsmittel** | «z.B. 5 handschriftliche A4-Seiten \| keine \| Formelsammlung» |

## Themenkarte (beim Init aus dem Material füllen)

Der Klausur-Bauplan: die Themen + je Thema die typische Falle. Bewusst ein
Abschnitt in dieser Datei und keine eigene Datei — so lädt Claude ihn
automatisch mit. Die Häppchen rotieren durch diese Themen.

| # | Thema | Typische Falle |
|---|-------|----------------|
| 1 | «…» | «…» |
| 2 | «…» | «…» |

## Die drei Kern-Dateien

- **`CLAUDE.md`** (diese Datei) = *wie* + Eckdaten + Themenkarte. Zuerst lesen.
- **`todo.md`** = *wo stehen wir* — Re-Entry-Punkt: Klausurdatum, Stand, aktive Dateien.
- **`fehlermuster.md`** = *was ich falsch mache*, der personalisierte Kern. Nach JEDEM
  Review mitziehen: User-Zitat → warum falsch → was stattdessen. Dominante Muster oben halten.
- **`Personalisierte_Übungen/`** — die Häppchen (`haeppchen_NN.tex` → `.pdf`),
  `.xopp`-Handschrift-Annotationen, `haeppchen_NN_reviewt.png` (annotierte Reviews).

## Situative Dateien — nur anlegen, wenn gebraucht

- **`notebooklm_lernpausen.md`** (nur wenn du Lernpausen-Videos/Quiz willst) — EIN
  kompaktes NotebookLM-Doc: (A) Fehlermuster, (B) Themen im Schnelldurchlauf. Kein
  LaTeX, Unicode. Dynamisch, nicht kumulativ.
- **`Klausur_mitnehmen/`** (nur falls Hilfsmittel erlaubt) — Mitnehm-Blätter;
  Patch-SSoT `cheatsheet_personalisierung.md` (Fehlermuster → Blatt-Änderungen).

## Lern-Loop (der Kern)

**1. Lern-Set öffnen** — auf „lass uns lernen": die Referenz-/Mitnehm-Blätter + die
zuletzt geänderte Übung (Firefox) + die neueste `.xopp` (Xournal++, `xournalpp <datei> &`).

**2. Häppchen-Prinzip** — personalisierte Übungen als **kleine 5–10-min-Einzelaufgaben**,
die durch die `themenkarte.md`-Themen **rotieren** — NICHT große Multi-Aufgaben-Blätter
(die wirken erschlagend und verhindern den Einstieg). Verbindliche Design-Regeln:
- **Knapp:** EINE Aufgabe, max. ~2 Teilaufgaben, wenig Fließtext. Zwei Themen ⇒ zwei Häppchen.
- **Lösungsfrei:** das Blatt trägt NUR Aufgabe + ggf. EINEN Hinweis — NIE die Lösung/
  Musterkette. Sonst misst das Review nichts.
- **Nur echte Rechenaufgaben** (wörtlich aus Klausur/Übungsblatt). Theorie/Definitionen
  nur als fertige Merksätze aufs Cheatsheet, nicht als Übung.
- **Konzeptlücken erst prüfen:** bei neuen Themen nicht Bekanntheit voraussetzen — 1–2-
  Satz-Konzeptintro, Notation ausschreiben (z.B. ⟨a,b⟩ = a₁b₁+a₂b₂).
- **Ablauf:** eine Mini-Aufgabe → User löst digital mit Zwischenschritten → schickt Foto/
  Scan → gezieltes Review → nächstes Häppchen (nächster Typ).
- **Neue Häppchen-PDF sofort selbst in Firefox öffnen**, nicht nachfragen.

**3. Review-Regel (verbindlich): Fehler SICHTBAR am Blatt des Users zeigen**, nicht nur
loggen. Neueste `.xopp` zu PNG exportieren, Fehlerstellen rot einkreisen/nummerieren,
Legende (rot = Fehler mit Korrektur, grün = neu Gemeistertes) in den Freiraum darunter,
als `haeppchen_NN_reviewt.png` speichern und **sofort in Firefox öffnen**. Zusätzlich im
Chat explizit durchgehen (Zitat → warum falsch → was stattdessen). Erst danach das nächste
Häppchen. Jedes Review auch in `fehlermuster.md` (+ ggf. situative Docs, falls angelegt).

**Modus-Split:**
- **schriftlich** → der Häppchen-Rechen-Loop wie oben.
- **mündlich** → Laut-erklären-Loop: Begründungen laut formulieren, auf Schlüsselwörter
  bestehen. Rechnen üben hilft dort wenig.

## Terminal-Regel

Chat-Erklärungen **OHNE LaTeX** — kein `$...$`, kein `\frac`. Unicode-Notation
(√, x², ∫, ≤, λ, x_1, Brüche als (a+b)/c). LaTeX gehört nur in die `.tex`-Häppchen.

## Building the LaTeX (falls Häppchen als PDF)

`pdflatex -interaction=nonstopmode haeppchen_NN.tex`. `.aux`/`.log` sind Wegwerf-
Nebenprodukte. Nach dem Klausurdatum: dieser Workspace wird archiviert/eingefroren.
