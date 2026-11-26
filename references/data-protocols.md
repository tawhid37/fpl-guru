# Live Data Protocols (No-Bluff Rules)

Prefer running `scripts/fpl_cli.py` first—it executes these exact chains while keeping raw JSON/HTML out of context. Only fetch manually via HTTP/web search/browser if `python` is unavailable or the script flags stale/missing data.

---

## 1. FPL Price Changes & Predictions Source Priority

When asked about FPL player prices, recent price changes, or tonight's rise/fall predictions, fetch live data in this strict priority order:

1. **Primary Predictor (JSON):** `https://livefpl.us/api/prices.json`
   - Parse `name`, `team`, `type`, `cost`, `progress`, `progress_tonight`, and `per_hour`.
   - Use `progress_tonight` / `progress` to identify likely risers (approaching/exceeding `+100%` / `1.0`) and fallers (approaching/exceeding `-100%` / `-1.0`).
2. **Official Ground Truth (JSON):** `https://fantasy.premierleague.com/api/bootstrap-static/`
   - Check `elements[]` (`web_name`, `now_cost / 10`, `cost_change_event`, `cost_change_start`, `transfers_in_event`, `transfers_out_event`) to confirm exact current prices and already-confirmed price changes.
3. **Fallback 1 (if LiveFPL fails):** `https://fpl.page/price-changes` — extract price change predictions from HTML.
4. **Fallback 2 (if Fallback 1 fails):** Try `https://fplstats.co/` first, then `https://fpledits.com/` (root URLs, not `/price-changes`).
5. **Output Rules:**
   - Cite which source URL(s) returned the data and the UTC timestamp.
   - Explicitly separate **Confirmed Prices** (`bootstrap-static`) from **Predicted Changes** (`livefpl.us` or fallbacks).
   - If all prediction sources fail, state that predictions could not be retrieved and show only confirmed `bootstrap-static` changes (or stop if that fails too).

---

## 2. Player Injury & Availability Lookup Protocol

Never rely solely on the FPL percentage flag. Follow this exact order:

1. **Official FPL Status + Timestamp (JSON):** `https://fantasy.premierleague.com/api/bootstrap-static/`
   - Read `status` (`a`=available, `d`=doubtful, `i`=injured, `s`=suspended, `u`=unavailable, `n`=not in squad), `chance_of_playing_this_round`, `chance_of_playing_next_round`, `news`, and `news_added`.
   - Check `news_added` age to judge freshness.
2. **Official PL & Manager Press Conference Updates:**
   - **Browser tool (if available):** `https://www.premierleague.com/en/latest-player-injuries` (JS-rendered; do not rely on raw curl/fetch).
   - **Direct SSR Team News (works with HTTP fetch):** `https://www.fantasyfootballscout.co.uk/fantasy-football-injuries/` and `https://www.fantasyfootballscout.co.uk/team-news/` for manager quotes and return timelines.
3. **Tier-1 Breaking News (when `news_added` is >24–48h old or a match/presser just happened):**
   - RSS feeds (fast XML with `<pubDate>`):
     - `https://feeds.bbci.co.uk/sport/football/rss.xml`
     - `https://www.theguardian.com/football/premierleague/rss`
     - `https://www.skysports.com/rss/12040`
   - Or targeted web search: `"<Player Name>" "<Club/Manager Name>" injury update press conference` (`site:premierleague.com` or official club news).
   - Note: `https://www.premierinjuries.com/injury-table.php` returns `403` to automated HTTP requests—access only via web search or browser.
4. **Output Rules:**
   - State both: (a) Official FPL `status`, `%`, `news`, and `news_added` date; and (b) any newer manager quote/news with exact date and source URL.
   - Highlight discrepancies if a newer presser contradicts the FPL flag.
   - If no update is newer than `news_added`, say so clearly—never invent return dates or fitness percentages.

---

## 3. Mini-League, Rival & H2H Comparison Protocol

- **Private Leagues Discovery:** `https://fantasy.premierleague.com/api/entry/{team_id}/` lists `leagues.classic` (`league_type == "x"`) and `leagues.h2h`. Let the user pick by league name rather than hunting IDs.
- **Classic Leagues:** Fetch `https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/`. Sample **Top 3–5 + immediate neighbors around the user** (max 6 rivals) to avoid rate limits and token bloat.
- **H2H Leagues:** Fetch `https://fantasy.premierleague.com/api/leagues-h2h-matches/league/{league_id}/?event={gw}` to isolate that exact week's opponent.
- **Decision Lens:**
  - **Chasing (`-15+ pts`):** Identify high-upside **Differentials** rivals lack + split **Captaincy** from the leader's template captain.
  - **Protecting a Lead (`+15+ pts`):** Identify high-ownership **Shield Threats** among Top 3–5 rivals and cover key captaincy EO.
  - **Chip Edge:** Compare remaining chips vs rivals (e.g., leverage unplayed BB/FH/TC before half-season expiry).

---

## 4. Public FPL API Caveats (Verify Before Tight Moves)

- **Selling Prices (`*`):** Public `/transfers/` gives exact buy price for transferred-in players (`buy + floor((now - buy)/2)`), but players held since GW1 or a Wildcard lack an explicit buy record—ask the user to verify in the FPL app whenever a move has `£0.0–0.3m` margin.
- **Free Transfers:** `fpl_cli.py` estimates FTs from `/history/` and chip history (5 FT max, WC/FH preserve FTs without adding `+1`). Confirm with the user before recommending a multi-FT combo or `-4` hit.
