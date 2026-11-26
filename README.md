# FPL Guru (`fpl-guru`)

An open-source, low-token **Fantasy Premier League (FPL)** AI strategist skill compatible with **Antigravity, Claude Code, Cursor, Codex, and Gemini CLI**.

- **Zero API keys, zero `pip install`:** Uses official public FPL APIs, LiveFPL, Fantasy Football Scout, and Tier-1 football RSS feeds via Python 3's built-in standard library.
- **No-Bluff Live Data:** Never hallucinates prices, injuries, or fixtures—always checks live sources and cites exact URLs + timestamps.
- **90%+ Token Optimization:** Compresses 2MB+ raw FPL JSON into compact tables with a 30-minute local cache (`~/.fpl-guru/cache/`).
- **Focused Scope:** Built exclusively for FPL and Premier League strategy—if asked off-topic questions, it stays grounded and clearly explains what it can help with.

---

## What FPL Guru Can Do

- **Weekly Squad Audit & Transfers:** Evaluates your 15-man squad, selling prices, banked Free Transfers, fixture swings, DEFCON/BPS potential, and captaincy.
- **Chip Timing Planner:** Finds the best Gameweeks for **Bench Boost, Free Hit, Triple Captain, and Wildcard** (tracking half-season chip expiry automatically).
- **Tonight's Price Changes & Predictions:** Checks `livefpl.us` + official `bootstrap-static` (with fallbacks) and flags players in your squad close to rising or falling.
- **Official-First Injury & Press Checks:** Combines FPL flags (`news_added` timestamps) with Fantasy Football Scout team news and BBC/Guardian/Sky RSS updates.
- **Mini-League & Rival Domination:** Compares your squad & remaining chips against your Classic mini-league's top contenders, specific rival IDs, or this week's **H2H opponent**.
- **New Season (GW1) Blueprint:** Helps build a flexible GW1 draft, plan early FT banking, and spot early Wildcard triggers.

---

## Super-Easy Install (No Coding Experience Needed)

### Option 1: Ask Your AI Assistant to Install It (Easiest)
Open **Antigravity, Claude Code, Cursor, Codex, or Gemini CLI** and paste this one message:

> **Install the `fpl-guru` skill globally from `https://github.com/tawhid37/fpl-guru` into my global skills folder.**

### Option 2: One-Line Terminal Install
- **Cross-agent CLI (`npx skills`):**
  ```bash
  npx skills add tawhid37/fpl-guru
  ```
- **Windows (PowerShell):**
  ```powershell
  git clone https://github.com/tawhid37/fpl-guru "$HOME\.gemini\config\skills\fpl-guru"
  # For Claude Code, replace the path with: "$HOME\.claude\skills\fpl-guru"
  ```
- **Mac / Linux:**
  ```bash
  git clone https://github.com/tawhid37/fpl-guru ~/.gemini/config/skills/fpl-guru
  # For Claude Code, replace the path with: ~/.claude/skills/fpl-guru
  ```

### Prerequisite Check (Optional)
FPL Guru works fastest with **Python 3** (no external packages needed). To check if Python is installed, run `python --version` (Windows) or `python3 --version` (Mac/Linux). If Python isn't installed, the skill automatically falls back to direct HTTP/web lookups.

---

## How to Find Your FPL Team Link or ID (30 Seconds)

1. Open [fantasy.premierleague.com](https://fantasy.premierleague.com/) and log in.
2. Click the **Points** (or **Pick Team**) tab.
3. Copy the URL from your browser's address bar — it looks like:
   `https://fantasy.premierleague.com/en/entry/123456/event/1`
4. Just paste that full link (or just the number `123456`) in chat—FPL Guru extracts your Team ID and remembers it locally in `~/.fpl-guru/profile.json`.

---

## How to Use (Speak Any Language!)

You don't need commands or jargon. Just talk naturally in **English, Bangla, Banglish**, or any language you prefer:

### English Examples
- *"Check my FPL team: `https://fantasy.premierleague.com/en/entry/123456/event/1` — what's my best transfer and captain this week?"*
- *"Which Gameweeks are best for my remaining Bench Boost and Free Hit?"*
- *"Who is rising or falling in price tonight?"*
- *"Check the latest injury news for Saka before the deadline."*
- *"How do I climb to #1 in my mini-league over the next 4 GWs?"*
- *"Compare my squad against rival `987654` for this Gameweek."*
- *"Help me build an optimal GW1 squad for the new season."*

### Bangla / Banglish Examples (বাংলা / বাংলিশ)
- *"Amar FPL team check koro: `https://fantasy.premierleague.com/en/entry/123456/event/1` — ei week-e best move ar captain ke hobe?"*
- *"Ajke raate kon player-er price barar ba komar chance ache?"*
- *"আমার মিনি-লিগের #১ জনকে কীভাবে বিট করবো আগামী ৪ গেমউইকে?"*

---

## Repository Structure

```text
fpl-guru/
├── LICENSE                     # MIT License
├── README.md                   # Setup guide & prompt examples
├── SKILL.md                    # Core low-token router, scope rules & workflow
├── references/
│   ├── data-protocols.md       # Price, injury, league & API verification rules
│   ├── strategy-and-chips.md   # Chip timing, DEFCON/BPS meta & transfer EV math
│   └── new-season-guide.md     # GW1 squad building & early-season roadmap
└── scripts/
    └── fpl_cli.py              # Zero-dependency Python 3 data & compression engine
```

---

## Author & License

Created by **Tawhid Sultan** — [GitHub (@tawhid37)](https://github.com/tawhid37) · [LinkedIn](https://www.linkedin.com/in/tawhid37/)

Licensed under the [MIT License](LICENSE).
