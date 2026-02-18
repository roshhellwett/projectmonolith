# PROJECT MONOLITH IS A BUNDLE TELEGRAM BOT PACK

Zenith is a multi-bot Telegram platform that delivers real-time blockchain intelligence, automated content moderation, and AI-powered conversations — all running on a single monolithic FastAPI gateway.

---



## 🤖 Bots

| Bot | Purpose |
|-----|---------|
| [**Zenith Crypto Bot**](https://t.me/zenithwhalebot) | On-chain analytics, token security scans, whale tracking, price alerts, portfolio P&L |
| [**Zenith Group Bot**](https://t.me/zenithgroupbot) | Automated group moderation — abuse filtering, spam detection, flood control |
| [**Zenith AI Bot**](https://t.me/zenithcodexbot) | AI assistant powered by Groq LLM with web search and YouTube transcript analysis |

---

## 💎 Zenith Crypto Bot — Tier Comparison

### 📊 Standard (Free)

| Feature | Limits |
|---------|--------|
| Market Intelligence | Fear & Greed Index + BTC/ETH prices only |
| Token Security Scan | Basic honeypot check — tax rates, holders redacted |
| Price Alerts | **1** active alert |
| Portfolio Tracker | **3** positions |
| Smart Money Alerts | Delayed (15 min) with redacted details |
| New Pair Scanner | Pair tokens visible, **pool address redacted** |
| Wallet Tracker | ❌ Locked |
| Top Gainers/Losers | ❌ Locked |

### ⚡ Pro (Included In Bundle/month)

| Feature | Limits |
|---------|--------|
| Market Intelligence | Full report: Fear & Greed + Top 10 Gainers/Losers + BTC dominance |
| Token Security Scan | **Full GoPlus report:** honeypot, tax rates, holder concentration, LP lock, proxy detection, ownership status |
| Price Alerts | **25** active alerts with instant notifications |
| Portfolio Tracker | **20** positions with live P&L, 24h change, and total value |
| Wallet Tracker | Track **5** whale wallets — instant alerts on transactions |
| Smart Money Alerts | **Real-time** with full details, contract addresses, and trade links |
| New Pair Scanner | Full pool addresses, Etherscan tx links, DexScreener charts |
| Gas Fee Optimizer | Current gas + priority tiers + trading recommendations |

### 🔑 Activation & Renewal

**First time:** Admin generates a key with `/keygen 30`, user activates with:
```
/activate ZENITH-XXXX-XXXX
```

**Renewal:** User pays → sends their Telegram ID → admin runs:
```
/extend 123456789 30
```
No new key needed. Days are added to the existing subscription. User is notified automatically.

**Expiry:** Users receive a warning 3 days before expiry and a notification when Pro access ends. All data (alerts, portfolio, wallets) is preserved for when they renew.

---

## 🤖 Zenith AI Bot — Tier Comparison

### 📊 Standard (Free)

| Feature | Limits |
|---------|--------|
| AI Chat | **10** messages/day with default persona |
| Web Search | Basic single-query search |
| Personas | Default assistant only |
| Deep Research | ❌ Locked |
| Document Summarizer | ❌ Locked |
| Code Interpreter | ❌ Locked |
| Image Prompt Crafter | ❌ Locked |
| Chat History | ❌ Locked |

### ⚡ Pro (Include In Bundle/month)

| Feature | Limits |
|---------|--------|
| AI Chat | **100** messages/day with any persona |
| Web Search | Enhanced multi-source search with news & knowledge graph |
| Personas | **6 AI personas** — Scholar, Creative Writer, Code Expert, Analyst, Philosopher, Comedian |
| Deep Research | Multi-pass research with synthesized reports |
| Document Summarizer | Summarize articles, YouTube videos, and long documents |
| Code Interpreter | Code generation, debugging, and explanation |
| Image Prompt Crafter | Generate optimized prompts for AI image generators |
| Chat History | Persistent conversation memory with `/history` and `/clear` |

---

## 🛡️ Zenith Group Bot — Tier Comparison

### 📊 Standard (Free)

| Feature | Limits |
|---------|--------|
| Protected Groups | **1** group |
| Anti-Spam | Default spam domain blocklist |
| Anti-Abuse | Default profanity word list |
| Flood Control | Medium threshold (5 msgs/3s) |
| New Member Quarantine | 24-hour link/media restriction |
| Strike System | Configurable (Low/Medium/High) |
| Custom Word Filter | ❌ Locked |
| Anti-Raid Shield | ❌ Locked |
| Moderation Analytics | ❌ Locked |
| Scheduled Messages | ❌ Locked |
| Custom Welcome | ❌ Locked |
| Audit Log | ❌ Locked |

### ⚡ Pro (Included In Bundle/month)

| Feature | Limits |
|---------|--------|
| Protected Groups | Up to **5** groups |
| Custom Word Filter | **200** custom words/phrases per group |
| Anti-Raid Shield | Instant lockdown — auto-mute all non-admins and restrict new joins |
| Moderation Analytics | 24h/7d stats, action breakdown, top violators leaderboard |
| Scheduled Messages | **10** daily recurring messages per group (UTC) |
| Custom Welcome | Personalized welcome with `{name}`, `{username}`, `{group}` variables + optional DM |
| Audit Log | Full action history — deletions, bans, quarantines, raid events (up to 50 entries) |

---

### 🔑 Activation & Renewal (All Bots)

**First time:** Admin generates a key with `/keygen 30`, user activates with:
```
/activate ZENITH-XXXX-XXXX
```

**Renewal:** User pays → sends their Telegram ID → admin runs:
```
/extend 123456789 30
```
No new key needed. Days are added to the existing subscription. User is notified automatically.

**Expiry:** Users receive a warning 3 days before expiry and a notification when Pro access ends. All data is preserved for when they renew.

**Shared Subscription:** One Pro key unlocks all 3 bots — Crypto, AI, and Group.

---

## 📡 Commands Reference

### Crypto Bot

| Command | Description |
|---------|-------------|
| `/start` | Open the Zenith terminal dashboard |
| `/audit 0x...` | Run a real security scan on any ERC-20 contract |
| `/alert BTC above 100000` | Set a price alert (Pro: 25, Free: 1) |
| `/alerts` | View your active price alerts |
| `/delalert [ID]` | Remove a price alert |
| `/track 0x... [label]` | Track a wallet for transaction alerts (Pro only) |
| `/wallets` | View tracked wallets |
| `/untrack 0x...` | Stop tracking a wallet |
| `/addtoken ETH 2500 1.5` | Add a position to your portfolio |
| `/portfolio` | View portfolio with live P&L |
| `/removetoken ETH` | Remove a position |
| `/market` | View market sentiment dashboard |
| `/gas` | Check Ethereum gas prices |
| `/activate [KEY]` | Activate Pro subscription |
| `/keygen [DAYS]` | Generate activation key (admin only) |
| `/extend [UID] [DAYS]` | Renew a user's Pro (admin only) |

### AI Bot

| Command | Description |
|---------|-------------|
| `/start` | Open the AI dashboard with feature buttons |
| `/ask [question]` | Chat with the AI (Free: 10/day, Pro: 100/day) |
| `/persona` | Switch AI personality (Pro: 6 personas) |
| `/research [topic]` | Deep multi-pass research with synthesized report (Pro only) |
| `/summarize [URL/text]` | Summarize articles, YouTube videos, or documents (Pro only) |
| `/code [prompt]` | Generate, debug, or explain code (Pro only) |
| `/imagine [prompt]` | Craft optimized prompts for AI image generators (Pro only) |
| `/history` | View your conversation history (Pro only) |
| `/clear` | Clear your chat history (Pro only) |
| `/activate [KEY]` | Activate Pro subscription |
| `/keygen [DAYS]` | Generate activation key (admin only) |
| `/extend [UID] [DAYS]` | Renew a user's Pro (admin only) |

### Group Bot

| Command | Description |
|---------|-------------|
| `/start` | Open the admin dashboard (DM only) |
| `/setup` | Configure moderation settings (use in group) |
| `/forgive` | Clear a user's strikes (reply or provide user ID) |
| `/reset` | Wipe all group data and reconfigure |
| `/addword [word]` | Add a custom banned word/phrase (Pro only) |
| `/delword [word]` | Remove a custom banned word (Pro only) |
| `/wordlist` | View all custom banned words (Pro only) |
| `/antiraid on/off` | Toggle anti-raid lockdown shield (Pro only) |
| `/analytics` | View moderation stats — 24h/7d breakdown (Pro only) |
| `/auditlog [count]` | View recent moderation actions (Pro only) |
| `/schedule HH:MM [msg]` | Schedule a daily recurring message in UTC (Pro only) |
| `/schedules` | View all active scheduled messages (Pro only) |
| `/delschedule [ID]` | Remove a scheduled message (Pro only) |
| `/welcome [msg]` | Set custom welcome message with variables (Pro only) |
| `/welcomeoff` | Disable custom welcome message (Pro only) |
| `/activate [KEY]` | Activate Pro subscription |
| `/keygen [DAYS]` | Generate activation key (admin only) |
| `/extend [UID] [DAYS]` | Renew a user's Pro (admin only) |

---

## Pricing

```bash

150.00 Rs - 1 Month Bundle

300.00 Rs - 3 Month Bundle

```

## 📦 Architecture

```
projectmonolith/
├── main.py                    # FastAPI gateway + rate limiter
├── run_crypto_bot.py          # Crypto bot lifecycle + commands
├── run_ai_bot.py              # AI bot lifecycle
├── run_group_bot.py           # Group bot lifecycle
├── core/
│   ├── config.py              # Environment variable loader
│   ├── logger.py              # Colored logging
│   └── task_manager.py        # Background task utilities
├── zenith_crypto_bot/
│   ├── models.py              # DB models (User, Subscription, PriceAlert, etc.)
│   ├── repository.py          # Data access layer
│   ├── market_service.py      # External APIs (CoinGecko, GoPlus, Etherscan)
│   ├── pro_handlers.py        # Pro feature command handlers
│   └── ui.py                  # Telegram keyboard layouts
├── zenith_ai_bot/             # AI bot module
├── zenith_group_bot/          # Group moderation module
└── utils/                     # Shared utilities
```

---

© 2026 [Zenith Open Source Projects](https://zenithopensourceprojects.vercel.app/). All Rights Reserved.  
Zenith is a Open Source Project Idea's by @roshhellwett

## 📄 License

MIT
