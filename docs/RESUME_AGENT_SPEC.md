# Australian Resume Content and Word Generator: specification, review and implementation

This is the source of truth for the resume agent. The code lives in `resume_agent/` (this repository) and is copied unchanged into Vikashan `api/_py/resume_agent/` for the New Page resume writer.

## 1. Requirements (summary of the agreed spec)

**Identity.** A senior Australian resume writer and document automation assistant. Output: an ATS-friendly resume and a formatted `.docx` built with `python-docx`.

> **Change agreed after the first release:** there is no separate "Reply Y" gate. Content approval is the only approval. Once the candidate approves, the Phase 2 JSON is shown and the Word file is generated, executed and validated in the same turn. The Python script is no longer offered for download. `AWAITING_EXECUTION_APPROVAL` remains in the code only so that sessions saved at the old gate still build.

**Workflow (four phases, one state at a time).** States: `DRAFTING`, `AWAITING_CONTENT_APPROVAL`, `PREPARING_JSON`, `AWAITING_EXECUTION_APPROVAL`, `GENERATING_SCRIPT`, `EXECUTING_SCRIPT`, `COMPLETED`, `EXECUTION_FAILED`.

1. **Draft.** Draft from the supplied materials (resume, job description, LinkedIn text, notes, certificates). Ask one concise set of questions when essential information is missing. Then stop and ask exactly: `Approve content? Please reply “Yes” or provide the amendments required.`
2. **Revision loop.** Apply the amendments, show the full revised resume, and ask again. Approval phrases: Yes, Approved, Looks good, Proceed, Go ahead, Content approved. "Okay" followed by changes is not approval.
3. **Phase 2, Prepare.** After explicit approval, show strict JSON in the agreed schema (double quotes, no comments, no trailing commas, no Markdown fences, optional sections as `[]`, approved wording unchanged).
4. **Script, execute, validate.** Straight after the JSON, in the same turn: generate a complete `python-docx` script, run it, check the file exists, is not empty, opens, and contains the name, summary, headings and employment. Only then say `<actual filename> successfully generated.` On failure, never claim success: correct the script and run it again (the candidate can also reply "Try again").

**Content rules.** Australian English. Senior tone where the experience supports it. Strong action verbs. Semi-functional structure, in this order:
1. Name and contact
2. Professional summary (three to four sentences, no first person)
3. Key skills (five to eight, one skill each, no ampersands, no "and" combinations)
4. Professional experience (reverse chronological; action + scope + method + result; three to eight bullets for recent roles, fewer for older ones)
5. Education and training
6. Awards
7. Certifications
8. Technical skills
9. Additional information

Omit any empty optional section. Never fabricate employers, titles, dates, qualifications, certifications, awards, technologies, metrics, team sizes, budgets or clearances. Separate confirmed facts from proposed wording. Never include a photo, date of birth, marital status, religion, gender or street address.

**Document rules.**
- Page: A4, portrait, margins 1.5 to 2 cm. No headers or footers, tables, text boxes, columns, graphics or page borders.
- Text: Calibri 11 pt (Latin and East Asian fonts both set), all black, single spacing, 0 pt before and after except small controlled gaps.
- Name: 22 pt, bold, uppercase, centred.
- Job title and contact details: centred, separated by `|`, plain text with no blue hyperlinks.
- Section headings: bold, with a single full-width black bottom border (no box, no shading).
- Bullets: Word's `List Bullet` style.
- Filename: `Candidate_Name_Generic_Job_Title_Resume.docx`, sanitised for Windows, with `Professional` as the fallback title.

**Inputs.** File upload of the resume and the job description, including PDF.

## 2. Review of what existed (October 2026)

| Area | Resume-Generator (standalone) | Vikashan New Page resume writer |
|---|---|---|
| "That didn't work" | Used OpenAI; nothing on Claude. | **Root cause found.** `askJson` forced `tool_choice: {type: "tool"}`. `claude-sonnet-5-5` and `claude-opus-5-5` reject that with HTTP 400, so every structured AI call failed: resume, resume edit, cover letter, Compass suggestions and section writers. The unit test mocked `fetch`, so it passed anyway. |
| Workflow and gates | One shot: generate, then free-form edit. No approval, JSON or Y gate. | Same one-shot flow. |
| JSON schema | Its own shape (`name`, `contact`, `experience[].bullets`, ...). | Copy of the same shape. |
| Word document | Five decorative templates (colour, sidebars, tables). Not ATS-safe and not to this spec. | Same builder. |
| Script and execution | No generated script; the builder is called directly. Nothing validates the output. | Same. |
| Job description upload | Paste only. | Paste only. |
| Writing rules | "programme", ampersand rule, no reverse-chronology or integrity check after generation. | Same prompt, copied. |

Smaller faults found along the way:
- The Sky coach's `max_tokens: 700` is shared with adaptive thinking on current models, so replies could come back empty.
- The `docx.py` and resume-session token checks were duplicated.

## 3. Design

```
browser ──start/reply──▶ host (FastAPI route or Vercel Python function)
                          └─ resume_agent.agent  (state machine, gates decided in code)
                               ├─ claude.ask_structured   phase 1 and revisions (structured outputs)
                               ├─ lint                    writing-rule and integrity checks, one repair pass
                               ├─ schema.to_json          phase 2: the approved draft, serialised
                               ├─ script.build_script     phase 3: complete python-docx script
                               └─ execute.generate_document  phase 4: run in a subprocess, validate, render check, retry
```

Decisions:

- **Claude writes the content. Code owns the gates and the JSON.** Approval detection (`workflow.classify_*`) is deterministic, so a model can never skip content approval. Phase 2 JSON is the approved draft serialised by `json.dumps`, so the approved wording reaches Word exactly and always parses.
- **The script is generated from a fixed, tested template with the approved data embedded, not written freehand by the model each time.** It is still a complete, standalone script: all imports, the data, every helper and the filename rules. It is written to disk and run with Python in a separate process. Running model-written code on a shared server would need a real sandbox. A template also gives identical formatting every time and keeps the acceptance tests meaningful. "Correct the script" on failure means: re-clean every string (the usual cause of `python-docx` failures is characters XML cannot hold), rebuild and run again. Failures are reported honestly and no file is returned.
- **Sessions are HMAC-signed** (`agent.seal`), so the servers stay stateless while the browser cannot forge a state such as "approved".
- **Structured outputs** (`output_config.format`) instead of forced tool use; current models reject the latter. Requests stream, use adaptive thinking at `medium` effort, and opt into server-side refusal fallback (`fallbacks: "default"`).
- **Model:** `claude-opus-5-5` for the resume (`RESUME_MODEL` overrides it).
- **Automatic checks** before the candidate sees a draft (`lint.py`):
  - Summary sentence count, key-skill count and format, and duplication with technical skills.
  - First person, emojis and US spellings.
  - Reverse chronology and bullet counts.
  - Figures, employers or qualifications that do not appear in the candidate's materials.

  Anything found goes back to Claude once for a targeted fix. Whatever remains is shown as "To confirm".
- **Visual validation** renders the file to PDF with LibreOffice where installed, and checks for blank pages and headings stranded at the bottom of a page. Where LibreOffice is missing (Vercel), the result says the check was not done.

## 4. Where it runs

| | Resume-Generator | Vikashan New Page |
|---|---|---|
| UI | `frontend/src/pages/AgentPage.js` (`/agent`, the landing page's main button) | `newpage/app/resume.js` (Tools → Resume writer) |
| API | `agent_routes.py`: `/api/agent/status`, `extract`, `start`, `reply`, `open` | `api/newpage/resume.py`: actions `extract`, `start`, `reply`, `open` |
| Saving | Browser session storage | `api/newpage/app.js` action `resume_save` (newpage_docs); saved resumes reopen at the approval gate |
| Secrets | `ANTHROPIC_API_KEY`, `RESUME_SESSION_SECRET` | `ANTHROPIC_API_KEY`; the session key is derived from `JWT_SECRET` |

When `resume_agent/` changes here, copy it to Vikashan `api/_py/resume_agent/`, and copy `tests/fixtures/` to `tests/py/fixtures/` there.

## 5. Acceptance tests (spec section 17) and where they are checked

| Requirement | Test |
|---|---|
| Drafts before JSON, stops, needs explicit approval, amendments loop back | `tests/test_resume_agent.py::test_full_workflow_gates_and_document`, `test_amendment_at_execution_gate_returns_to_drafting`, `test_questions_when_essential_information_is_missing` |
| Approval wording ("okay" alone or "okay but..." is not approval) | `tests/fixtures/replies.json`, used by both repositories |
| Content approval cannot be skipped; approval builds the file with no second gate | `test_session_cannot_be_forged_or_skip_gates`, `test_state_machine_rejects_skips`, `test_full_workflow_gates_and_document` |
| Failed or lost builds can be rebuilt | `test_failed_build_can_be_retried`, `test_session_saved_at_the_old_y_gate_still_builds` |
| JSON parses, matches the schema, keeps the wording, no fences, empty sections as arrays | `test_full_workflow_gates_and_document`, `test_schema_and_json` |
| A4, name 22 pt bold uppercase centred, centred contact, Calibri 11 pt, black, bordered headings, List Bullet, no tables, no hyperlinks, no blank pages, filename | `execute.validate_docx` (26 checks run on every generated file), `test_document_formatting`, `test_validator_catches_bad_documents`, `render_check` |
| No unsupported facts or invented metrics | `lint.integrity_issues`, `test_integrity_lint_flags_invented_facts`, `test_lint_repair_pass_runs_and_reports_leftovers` |
| No success claim unless the file exists and is readable | `test_failure_is_reported_honestly` |
| Script complete and runnable without editing | Run in a separate process for every document; `test_execute_python_contract` |
| PDF job description upload | `tests/test_agent_api.py::test_job_description_pdf_upload`; Vikashan `tests/py/test_resume_api.py` |
| The real Claude request shape | `tests/test_agent_api.py` (mock Anthropic server, streamed); Vikashan `tests/newpage-tools.test.js` (`askJson`) |
