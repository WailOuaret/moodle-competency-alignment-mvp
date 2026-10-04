# Moodle plugin: browser verification checklist

Checkpoint E needs a person to use the plugin in a browser. Scripts can show that the
code runs. They cannot show that the pages look right, because Moodle's command-line
renderer draws no theme at all: no header, no navigation, no styling.

**Result: PENDING.** It stays pending until the person who ran this checklist reports back.

**Ground rules**

- Everything you save is development or demo data. It must never be mixed with teacher-study
  records. Step 6 empties the plugin's tables when you are done.
- The suggestions come from the service's **mock backend**. A yellow notice on the review page
  says so. That is expected: they are placeholders, not model output.
- Writing to Moodle's competency links is not implemented. Nothing in this checklist should
  create or change one, and the pages should say so.
- Nothing here touches the frozen research data.

## 1. Start the environment

Use three terminals. Stop terminals 2 and 3 with **Ctrl+C** when you are done.

**Terminal 1: Moodle** (skip if it is already running). Open http://localhost:8000 afterwards.

```bash
cd ~/moodle-dev/moodle-docker && source ../moodle-env.sh
bin/moodle-docker-compose start
bin/moodle-docker-wait-for-db
```

**Terminal 2: the mock alignment service** (port 8001)

```bash
cd ~/projects/moodle_competency_mvp && source .venv/bin/activate
ALIGNMENT_BACKEND=mock uvicorn service.main:app --host 0.0.0.0 --port 8001
```

**Terminal 3: Moodle cron.** An analysis only starts when cron runs, and nothing runs it by
itself in this sandbox. Leave this loop running:

```bash
cd ~/moodle-dev/moodle-docker && source ../moodle-env.sh
while true; do
  bin/moodle-docker-compose exec -T -u www-data webserver php /var/www/html/admin/cli/cron.php
  sleep 2
done
```

- The script is `/var/www/html/admin/cli/cron.php` inside the container. Moodle 5.2 has no
  `public/admin/cli/cron.php`; `public/admin/cron.php` is the web endpoint, not this script.
- **Each run stays alive for about three minutes** (Moodle's default "keep alive" window, which
  you can change under Site administration, Server, Tasks, Task processing) and keeps checking for
  new tasks. A new analysis was picked up and finished 3 seconds after it was queued. The loop
  starts the next run as soon as one ends.
- **The very first run is slow.** It runs about 90 overdue scheduled tasks, several of which reach
  out over the internet. It took 4 minutes 30 seconds here, and two of those tasks (the update check
  and the Moodle Apps portal) report a failure in this sandbox. The failures do not involve the
  plugin. That first pass was already done on 4 October 2026, so a run you start now is quick, but
  after a rebuild of the sandbox give the first run a few minutes before you press any button.
- To stop, press **Ctrl+C**. A run that is already in progress keeps living inside the container
  for up to three minutes, so also run this to end it at once:
  `bin/moodle-docker-compose exec -T -u www-data webserver php /var/www/html/admin/cli/cron.php --stop`.
- A lighter alternative that only runs the plugin's queued analyses, and none of the scheduled
  tasks: use `php /var/www/html/admin/cli/adhoc_task.php --execute` in the loop instead, with
  `sleep 5` (that command does not wait for new tasks).

**Accounts.** The sandbox has `teacher_mvp` (teacher of "MVP-SW"), `student_mvp` and `admin`.
Use two browser profiles, or a private window, so the teacher and the student can be logged in
side by side. If you do not remember a password, set a new one. This changes that account's
password in the sandbox:

```bash
cd ~/moodle-dev/moodle-docker && source ../moodle-env.sh
bin/moodle-docker-compose exec -u www-data webserver php /var/www/html/admin/cli/reset_password.php \
  --username=teacher_mvp --password='choose-a-password'
```

Add `--ignore-password-policy` if Moodle refuses a simple password.

**Starting state.** The plugin's tables are empty, so every Page shows "Not analysed". As
administrator, `http://localhost:8000/local/compalign/index.php` should say **Connected** once the
mock service is running.

## 2. The checklist

Take a screenshot where there is a camera. Mark each item PASS or FAIL.

| # | Where and what to do | PASS if |
|---|---|---|
| 1 | Log in as `teacher_mvp`. Open the course: http://localhost:8000/course/view.php?id=2 📷 | The course page looks normal, with no error and no broken layout. |
| 2 | In the course's top navigation open the **More** menu. On a wide window it may be a visible tab instead. | **Competency Alignment** is listed, with an icon, after "LTI External tools". Clicking it opens the plugin dashboard. |
| 3 | The dashboard, `/local/compalign/index.php?courseid=2` 📷 | Heading "Competency Alignment"; the sentence "Ask the assistant to suggest competencies for a resource ... nothing is written to Moodle competency links."; a table with the columns Resource, Type, Analysis, Current Moodle competency links, Action; one row per resource (Announcements, four Pages, the Quiz). |
| 4 | Look at the row "Software Development Lifecycle and Deployment". | Analysis says **Not analysed**, its current Moodle competency links are listed, and the action is a **Suggest competencies** button. The forum and the quiz say "Resource type not supported in this prototype." and have no button. |
| 5 | Press **Suggest competencies** in the "Software Development Lifecycle and Deployment" row. 📷 | You land on "Competency suggestions: Software Development Lifecycle and Deployment" with the green message "The analysis was queued." |
| 6 | Right after item 5, watch the page without reloading it (terminal 3 must be running). 📷 | A "Queued" notice reads "The analysis starts when Moodle next runs its background tasks (cron). This page refreshes by itself." Within a few seconds (the page checks every 5 seconds) it changes to the result by itself. A brief "Analysing" state may flash past. |
| 7 | The completed analysis 📷 | A yellow notice "This analysis used the test backend. Its suggestions are placeholders and are not model output."; a blue notice "Official write-back is off. Saving a decision does not create or change any Moodle competency link."; at least one card; a secondary **Reanalyse** button with an explanation. |
| 8 | Look at the layout of one card. | In this order: "Suggested competency" with code and name, the description, "Exact evidence from the resource", the collapsed "Technical details", "Not reviewed yet", then the decision form. Everything is readable. |
| 9 | Back on the dashboard press **Suggest competencies** in the row **Computer Architectures, Networks and Cybersecurity**, then wait for the result. 📷 (whole page) | Three cards: GI_C2 (Concevoir et mettre en œuvre des architectures informatiques), GI_C2_1 (Architectures logicielles et matérielles ...) and GI_C2_2 (Architectures communicantes ...). |
| 10 | Read the "Hierarchy note" on each of the three cards. | GI_C2 says a more specific child competency (GI_C2_1 ..., GI_C2_2 ...) is also suggested. Each child says its parent competency (GI_C2 ...) is also suggested. A teacher who has never seen this would understand it is information, not an error, and it names the related competency. |
| 11 | Open the Page itself in another tab and compare it with the evidence on each card. | Each quotation appears in the Page word for word. |
| 12 | Look at every plugin page, including expanded technical details. | No raw JSON (`{`, `[{`, `"key": ...`), no stack trace, no code. |
| 13 | Look for anything that looks like an answer key. | Nowhere do you see "gold", "reference", "expected", "ground truth" or "annotation", or a label that reveals what the right answer is. The only competency codes are the suggestions and the official links, and they are labelled. |
| 14 | On a card, expand and collapse **Technical details**. | It is collapsed at first and visually secondary. Expanded it shows Search rank (BM25), Model confidence (not a probability), Supporting passages and Passages. |
| 15 | On a card choose **Accept**, evidence usefulness **2**, comment "Accept test", then **Save decision**. 📷 | A green "Your decision was saved. Nothing was written to Moodle competency links."; the card shows "Your decision: Accepted" and "Revision 1, saved ..."; the form shows your choices. |
| 16 | On another card choose **Reject**, usefulness **0**, then save. | The card shows "Rejected" with no replacement competency. Usefulness **0 is selected** (zero is a rating, not "empty"). |
| 17 | On the third card choose **Modify**. 📷 | The **Replacement competency** dropdown appears only now. It lists the other 12 competencies as "code - name" and not the suggested one. Choose GI_C2_3 and save: "Modified to GI_C2_3 ...". Then choose Modify, leave the dropdown empty and save: the error "Choose the competency that replaces the suggestion." appears and nothing is saved. |
| 18 | Open a card that has not been reviewed yet, or use a fresh private window. | None of Accept, Reject, Modify and none of 0, 1, 2 is pre-selected. |
| 19 | Save a comment such as `<b>bold</b> & "quotes"`, then try one longer than 1000 characters. | The first is shown as plain text, with no bold and nothing executed. The second gives "The comment is longer than 1000 characters." and nothing is saved. |
| 20 | Press **Save decision** with no decision chosen. | A clear red message, "Choose accept, reject or modify." Together with items 15 to 19, every success and error message is plain English with no text like `[[...]]`. |
| 21 | In a private window log in as `student_mvp`. Look at the course, then open `/local/compalign/index.php?courseid=2` and `/local/compalign/review.php?cmid=6`. 📷 | No Competency Alignment entry in the course navigation. Both addresses show Moodle's "Sorry, but you do not currently have permissions to do that (View the Competency Alignment Assistant)" and no suggestions or forms. |
| 22 | As `admin` open Site administration, Plugins, Local plugins, Competency Alignment Assistant (`/admin/settings.php?section=local_compalign`). 📷 | URL `http://host.docker.internal:8001`; the token field is empty or masked and never shows the token; timeout 120; framework "UTC GI Competency Framework - MVP (UTC_GI_MVP_2026)"; Top-K "Fixed at 5 ..."; Maximum suggestions 3; "Enable official write-back" unticked and described as Reserved with no effect; "Require human review" described as always on; a connection-status link. `/local/compalign/index.php` says **Connected**. |
| 23 | Narrow the window, or open the browser's device toolbar, to about 1024, 768 and 375 pixels wide. Check the dashboard and the three-card review page. 📷 (375 px) | The page never scrolls sideways as a whole. The table scrolls or wraps inside its own area, the cards stack, and buttons, radios and the dropdown remain usable. |
| 24 | Throughout items 1 to 23. | No overlapping text, clipped buttons, unstyled or broken template, raw language keys such as `[[something]]` or `local_compalign/...`, PHP warnings or raw exception text. If you see one, note the page and take a screenshot. |

### Optional extras (not needed for Checkpoint E)

- **X1 Revision.** Change an earlier decision and save. The card says "Revision 2".
- **X2 Edited Page.** Add a word to the Page's text and reload its review page. The warning "This
  page was edited after the analysis ..." appears. Undo your edit afterwards.
- **X3 Service down.** Stop terminal 2, press **Reanalyse**, and wait for cron. The page says
  "The analysis did not complete" and "The alignment service could not be reached." Restart the
  service and **Reanalyse** works again.
- **X5 Empty state.** Open `http://localhost:8000/local/compalign/review.php?cmid=4` for a Page that has not
  been analysed. It says "No analysis has been requested for this resource yet." and offers
  **Suggest competencies**.
- **X4 Double click.** Press **Reanalyse** twice quickly. Only one analysis runs ("An analysis is
  already in progress for this resource.").

## 3. Report back

Send the table back with PASS or FAIL for each number, and a screenshot for every FAIL, for
example `17 FAIL: the dropdown shows the proposed competency (screenshot)`. Anything that looked
odd but did not fail an item is worth a line too.

## 4. When you have finished

1. Press **Ctrl+C** in terminals 2 and 3.
2. Empty the plugin's development records. Sandbox only: this deletes every analysis and every
   review, and nothing else.

   ```bash
   docker exec moodle_comp_mvp-db-1 psql -U moodle -d moodle -c \
     "TRUNCATE m_local_compalign_review, m_local_compalign_evidence, m_local_compalign_sugg, m_local_compalign_analysis RESTART IDENTITY;"
   ```

3. Leave the sandbox's HTTP-security exception in place while the plugin is still being developed.
   `GUIDE.md` section 21 has the restore procedure for when local testing ends.
