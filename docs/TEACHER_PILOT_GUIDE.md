# Competency Alignment Assistant: guide for pilot teachers

**Status: DRAFT, written before any teacher has used the system. The pilot site is not open yet.**
Every step below describes how the plugin behaves in the development sandbox. It has not yet been
walked through by a teacher on the pilot site. Wording may change after the first walkthrough.

You have been invited to try a small tool and tell us honestly whether it helps. You are testing the
tool. You are not being tested, and there are no wrong answers.

## What the tool does

You have a learning **Page** in a Moodle course. Your institution describes the skills students
should gain as **competencies**: here, 13 competencies of the UTC GI framework (for example GI_C2,
"Concevoir et mettre en œuvre des architectures informatiques", and the more specific competencies
below it).

The assistant reads one Page and **suggests** which competencies the Page supports. For every
suggestion it shows the **exact sentences from your Page** that it relied on, so you can check the
reasoning in a few seconds instead of taking its word for it.

**You decide.** The assistant never decides and never changes anything in Moodle. In this pilot,
saving a decision does **not** create or change any Moodle competency link. It only records what you
decided so that we can learn from it.

The suggestions come from an AI language model. It can be wrong, and it can miss something. Your
judgement is the point of the exercise. Treat each suggestion as a colleague's proposal.

## Your account

You will receive, from the pilot organiser:

- the address of the site,
- a **username** such as `teacher03` and a **temporary password**.

At your first login Moodle asks you to choose a new password. Choose one only you know, and do
not reuse one from another site. Your account is called a **pseudonym** in all records (for example
`T003`): the site does not know your name, and the records of the pilot refer to you only by that
code. The organiser, and only the organiser, keeps the list that says which person has which code.

The account has a placeholder email address that cannot receive mail. That is deliberate: **the site
sends no email**. If you forget your password, ask the organiser for a new one.

You are a **Teacher** in one course only, "Competency Alignment Pilot". The suggestions for a Page are
shared: if a colleague has already analysed a Page you see the same suggestions, and pressing
**Reanalyse** replaces them for everyone. Your **decisions** are individual: you see only your own, and
nobody else sees yours in the plugin.

## How to review a Page, step by step

1. Log in and open the course **Competency Alignment Pilot**.
2. In the course menu (the **More** menu on a narrow window), choose **Competency Alignment**.
3. You see a table of the course's Pages. Each row says **Not analysed** or shows an earlier result.
4. Press **Suggest competencies** on a Page that you want to look at.
5. You land on a page that says the analysis was queued. **Wait and leave the page open.** It
   refreshes by itself every few seconds, and the suggestions appear when the analysis is done.
   This normally takes under a minute, and sometimes a few minutes. Please do not press the button again
   in the meantime: the site notices and will not start a second run.
6. Read each **card**. A card shows:
   - the suggested competency (code, name and description),
   - **Exact evidence from the resource**: sentences taken word for word from your Page,
   - a collapsed **Technical details** section. You can ignore it. It holds scores for the researchers,
   - sometimes a **Hierarchy note**. Competencies are organised as parents and children. If the
     assistant suggests both a parent and one of its children, the note tells you so. It is information, not
     an error.
7. For each card choose **Accept**, **Reject** or **Modify**:
   - **Accept**: the competency is right for this Page.
   - **Reject**: it is not right.
   - **Modify**: a different competency fits better. A list appears and you pick the one you would use
     instead.
8. Optionally rate the evidence (**0**, **1** or **2**): did the quoted sentences help you decide?
   - 0: did not help justify the decision
   - 1: partly useful
   - 2: clearly supported the decision

   Nothing is pre-selected. Leaving it empty is fine.
9. Optionally write a comment (up to 1000 characters): anything that was unclear, hard, wrong or
   surprising. **Comments are the most useful thing you can give us.**
10. Press **Save decision**. A green message confirms it. You can change a decision later. We keep
    your earlier version as well as the new one.

If the assistant suggests nothing, the page says so. That is a legitimate result: tell us in a comment
if you think it should have found something.

### Reanalyse

The **Reanalyse** button asks the assistant to look at the Page again and replaces the suggestions
you see. Your earlier decisions are kept. Use it only if the Page changed or something went wrong. Because the suggestions are shared, check with
your colleagues before replacing them.
Each analysis uses the AI service, which costs money and counts towards a quota, so please do not
press it out of curiosity.

## You may use your own Pages

The course contains six sample Pages. If your organiser tells you that you may add your own, **do not
paste anything that contains names, grades, personal data or confidential material.** The text of a
Page is sent to an AI service outside this site to be analysed (see below). Public lecture notes are
fine.

## What is recorded, and who sees it

When you save a decision, the site stores: which Page, which suggestion, your pseudonym, **accept /
reject / modify** (and the competency you chose when modifying), your 0 to 2 rating, your comment, the
time of the decision, and **how long the card was open before you saved** (the time between the
suggestion being shown to you and your save; if you leave a card open for hours, the figure is not
used). It does not record your keystrokes, your screen or what else you do on the site.

What is sent out: the text of the Page you analyse, with the list of 13 competencies and their
descriptions, goes to the model provider's service (Google Gemini) so it can produce suggestions. Your
username, pseudonym and anything else about you are **not** sent.

The records are used by the researchers to evaluate the tool, and are reported without your name or
anything that identifies you. [To be completed by the organiser before the pilot starts: the exact
statement of consent, how long the data is kept, and who to contact to withdraw. This guide must not be
issued without it.]

You can stop at any time, and ask for your records to be removed.

## If something looks wrong

- **The page says the analysis did not complete.** Wait a minute and press **Reanalyse** once. If it
  fails again, tell the organiser. Say which Page and roughly when.
- **The page says the service cannot be reached.** Not your fault. Tell the organiser.
- **You see something that looks like an answer key, a score you do not understand, or code.** Please
  report it with a screenshot. It is not meant to be there.
- **Anything else odd.** A screenshot and one line is enough.

Screenshots may show the Page text and your pseudonym. They do not show your password. Please do not
send passwords by email or chat.

## Contact

[To be completed by the organiser: name, email, and when you will answer.]
