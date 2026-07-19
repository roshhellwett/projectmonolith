# AI Convergence — Implementation Plan & Progress

## Goal

Merge AI capabilities across the Crypto Bot and AI Bot with a **user-owned Groq key** model. Crypto bot gets a built-in crypto-specialized AI co-pilot. AI bot continues independently but reads the same user key. Admin removes the global `GROQ_API_KEY` — users bring their own.

---

## Architecture

```
                    ┌──────────────────────────────┐
                    │    crypto_users table          │
                    │  ┌────────────────────────┐   │
                    │  │ user_id | groq_api_key  │   │
                    │  └────────────────────────┘   │
                    └──────────┬───────────────────┘
                               │ reads key
                    ┌──────────┴──────────┐
                    │                     │
         ┌──────────▼──────┐   ┌─────────▼─────────┐
         │  CRYPTO BOT      │   │  AI BOT             │
         │  /ai             │   │  /zenith            │
         │  crypto-focused  │   │  /research          │
         │  read-only data  │   │  /summarize         │
         │  web research    │   │  /code /imagine     │
         └─────────────────┘   └───────────────────┘
                    │                     │
                    └──────────┬──────────┘
                               │ calls Groq with user's key
                    ┌──────────▼──────────┐
                    │     Groq API         │
                    │  (user's own key)    │
                    └─────────────────────┘
```

---

## Progress Table

| Phase | Description | Status | Files Changed |
|-------|-------------|--------|---------------|
| 0 | Schema — models.py + column, repository.py +4 methods | ✅ Done | 2 |
| 1 | Crypto AI Engine — system prompt, Groq call, key validation, search | ✅ Done | 1 (NEW) |
| 2 | Crypto AI Handlers — /ai, /setkey, /mykey, /delkey, followup callbacks | ✅ Done | 1 (NEW) |
| 3 | Crypto UI additions — welcome, key setup, response, errors, follow-up buttons | ✅ Done | 1 |
| 4 | Registration — run_crypto_bot.py handlers | ✅ Done | 1 |
| 5 | AI Bot accept per-user key — llm_engine.py, pro_handlers.py, run_ai_bot.py | ✅ Done | 4 |
| 6 | Remove global GROQ_API_KEY from config.py + fix dependent imports | ✅ Done | 3 |
| 7 | Verification — ruff, mypy, pytest | ✅ Done | — |

---

## Phase Details

### Phase 0 — Schema

**File: `src/zenith_crypto_bot/models.py`**
- Added `groq_api_key = Column(String(200), nullable=True)` to `CryptoUser`

**File: `src/zenith_crypto_bot/repository.py`**
- Added 4 methods to `SubscriptionRepo`:
  - `set_groq_key(user_id, api_key)` — upsert key
  - `get_groq_key(user_id)` → `str | None`
  - `delete_groq_key(user_id)` — set to None
  - `get_user_ai_context(user_id)` → formatted text blob of subscription, portfolio, alerts, wallets, audits

### Phase 1 — Crypto AI Engine

**File: `src/zenith_crypto_bot/ai_engine.py` (NEW)**

Key components:
- `SYSTEM_PROMPT` — warm crypto-friend personality, read-only data context, crypto-only scope, off-topic redirect
- `validate_groq_key(api_key)` — test call to Groq, returns `(valid, error_msg)`
- `needs_search(query)` — detects news/price/analysis keywords
- `call_crypto_ai(api_key, user_id, query)` — builds system prompt with user context, optional web search, calls Groq, sanitizes output, handles errors (rate_limited, invalid_key, server_error)

### Phase 2 — Crypto AI Handlers

**File: `src/zenith_crypto_bot/ai_handlers.py` (NEW)**

Commands:
- `/ai [query]` — full flow: check key → fetch context → search if needed → stage animation → call Groq → response + follow-up buttons
- `/setkey gsk_xxx` — validate key → store in DB
- `/mykey` — show whether key is set
- `/delkey` — remove key
- `handle_ai_followup` — callback handler for follow-up buttons, re-runs AI with pre-filled topic

Stage animation: ["Reading your data", "Checking markets", "Thinking"] via `edit_with_stages`

### Phase 3 — Crypto UI Additions

**File: `src/zenith_crypto_bot/ui.py`** (8 new functions)

| Function | Purpose |
|----------|---------|
| `get_ai_no_key_msg()` | Onboarding: "Get a free Groq key" + link |
| `get_ai_key_set_success_msg()` | After key set: "You're live!" + try buttons |
| `get_ai_key_status_msg(has_key)` | Key status display |
| `get_ai_key_deleted_msg()` | Key removed confirmation |
| `get_ai_empty_query_msg()` | "Ask me anything" + 5 suggestion buttons |
| `get_ai_response_msg(response, query)` | Rich response + context-aware follow-up grid |
| `get_ai_rate_limited_msg()` | "Rate limited, wait or replace key" |
| `get_ai_invalid_key_msg()` | "Key invalid, set a new one" |
| `get_ai_server_error_msg()` | "Couldn't reach AI, try again" |

Follow-up button categories:
- Portfolio → Compare BTC, Top Gainer, Market Today
- Market/Price → Top Movers, Gas Fees, My Portfolio
- Alerts → View Alerts, Alert Strategy
- Wallets → View Wallets, Recent Txs
- Gas → Live Gas, Optimization
- Audit → Run Audit, Risk Guide
- Subscription → Pro Features, Buy Pro
- News/Prediction → Market Outlook, Technical Analysis, My Portfolio
- Default → My Portfolio, Market Today, My Alerts, Gas Fees

### Phase 4 — Registration

**File: `src/run_crypto_bot.py`**
- Imported: `cmd_ai`, `cmd_setkey`, `cmd_mykey`, `cmd_delkey`, `handle_ai_followup`
- Registered: `/ai`, `/setkey`, `/mykey`, `/delkey` + `^ai_followup_` callback

### Phase 5 — AI Bot Per-User Key

**File: `src/zenith_ai_bot/llm_engine.py`**
- `get_groq_client(api_key)` — removed singleton global, now accepts key parameter
- All 5 processors accept `api_key`:
  - `process_ai_query(..., api_key=None)`
  - `process_research(..., api_key=None)`
  - `process_summarize(..., api_key=None)`
  - `process_code(..., api_key=None)`
  - `process_imagine(..., api_key=None)`
- Each returns no-key message if `api_key` not provided

**File: `src/zenith_ai_bot/pro_handlers.py`**
- `cmd_research` — fetches key, passes to `process_research(api_key=...)`
- `cmd_summarize` — fetches key, passes to `process_summarize(api_key=...)`
- `cmd_code` — fetches key, passes to `process_code(api_key=...)`
- `cmd_imagine` — fetches key, passes to `process_imagine(api_key=...)`

**File: `src/run_ai_bot.py`**
- `ai_worker` — fetches `api_key` per job; skips with no-key message if unset

**File: `src/zenith_ai_bot/ui.py`**
- Added `get_no_key_msg()` — directs user to set key in crypto bot

### Phase 6 — Remove Global Key

**File: `src/core/config.py`**
- Removed `GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")`

**File: `src/core/__init__.py`**
- Removed `GROQ_API_KEY` import and export

**File: `src/zenith_support_bot/ai_responder.py`**
- Changed to read `SUPPORT_GROQ_API_KEY` from env directly (optional, graceful fallback)
- Both `generate_ai_response` and `generate_faq_answer` return fallback text if no key set

### Phase 7 — Verification

| Check | Result |
|-------|--------|
| ruff | ✅ No errors |
| mypy | ✅ No issues (67 files) |
| pytest | ✅ 194/194 passed |

---

## Environment Changes

| Variable | Action |
|----------|--------|
| `GROQ_API_KEY` | **Remove** from .env / Railway |
| `SUPPORT_GROQ_API_KEY` | Optional — only if support AI auto-responder is needed |

---

## Files Summary

| Action | Files |
|--------|-------|
| **New** | `zenith_crypto_bot/ai_engine.py`, `zenith_crypto_bot/ai_handlers.py` |
| **Modified** | `zenith_crypto_bot/models.py`, `zenith_crypto_bot/repository.py`, `zenith_crypto_bot/ui.py`, `run_crypto_bot.py` |
| **Modified** | `zenith_ai_bot/llm_engine.py`, `zenith_ai_bot/pro_handlers.py`, `zenith_ai_bot/ui.py`, `run_ai_bot.py` |
| **Modified** | `core/config.py`, `core/__init__.py` |
| **Modified** | `zenith_support_bot/ai_responder.py` |
| **Total** | **13 files** |

---

## Fallback Matrix

| Scenario | Crypto AI Bot (`/ai`) | AI Bot (`/zenith`, etc.) |
|----------|----------------------|--------------------------|
| No key set | Onboarding with steps + button | "Set key in crypto bot" |
| Invalid key on set | "Key failed validation" | N/A |
| Key goes invalid later | "Key doesn't work, set new one" | Falls through to Groq error |
| Groq 429 | "Rate limited. Wait or /setkey new key" | Same |
| Groq 5xx / network | "Couldn't reach AI, try again" | Same |
| No query | 5 suggested buttons as grid | Help text with examples |
| Off-topic | System prompt enforces redirect | Existing persona handles it |
| User data fetch fails | Respond without context (missing data fields) | N/A |
| Web search fails | Respond without search results | N/A |
| Empty response from Groq | "Couldn't reach AI, try again" | Fallback error message |
