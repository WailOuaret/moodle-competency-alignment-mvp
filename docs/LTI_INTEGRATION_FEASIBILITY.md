# LTI integration feasibility

**Status:** OPTIONAL / FUTURE EXTENSION  
**Not implemented.**

IMS Learning Tools Interoperability (LTI) is a logical next step if supervisors want teachers to open this app from inside a Moodle course rather than from a separate Streamlit URL. It is not required to complete the research MVP.

## Why LTI is a sensible follow-on

- Moodle already speaks LTI 1.3 / Advantage as a platform.
- The current tool is an **external Python application**. LTI preserves that split: Moodle launches the tool; the alignment pipeline stays in Python.
- Course, user, and role context can be passed without copying Moodle’s competency tables into a plugin.

## Current architecture

```
Moodle (content + GI framework)
    → one-time REST / SQL extraction for the frozen experiment
Teacher browser
    → Streamlit app (analyze / review)
    → existing Python modules (fragment, BM25, constrained LLM, validation)
```

Runtime Mode A already reuses extracted Pages and Quiz questions. It does not write back to Moodle.

## Possible Moodle → app launch flow

1. Admin registers an external LTI tool (client ID, JWKS, redirect URLs).
2. Teacher or student clicks the activity in a course.
3. Moodle sends an OIDC login then a resource-link JWT (LTI 1.3).
4. The app verifies the JWT, creates a session, and reads:
   - `iss`, `sub`
   - `https://purl.imsglobal.org/spec/lti/claim/roles`
   - context (`context_id`, course label)
   - resource link / custom parameters (cmid, resource type)
5. The app maps that context onto an existing extracted resource or asks the teacher to paste/upload.
6. Analysis proceeds with the current pipeline. Results stay in `data/runtime/` unless a later version writes grade or competency line items.

## Authentication and roles

- Trust the platform JWT; do not reuse `MOODLE_TOKEN` in the browser.
- Map LTI roles to the app roles already used: teacher, supervisor (admin/manager), researcher (optional custom role). Students should not persist ACCEPT/REJECT unless that is explicitly wanted.
- Keep Gemini keys and database passwords on the server. Never put them in LTI custom fields.

## Course and context transfer

Custom parameters can carry `course_shortname`, `cmid`, and `resource_type`. The app already understands `MVP-SW` / `MVP-DATA` and `page` / `quiz_question`. A production deployment would need a live extractor or a Moodle web-service call at launch time rather than only the frozen `resources.jsonl`.

## Security

- Validate issuer, audience, nonce, and expiry on every launch.
- Use HTTPS, rotating keys, and a server-side session store (Render’s filesystem is ephemeral).
- Treat LTI `sub` as a stable user key; do not display platform secrets.
- Continue to treat uploaded HTML as data, not executable content.

## Deployment requirements

- Public HTTPS URL for the tool
- Moodle admin rights to register LTI
- Persistent database for sessions and reviews (do not rely on local CSV alone)
- Unchanged: BM25 index, prompt version 1.0, evidence validator, hierarchy post-process

## What would need to change

- Add an LTI login route beside Streamlit, or wrap Streamlit behind a verified session
- Persist reviews per platform user
- Optional Names and Roles / Assignment and Grade Services if Moodle gradebook sync is required

## What can remain unchanged

- Frozen Gemini experiment files
- Fragmentation, BM25, constrained JSON contract
- Human-reviewed reference and metrics
- Competency catalogue of 13 GI items

## Explicit mark

**LTI = FUTURE EXTENSION.** This repository does not implement LTI.
