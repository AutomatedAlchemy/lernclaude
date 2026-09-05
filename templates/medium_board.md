# Arbeitsmedium-Mechanik: Tutor Board

## Ankommen (in dieser Reihenfolge, ohne nachzufragen)

1. `list_boards` — welcher Board gehört zu diesem Kurs? Ein Kurs = ein Board.
   Gibt es keinen, `create_board` (Name ist beim Anlegen Pflicht) und ihn nach
   dem Kurs benennen. **Nie auf dem Board eines anderen Kurses bauen** — Boards
   heißen nach ihrem Fach, danach gehen.
2. `select_board <id>` — ab da wirken alle Tools auf diesem Board. Die Auswahl
   gilt allerdings **kontoweit und nicht pro Session**: eine parallel laufende
   Lern-Session für einen anderen Kurs biegt sie um, und der nächste Schreibzugriff
   landet auf dem falschen Board. Deshalb `select_board` **vor jedem schreibenden
   Call** wiederholen (`create_tab`, `append_blocks`, `update_block`, `show_board`,
   `clear_board`), solange die Auswahl kontoweit gilt und mehrere Lern-Sessions
   parallel laufen. (Frühere Sessions hielten `select_board` für nicht vorhanden
   und bauten blind über Edit-Links; das ist überholt.)
3. **`open_board_for_user`, dann erst Firefox** — immer zuerst
   `open_board_for_user` mit einem kurzen `note`, was dort wartet. Der Call
   erreicht nur gerade offene Board-Seiten und meldet, wie viele er erreicht hat.
   Meldet er ≥ 1, hat der User den Knopf und es braucht kein zweites Fenster.
   Meldet er 0, schaut niemand zu → **jetzt Firefox** auf die konkrete Board-URL
   (das Feld `url` aus `list_boards` / `select_board`), nicht auf die Startseite.
   Die Startseite ist nur die Board-Liste; der User müsste selbst weiterklicken.
4. `list_tabs` — der Ankunftsbericht. `submissions_you_have_not_read` heißt:
   der User hat abgegeben, während niemand zusah → **zuerst `read_board` auf
   diesen Tab und reviewen**, bevor irgendetwas Neues entsteht.
   Ein bereits ausgegebenes, aber ungerechnetes Häppchen wird **wieder
   vorgelegt, nicht ersetzt**.

## Struktur (verbindlich)

- **Tab 0 = „Übersicht"** — die Kursübersicht (§Kursübersicht der Kurs-CLAUDE.md)
  samt Fortschrittsspiegel, siehe den Abschnitt unten. Re-Entry-Punkt des Boards
  und Spiegel von `todo.md`/`fehlermuster.md`, nicht deren Ersatz.
  Fehlt der Tab, **jetzt** anlegen und mit `reorder_tab(position: 0)` nach vorn
  holen — ein neuer Tab landet immer am Ende.
- **Jeder weitere Tab = genau EIN Häppchen.** Titel kurz und referenzierbar
  (`H03 …`, harte Grenze 24 Zeichen); der ganze Satz gehört in die
  Tab-Beschreibung, die der User beim Hovern sieht.
- **Quiz-Häppchen** als eigener Tab (`Q01 <Thema>`), eine Frage pro Block,
  geantwortet wird im selben Tab.

## Blöcke bauen

- **Formeln gehören in `markdown`-Blöcke** — dort rendert LaTeX (`$…$`, `$$…$$`).
  **Widget-Labels case-neutral formulieren** („ankreuzen", „vorfaktor",
  „exponent"): das Board rendert Labels per CSS in Großbuchstaben, aus
  „f(x) = eˣ" wird „F(X) = Eˣ".
- **Antwortformat vor Freitext-Mathe bevorzugen**: Zahlenfelder mit vorgedruckter
  Form, oder `radio`. Exponenten zu tippen frisst mehr Zeit als das Rechnen, und
  ein Radio hat kein leeres Feld, in dem man sich verstecken kann.
- **Wunde Stellen in Einzelfelder zerlegen** (Vorzeichen, Vorfaktor, Exponent
  getrennt) und in jedem Schritt den Wert neu hinschreiben, statt auf die Zeile
  darüber zu verweisen — sonst wird die Zahl von oben durchgereicht.
- **Der Antwortschlüssel am `submit`-Button ist Teil der Aufgabe, nicht Beiwerk.**
  Vor dem `select_tab` jeden Eintrag selbst nachrechnen und die Zuordnung
  Feld → Wert prüfen. Ein falscher Schlüssel markiert eine richtige Abgabe als
  falsch und verfälscht das Fehlermuster. Für gleichwertige Schreibweisen ein
  Array angeben (`{"a1": ["0.5", "1/2"]}`); der Vergleich faltet Potenz-Notation,
  aber **keine Algebra**.

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
   Material. Formeln in `markdown`-Blöcke.
4. **Materialien** — jede Datei mit Pfad und einem Halbsatz beschrieben. Das
   Board nimmt keine PDFs an (`request_upload` nur Bilder und Video); Fotos
   dürfen als `image`-Block rein, einzelne PDF-Seiten nur situativ im Häppchen,
   das sie braucht (als PNG gerendert), nie ganze Skripte.
5. **Vereinbarung** — drin / nicht drin / offene Fragen. Darunter genau EIN
   `submit`-Knopf („Gelesen & einverstanden"); sonst **keine Eingabefelder** im Tab.

Bestätigung: auf den Klick warten (§„Auf einen Klick warten"); sagt der User es
im Chat, gilt das genauso. Danach in `todo.md`
`Übersicht: bestätigt YYYY-MM-DD` eintragen und erst dann das erste Häppchen.

**Tab 0 wird immer an Ort und Stelle geändert**, auch beim Umbau: Blöcke mit
`update_block` ersetzen, mit `append_blocks` ergänzen, mit `remove_block`
entfernen, den Tab mit `reorder_tab(position: 0)` nach vorn holen. Kein
`show_board`/`clear_board` für eine Änderung an einem Tab — das setzt das ganze
Board zurück und räumt die laufenden Häppchen-Tabs ins Regal. `clear_board` nur
für ein leeres oder für ein falsch aufgebautes Board.

Nachziehen bei einem Board, dessen Tab 0 bisher nur der Fortschrittsspiegel war:
die fehlenden Blöcke ergänzen und in die Reihenfolge oben bringen.

## Häppchen übergeben und einsammeln

- Bauen mit `create_tab(select: false)`, in der Übersicht eintragen, **dann erst**
  `select_tab` — den User nie mitten im Rechnen wegreißen.
- Danach auf die Abgabe warten, siehe §„Auf einen Klick warten".

## Auf einen Klick warten (`wait_url`)

Gilt für jeden Wait: Übersichts-Bestätigung, Häppchen-Abgabe, „Noch eins?".

- `wait_url` holen und die zurückgegebene `curl`-Zeile als
  **Hintergrund-Shell-Kommando** laufen lassen. Das kostet keine Modellaufrufe
  und weckt die Session beim Klick. **Immer `kinds: ["click","submit"]`**
  abonnieren — ein reines `["submit"]` feuert nicht zuverlässig.
- **Wird der Wait beendet, ohne gefeuert zu haben**, ist das normal:
  langlaufende Hintergrund-Shells werden vom Harness abgeräumt. Dann in dieser
  Reihenfolge: einmal `read_board` — oft liegt die Abgabe längst vor; sonst den
  Wait höchstens **zweimal** neu starten; danach dem User in einem Satz sagen,
  dass er sich nach dem Abgeben kurz melden soll. Keine dritte Runde.
- **Rückfallebene ohne Hintergrundprozess:** `await_event` wartet im
  Modellkontext und kann deshalb nicht abgeräumt werden, kostet aber mehr. Nur
  nehmen, wenn der Wait wiederholt stirbt — nicht als Standard.

## Review

- `read_board` liefert die eingetragenen Werte und die Submissions samt
  server-berechnetem Score. Trägt der Tab eine Zeichnung (`drawings > 0`), sie
  mit `get_canvas` holen — **nie über eine ungesehene Zeichnung raten**.
- Die Korrektur als Block **am selben Tab** zeigen, nicht nur im Chat: Zitat →
  warum falsch → was stattdessen. Ist der Score falsch, weil der Schlüssel
  falsch war, das auf dem Board richtigstellen und dem User sagen.
- Danach die Übersicht per `update_block` nachziehen (Themen-Level,
  Häppchen-Status, `Fortschritt:`-Zeile). Fertig reviewte Tabs bei Bedarf mit
  `archive_tab` aufräumen; ihr Eintrag in der Übersicht bleibt.

## Animation bei wiederkehrendem Fehlermuster

Steht ein Fehlermuster zum zweiten oder dritten Mal in `fehlermuster.md` **und**
ist es geometrisch oder dynamisch (Vektordrehung, Epsilon-Delta, Konvergenz,
Transformationen), darf ein kurzer Clip an die Korrektur — dafür gibt es die
`manim-kit`-Skill. Ein einmaliger Vorzeichenfehler bekommt einen Satz, keinen Film.

- **Nie in der Übersicht und nie in einer Aufgabe.** Ein Häppchen sind fünf
  Minuten; Rendern kostet mehrere davon, und der User wartet zu.
- **Asynchron bauen**: Render als Hintergrund-Shell starten, währenddessen das
  nächste Häppchen bauen, den Clip per `request_upload` als Video-Block an den
  Tab mit der Korrektur nachreichen. 20 Sekunden reichen, eine Idee pro Szene.
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
- Danach auf den Klick warten (§„Auf einen Klick warten"). Kommt der Klick, folgt
  das nächste Häppchen als neuer Tab; bleibt er aus oder sagt der User ab, ein
  Satz Abschied.
- Antwortet er stattdessen im Chat, gilt das genauso — den Knopf dann nicht
  wiederholen.
