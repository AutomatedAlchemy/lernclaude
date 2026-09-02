# CLAUDE.md — Lern-Loop-Workspace: «FACH»

> Generalisiertes Lern-Loop-Muster (Prototyp: Math DS 2). Diese Datei wurde von
> der Kurs-Anlage in den Materialordner gestempelt. Die anlegende Claude-Instanz
> füllt die «Platzhalter» aus dem vorhandenen Material aus.
> Gestartet wird der Loop über `lernen «dieser Ordner»` (eigenes Desktop-Icon möglich).

## Eckdaten (beim Anlegen ausfüllen)

| | |
|---|---|
| **Fach** | «FACH» |
| **Klausur** | «Datum, Uhrzeit, Ort» |
| **Modus** | «schriftlich \| mündlich» |
| **Bestehen ab** | «z.B. 50 %» |
| **Hilfsmittel** | «z.B. 5 handschriftliche A4-Seiten \| keine \| Formelsammlung» |

## Themenkarte (beim Anlegen aus dem Material füllen)

Der Klausur-Bauplan: die Themen + je Thema die typische Falle. Bewusst ein
Abschnitt in dieser Datei und keine eigene Datei — so lädt Claude ihn
automatisch mit. Die Häppchen rotieren durch diese Themen.

| # | Thema | Typische Falle |
|---|-------|----------------|
| 1 | «…» | «…» |
| 2 | «…» | «…» |

## Kursübersicht (beim Anlegen bauen, vom User bestätigen)

Der Vertrag zwischen Tutor und Lerner darüber, was Kurs und Prüfung umfassen.
Beim Anlegen aus dem Material gebaut, vom User allein gelesen und bestätigt;
nach jeder Änderung der Themenkarte nachgezogen und neu bestätigt. Ohne
bestätigte Übersicht kein Häppchen.

Inhalt, in dieser Reihenfolge — kein Vorwissen voraussetzen, nichts abkürzen,
der User soll sie ohne Rückfrage lesen und verstehen können:

1. **Prüfung** — die Eckdaten von oben, dazu Aufgabenformat (Rechnen, Ankreuzen,
   Herleiten, mündlich), Gewichtung und was „bestanden" konkret heißt.
2. **Themen** — je Zeile der Themenkarte: die Idee in eigenen Worten, was die
   Prüfung dazu verlangt (Aufgabentyp, Tiefe), die Notation ausgeschrieben, die
   typische Falle, und welches Material das Thema abdeckt.
3. **Materialien** — jede Datei und jeder Ordner im Kurs-Ordner und jede Quelle
   (Folien, Übungsblätter, Altklausuren, Skript, Bücher): was es ist, wofür es
   taugt, wie der Loop es nutzt. Der Lerner soll jedes Material von der
   Übersicht aus erreichen können.
4. **Vereinbarung** — was drin ist, was ausdrücklich nicht, offene Fragen an den
   User. Der User bestätigt; erst dann gilt sie.

Ort: im Arbeitsmedium (Mechanik im Systemprompt), nicht als Datei — der Lerner
sieht nur das Medium. Buchung: genau eine Zeile `Übersicht: bestätigt YYYY-MM-DD`
in `todo.md` (bis dahin `Übersicht: fehlt`); das `lernen`-Startmenü liest genau
diese Zeile. Bei Neubestätigung das Datum ersetzen.

## Die drei Kern-Dateien

- **`CLAUDE.md`** (diese Datei) = *wie* + Eckdaten + Themenkarte. Zuerst lesen.
- **`todo.md`** = *wo stehen wir* — Re-Entry-Punkt: Klausurdatum, Stand, aktive Dateien.
  Enthält immer genau eine Zeile `Fortschritt: x/y Häppchen` — x = reviewte Häppchen,
  y = aktuelle Schätzung, wie viele Häppchen es insgesamt bis zur Klausurbereitschaft
  braucht. y ist eine lebende Schätzung (nach jedem Review neu bewerten, gern anhand
  der Themenkarte). Das `lernen`-Startmenü liest genau diese Zeile als Kurs-Fortschritt.
  Zweite Pflichtzeile: `Übersicht: bestätigt YYYY-MM-DD` (siehe §Kursübersicht).
- **`fehlermuster.md`** = *was ich falsch mache*, der personalisierte Kern. Nach JEDEM
  Review mitziehen: User-Zitat → warum falsch → was stattdessen. Dominante Muster oben halten.
- **`Personalisierte_Übungen/`** — die Häppchen (`haeppchen_NN.tex` → `.pdf`),
  eigenständige `.xopp`-Rechenblätter (nicht auf dem PDF!), `haeppchen_NN_reviewt.png`
  (annotierte Reviews).

## Situative Dateien — nur anlegen, wenn gebraucht

- **`notebooklm_lernpausen.md`** (nur wenn du Lernpausen-Videos willst) — EIN
  kompaktes NotebookLM-Doc: (A) Fehlermuster, (B) Themen im Schnelldurchlauf. Kein
  LaTeX, Unicode. Dynamisch, nicht kumulativ.
- **`Klausur_mitnehmen/`** (nur falls Hilfsmittel erlaubt) — Mitnehm-Blätter;
  Patch-SSoT `cheatsheet_personalisierung.md` (Fehlermuster → Blatt-Änderungen).

## Lern-Loop (der Kern)

**0. Arbeitsmedium** — kommt vom Launcher, nicht aus dieser Datei: der Umschalter
im `lernen`-Startmenü (`m`) bestimmt Xournal++ oder Tutor Board, und die Mechanik
des aktiven Mediums steht im Systemprompt der Session. **Nicht erfragen.** Der
User darf **mitten im Lernen wechseln** („lass uns aufs Board", „zurück zu
Xournal") — dann ab dem nächsten Häppchen im neuen Medium weiterarbeiten und ihn
erinnern, fürs nächste Mal den Schalter im Menü umzulegen.

**0b. Kursübersicht** — ohne bestätigte Übersicht (§Kursübersicht, Zeile in
`todo.md`) kein Häppchen: erst bauen bzw. nachziehen, bestätigen lassen, buchen.

**1. Lern-Set öffnen** — auf „lass uns lernen" das Arbeitsfenster des aktiven
Mediums öffnen (wie im Systemprompt beschrieben, ohne nachzufragen) plus
Referenz-/Mitnehm-Blätter und die zuletzt geänderte Übung.

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
- **Neues Häppchen sofort selbst öffnen**, nicht nachfragen — im aktiven Medium,
  wie im Systemprompt beschrieben.

**2b. Quiz-Häppchen — Wissensabfragen laufen IM Loop, nie extern.** Externe
Quiz-Generatoren (NotebookLM & Co.) sieht der Tutor nie: Antworten und bewiesenes
Wissen gehen für Fehlermuster + Fortschritt verloren. Wissensabfragen daher als
eigenes Häppchen hier im Loop:
- **Format zuerst prüfen — Choice-Framing ist nicht automatisch richtig.** Gut für
  Single/Multiple Choice: Erkennen und Unterscheiden (Definitionen, Notation, „welche
  Aussage gilt"), schnelle Konzept-Checks vor einem neuen Thema, Faktenwissen im
  mündlich-Modus. Falsch für alles mit Rechenweg/Herleitung — dort misst MC nur
  Ausschlussdenken; das bleibt ein Rechen-Häppchen. Im Zweifel offene Frage statt
  Optionen.
- **Umsetzung im aktiven Medium** (s. Systemprompt): AskUserQuestion-Runden im Chat
  bzw. ein eigener Quiz-Tab auf dem Board. Distraktoren gezielt aus `fehlermuster.md`
  bauen: der falsche Weg, den der User wirklich geht, ist die beste Falle.
- **Nachbereitung wie jedes Review:** falsche Antworten → `fehlermuster.md` (Zitat →
  warum falsch → was stattdessen); ein Quiz zählt als Häppchen in der
  `Fortschritt:`-Zeile.

**3. Review-Regel (verbindlich): Fehler SICHTBAR am Blatt des Users zeigen**, nicht nur
loggen — wie, steht in der Medium-Mechanik im Systemprompt (annotiertes PNG bzw.
Korrektur am Board-Tab). Zusätzlich im Chat explizit durchgehen (Zitat → warum falsch →
was stattdessen). Erst danach das nächste Häppchen. Jedes Review auch in
`fehlermuster.md` (+ ggf. situative Docs, falls angelegt), und die Zeile
`Fortschritt: x/y Häppchen` in `todo.md` mitziehen (x hochzählen, y neu schätzen).

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
