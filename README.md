# FPL Guru (`fpl-guru`)

**Your personal AI Fantasy Premier League coach — built for real FPL managers, no coding required.**

Paste your FPL team link and ask anything in plain **English, Bangla, or Banglish**. FPL Guru checks live Premier League data before every answer so you get real numbers, real injury news, and smarter moves — never guesswork.

---

## What It Helps You Win

- **Weekly Transfers & Captaincy:** Tells you who to buy, who to bench, who to captain, and whether a `-4` hit is actually worth it.
- **Chip Timing Planner:** Finds the best Gameweeks to play your **Bench Boost, Free Hit, Triple Captain, and Wildcard** before they expire.
- **Tonight's Price Rise & Fall Alerts:** Warns you before players in your squad drop in value or your targets go up tonight.
- **Verified Injury & Press News:** Checks official FPL flags alongside manager press conferences and major sports news — no fake rumors.
- **Beat Your Mini-League & Rivals:** Compares your squad and remaining chips against the leaders in your friends/office league (or your weekly H2H opponent) and shows how to catch or stay ahead of them.
- **New Season (GW1) Setup:** Helps you build a balanced Gameweek 1 squad from scratch.

---

## 2-Minute Setup (No Coding Needed)

### Step 1: Open Your AI Assistant
Use any AI assistant that supports skills, such as **Antigravity, Claude Code, Cursor, Codex, or Gemini CLI**.

### Step 2: Copy & Paste This One Message
Open a new chat in your AI assistant and send this exact message:

> **Install the `fpl-guru` skill globally from `https://github.com/tawhid37/fpl-guru` for me.**

That's it! Your AI assistant will download and set everything up automatically.

*(Prefer doing it manually? Click the green **`Code` → `Download ZIP`** button at the top of this page, unzip it, and place the `fpl-guru` folder inside your tool's global skills folder — see [Manual & Developer Install](#for-developers--manual-install) below.)*

### Step 3: Copy Your FPL Team Link (30 Seconds)
1. Log in at [fantasy.premierleague.com](https://fantasy.premierleague.com/).
2. Click the **Points** (or **Pick Team**) tab.
3. Copy the web address from your browser's address bar. It looks like:
   `https://fantasy.premierleague.com/en/entry/123456/event/1`
4. Paste that link in chat — FPL Guru automatically finds your Team ID and remembers it for future chats.

---

## Ready-to-Use Prompts (Just Copy & Paste)

### English Examples
- *"Check my FPL team: `https://fantasy.premierleague.com/en/entry/123456/event/1` — what's my best move and captain this week?"*
- *"Which Gameweeks are best for my remaining Bench Boost and Free Hit?"*
- *"Which players are about to rise or fall in price tonight?"*
- *"Will Saka play this weekend? Check the latest injury and press conference news."*
- *"How can I catch #1 in my mini-league over the next 4 Gameweeks?"*
- *"Compare my team with rival `987654` for this week."*
- *"Help me build an optimal Gameweek 1 squad for the new season."*

### Bangla / Banglish Examples (বাংলা / বাংলিশ)
- *"Amar FPL team check koro: `https://fantasy.premierleague.com/en/entry/123456/event/1` — ei week-e best transfer ar captain ke hobe?"*
- *"Ajke raate kon player-er price barar ba komar chance ache?"*
- *"আমার মিনি-লিগের #১ জনকে কীভাবে বিট করবো আগামী ৪ গেমউইকে?"*

> **Note:** FPL Guru is built strictly for Fantasy Premier League and Premier League topics. If you ask something unrelated, it will politely let you know what it can help with instead of giving off-topic guesses.

---

## For Developers & Manual Install

<details>
<summary>Click to expand CLI commands, token optimization details, and repo structure</summary>

### Manual / CLI Installation
- **Cross-agent CLI (`npx skills`):**
  ```bash
  npx skills add tawhid37/fpl-guru
  ```
- **Windows (PowerShell):**
  ```powershell
  git clone https://github.com/tawhid37/fpl-guru "$HOME\.gemini\config\skills\fpl-guru"
  # For Claude Code: "$HOME\.claude\skills\fpl-guru"
  ```
- **Mac / Linux:**
  ```bash
  git clone https://github.com/tawhid37/fpl-guru ~/.gemini/config/skills/fpl-guru
  # For Claude Code: ~/.claude/skills/fpl-guru
  ```

### Technical Highlights
- **Zero Dependencies & Zero API Keys:** Runs on Python 3 standard library (`scripts/fpl_cli.py`) using public FPL APIs, `livefpl.us`, Fantasy Football Scout SSR pages, and BBC/Guardian/Sky RSS feeds. Falls back to direct HTTP/web lookups if Python is not installed.
- **90%+ Token Reduction:** Compresses ~2MB+ raw `bootstrap-static` JSON into compact 20–40 line Markdown summaries with a 30-minute local cache (`~/.fpl-guru/cache/`).
- **Private Local State:** Your saved Team ID, playstyle, and cache stay locally in `~/.fpl-guru/profile.json`—never inside the skill repo.
- **Progressive Disclosure:** Tight `SKILL.md` router loads specialized `references/` files only for the active branch.

### Repository Structure
```text
fpl-guru/
├── LICENSE                     # MIT License
├── README.md                   # User-friendly setup & developer reference
├── SKILL.md                    # Core low-token router, scope guardrails & workflow
├── references/
│   ├── data-protocols.md       # Price, injury, league & API verification rules
│   ├── strategy-and-chips.md   # Chip timing, DEFCON/BPS meta & transfer EV math
│   └── new-season-guide.md     # GW1 squad building & early-season roadmap
└── scripts/
    └── fpl_cli.py              # Zero-dependency Python 3 data & compression engine
```

</details>

---

## Author & License

Created by **Tawhid Sultan** — [GitHub (@tawhid37)](https://github.com/tawhid37) · [LinkedIn](https://www.linkedin.com/in/tawhid37/)

Licensed under the [MIT License](LICENSE).
