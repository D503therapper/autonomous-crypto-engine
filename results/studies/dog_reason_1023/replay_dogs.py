"""10/23 CUTOFF STUDY - does the Dog of the Day's 'needs a named reason' gate (sports.good) cost us?
Built on tools/value_play_replay.Replay (8:35 AM PT board, closing prices, params re-tuned each July 1 on the seasons
before). Each board day the candidates are built ONCE, then make_board runs under each variant:
  A  today: good() needs a named reason
  B  a ml dog that clears dog_gate (whole dog score >= the sport's gate + own read over the price) needs no named reason
  C  'sharp money moving this way' fires at a line move of 0.04 (not 0.08) - the reason list only
  D  B, but only for a dog whose dog score clears its gate by 1+ point (a buffer)
Also dumps every ml dog +100..+350 candidate with its gate / reasons / line move for offline checks.
Usage: python replay_dogs.py START END OUT.jsonl [step]"""
import json, os, sys, time
from datetime import datetime, timedelta
WT = "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/wt"
sys.path.insert(0, WT); sys.path.insert(0, WT + "/tools")
os.chdir(WT)
os.environ.setdefault("REPLAY_PARAMS_DIR", "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/cutoff_study/params")
import value_play_replay as vpr   # noqa: E402
vpr.PARAMS_DIR = os.environ["REPLAY_PARAMS_DIR"]
import sports, sports_data as sd, sports_players as sp, sports_model as sm   # noqa: E402

ORIG_GOOD = sports.good
SHARP = "sharp money moving this way"
GATES = {"nfl": sports.DOG_GATE, "nhl": sports.NHL_DOG_GATE, "ncaaf": sports.NCAAF_DOG_GATE,
         "nba": sports.NBA_DOG_GATE, "ncaab": sports.NCAAB_DOG_GATE}


def good_B(buffer=0.0):
    def g(c):
        if ORIG_GOOD(c):
            return True
        if c.get("reasons") or c.get("market") != "ml" or c.get("odds", 0) < 100 or c.get("trap") \
                or c.get("odds", 0) > sports.DOG_DAY_MAX or sports.hockey_fav_bad(c):
            return False
        if not sports.dog_gate(c):
            return False
        if buffer and (c.get("dog_score") or -99) < GATES.get(c.get("league"), 99) + buffer:
            return False
        return True
    return g


VARIANTS = {"A": (ORIG_GOOD, False), "B": (good_B(), False), "C": (ORIG_GOOD, True), "D": (good_B(1.0), False)}


class R2(vpr.Replay):
    def day(self, day):
        tune_at = datetime.strptime(f"{day.year if day.strftime('%m-%d') >= vpr.TUNE_MONTH_DAY else day.year - 1}-{vpr.TUNE_MONTH_DAY}",
                                    "%Y-%m-%d").date()
        if self.tuned_before != tune_at:
            self.tune(tune_at)
        now = datetime(day.year, day.month, day.day, vpr.BOARD_AT[0], vpr.BOARD_AT[1], tzinfo=vpr.PT).astimezone(vpr.timezone.utc)
        snap = dict(self.hist)
        real = {}
        import copy
        for g in self.by_day.get(day, []):
            real[g["id"]] = g
            c = copy.copy(g)
            c["status"], c["home_score"], c["away_score"] = "pre", "", ""
            c["inj_home"], c["inj_away"] = "", ""
            snap[g["id"]] = c
        rows = []
        if any(g.get("ml_home", "") != "" and g.get("status") == "final" for g in real.values()):
            self.states(snap, now)
            cands = sports.candidates(snap, self.model, now, day, None)
            cands = [c for c in cands if not c.get("hurt")]
            far = now + timedelta(days=30)
            lm = {}
            for c in cands:
                g = snap.get(c["game_id"])
                lm[(c["game_id"], c["side"])] = (sm.line_move(g) * (1 if c["side"] == "home" else -1)) if g else 0.0
            for vname, (gfn, soft) in VARIANTS.items():
                cc = [dict(c) for c in cands]
                if soft:
                    for c in cc:
                        if lm[(c["game_id"], c["side"])] >= 0.04 and SHARP not in (c.get("reasons") or []):
                            c["reasons"] = list(c.get("reasons") or []) + [SHARP]
                sports.good = gfn
                try:
                    board = sports.make_board(cc)
                finally:
                    sports.good = ORIG_GOOD
                for kind in ("lock", "dog", "solo"):
                    b = board.get(kind)
                    if b:
                        for leg in b["legs"]:
                            r = self.row(day, kind, 0, leg, real, far, len(cands))
                            r.update(variant=vname, lm=round(lm[(leg["game_id"], leg["side"])], 4),
                                     dog_score_leg=leg.get("dog_score"))
                            rows.append(r)
            # every ml dog candidate (diagnostics)
            for c in cands:
                if c.get("market") == "ml" and 100 <= c.get("odds", 0) <= sports.DAILY_DOG_MAX:
                    r = self.row(day, "cand", 0, dict(c), real, far, len(cands))
                    r.update(variant="cand", lm=round(lm[(c["game_id"], c["side"])], 4), good=bool(ORIG_GOOD(dict(c))),
                             trap=bool(c.get("trap")), fighting=bool(sports.fighting(c)))
                    rows.append(r)
        self.feed(day)
        return rows


def main(start, end, out, step=1):
    t0 = time.time()
    games = sd.load_games()
    cache = sp.load()
    rp = R2(games, cache)
    d0 = datetime.strptime(start, "%Y-%m-%d").date()
    d1 = datetime.strptime(end, "%Y-%m-%d").date()
    for day in sorted(d for d in rp.by_day if d < d0):
        for g in rp.by_day[day]:
            rp.hist[g["id"]] = g
    n = 0
    with open(out, "w") as f:
        d = d0
        while d <= d1:
            try:
                if (d - d0).days % step:
                    rp.feed(d); rows = []
                else:
                    rows = rp.day(d)
            except Exception as e:   # noqa: BLE001
                import traceback; traceback.print_exc()
                print(f"{d}: FAILED {str(e)[:160]}", flush=True)
                rp.feed(d); rows = []
            for r in rows:
                f.write(json.dumps(r) + "\n")
            f.flush()
            n += len(rows)
            if d.day == 1 or d == d1:
                print(f"{d}: {n} rows, {time.time() - t0:.0f}s", flush=True)
            d += timedelta(days=1)
    print(f"done {n} rows {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 1)
