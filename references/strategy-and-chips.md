# Strategy, Chips & Optimization Playbook

Adapt every recommendation to the user's **goal** (`overall` vs `league` vs `h2h`) and **playstyle** (`safe` vs `balanced` vs `aggressive`), using verified season rules (`~/.fpl-guru/season_rules.md` or live check).

---

## 1. Chip Optimization Rules

- **Half-Season Split (2025/26+ format):** Track First-Half chips (`GW1–GW19` deadline) separately from Second-Half chips (`GW20–GW38`). Unplayed First-Half chips expire—schedule them proactively rather than hoarding for non-existent GW1–19 doubles.
- **Bench Boost (BB):**
  - Target the GW where **15/15 players are nailed starters**, **0 flagged GKs**, and Bench 4 have low FDR (`<= 3`, ideally home games or high-DEFCON away fixtures).
  - Avoid activating BB during extreme 3-games-in-7-days festive rotation unless all bench assets are heavy minutes locks.
- **Free Hit (FH):**
  - **With Blank/Double GWs:** Attack a major BGW (field 11 players without wrecking long-term structure) or a stacked DGW.
  - **Without BGW/DGW (e.g., First Half):** Target the GW with the **highest contrast**—where the user's current squad has `5+` hard fixtures (`FDR >= 4`) while 2–3 unowned teams have `FDR 2` home bankers.
  - Remember: FH preserves saved FTs (up to 5) into the next GW, though you do not gain `+1` FT for the FH week itself.
- **Triple Captain (TC):**
  - Prioritize DGW premium talismans on penalties/90-min locks; if no DGW exists before GW19, target a high-xGI home fixture (`FDR 2`) against a leaky defense.
- **Wildcard (WC):**
  - Trigger on **fixture swings + 3+ structural problems** (dead spots, injured premiums, wrong price structure). Pair with `chips` analysis to set up an upcoming BB window.

---

## 2. Transfer, Hit (`-4`) & Roll-FT Math

- **Value of 1 FT:** Rolling a FT (banking up to **5 FT**) gives mini-Wildcard flexibility; avoid sideways luxury moves.
- **When a `-4` Hit is +EV:**
  - Taking out an unavailable/benched player (`0–1` pt) for a nailed starter with strong 3–4 GW fixtures (`>= +4` expected gain over the next 2–3 GWs).
  - Dodging a `£0.2m` price swing that would permanently price out a core target.
  - Avoid `-4` hits solely to chase last week's points when the outgoing player is still nailed with decent fixtures.

---

## 3. Scoring Meta (DEFCON, BPS & Captaincy)

- **DEFCON Floor:** High-CBIT centre-backs (`10` CBIT = `+2` pts) and high-CBIRT central/holding mids (`12` CBIRT = `+2` pts) provide reliable 4-pt floors—ideal for budget enablers and Bench Boost slots.
- **BPS Profile:** Check current season BPS weights (in 2026/27: no penalty for being tackled boosts high-dribble wingers/mids, while balanced CB weights favor GKs, attacking full-backs, and forwards).
- **Captaincy:**
  - When defending rank/league lead: stick close to high-EO template captains unless a clear fixture gap exists.
  - When chasing: target high-xGI differentials in `FDR 2` matchups when the template captain faces `FDR 4–5` away.
