# Boox Routines Handoff (as of Sun 9/13/26, morning)

One notebook, one Brief, one Drive folder. Ink is the input. The Brief is the output. The Brief also lands on today's Daily Log page.

## Files
| File | Where | Role |
|---|---|---|
| Journal_2026-Sep-Oct.pdf (114 p) | tablet + Boox/Journal | Everything handwritten. README p2, Key p3, Index p4, Daily Log Sept p35 (carried over) then one page per day from p36, Oct p75, sheets after. |
| Brief.pdf (2 p) | Boox/Brief, download daily | Work then Personal. Regenerated each run. Subtitle says which Daily Log page today's block is on. Write only in Intake zones. |
| templates.pdf + templates.json | Boox/state | Reusable sheets for #add / penciled titles. |
| build_brief.py, daily_sync.py, journal_edit.py, journal_typeset.py, build_custom.py | Boox/state | The run's tools. Don't open. |
| ripple_state.json, <journal>_manifest.json, audit.log | Boox/state | State. Don't open. `daily_pages` maps each date to its Daily Log page. |
| Boox/Archive/YYYY-MM/DD.md | Drive | Transcript of every page the run read. |
| Boox/Answers/ | Drive | Long >C answers. |
| Boox/_purge (review then delete)/ | Drive | Retired files. Nothing is ever deleted; you empty this. |
| COWORK_BRIEF_TASK.md | Boox/state | The scheduled-task prompt (v7, daily page sync). |

## Daily
1. Morning: Drive app > Boox > Brief > Brief.pdf > Download > open in NeoReader.
2. Open the Journal to the Daily Log page named on the Brief. The date, today's events and due items are already typed at the top; rapid-log under them with the Key symbols. One page per day.
3. Tick a typed checkbox = done; X over a typed circle = attended. The run reads both.
4. Intake zone on the Brief for meeting notes and weather. Tags there count.
5. Semi Hard: tag the day `#75 M D R S F L`.

## Weekly (Sunday, 10 min)
1. NeoReader share > upload the Journal to Boox/Journal (overwrite). This is what lets the run see your ink, and what lets the daily block land in the Journal (the run only stamps a Journal that is newer than its last stamp, so your ink is never clobbered).
2. After the next run, re-download the Journal if the reply said it changed.
3. Migration pass in the log: `>` forward, `X` done, scribble out the dead.
4. Empty `_purge` if you feel like it. Native Boox backup to Drive once a month.

## Runs (Cowork scheduled task, weekdays 06:00 and 12:00; "Run now" for a force)
Each run: read state, read changed ink, act on commands, type ink on non-log pages, pull calendars, mail, Asana, stamp today's Daily Log page (06:00 run, only if the Journal was uploaded since the last stamp), build the Brief, archive the old one, transcript everything, one-line reply. Staging until 9/26: `>A` shows as "proposed" on the Brief and does not create Asana tasks. After that, `>A` creates one Asana task in My Tasks (the only Asana write, ever).

## Ink grammar
- Symbols: `•` task, `X` done, `>` migrated, `<` scheduled, `○` event, `–` note, `*` priority, `!` critical, `?` question. The last two are signifiers only.
- End of line: `>A` Asana task. `>C` ask Claude (answer comes back as a typed sheet).
- Tags: `@ MM/DD HHMM text` calendar event. `#fu Name` / `#wait Name`, close with `#done fu Name`. `#cit 2h`, `#study Topic 1h`, `#dog buried 4m B`, `#gear $180 QBP`, `#spend $40 gas`. `#w` / `#p` forces the sheet. `#add meeting`, `#remove p88`.
- On sheets: DELETE or REMOVE = page removed. MORE = fresh copy appended. PRIVATE at top = never read. Scribble = delete.
- Index: pencil a title anywhere = new page, tap-link put over your ink. Names that match a template get that sheet; anything else gets a dot page with your title.
- Template Draft page: draw a sheet (TITLE:, lines, boxes, squares, "x8"); the run turns it into a real template and appends the clean page.

## Ink policy
Handwriting stays only on Daily Log pages. Everywhere else the run types it in place and removes the ink; the original wording is in the Archive transcript. The typed daily block is an overlay; nothing under it is ever redrawn.

## Sheets available (#add key)
fallcal, weekly, meeting, aar, aerial, cit, study, dog, reading, gear, field, ideas, wait, wedding, creds, dotgrid, checklist, candor, oneonone, wlodkowski, draft, readme, studyplan
(templates.pdf currently has pages for the first 17; candor through studyplan need their pages built with build_custom.py before #add works for them.)

## Month rollover
Nov 1 run generates Journal_2026-Nov-Dec.pdf, page 1 carried over (`>`) and scheduled (`<`) items typed in. Old file moves to Boox/Archive. Same on Jan 1. `daily_pages` resets.

## Guardrails the run never crosses
Send or reply to mail. Edit or complete Asana tasks. Delete a file. Read a PRIVATE page. Act on anything that isn't your handwriting. Redraw a Daily Log page (the daily block is typed on top, once, and only into a freshly uploaded Journal). A `PAUSE` file in Boox/state stops all runs.

## Still on you (once)
1. Put the stamped Journal (sent to you in chat on 9/13, block on Daily Log p37; p36 is left for your 9/12 log) into Boox/Journal, overwriting, and onto the tablet. If you inked the tablet since the 9/12 upload, upload that first instead and the next run will stamp p37 itself.
2. Cowork: new scheduled task, weekdays 06:00 and 12:00, paste the prompt from Boox/state/COWORK_BRIEF_TASK.md (v7). Run it once by hand.
3. Finish connecting Microsoft 365 in claude.ai (shows connect_incomplete); until then the Brief says Outlook was skipped.
4. Optional later: FolderSync (Journal two-way, Brief download-only), then set `journal_synced: true` in ripple_state.json so the daily block lands every morning without the Sunday upload.

## Known limits
Printed page numbers on the Index drift after a removal (taps stay correct). Handwriting OCR is reliable for block caps and tags, lossy for prose. The Brief is only as fresh as your last upload for the "from notes" section; calendar and mail are always current at run time. One Daily Log page per day means September's 39 pages cover the month with room to spare; heavy days keep going on the next page and the run skips it.

## Known bug: templates.json / templates.pdf out of sync
As of 9/19, `templates.json` lists 24 sheets (`fallcal` page 0 through `comms` page 23), but `templates.pdf` has only 17 pages (indices 0-16). The 7 entries from `candor` (17) through `comms` (23) — `candor`, `oneonone`, `wlodkowski`, `draft`, `readme`, `studyplan`, `comms` — point at pages that don't exist; `journal_edit.py <journal> add <key>` for any of them will raise an IndexError. `draft` is in this dangling range too, which means the hand-drawn "Template Draft" page mechanism described above can't currently be invoked via `#add draft` either. `comms` isn't even in the "Sheets available" list above — its entry has no documented trigger. Fix: build the missing pages with `build_custom.py <spec> --template` (one call per key, in key order so the appended pages land at the indices templates.json already expects), then re-upload templates.pdf.
