#!/usr/bin/env python3
"""
FPL Guru CLI — Zero-dependency, token-optimized Fantasy Premier League analyzer.
Uses only Python 3 standard library. Caches static API responses locally in ~/.fpl-guru/cache/.
"""

import argparse
import datetime
import json
import math
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

USER_AGENT = "Mozilla/5.0 (compatible; FPLGuruSkill/1.0)"
FPL_BASE = "https://fantasy.premierleague.com/api"
LIVEFPL_PRICES_URL = "https://livefpl.us/api/prices.json"
FPL_PAGE_PRICES_URL = "https://fpl.page/price-changes"
FPLSTATS_URL = "https://fplstats.co/"
FPLEDITS_URL = "https://fpledits.com/"
FFS_INJURIES_URL = "https://www.fantasyfootballscout.co.uk/fantasy-football-injuries/"
FFS_TEAM_NEWS_URL = "https://www.fantasyfootballscout.co.uk/team-news/"
RSS_FEEDS = [
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ("The Guardian", "https://www.theguardian.com/football/premierleague/rss"),
    ("Sky Sports", "https://www.skysports.com/rss/12040"),
]

HOME_DIR = Path.home() / ".fpl-guru"
CACHE_DIR = HOME_DIR / "cache"
PROFILE_PATH = HOME_DIR / "profile.json"
DEFAULT_TTL_SECONDS = 1800  # 30 minutes


def ensure_dirs():
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def utc_now_str():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def fetch_raw(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_json_cached(url, cache_key, ttl=DEFAULT_TTL_SECONDS, force_refresh=False):
    ensure_dirs()
    safe_key = re.sub(r"[^a-zA-Z0-9_.-]+", "_", cache_key)
    cpath = CACHE_DIR / f"{safe_key}.json"
    if not force_refresh and cpath.exists():
        age = time.time() - cpath.stat().st_mtime
        if age < ttl:
            try:
                return json.loads(cpath.read_text(encoding="utf-8")), True
            except Exception:
                pass
    data = json.loads(fetch_raw(url))
    cpath.write_text(json.dumps(data), encoding="utf-8")
    return data, False


def parse_team_id(raw_value):
    if raw_value is None:
        return None
    s = str(raw_value).strip()
    m = re.search(r"/entry/(\d+)", s)
    if m:
        return int(m.group(1))
    if s.isdigit():
        return int(s)
    raise ValueError(f"Could not extract numeric Team ID from '{raw_value}'")


def load_profile():
    ensure_dirs()
    if PROFILE_PATH.exists():
        try:
            return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"default_team": None, "teams": {}}


def save_profile(profile):
    ensure_dirs()
    PROFILE_PATH.write_text(json.dumps(profile, indent=2), encoding="utf-8")


def resolve_team_id(team_arg, alias="default"):
    if team_arg:
        return parse_team_id(team_arg)
    prof = load_profile()
    teams = prof.get("teams", {})
    if alias in teams and teams[alias].get("team_id"):
        return int(teams[alias]["team_id"])
    if prof.get("default_team"):
        return int(prof["default_team"])
    raise ValueError("No Team ID provided and none saved in ~/.fpl-guru/profile.json. Pass --team <id_or_url>.")


def get_bootstrap(refresh=False):
    boot, _ = fetch_json_cached(f"{FPL_BASE}/bootstrap-static/", "bootstrap_static", ttl=1800, force_refresh=refresh)
    return boot


def get_fixtures(refresh=False):
    fix, _ = fetch_json_cached(f"{FPL_BASE}/fixtures/", "fixtures", ttl=1800, force_refresh=refresh)
    return fix


def get_current_and_next_gw(boot):
    events = boot.get("events", [])
    curr = next((e for e in events if e.get("is_current")), None)
    nxt = next((e for e in events if e.get("is_next")), None)
    if not curr:
        finished = [e for e in events if e.get("finished")]
        curr = finished[-1] if finished else (events[0] if events else None)
    return curr, nxt


def detect_season_label(boot):
    events = boot.get("events", [])
    if not events:
        return "unknown"
    first_dl = events[0].get("deadline_time", "")
    m = re.match(r"(\d{4})-", first_dl)
    if m:
        yr = int(m.group(1))
        return f"{yr}/{str(yr + 1)[-2:]}"
    return "unknown"


def estimate_free_transfers(history_rows, chips):
    """
    Estimate available Free Transfers for the upcoming GW using transfer history + WC/FH rules.
    Under 2024/25+ rules, max banked FTs = 5; playing WC or FH preserves saved FTs without adding +1.
    """
    chip_events = {c["event"]: c["name"] for c in chips if c.get("event")}
    ft = 1
    for row in history_rows:
        ev = row["event"]
        chip = chip_events.get(ev)
        if chip in ("wildcard", "freehit"):
            continue
        used = row.get("event_transfers", 0)
        remaining = max(0, ft - used)
        ft = min(5, remaining + 1)
    return ft


def compute_selling_prices(picks, transfers, elements_map):
    """
    Compute exact selling price where last transfer-in price is known.
    Returns dict: element_id -> (sell_cost_tenths, exact_bool, bought_tenths_or_None)
    """
    bought = {}
    # transfers API is newest-first; iterate oldest-first
    for tr in reversed(transfers):
        bought[tr["element_in"]] = tr["element_in_cost"]

    result = {}
    for pk in picks:
        eid = pk["element"]
        now_c = elements_map[eid]["now_cost"]
        if eid in bought:
            b = bought[eid]
            if now_c > b:
                sell = b + (now_c - b) // 2
            else:
                sell = now_c
            result[eid] = (sell, True, b)
        else:
            result[eid] = (now_c, False, None)
    return result


def build_fixture_lookup(fixtures, teams_map):
    lookup = {}
    for f in fixtures:
        ev = f.get("event")
        if not ev:
            continue
        h, a = f["team_h"], f["team_a"]
        lookup.setdefault(h, {}).setdefault(ev, []).append((teams_map[a]["short_name"], True, f["team_h_difficulty"]))
        lookup.setdefault(a, {}).setdefault(ev, []).append((teams_map[h]["short_name"], False, f["team_a_difficulty"]))
    return lookup


def fmt_gw_fixtures(fix_list):
    if not fix_list:
        return "BLANK"
    return "+".join(f"{opp}({'H' if h else 'A'},{fdr})" for opp, h, fdr in fix_list)


def remaining_half_chips(chips_used, current_gw):
    """FPL 2-half chip format: 1 set (WC, FH, TC, BB) in GW1-19, fresh set in GW20-38."""
    all_chips = ["wildcard", "freehit", "3xc", "bboost"]
    if current_gw <= 19:
        used_half = {c["name"] for c in chips_used if c.get("event", 0) <= 19}
        window = "GW1-19 (expires GW19 deadline)"
    else:
        used_half = {c["name"] for c in chips_used if c.get("event", 0) >= 20}
        window = "GW20-38"
    left = [c for c in all_chips if c not in used_half]
    return left, sorted(used_half), window


# ---------- Subcommands ----------

def cmd_profile(args):
    prof = load_profile()
    if args.set_team:
        tid = parse_team_id(args.set_team)
        entry, _ = fetch_json_cached(f"{FPL_BASE}/entry/{tid}/", f"entry_{tid}", ttl=300, force_refresh=True)
        alias = args.alias or "default"
        existing = prof.get("teams", {}).get(alias, {})
        prof.setdefault("teams", {})[alias] = {
            "team_id": tid,
            "team_name": entry.get("name"),
            "manager": f"{entry.get('player_first_name', '')} {entry.get('player_last_name', '')}".strip(),
            "playstyle": args.style or existing.get("playstyle", "balanced"),
            "goal": args.goal or existing.get("goal", "overall"),
            "tracked_league_id": int(args.league) if args.league else existing.get("tracked_league_id"),
            "rivals": existing.get("rivals", []),
        }
        if alias == "default" or not prof.get("default_team"):
            prof["default_team"] = tid
        save_profile(prof)
        print(f"Saved profile '{alias}': Team {tid} ({entry.get('name')}) | style={prof['teams'][alias]['playstyle']} | goal={prof['teams'][alias]['goal']}")
        return

    if args.style or args.goal or args.league or args.add_rival:
        alias = args.alias or "default"
        if alias not in prof.get("teams", {}):
            raise ValueError(f"Profile alias '{alias}' not found. Run with --set-team first.")
        t = prof["teams"][alias]
        if args.style:
            t["playstyle"] = args.style
        if args.goal:
            t["goal"] = args.goal
        if args.league:
            t["tracked_league_id"] = int(args.league)
        if args.add_rival:
            rid = parse_team_id(args.add_rival)
            if rid not in t.setdefault("rivals", []):
                t["rivals"].append(rid)
        save_profile(prof)
        print(json.dumps(prof, indent=2))
        return

    print(json.dumps(prof, indent=2))


def cmd_brief(args):
    tid = resolve_team_id(args.team, args.alias or "default")
    boot = get_bootstrap(refresh=args.refresh)
    fixtures = get_fixtures(refresh=args.refresh)
    entry, _ = fetch_json_cached(f"{FPL_BASE}/entry/{tid}/", f"entry_{tid}", ttl=300, force_refresh=args.refresh)
    hist, _ = fetch_json_cached(f"{FPL_BASE}/entry/{tid}/history/", f"hist_{tid}", ttl=300, force_refresh=args.refresh)
    transfers, _ = fetch_json_cached(f"{FPL_BASE}/entry/{tid}/transfers/", f"tr_{tid}", ttl=300, force_refresh=args.refresh)

    curr, nxt = get_current_and_next_gw(boot)
    curr_gw = curr["id"] if curr else (entry.get("current_event") or 1)
    picks_data, _ = fetch_json_cached(
        f"{FPL_BASE}/entry/{tid}/event/{curr_gw}/picks/", f"picks_{tid}_{curr_gw}", ttl=300, force_refresh=args.refresh
    )

    teams_map = {t["id"]: t for t in boot["teams"]}
    el_map = {e["id"]: e for e in boot["elements"]}
    pos_map = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
    fix_lookup = build_fixture_lookup(fixtures, teams_map)

    season = detect_season_label(boot)
    chips_used = hist.get("chips", [])
    left_chips, used_half, chip_win = remaining_half_chips(chips_used, nxt["id"] if nxt else curr_gw)
    est_ft = estimate_free_transfers(hist.get("current", []), chips_used)
    pending_next_trs = [t for t in transfers if nxt and t.get("event") == nxt["id"]]
    sell_map = compute_selling_prices(picks_data["picks"], transfers, el_map)

    # Optional LiveFPL quick check for squad price risk
    livefpl_map = {}
    try:
        lp, _ = fetch_json_cached(LIVEFPL_PRICES_URL, "livefpl_prices", ttl=900, force_refresh=args.refresh)
        if isinstance(lp, dict):
            livefpl_map = lp
    except Exception:
        pass

    print(f"# FPL Brief — {entry.get('name')} (ID: {tid}) | Season {season}")
    print(f"Manager: {entry.get('player_first_name')} {entry.get('player_last_name')} | Points: {entry.get('summary_overall_points')} | OR: {entry.get('summary_overall_rank'):,}")
    bank = (entry.get("last_deadline_bank") or 0) / 10
    val = (entry.get("last_deadline_value") or 0) / 10
    print(f"Bank: £{bank:.1f}m | Value: £{val:.1f}m | Est. FT (pre-pending): {est_ft} | Pending GW{nxt['id'] if nxt else '?'} transfers: {len(pending_next_trs)}")
    if nxt:
        print(f"Next Deadline: GW{nxt['id']} — {nxt.get('deadline_time')} | Current GW{curr_gw} finished={curr.get('finished') if curr else '?'}")
    print(f"Chips ({chip_win}): Left={left_chips or 'None'} | Used={used_half or 'None'}")

    start_gw = nxt["id"] if nxt else curr_gw + 1
    gw_cols = [start_gw, start_gw + 1, start_gw + 2]
    print("\n## Squad (15)")
    print("| # | Pos | Player | Team | Now | Sell | Form | xGI | DEFCON | Status | Next 3 | PriceProg |")
    print("|---:|:---:|:---|:---:|---:|---:|---:|---:|---:|:---|:---|---:|")
    unverified_sell = []
    for pk in picks_data["picks"]:
        el = el_map[pk["element"]]
        tm = teams_map[el["team"]]["short_name"]
        sell_c, exact_b, _ = sell_map[pk["element"]]
        if not exact_b:
            unverified_sell.append(el["web_name"])
        sell_str = f"£{sell_c/10:.1f}" + ("" if exact_b else "*")
        role = " (C)" if pk["is_captain"] else (" (VC)" if pk["is_vice_captain"] else "")
        slot = f"B{pk['position']-11}" if pk["position"] > 11 else str(pk["position"])
        ch = el.get("chance_of_playing_next_round")
        st = el["status"] if ch is None else f"{el['status']}({ch}%)"
        if el.get("news"):
            st += f": {el['news'][:35]}"
        n3 = " / ".join(fmt_gw_fixtures(fix_lookup.get(el["team"], {}).get(g, [])) for g in gw_cols)
        lp_row = livefpl_map.get(str(el["id"]))
        prog = f"{lp_row.get('progress_tonight', 0)*100:+.0f}%" if lp_row else "-"
        print(f"| {slot} | {pos_map[el['element_type']]} | {el['web_name']}{role} | {tm} | £{el['now_cost']/10:.1f} | {sell_str} | {el['form']} | {el['expected_goal_involvements']} | {el.get('defensive_contribution', 0)} | {st} | {n3} | {prog} |")

    if unverified_sell:
        print(f"\n*Note: Sell prices marked `*` ({', '.join(unverified_sell)}) are held since GW1/Wildcard so original buy price isn't in public transfers API; verify in FPL app if budget is tight by £0.1–0.3m.*")

    priv_classic = [l for l in entry.get("leagues", {}).get("classic", []) if l.get("league_type") == "x"]
    priv_h2h = entry.get("leagues", {}).get("h2h", [])
    if priv_classic or priv_h2h:
        print("\n## Private Leagues")
        for l in priv_classic[:8]:
            print(f"- [Classic] {l['name']} (ID: `{l['id']}`) | Rank: {l.get('entry_rank')} (prev {l.get('entry_last_rank')})")
        for l in priv_h2h[:5]:
            print(f"- [H2H] {l['name']} (ID: `{l['id']}`) | Rank: {l.get('entry_rank')}")
    print(f"\nSource: {FPL_BASE}/entry/{tid}/ (+ bootstrap-static, fixtures) | Fetched: {utc_now_str()}")


def cmd_targets(args):
    boot = get_bootstrap(refresh=args.refresh)
    fixtures = get_fixtures(refresh=args.refresh)
    _, nxt = get_current_and_next_gw(boot)
    start_gw = nxt["id"] if nxt else 1
    gw_cols = list(range(start_gw, start_gw + args.gw_window))

    teams_map = {t["id"]: t for t in boot["teams"]}
    fix_lookup = build_fixture_lookup(fixtures, teams_map)
    pos_rev = {"GK": 1, "DEF": 2, "MID": 3, "FWD": 4}
    pos_id = pos_rev[args.pos.upper()]
    excl = {x.strip().upper() for x in (args.team_exclude or "").split(",") if x.strip()}
    max_cost = int(round(args.max_price * 10)) if args.max_price else 999

    scored = []
    for el in boot["elements"]:
        if el["element_type"] != pos_id:
            continue
        if el["status"] not in ("a", "d") or el["now_cost"] > max_cost:
            continue
        if el["minutes"] < args.min_minutes:
            continue
        t_short = teams_map[el["team"]]["short_name"]
        if t_short in excl:
            continue

        fdrs = []
        n_str = []
        for g in gw_cols:
            fl = fix_lookup.get(el["team"], {}).get(g, [])
            n_str.append(fmt_gw_fixtures(fl))
            fdrs.extend([x[2] for x in fl] if fl else [5])
        avg_fdr = sum(fdrs) / max(1, len(fdrs))
        form = float(el["form"] or 0)
        ppg = float(el["points_per_game"] or 0)
        xgi = float(el["expected_goal_involvements"] or 0)
        defcon = float(el.get("defensive_contribution") or 0)
        # Balanced fixture-adjusted score
        fdr_bonus = (3.3 - avg_fdr) * 1.5
        score = form * 0.5 + ppg * 0.4 + xgi * 0.2 + (defcon / 40.0) + fdr_bonus
        scored.append((score, avg_fdr, el, t_short, " / ".join(n_str[:4])))

    scored.sort(key=lambda x: x[0], reverse=True)
    print(f"# Top {args.pos.upper()} Targets (<= £{max_cost/10:.1f}m, mins >= {args.min_minutes}, next {args.gw_window} GWs from GW{start_gw})")
    print("| Player | Team | Cost | Form | PPG | Pts | xGI | DEFCON | AvgFDR | Sel% | Status | Next 4 |")
    print("|:---|:---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---|")
    for _, avg_fdr, el, t_short, n4 in scored[: args.limit]:
        print(f"| {el['web_name']} | {t_short} | £{el['now_cost']/10:.1f} | {el['form']} | {el['points_per_game']} | {el['total_points']} | {el['expected_goal_involvements']} | {el.get('defensive_contribution', 0)} | {avg_fdr:.2f} | {el['selected_by_percent']}% | {el['status']} | {n4} |")
    print(f"\nSource: {FPL_BASE}/bootstrap-static/ & /fixtures/ | Fetched: {utc_now_str()}")


def cmd_chips(args):
    tid = resolve_team_id(args.team, args.alias or "default")
    boot = get_bootstrap(refresh=args.refresh)
    fixtures = get_fixtures(refresh=args.refresh)
    curr, nxt = get_current_and_next_gw(boot)
    curr_gw = curr["id"] if curr else 1
    start_gw = args.from_gw or (nxt["id"] if nxt else curr_gw + 1)
    end_gw = args.to_gw or (19 if start_gw <= 19 else 38)

    picks_data, _ = fetch_json_cached(f"{FPL_BASE}/entry/{tid}/event/{curr_gw}/picks/", f"picks_{tid}_{curr_gw}", ttl=300, force_refresh=args.refresh)
    hist, _ = fetch_json_cached(f"{FPL_BASE}/entry/{tid}/history/", f"hist_{tid}", ttl=300, force_refresh=args.refresh)
    teams_map = {t["id"]: t for t in boot["teams"]}
    el_map = {e["id"]: e for e in boot["elements"]}
    fix_lookup = build_fixture_lookup(fixtures, teams_map)

    left_chips, used_half, chip_win = remaining_half_chips(hist.get("chips", []), start_gw)
    squad = [el_map[pk["element"]] for pk in picks_data["picks"]]

    print(f"# Chip Window Planner — Team {tid} (GW{start_gw}–GW{end_gw})")
    print(f"Chips ({chip_win}): Left={left_chips or 'None'} | Used={used_half or 'None'}\n")
    print("| GW | AvgFDR | Easy(<=2) | Hard(>=4) | Homes | BenchAvgFDR | DGW/BGW | Top League FDR<=2 Teams |")
    print("|---:|---:|---:|---:|---:|---:|:---|:---|")

    for gw in range(start_gw, end_gw + 1):
        all_fdrs, easy, hard, homes = [], 0, 0, 0
        for el in squad:
            fl = fix_lookup.get(el["team"], {}).get(gw, [])
            if not fl:
                all_fdrs.append(5)
                hard += 1
                continue
            fdr_avg = sum(x[2] for x in fl) / len(fl)
            all_fdrs.append(fdr_avg)
            if any(x[1] for x in fl):
                homes += 1
            if min(x[2] for x in fl) <= 2:
                easy += 1
            if min(x[2] for x in fl) >= 4:
                hard += 1

        bench_fdrs = []
        for el in squad[11:]:
            fl = fix_lookup.get(el["team"], {}).get(gw, [])
            bench_fdrs.append(sum(x[2] for x in fl) / len(fl) if fl else 5)

        dgw = [t["short_name"] for tid2, t in teams_map.items() if len(fix_lookup.get(tid2, {}).get(gw, [])) > 1]
        bgw = [t["short_name"] for tid2, t in teams_map.items() if len(fix_lookup.get(tid2, {}).get(gw, [])) == 0]
        special = []
        if dgw: special.append("DGW:" + ",".join(dgw[:4]))
        if bgw: special.append("BGW:" + ",".join(bgw[:4]))
        spec_str = "; ".join(special) if special else "Normal"

        easy_league = []
        for tid2, t in teams_map.items():
            fl = fix_lookup.get(tid2, {}).get(gw, [])
            if fl and min(x[2] for x in fl) <= 2:
                easy_league.append(f"{t['short_name']}({fmt_gw_fixtures(fl)})")

        print(f"| GW{gw} | {sum(all_fdrs)/15:.2f} | {easy} | {hard} | {homes}/15 | {sum(bench_fdrs)/4:.2f} | {spec_str} | {', '.join(easy_league[:6])} |")
    print(f"\nSource: {FPL_BASE}/entry/{tid}/event/{curr_gw}/picks/ & /fixtures/ | Fetched: {utc_now_str()}")


class _TextTableExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_tr = False
        self.in_cell = False
        self.rows = []
        self._cur_row = []
        self._cur_cell = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.in_tr = True
            self._cur_row = []
        elif tag in ("td", "th") and self.in_tr:
            self.in_cell = True
            self._cur_cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.in_cell:
            self.in_cell = False
            txt = " ".join("".join(self._cur_cell).split())
            self._cur_row.append(txt)
        elif tag == "tr" and self.in_tr:
            self.in_tr = False
            if any(self._cur_row):
                self.rows.append(self._cur_row)

    def handle_data(self, data):
        if self.in_cell:
            self._cur_cell.append(data)


def cmd_prices(args):
    squad_ids = set()
    if args.team:
        tid = resolve_team_id(args.team, args.alias or "default")
        boot = get_bootstrap(refresh=args.refresh)
        curr, _ = get_current_and_next_gw(boot)
        curr_gw = curr["id"] if curr else 1
        picks_data, _ = fetch_json_cached(f"{FPL_BASE}/entry/{tid}/event/{curr_gw}/picks/", f"picks_{tid}_{curr_gw}", ttl=300)
        squad_ids = {pk["element"] for pk in picks_data["picks"]}
    else:
        boot = get_bootstrap(refresh=args.refresh)

    teams_map = {t["id"]: t["short_name"] for t in boot["teams"]}
    sources_used = []

    # 1. Primary Predictor: LiveFPL
    live_rows = []
    try:
        lp, _ = fetch_json_cached(LIVEFPL_PRICES_URL, "livefpl_prices", ttl=900, force_refresh=args.refresh)
        sources_used.append(LIVEFPL_PRICES_URL)
        if isinstance(lp, dict):
            for k, v in lp.items():
                v["_id"] = int(k) if str(k).isdigit() else None
                live_rows.append(v)
        elif isinstance(lp, list):
            live_rows = lp
    except Exception as e:
        print(f"LiveFPL unavailable ({e}); trying fallback sources...")

    # 2. Official Confirmed Ground Truth: bootstrap-static
    sources_used.append(f"{FPL_BASE}/bootstrap-static/")
    confirmed_risers = sorted(
        [e for e in boot["elements"] if (e.get("cost_change_event") or 0) > 0],
        key=lambda x: (-x["cost_change_event"], -x["transfers_in_event"]),
    )
    confirmed_fallers = sorted(
        [e for e in boot["elements"] if (e.get("cost_change_event") or 0) < 0],
        key=lambda x: (x["cost_change_event"], -x["transfers_out_event"]),
    )

    print(f"# FPL Price Changes & Predictions (Fetched: {utc_now_str()})")
    if live_rows:
        risers = sorted(live_rows, key=lambda x: float(x.get("progress_tonight", x.get("progress", 0)) or 0), reverse=True)
        fallers = sorted(live_rows, key=lambda x: float(x.get("progress_tonight", x.get("progress", 0)) or 0))
        print("\n## Predicted Risers Tonight (LiveFPL)")
        print("| Player | Team | Pos | Cost | Tonight% | TotalProg% | PerHr |")
        print("|:---|:---|:---:|---:|---:|---:|---:|")
        for r in risers[: args.limit]:
            pt = float(r.get("progress_tonight") or 0) * 100
            pr = float(r.get("progress") or 0) * 100
            ph = float(r.get("per_hour") or 0) * 100
            mark = " *" if r.get("_id") in squad_ids else ""
            print(f"| {r.get('name')}{mark} | {r.get('team')} | {r.get('type')} | £{r.get('cost')} | {pt:+.1f}% | {pr:+.1f}% | {ph:+.2f}% |")

        print("\n## Predicted Fallers Tonight (LiveFPL)")
        print("| Player | Team | Pos | Cost | Tonight% | TotalProg% | PerHr |")
        print("|:---|:---|:---:|---:|---:|---:|---:|")
        for r in fallers[: args.limit]:
            pt = float(r.get("progress_tonight") or 0) * 100
            pr = float(r.get("progress") or 0) * 100
            ph = float(r.get("per_hour") or 0) * 100
            mark = " *" if r.get("_id") in squad_ids else ""
            print(f"| {r.get('name')}{mark} | {r.get('team')} | {r.get('type')} | £{r.get('cost')} | {pt:+.1f}% | {pr:+.1f}% | {ph:+.2f}% |")

        if squad_ids:
            sq_alerts = [
                r for r in live_rows
                if r.get("_id") in squad_ids and abs(float(r.get("progress_tonight") or 0)) >= 0.4
            ]
            if sq_alerts:
                print("\n## Your Squad Price Alerts (>=40% movement)")
                for r in sorted(sq_alerts, key=lambda x: abs(float(x.get("progress_tonight") or 0)), reverse=True):
                    print(f"- {r.get('name')} (£{r.get('cost')}): tonight {float(r.get('progress_tonight') or 0)*100:+.1f}%")
    else:
        # Fallback 1 & 2
        fallback_rows = []
        for fb_url in (FPL_PAGE_PRICES_URL, FPLSTATS_URL, FPLEDITS_URL):
            try:
                html = fetch_raw(fb_url)
                parser = _TextTableExtractor()
                parser.feed(html)
                if parser.rows:
                    sources_used.append(fb_url)
                    fallback_rows = parser.rows[: args.limit * 2]
                    break
            except Exception:
                continue
        if fallback_rows:
            print(f"\n## Fallback Price Predictions ({sources_used[-1]})")
            for row in fallback_rows[: args.limit]:
                print("- " + " | ".join(row[:6]))
        else:
            print("\n**All prediction sources failed; showing only Official Confirmed changes below.**")

    print("\n## Official Confirmed GW Price Changes (`bootstrap-static`)")
    print("**Risers:** " + (", ".join(f"{e['web_name']} ({teams_map[e['team']]}, £{e['now_cost']/10:.1f}, +{e['cost_change_event']/10:.1f})" for e in confirmed_risers[:10]) or "None this GW"))
    print("**Fallers:** " + (", ".join(f"{e['web_name']} ({teams_map[e['team']]}, £{e['now_cost']/10:.1f}, {e['cost_change_event']/10:.1f})" for e in confirmed_fallers[:10]) or "None this GW"))
    print("\nSources: " + " | ".join(sources_used))


def cmd_injury(args):
    query = args.player.strip().lower()
    boot = get_bootstrap(refresh=args.refresh)
    teams_map = {t["id"]: t for t in boot["teams"]}
    matches = [
        e for e in boot["elements"]
        if query in e["web_name"].lower() or query in f"{e['first_name']} {e['second_name']}".lower()
    ]
    if not matches:
        print(f"No player found matching '{args.player}' in FPL bootstrap-static.")
        return

    matches.sort(key=lambda x: x["minutes"], reverse=True)
    el = matches[0]
    team_name = teams_map[el["team"]]["name"]
    team_short = teams_map[el["team"]]["short_name"]
    status_desc = {"a": "Available", "d": "Doubtful", "i": "Injured", "s": "Suspended", "u": "Unavailable", "n": "Not in squad"}.get(el["status"], el["status"])

    print(f"# Injury & Availability Check — {el['first_name']} {el['second_name']} ({team_name} / {team_short})")
    print(f"1. **Official FPL API (`{FPL_BASE}/bootstrap-static/`):**")
    print(f"   - Status: `{el['status']}` ({status_desc}) | ThisGW%: {el.get('chance_of_playing_this_round')} | NextGW%: {el.get('chance_of_playing_next_round')}")
    print(f"   - News: {el.get('news') or 'None'} | news_added: `{el.get('news_added') or 'N/A'}`")

    # 2. Fantasy Football Scout SSR pages
    print("\n2. **Fantasy Football Scout (SSR Team News / Injuries):**")
    ffs_hits = []
    for ffs_url in (FFS_INJURIES_URL, FFS_TEAM_NEWS_URL):
        try:
            html = fetch_raw(ffs_url, timeout=12)
            parser = _TextTableExtractor()
            parser.feed(html)
            for r in parser.rows:
                joined = " ".join(r)
                if el["web_name"].lower() in joined.lower() or el["second_name"].lower() in joined.lower():
                    ffs_hits.append(f"[{ffs_url}] " + " | ".join(r[:6]))
            # Also scan article links/headings on team-news
            if "team-news" in ffs_url:
                for m in re.finditer(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>([^<]+)</a>", html, re.I):
                    txt = " ".join(m.group(2).split())
                    if team_name.lower() in txt.lower() or el["second_name"].lower() in txt.lower():
                        ffs_hits.append(f"[{ffs_url}] Link: {txt} ({m.group(1)})")
        except Exception as e:
            ffs_hits.append(f"[{ffs_url}] fetch error: {e}")

    if ffs_hits:
        for h in ffs_hits[:6]:
            print(f"   - {h}")
    else:
        print("   - No direct player/club row matched on FFS tables.")

    # 3. Tier-1 RSS Feeds
    print("\n3. **Tier-1 Football RSS Feeds:**")
    rss_hits = []
    keywords = [el["second_name"].lower(), el["web_name"].lower(), team_name.lower()]
    for name, rss_url in RSS_FEEDS:
        try:
            xml_txt = fetch_raw(rss_url, timeout=10)
            root = ET.fromstring(xml_txt)
            for item in root.findall(".//item")[:40]:
                title = (item.findtext("title") or "").strip()
                desc = (item.findtext("description") or "").strip()
                pub = (item.findtext("pubDate") or "").strip()
                blob = f"{title} {desc}".lower()
                if any(k in blob for k in keywords) and any(w in blob for w in ("injury", "injured", "doubt", "fit", "return", "ban", "suspend", "miss", "shoulder", "hamstring", "knee", "ankle", "squad", "boss", "arteta", "manager", "team news")):
                    rss_hits.append(f"[{name} | {pub}] {title}")
        except Exception:
            continue

    if rss_hits:
        for rh in rss_hits[:6]:
            print(f"   - {rh}")
    else:
        print("   - No recent injury/team-news headline matched in BBC/Guardian/Sky RSS (run targeted web search if news_added is >24–48h old).")
    print(f"\nChecked at: {utc_now_str()}")


def cmd_league(args):
    tid = resolve_team_id(args.team, args.alias or "default")
    boot = get_bootstrap(refresh=args.refresh)
    curr, nxt = get_current_and_next_gw(boot)
    curr_gw = curr["id"] if curr else 1
    el_map = {e["id"]: e for e in boot["elements"]}
    teams_map = {t["id"]: t["short_name"] for t in boot["teams"]}
    pos_map = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

    entry, _ = fetch_json_cached(f"{FPL_BASE}/entry/{tid}/", f"entry_{tid}", ttl=300, force_refresh=args.refresh)

    # Explicit rival IDs mode
    rival_entries = []
    league_title = "Custom Rivals"
    if args.rivals:
        for r_raw in args.rivals.split(","):
            rid = parse_team_id(r_raw)
            if rid and rid != tid:
                rentry, _ = fetch_json_cached(f"{FPL_BASE}/entry/{rid}/", f"entry_{rid}", ttl=300)
                rival_entries.append({
                    "entry": rid,
                    "entry_name": rentry.get("name"),
                    "player_name": f"{rentry.get('player_first_name', '')} {rentry.get('player_last_name', '')}".strip(),
                    "rank": rentry.get("summary_overall_rank"),
                    "total": rentry.get("summary_overall_points"),
                })
    else:
        priv_classic = [l for l in entry.get("leagues", {}).get("classic", []) if l.get("league_type") == "x"]
        priv_h2h = entry.get("leagues", {}).get("h2h", [])
        lid = int(args.league) if args.league else (priv_classic[0]["id"] if priv_classic else (priv_h2h[0]["id"] if priv_h2h else None))
        if not lid:
            raise ValueError("No private league found for this team. Pass --league <id> or --rivals <id1,id2>.")

        is_h2h = any(l["id"] == lid for l in priv_h2h)
        if is_h2h:
            target_gw = nxt["id"] if nxt else curr_gw
            matches, _ = fetch_json_cached(
                f"{FPL_BASE}/leagues-h2h-matches/league/{lid}/?event={target_gw}",
                f"h2h_{lid}_{target_gw}",
                ttl=300,
                force_refresh=args.refresh,
            )
            league_title = f"H2H League {lid} (GW{target_gw})"
            for m in matches.get("results", []):
                if m.get("entry_1_entry") == tid:
                    rival_entries.append({"entry": m["entry_2_entry"], "entry_name": m["entry_2_name"], "player_name": m["entry_2_player_name"], "rank": "Opp", "total": m.get("entry_2_points")})
                    break
                if m.get("entry_2_entry") == tid:
                    rival_entries.append({"entry": m["entry_1_entry"], "entry_name": m["entry_1_name"], "player_name": m["entry_1_player_name"], "rank": "Opp", "total": m.get("entry_1_points")})
                    break
        else:
            standings, _ = fetch_json_cached(
                f"{FPL_BASE}/leagues-classic/{lid}/standings/",
                f"league_{lid}",
                ttl=300,
                force_refresh=args.refresh,
            )
            league_title = standings.get("league", {}).get("name", f"League {lid}")
            rows = standings.get("standings", {}).get("results", [])
            top_slice = rows[: args.top]
            user_idx = next((i for i, r in enumerate(rows) if r["entry"] == tid), None)
            neighbors = []
            if user_idx is not None:
                for offset in (-1, 1):
                    idx = user_idx + offset
                    if 0 <= idx < len(rows):
                        neighbors.append(rows[idx])
            seen = {tid}
            for r in top_slice + neighbors:
                if r["entry"] not in seen:
                    seen.add(r["entry"])
                    rival_entries.append(r)

    rival_entries = rival_entries[:6]  # Cap at 6 rivals for speed & token budget
    if not rival_entries:
        print("No rivals found to compare.")
        return

    my_picks, _ = fetch_json_cached(f"{FPL_BASE}/entry/{tid}/event/{curr_gw}/picks/", f"picks_{tid}_{curr_gw}", ttl=300)
    my_set = {pk["element"] for pk in my_picks["picks"]}
    my_cap = next((el_map[pk["element"]]["web_name"] for pk in my_picks["picks"] if pk["is_captain"]), "?")
    my_pts = entry.get("summary_overall_points")

    rival_ownership = {}
    print(f"# Rival Comparison — {league_title} (Base GW{curr_gw})")
    print(f"You: **{entry.get('name')}** ({my_pts} pts | Cap: {my_cap})\n")
    print("| Rival Team | Rank | Pts | Gap vs You | Cap (GW{gw}) | Chips Left (Half) |".replace("{gw}", str(curr_gw)))
    print("|:---|---:|---:|---:|:---|:---|")

    for rv in rival_entries:
        rid = rv["entry"]
        r_picks, _ = fetch_json_cached(f"{FPL_BASE}/entry/{rid}/event/{curr_gw}/picks/", f"picks_{rid}_{curr_gw}", ttl=300)
        r_hist, _ = fetch_json_cached(f"{FPL_BASE}/entry/{rid}/history/", f"hist_{rid}", ttl=300)
        r_left, _, _ = remaining_half_chips(r_hist.get("chips", []), nxt["id"] if nxt else curr_gw)
        r_cap = next((el_map[pk["element"]]["web_name"] for pk in r_picks["picks"] if pk["is_captain"]), "?")
        for pk in r_picks["picks"]:
            rival_ownership[pk["element"]] = rival_ownership.get(pk["element"], 0) + 1
        r_tot = rv.get("total")
        gap = f"{r_tot - my_pts:+d}" if isinstance(r_tot, int) and isinstance(my_pts, int) else "-"
        print(f"| {rv.get('entry_name')} | {rv.get('rank')} | {r_tot} | {gap} | {r_cap} | {', '.join(r_left) or 'None'} |")

    n_rv = len(rival_entries)
    threats = [(cnt, eid) for eid, cnt in rival_ownership.items() if eid not in my_set]
    threats.sort(key=lambda x: (-x[0], -el_map[x[1]]["total_points"]))
    diffs = [(n_rv - rival_ownership.get(eid, 0), eid) for eid in my_set if rival_ownership.get(eid, 0) < n_rv]
    diffs.sort(key=lambda x: (-x[0], -el_map[x[1]]["total_points"]))

    print(f"\n## Shield Threats (Owned by rivals, NOT in your squad — out of {n_rv})")
    for cnt, eid in threats[:10]:
        el = el_map[eid]
        print(f"- {el['web_name']} ({pos_map[el['element_type']]}, {teams_map[el['team']]}, £{el['now_cost']/10:.1f}) — owned by {cnt}/{n_rv} | form {el['form']}")

    print(f"\n## Your Differentials (In your squad, low rival ownership)")
    for missing_cnt, eid in diffs[:10]:
        el = el_map[eid]
        owned_cnt = n_rv - missing_cnt
        print(f"- {el['web_name']} ({pos_map[el['element_type']]}, {teams_map[el['team']]}, £{el['now_cost']/10:.1f}) — only {owned_cnt}/{n_rv} rivals own | form {el['form']}")

    print(f"\nSource: {FPL_BASE}/ (entry, picks, standings) | Fetched: {utc_now_str()}")


def main():
    p = argparse.ArgumentParser(description="FPL Guru low-token CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("profile", help="View or save user FPL profile")
    sp.add_argument("--set-team", help="FPL Team ID or URL")
    sp.add_argument("--alias", default="default")
    sp.add_argument("--style", choices=["safe", "balanced", "aggressive"])
    sp.add_argument("--goal", choices=["overall", "league", "h2h"])
    sp.add_argument("--league", help="Tracked league ID")
    sp.add_argument("--add-rival", help="Rival Team ID or URL")
    sp.add_argument("--show", action="store_true")

    sb = sub.add_parser("brief", help="Compact squad + fixtures + FT + chip summary")
    sb.add_argument("--team", help="Team ID or FPL URL")
    sb.add_argument("--alias", default="default")
    sb.add_argument("--refresh", action="store_true")

    st = sub.add_parser("targets", help="Top transfer targets by position & budget")
    st.add_argument("--pos", required=True, choices=["GK", "DEF", "MID", "FWD", "gk", "def", "mid", "fwd"])
    st.add_argument("--max-price", type=float, default=20.0)
    st.add_argument("--gw-window", type=int, default=5)
    st.add_argument("--min-minutes", type=int, default=270)
    st.add_argument("--team-exclude", default="")
    st.add_argument("--limit", type=int, default=12)
    st.add_argument("--refresh", action="store_true")

    sc = sub.add_parser("chips", help="GW-by-GW chip window analyzer")
    sc.add_argument("--team", help="Team ID or FPL URL")
    sc.add_argument("--alias", default="default")
    sc.add_argument("--from-gw", type=int)
    sc.add_argument("--to-gw", type=int)
    sc.add_argument("--refresh", action="store_true")

    spr = sub.add_parser("prices", help="No-bluff price predictions & confirmed changes")
    spr.add_argument("--team", help="Highlight squad players")
    spr.add_argument("--alias", default="default")
    spr.add_argument("--limit", type=int, default=10)
    spr.add_argument("--refresh", action="store_true")

    si = sub.add_parser("injury", help="Official-first injury & news check")
    si.add_argument("--player", required=True, help="Player name")
    si.add_argument("--refresh", action="store_true")

    sl = sub.add_parser("league", help="Mini-league or H2H/rival comparison")
    sl.add_argument("--team", help="Your Team ID or URL")
    sl.add_argument("--alias", default="default")
    sl.add_argument("--league", help="League ID")
    sl.add_argument("--rivals", help="Comma-separated rival IDs/URLs")
    sl.add_argument("--top", type=int, default=4)
    sl.add_argument("--refresh", action="store_true")

    args = p.parse_args()
    dispatch = {
        "profile": cmd_profile,
        "brief": cmd_brief,
        "targets": cmd_targets,
        "chips": cmd_chips,
        "prices": cmd_prices,
        "injury": cmd_injury,
        "league": cmd_league,
    }
    try:
        dispatch[args.cmd](args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
