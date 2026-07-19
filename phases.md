# Zenith Bot Polish — Phases & Progress

> Classy, minimal, premium SaaS-level Telegram bot polish. One bot at a time.

---

## Progress Overview

| Phase | Bot | Status | Started | Completed | Files Changed |
|-------|-----|--------|---------|-----------|---------------|
| 1 | GROUP | ✅ Complete | 2026-07-19 | 2026-07-19 | 9 files |
| 2 | AI | ✅ Complete | 2026-07-19 | 2026-07-19 | 4 files |
| 3 | CRYPTO | ✅ Complete | 2026-07-19 | 2026-07-19 | 3 files |
| 4 | SUPPORT | ✅ Complete | 2026-07-19 | 2026-07-19 | 4 files |
| 5 | ADMIN | ✅ Complete | 2026-07-19 | 2026-07-19 | 4 files |
| 6 | Core (animation, formatters) | ✅ Complete | 2026-07-19 | 2026-07-19 | 4 files |

---

## Phase 1 — GROUP Bot

### Goal
Polish every user-facing text string, animation trigger, and error path to classy SaaS quality. Consolidate all message building into `ui.py`.

### Emoji Policy
- **Keep**: 🛡️ ✅ ⚠️ 🔒 ⚙️ 📊 🔔 🔙 📋 🔑
- **Remove**: 💎 🆓 ❌ 🚨 ✖️ ↩️ 🔍 🎯 ✨ 🤖 🔞 🌊 ⏸️ 🚫 🔇 🔊 🗑️ 🔴🟡🟢 ⛔ 👋 💬 📝 📜 ⏰ 🔄 ❓ (replaced with bold text labels)

### Steps
- [x] 1.1 Emoji cleanup + text refinement (all files)
- [x] 1.2 Consolidate message building into `ui.py` (pro_handlers, group_app, setup_flow, ai_handlers, crypto_handlers → ui.py)
- [x] 1.3 Wire up confirmation dialogs (forgive, reset, add/del word, schedule)
- [x] 1.4 Use animation utilities (ai_handlers, crypto_handlers)
- [x] 1.5 Persist raid mode to DB (models, repository, pro_handlers)
- [x] 1.6 Error message recovery hints (all error paths)
- [x] 1.7 Eliminate silent moderation failures (group_app) — added logging for ban failures; _notify_owner still covers strike detection
- [x] 1.8 Extract hardcoded limits to constants (MAX_CUSTOM_WORDS=200, MAX_SCHEDULED_MESSAGES=10, MAX_SCHEDULE_MESSAGE_LENGTH=1000, MAX_WELCOME_LENGTH=500, FREE_MAX_TOKENS=512, PRO_MAX_TOKENS=1024, FREE_MAX_RESPONSE_LENGTH=1500)

### Files

| File | Action | Details |
|------|--------|---------|
| `src/zenith_group_bot/ui.py` | **Heavy rewrite** | Absorb all message building; clean, minimal emoji formatting |
| `src/zenith_group_bot/pro_handlers.py` | **Restructure** | Thin validation + ui.py calls; add confirmations; raid mode DB |
| `src/zenith_group_bot/group_app.py` | **Restructure** | Add confirmations (forgive/reset); error hints; fix silent failures |
| `src/zenith_group_bot/setup_flow.py` | **Refactor** | Messages → ui.py; cleaner text |
| `src/zenith_group_bot/ai_group_handlers.py` | **Refactor** | Messages → ui.py; use animation.py |
| `src/zenith_group_bot/crypto_group_handlers.py` | **Refactor** | Messages → ui.py; use animation.py |
| `src/zenith_group_bot/repository.py` | **Enhance** | Add raid_mode DB CRUD; add config getters |
| `src/zenith_group_bot/models.py` | **Enhance** | Add raid_mode, raid_expires_at columns |
| `src/run_group_bot.py` | **Refactor** | Delegate welcome/status to ui.py |

### Verification
- [ ] Ruff lint & format
- [ ] MyPy type check
- [ ] Pytest (212/212)
- [ ] Manual: /start, /setup, /addword, /delword, /forgive, /reset, /antiraid, /schedule, /welcome

---

## Phase 2 — AI Bot

### Steps
- [x] 2.1 Emoji cleanup + text refinement
- [x] 2.2 Consolidate message building into `ui.py`
- [x] 2.3 Refine persona descriptions and usage cards
- [x] 2.4 Error message recovery hints
- [x] 2.5 Use animation utilities for "thinking" states

### Files
- `src/zenith_ai_bot/ui.py`
- `src/zenith_ai_bot/pro_handlers.py`
- `src/zenith_ai_bot/ai_handlers.py`
- `src/run_ai_bot.py`

### Verification
- [ ] Ruff lint & format
- [ ] MyPy type check
- [ ] Pytest (212/212)

---

## Phase 3 — CRYPTO Bot

### Steps
- [x] 3.1 Emoji cleanup + text refinement
- [x] 3.2 Consolidate message building into `ui.py`
- [x] 3.3 Refine market dashboard, portfolio, alerts UI
- [x] 3.4 Error message recovery hints
- [x] 3.5 Use animation utilities for data loading

### Files
- `src/zenith_crypto_bot/ui.py` — complete rewrite: 35+ message builders, `build_gauge`, `get_audit_*` helpers
- `src/zenith_crypto_bot/pro_handlers.py` — all inline HTML → `crypto_ui.*` calls; `send_loading_message` for loading states
- `src/run_crypto_bot.py` — all inline HTML → `crypto_ui.*` calls; confirmation dialogs for delete alert + untrack wallet; background loops use ui.py functions

### Verification
- [x] Ruff lint & format
- [x] MyPy type check
- [x] Pytest (211/211)

---

## Phase 4 — SUPPORT Bot

### Steps
- [x] 4.1 Emoji cleanup + text refinement
- [x] 4.2 Consolidate message building into `ui.py`
- [x] 4.3 Refine ticket dashboard, FAQ, canned responses
- [x] 4.4 Error message recovery hints

### Files
- `src/zenith_support_bot/ui.py` — complete rewrite: 60+ message builders; zero decorative emojis (all replaced with bold text / plain labels)
- `src/zenith_support_bot/pro_handlers.py` — all inline HTML → `support_ui.*` calls (cmd_priority, savereply, replies, reply, addfaq, delfaq, rate, stats, resolve)
- `src/zenith_support_bot/user_handlers.py` — all inline HTML → `support_ui.*` calls (handle_ticket_reply_callback, handle_ticket_close_callback, handle_ticket_reply_message)
- `src/run_support_bot.py` — all inline HTML → `support_ui.*` calls; confirmation dialog for close ticket (sup_close_confirm_)

### Verification
- [x] Ruff lint & format
- [x] MyPy type check
- [x] Pytest (211/211)

---

## Phase 5 — ADMIN Bot

### Steps
- [x] 5.1 Emoji cleanup + text refinement
- [x] 5.2 Consolidate message building into `ui.py`
- [x] 5.3 Professional admin panel redesign
- [x] 5.4 Error message recovery hints

### Files
- `src/zenith_admin_bot/ui.py` — rewrite: 30+ formatting functions, keyboards, helpers; zero decorative emojis
- `src/zenith_admin_bot/commands.py` — all inline HTML → `admin_ui.*` calls across 17+ command handlers
- `src/zenith_admin_bot/dashboard.py` — all inline HTML → `admin_ui.*` calls; imported as module (`admin_ui`)
- `src/zenith_admin_bot/common.py` — emoji strings replaced with plain text (`⏳`/`⛔` removed)

### Verification
- [x] Ruff lint & format
- [x] MyPy type check
- [x] Pytest (211/211)

---

## Phase 6 — Core (animation, formatters)

### Steps
- [x] 6.1 Refine animation.py — review and polish loading states (removed 14 unused functions; kept 3 used: send_loading_message, send_typing_action, edit_with_stages)
- [x] 6.2 Refine formatters.py — ensure consistency with new UI style (stripped from 25 functions to 3: format_progress_bar, format_address, format_divider)
- [x] 6.3 Audit formatters vs actual usage — removed 22 unused functions

### Files
- `src/core/animation.py` — stripped 14 unused functions; kept 3; renamed `edit_with_animation` → `_edit_with_animation` (internal)
- `src/core/formatters.py` — stripped 22 unused functions; kept 3 (`format_progress_bar`, `format_address`, `format_divider`)
- `src/core/__init__.py` — updated re-exports to match
- `tests/test_formatters.py` — rewritten to test only remaining 3 functions

### Verification
- [x] Ruff lint & format
- [x] MyPy type check
- [x] Pytest (194/194) — reduced from 211 due to removed dead function tests

---

### Current Status — All 6 Phases Complete

All bots migrated to dedicated `ui.py` message builders — zero inline HTML in handlers. Core libraries trimmed from 40+ functions to 6 actively used ones. 194 tests pass.

- **Phase 5 (ADMIN)** — ui.py rewritten, commands.py/dashboard.py → `admin_ui.*`, common.py emoji cleanup
- **Phase 6 (Core)** — formatters.py: 25→3 functions, animation.py: 17→3 functions, tests rewritten
- ruff ✅, mypy ✅, pytest 194/194 ✅

---

## Changelog

### 2026-07-19
- Created phases.md with full plan structure
- **Phase 1 (GROUP bot) — Complete**
- **Phase 2 (AI bot) — Complete**
- **Phase 3 (CRYPTO bot) — Complete**
  - Rewrote ui.py: 35+ message builders covering market, gas, alerts, wallets, portfolio, audit, subscription, welcome, help
  - Added `build_gauge()`, `get_risk_label()`, `get_audit_*()` report builders
  - Rewrote pro_handlers.py: all inline HTML → `crypto_ui.*` calls; `send_loading_message` for market/gas/portfolio/alerts/wallets loading states
  - Rewrote run_crypto_bot.py: `handle_dashboard` fully delegates to ui.py; added confirmation dialogs for `ui_del_alert_confirm_` and `ui_untrack_confirm_`; background loops (price alerts, wallet watcher, blockchain watcher, subscription monitor) all use ui.py functions
  - Pruned emoji from 30+ to 0 decorative emojis (data content preserved in plain text)
  - Verification: ruff ✅, mypy ✅, 211/211 pytest ✅
- **Phase 2 (AI bot) — Complete**
  - Rewrote ui.py: consolidated ALL message building; removed duplicate PERSONAS dict (now imports from prompts.py)
  - Rewrote run_ai_bot.py: all inline HTML replaced with ui.py calls; fixed clear history confirmation dialog
  - Rewrote pro_handlers.py: fixed duplicate cmd_history code; all messages via ui.py
  - Pruned emojis from 25+ to minimal set
  - Verification: ruff ✅, mypy ✅, 211/211 pytest ✅
- **Phase 3 (CRYPTO bot) — Complete**
  - Rewrote ui.py: 35+ message builders covering market, gas, alerts, wallets, portfolio, audit, subscription, welcome, help
  - Added `build_gauge()`, `get_risk_label()`, `get_audit_*()` report builders
  - Rewrote pro_handlers.py: all inline HTML → `crypto_ui.*` calls; `send_loading_message` for loading states
  - Rewrote run_crypto_bot.py: handle_dashboard fully delegates to ui.py; confirmation dialogs; background loops use ui.py
  - Pruned emoji from 30+ to 0 decorative
  - Verification: ruff ✅, mypy ✅, 211/211 pytest ✅
- **Phase 4 (SUPPORT bot) — Complete**
  - Rewrote ui.py: 60+ message builders covering tickets, FAQ, canned responses, priority, ratings, analytics, pro features; zero decorative emojis
  - Rewrote pro_handlers.py: all inline HTML → support_ui.* calls for all 9 pro commands
  - Rewrote user_handlers.py: all inline HTML → support_ui.* calls for ticket reply/close flows
  - Rewrote run_support_bot.py: handle_dashboard fully delegates to support_ui; confirmation dialog for sup_close_confirm_
  - Verification: ruff ✅, mypy ✅, 211/211 pytest ✅
- **Phase 5 (ADMIN bot) — Complete**
  - Rewrote ui.py: 30+ formatting functions, keyboards, inline helpers; zero decorative emojis
  - Rewrote commands.py: all inline HTML → `admin_ui.*` calls across 17+ command handlers
  - Rewrote dashboard.py: all inline HTML → `admin_ui.*` calls; imported as module (`admin_ui`)
  - Rewrote common.py: emoji strings replaced with plain text
  - Verification: ruff ✅, mypy ✅, 211/211 pytest ✅
- **Phase 6 (Core) — Complete**
  - Stripped formatters.py from 25 functions to 3 used ones (format_progress_bar, format_address, format_divider)
  - Stripped animation.py from 17 functions to 3 used ones (send_loading_message, send_typing_action, edit_with_stages)
  - Updated core/__init__.py re-exports; rewrote test_formatters.py
  - Verification: ruff ✅, mypy ✅, 194/194 pytest ✅
- **Phase 1 (GROUP bot) — Complete**
  - Rewrote ui.py: consolidated ALL message building from handlers; pruned emojis to minimal set
  - Updated pro_handlers, group_app, setup_flow, ai_handlers, crypto_handlers → ui.py calls
  - Updated run_group_bot: all text delegates to ui.py; registered new callback handlers
  - Wired up confirmation dialogs: addword, delword, schedule, forgive, reset
  - Replaced raw loading strings with send_loading_message in AI and crypto handlers
  - Added raid_mode + raid_expires_at to GroupSettings model; persisted to DB with auto-expiry
  - Added error recovery hints to forgive/reset messages
  - Added logging for ban failures
  - Extracted all hardcoded limits to module-level constants
  - Verification: ruff ✅, mypy ✅, 211/211 pytest ✅
