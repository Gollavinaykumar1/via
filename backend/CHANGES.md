# VIA Platform — Agent & Build Changes

## Phase 3 — Human Personas & `human_note` (EXTENDED existing files)
- `backend/core/house_style.py` — **NEW**: shared `HOUSE_STYLE_PROMPT` constant injected into every agent.
- `backend/agents/ceo_agent.py` — **EXTENDED**: Added Arjun persona + house style + `human_note` in JSON schema.
- `backend/agents/backend_agent.py` — **EXTENDED**: Added Dev persona + `human_note`.
- `backend/agents/security_agent.py` — **EXTENDED**: Added Ravi persona + `human_note`.
- `backend/agents/devops_agent.py` — **EXTENDED**: Added Sam persona + `human_note`.
- `backend/agents/architecture_agent.py` — **EXTENDED**: Added Vikram persona + `human_note`.
- `backend/agents/ai_research_agent.py` — **EXTENDED**: Added Nina persona + `human_note`.
- `backend/agents/hr_agent.py` — **EXTENDED**: Added Priya persona + `HUMAN_NOTE:` line parsing.
- `backend/agents/finance_agent.py` — **EXTENDED**: Added Meera persona + `HUMAN_NOTE:` line parsing.
- `backend/agents/marketing_agent.py` — **EXTENDED**: Added Kabir persona + `HUMAN_NOTE:` line parsing.
- `backend/agents/frontend_agent.py` — **EXTENDED**: Added Anya persona. `human_note` generated programmatically post-build (not via LLM, to avoid contaminating code generation).
- `backend/agents/agent_executor.py` — **EXTENDED**: Extracts `human_note` from agent output, handles `needs_clarification` status, passes `human_note` to `ws_manager`.
- `backend/core/ws_manager.py` — **EXTENDED**: `send_agent_done()` now accepts and broadcasts `human_note`.

## Phase 1 — Agent Pre-Build Discussion (EXTENDED existing files)
- `backend/core/meeting_engine.py` — **EXTENDED**: Added `run_pre_build_discussion()` for structured live agent exchange during builds (Backend shares API shape → Security flags risk → Backend acknowledges → DevOps adds infra constraint → CEO closes conflict). Separate from the planning meeting.
- `backend/agents/agent_executor.py` — **EXTENDED**: Calls `run_pre_build_discussion()` before agent runs if `backend` is in the build. Wrapped in try/except so it never blocks the pipeline.

## Phase 2 — Build Verification + Self-Correction (EXTENDED existing files)
- `backend/core/code_runner.py` — **EXTENDED**: Added `verify_frontend_build()` (npm install + npm run build capture) and `check_live_url()` (HTTP polling with retries).
- `backend/core/fullstack_builder.py` — **EXTENDED**: Added `self_correct_backend()` — sends syntax errors back to LLM to fix generated `main.py`, max 3 attempts.
- `backend/main.py` — **EXTENDED** (both `/deploy/` pipeline):
  - Self-correction loop after `generate_backend_files_llm()`: checks syntax on every `.py` file, re-generates on failure up to 3 times, broadcasts each attempt via `ws_manager.send_step()`.
  - Post-deploy URL health check: polls Render URL (2 retries, 10s wait) and GitHub Pages URL (1 retry, 5s wait) after deploy; results stored in `phase5`/`phase6` dicts.

## Phase 4 — Self-Correction Visibility (EXTENDED existing files)
- `backend/core/ws_manager.py` — **EXTENDED**: Added `send_self_correction()` broadcast helper for explicit in-character self-correction events.
- `backend/core/memory_store.py` — **EXTENDED**: Added `check_agent_contradiction()` — compares a new agent decision against its last stored summary using `SequenceMatcher`. Returns a first-person contradiction note if content diverges significantly (ratio < 0.3).

## Known Limitations / Flagged Items
- `check_agent_contradiction()` uses `difflib.SequenceMatcher` (string similarity), not semantic embeddings. Works well for obvious shifts but may miss subtle reasoning changes. A proper solution would use vector similarity on embeddings — deferred for cost/latency reasons.
- `verify_frontend_build()` requires Node.js available in the runtime environment. If Node is absent, the `npm install` subprocess will error (caught and returned as `{passed: False}`).
- Pre-build discussion adds ~3–5 LLM calls (~15–25s) to build startup. If the LLM is rate-limited, the block is wrapped in try/except and silently skipped.
- The self-correction loop only patches `main.py`. Other generated files (`models.py`, `database.py`) are syntax-checked but not auto-fixed — they rarely have issues.
