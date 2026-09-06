# Arbeitsmedium-Mechanik: Tutor Board

**Bedienung des Boards:** den Tool-Beschreibungen und den Server-Instructions des
Tutor-Board-MCP folgen. Diese Datei sagt nur, was der Lern-Loop auf dem Board haben
will. Bei Widerspruch gewinnt der Server; eine Eigenheit des Servers wird dort
beschrieben oder behoben, nicht hier umschifft.

## Ankommen (in dieser Reihenfolge, ohne nachzufragen)

1. Ein Kurs = ein Board, benannt nach dem Kurs. Gibt es keins, eines anlegen.
   **Nie auf dem Board eines anderen Kurses bauen.** Mehrere Lern-Sessions laufen
   oft parallel auf demselben Konto: vor jedem schreibenden Call prüfen, dass das
   gewählte Board noch das eigene ist.
2. Den User aufs Board holen: erst über das Board selbst einladen, und nur wenn
   niemand zuschaut, Firefox auf die konkrete Board-URL öffnen, nicht auf die
   Startseite.
3. Ankunftsbericht lesen: gibt es ungelesene Abgaben, **zuerst reviewen**, bevor
   irgendetwas Neues entsteht. Ein bereits ausgegebenes, aber ungerechnetes
   Häppchen wird **wieder vorgelegt, nicht ersetzt**.

## Struktur (verbindlich)

- **Tab 0 = „Übersicht"** — die Kursübersicht (§Kursübersicht der Kurs-CLAUDE.md)
  samt Fortschrittsspiegel, siehe den Abschnitt unten. Re-Entry-Punkt des Boards
  und Spiegel von `todo.md`/`fehlermuster.md`, nicht deren Ersatz. Fehlt der Tab,
  **jetzt** anlegen und an Position 0 holen.
- **Jeder weitere Tab = genau EIN Häppchen.** Titel kurz und referenzierbar
  (`H03 …`); der ganze Satz gehört in die Tab-Beschreibung.
- **Quiz-Häppchen** als eigener Tab (`Q01 <Thema>`), eine Frage pro Block,
  geantwortet wird im selben Tab.

## Blöcke bauen

- **Formeln in `markdown`-Blöcke**, dort rendert LaTeX.
- **Antwortformat vor Freitext-Mathe bevorzugen**: Zahlenfelder mit vorgedruckter
  Form, oder `radio`. Exponenten zu tippen frisst mehr Zeit als das Rechnen, und
  ein Radio hat kein leeres Feld, in dem man sich verstecken kann.
- **Wunde Stellen in Einzelfelder zerlegen** (Vorzeichen, Vorfaktor, Exponent
  getrennt) und in jedem Schritt den Wert neu hinschreiben, statt auf die Zeile
  darüber zu verweisen — sonst wird die Zahl von oben durchgereicht.
- **Jede Aufgabe endet mit einem `submit`-Knopf mit Antwortschlüssel**, sobald die
  Antworten objektiv prüfbar sind. Der Schlüssel ist Teil der Aufgabe: vor dem
  `select_tab` jeden Eintrag selbst nachrechnen und die Zuordnung Feld → Wert
  prüfen. Ein falscher Schlüssel markiert eine richtige Abgabe als falsch und
  verfälscht das Fehlermuster. Gleichwertige Schreibweisen als Liste angeben.

## Kursübersicht (Tab 0)

Tab 0 ist der eine Übersichts-Tab des Kurses — der Vertrag aus §Kursübersicht der
Kurs-CLAUDE.md und der Fortschrittsspiegel in einem. Reihenfolge der Blöcke:

1. **Prüfung** — Eckdaten, Format, Bestehen.
2. **Themenkarte mit Fortschritt** — als Tabelle, je Thema eine Anzeige
   (🔴/🟠/🟡/🟢 oder `▓▓▓░░`, mit Legende) und die zugehörigen Häppchen namentlich
   („→ H03 …"); darunter die offenen Fehlermuster in je einem Satz und die Zeile
   `Fortschritt: x/y Häppchen`. Dieser Block wird nach jedem Review per
   `update_block` nachgezogen.
3. **Themen erklärt** — je Thema Idee, Prüfungsanforderung, Notation, Falle,
   Material, höchstens 6 Sätze. Formeln in `markdown`-Blöcke.
4. **Materialien** — jede Datei mit Pfad und einem Halbsatz beschrieben. Fotos
   als Bild-Block, einzelne PDF-Seiten nur situativ im Häppchen, das sie braucht
   (als PNG gerendert), nie ganze Skripte.
5. **Vereinbarung** — drin / nicht drin / offene Fragen. Darunter genau EIN
   `submit`-Knopf („Gelesen & einverstanden"); sonst **keine Eingabefelder** im Tab.

Bestätigung: auf den Klick warten (§„Auf den User warten"); sagt der User es
im Chat, gilt das genauso. Danach in `todo.md`
`Übersicht: bestätigt YYYY-MM-DD` eintragen und erst dann das erste Häppchen.

**Tab 0 wird immer an Ort und Stelle geändert**, auch beim Umbau: Blöcke mit
`update_block` ersetzen, mit `append_blocks` ergänzen, mit `remove_block`
entfernen. Kein `show_board`/`clear_board` für eine Änderung an einem Tab — das
setzt das ganze Board zurück. `clear_board` nur für ein leeres oder für ein
falsch aufgebautes Board.

Nachziehen bei einem Board, dessen Tab 0 bisher nur der Fortschrittsspiegel war:
die fehlenden Blöcke ergänzen und in die Reihenfolge oben bringen.

## Häppchen übergeben und einsammeln

- Bauen mit `create_tab(select: false)`, in der Übersicht eintragen, **dann erst**
  `select_tab` — den User nie mitten im Rechnen wegreißen.
- Danach auf die Abgabe warten, siehe §„Auf den User warten".

## Auf den User warten

Gilt für jeden Wait: Übersichts-Bestätigung, Häppchen-Abgabe, „Noch eins?".

- Warten, wie der MCP es beschreibt (bevorzugt der Weg, der keine Modellaufrufe
  kostet). Nach dem Aufwachen sagt das Ereignis, ob der User geklickt oder
  geschrieben hat; entsprechend Board oder Chat lesen.
- **Wird der Wait beendet, ohne gefeuert zu haben**, ist das normal:
  langlaufende Hintergrund-Shells werden vom Harness abgeräumt. Dann in dieser
  Reihenfolge: einmal das Board lesen — oft liegt die Abgabe längst vor; sonst den
  Wait höchstens **zweimal** neu starten; danach dem User in einem Satz sagen,
  dass er sich nach dem Abgeben kurz melden soll. Keine dritte Runde.
- Stirbt der Hintergrund-Wait wiederholt, den Wait im Modellkontext nehmen, den
  der MCP als Rückfallebene anbietet — nicht als Standard.

## Review

- Abgaben samt Score vom Board lesen. Trägt der Tab eine Zeichnung, sie holen —
  **nie über eine ungesehene Zeichnung raten**.
- Die Korrektur als Block **am selben Tab** zeigen, nicht nur im Chat: Zitat →
  warum falsch → was stattdessen, **je Fehler höchstens fünf Sätze**. Ist der
  Score falsch, weil der Schlüssel falsch war, das auf dem Board richtigstellen
  und dem User sagen.
- Danach die Übersicht per `update_block` nachziehen (Themen-Level,
  Häppchen-Status, `Fortschritt:`-Zeile). Fertig reviewte Tabs bei Bedarf
  archivieren; ihr Eintrag in der Übersicht bleibt.

## Animation bei wiederkehrendem Fehlermuster

Steht ein Fehlermuster zum zweiten oder dritten Mal in `fehlermuster.md` **und**
ist es geometrisch oder dynamisch (Vektordrehung, Epsilon-Delta, Konvergenz,
Transformationen), darf ein kurzer Clip an die Korrektur — dafür gibt es die
`manim-kit`-Skill. Ein einmaliger Vorzeichenfehler bekommt einen Satz, keinen Film.

- **Nie in der Übersicht und nie in einer Aufgabe.** Ein Häppchen sind fünf
  Minuten; Rendern kostet mehrere davon, und der User wartet zu.
- **Asynchron bauen**: Render als Hintergrund-Shell starten, währenddessen das
  nächste Häppchen bauen, den Clip als Video-Block an den Tab mit der Korrektur
  nachreichen. 20 Sekunden reichen, eine Idee pro Szene.
- **Fail into silence**: `manim-kit doctor` einmal pro Host; fehlt LaTeX oder
  ffmpeg oder scheitert der Render, bleibt es beim Textblock. Kein Hinweis an
  den User, keine zweite Runde.

## „Noch eins?“ (Quickie)

Die Frage nach dem nächsten Quickie gehört **aufs Board, nicht ins Terminal** —
der User schaut ohnehin dorthin, und ein Klick ist billiger als eine getippte
Antwort.

- Ans Ende des Häppchen-Tabs, direkt unter die Korrektur, genau EINEN
  `submit`-Knopf („Noch eins?“). Kein Gegenstück zum Ablehnen — wer aufhören
  will, klickt einfach nicht oder sagt es im Chat; ein „für heute reicht's“-Knopf
  macht das Aufhören zur angebotenen Option und arbeitet gegen die Gewohnheit.
- Danach auf den Klick warten (§„Auf den User warten"). Kommt der Klick, folgt
  das nächste Häppchen als neuer Tab; bleibt er aus oder sagt der User ab, ein
  Satz Abschied.
- Antwortet er stattdessen im Chat, gilt das genauso — den Knopf dann nicht
  wiederholen.
