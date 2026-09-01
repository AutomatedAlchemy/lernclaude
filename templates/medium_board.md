# Arbeitsmedium-Mechanik: Tutor Board

## Ankommen (in dieser Reihenfolge, ohne nachzufragen)

1. `list_boards` — welcher Board gehört zu diesem Kurs? Ein Kurs = ein Board.
   Gibt es keinen, `create_board` (Name ist beim Anlegen Pflicht) und ihn nach
   dem Kurs benennen. **Nie auf dem Board eines anderen Kurses bauen** — Boards
   heißen nach ihrem Fach, danach gehen.
2. `select_board <id>` — ab da wirken alle Tools auf diesem Board, auch über
   Turns hinweg. (Frühere Sessions hielten `select_board` für nicht vorhanden
   und bauten blind über Edit-Links; das ist überholt.)
3. **Erst jetzt Firefox** — auf die konkrete Board-URL (das Feld `url` aus
   `list_boards` / `select_board`), nicht auf die Startseite. Die Startseite ist nur die Board-Liste; der User
   müsste selbst weiterklicken. Hat er schon eine Board-Seite offen, holt
   `open_board_for_user` ihn herüber, statt ein zweites Fenster aufzumachen.
4. `list_tabs` — der Ankunftsbericht. `submissions_you_have_not_read` heißt:
   der User hat abgegeben, während niemand zusah → **zuerst `read_board` auf
   diesen Tab und reviewen**, bevor irgendetwas Neues entsteht.
   Ein bereits ausgegebenes, aber ungerechnetes Häppchen wird **wieder
   vorgelegt, nicht ersetzt**.

## Struktur (verbindlich)

- **Tab 0 = „Übersicht"** — Themenkarte als Tabelle, je Thema eine
  Fortschrittsanzeige (🔴/🟠/🟡/🟢 oder `▓▓▓░░`, mit Legende) und die zugehörigen
  Häppchen namentlich („→ H03 …"). Dazu die offenen Fehlermuster in je einem
  Satz und die Zeile `Fortschritt: x/y Häppchen`. Re-Entry-Punkt des Boards und
  Spiegel von `todo.md`/`fehlermuster.md`, nicht deren Ersatz.
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

## Vorbereitungs-Übersicht (Modus „Vorbereitung")

Die Übersicht *vor* der Abfrage ist ein **eigener Tab** (`V01 <Thema>`, harte
Grenze 24 Zeichen) — nicht Tab 0. Tab 0 bleibt der Fortschrittsspiegel des
Kurses; V01 ist Lesestoff für diese eine Session.

- In Lesereihenfolge bauen, je Thema: Idee, ausgeschriebene Notation, Vorgehen
  in Schritten, ein durchgerechnetes Beispiel, die typische Falle. Formeln in
  `markdown`-Blöcke — dort rendert LaTeX.
- **Keine Eingabefelder** in diesem Tab: hier wird gelesen, nicht geantwortet.
  Ganz unten genau EIN `submit`-Knopf („Gelesen — frag mich ab").
- Übergabe wie bei jedem Häppchen: `create_tab(select: false)`, dann `select_tab`,
  dann mit `wait_url` (`kinds: ["click","submit"]`) als Hintergrund-Shell auf den
  Klick warten. Sagt der User es stattdessen im Chat, gilt das genauso.
- Der Tab bleibt liegen: die Häppchen der Session verweisen auf ihn („wie in
  V01"), und in Tab 0 bekommt er eine Zeile wie ein Häppchen.

## Häppchen übergeben und einsammeln

- Bauen mit `create_tab(select: false)`, in der Übersicht eintragen, **dann erst**
  `select_tab` — den User nie mitten im Rechnen wegreißen.
- Danach auf die Abgabe warten: `wait_url` holen und die zurückgegebene
  `curl`-Zeile als **Hintergrund-Shell-Kommando** laufen lassen. Das kostet keine
  Modellaufrufe und weckt die Session beim Klick.
  **Immer `kinds: ["click","submit"]`** abonnieren — ein reines `["submit"]`
  feuert nicht zuverlässig.

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

## „Noch eins?“ (Quickie)

Die Frage nach dem nächsten Quickie gehört **aufs Board, nicht ins Terminal** —
der User schaut ohnehin dorthin, und ein Klick ist billiger als eine getippte
Antwort.

- Ans Ende des Häppchen-Tabs, direkt unter die Korrektur, genau EINEN
  `submit`-Knopf („Noch eins?“). Kein Gegenstück zum Ablehnen — wer aufhören
  will, klickt einfach nicht oder sagt es im Chat; ein „für heute reicht's“-Knopf
  macht das Aufhören zur angebotenen Option und arbeitet gegen die Gewohnheit.
- Danach mit `wait_url` (`kinds: ["click","submit"]`) als Hintergrund-Shell auf
  den Klick warten. Kommt der Klick, folgt das nächste Häppchen als neuer Tab;
  bleibt er aus oder sagt der User ab, ein Satz Abschied.
- Antwortet er stattdessen im Chat, gilt das genauso — den Knopf dann nicht
  wiederholen.
