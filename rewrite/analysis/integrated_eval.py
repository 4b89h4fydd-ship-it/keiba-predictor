# Vendored 2026-11-17 for production use (user instruction: put ALL
# collected netkeiba materials into the production forecast) from the
# research tree: goals/arvexq-repair-and-accuracy-improvement/
# hidden_files/netkeiba-integration-20261116/integrated_eval.py
# The research copy remains the reference; this copy is byte-identical
# below this header so that what was validated is what runs (the
# validation harness's own principle). DEFAULT_WEIGHTS are the frozen
# weights of the integrated evaluation — the publish lane does not
# retune them.
"""ARVEXQ integrated evaluation (netkeiba premium materials + v9b).

One evaluation object per race produces ALL outputs so they can never drift
apart:
  - win probabilities (integrated score)
  - marks ◎○▲△☆ (rank order of the integrated probabilities)
  - tickets (the existing R24 rule -- top combos by joint probability under
    Harville -- applied to the integrated probabilities, same point counts)
  - pace text (generated from the same pace layer stored in the evaluation)

Form (transparent, no black box):
  logp_adj(h) = log(p_v9b(h))
              + w_comment * comment_z(h)     # rule-based polarity score
              + w_grade   * grade_z(h)       # training evaluation A/B/C
              + w_speed   * speed_resid_z(h) # netkeiba speed index residual
              + w_speed_slope * slope_z(h)   # index trend: rising / falling
              + w_speed_dev   * dev_z(h)     # last run vs own 5-run average
              + w_speed_vol   * vol_z(h)     # index volatility (range)
              + w_speed_sd    * sd_z(h)      # spread around the recent mean
              + w_speed_overlap * overlap_z(h) # mean+-sd band overlap vs field
              + w_speed_fit   * fit_z(h)     # condition (dist/course) edge
              + w_speed_bias  * bias_z(h)    # course-vs-distance aptitude bias
  p_int = softmax(logp_adj)

Missing material contributes 0 and is counted in coverage. All z-scores are
within-race. Weights are per-segment (jra / nar) and are meant to be fit on a
training window by winner log-likelihood, then frozen. DEFAULT_WEIGHTS below
are conservative placeholders for the smoke test only -- NOT learned values.

Pace layer (display + scenario record): front_rate per horse from past
first-corner positions (same definition as pace-linkage-20261116), field pace
pressure P = mean(front_rate), likely-forward = top front_rate horses.
The pace layer does NOT adjust probabilities in v1: the pace-linkage
validation measured the learned pace x style interaction at 0 on NAR
(gamma=0 chosen on the training window). The slot `w_pace` exists so a
segment where a nonzero effect is ever measured can enable it without
redesign; the pace text and the evaluation share the same pace quantities,
which is what removes the structural contradiction.
"""
import math
import re
from itertools import permutations

# ---------------------------------------------------------------- comments
# Rule-based polarity dictionary. Each entry: phrase -> weight.
# +2 strong positive / -2 strong negative, +1 / -1 mild. Matching is plain
# substring; negation handling is a documented v1 limitation.
COMMENT_POSITIVE = {
    # 状態・仕上がり (strong)
    "前走以上": 2, "好調": 2, "上積み": 2, "良化": 1, "上向き": 1,
    "順調": 1, "仕上が": 1, "気配は上向き": 2, "状態はいい": 1,
    "状態も悪くない": 1, "出来は良": 1, "動きは上々": 2, "動きも良": 1,
    "動きはいい": 1, "よく動け": 1, "水準以上": 1, "水準より上": 2,
    "態勢": 1, "万全": 2, "好仕上がり": 2, "一番の出来": 2,
    "ピリッとして": 1, "成長": 1, "楽しみ": 1, "期待": 1,
    # 適性
    "合っている": 1, "合いそう": 1, "合うはず": 1, "合いそうです": 1,
    "こなせる": 1, "こなせそう": 1, "守備範囲": 1, "ベスト条件": 2,
    "相性がいい": 1, "相性もいい": 1, "向いている": 1, "向きです": 1,
    "舞台は合う": 1, "舞台も合": 1, "コースは合う": 1, "コースも合": 1,
    "得意の": 1, "実績のある": 1,
}
COMMENT_NEGATIVE = {
    # 状態・仕上がり
    "良化途上": -1, "使いつつ": -1, "使いながら": -1, "使えば良く": -1,
    "成長待ち": -2, "幼さ": -1, "幼い": -1, "幼く": -1, "非力": -1,
    "緩さ": -1, "緩く": -1, "緩め": -1, "余裕がある": -1, "余裕はある": -1,
    "太め": -1, "もうひとつ": -1, "もう一歩": -1, "目立たない": -1,
    "目立つところがありません": -2, "詰まってこない": -1, "割引": -1,
    "見劣り": -2, "不安": -1, "イレ込": -1, "気難しい": -1,
    "気性が難": -1, "気難し": -1, "まだ子ども": -1, "子どもっぽ": -1,
    "未完成": -1, "良くなるのは先": -2, "力不足": -2, "ワンペース": -1,
    "一本調子": -1, "ピリッとしない": -1, "動きはもうひとつ": -2,
    "それほど差はない": 0,
    # 適性
    "不向き": -2, "合わない": -2, "苦手": -1, "長い印象": -1,
    "長い気も": -1, "若干長い": -1, "距離は少し長い": -1,
}
# "それほど差はない" style neutral phrases score 0 and are listed only to
# document that they were considered; they are skipped in scoring.

def comment_score(text):
    """Sum of dictionary weights over the comment text. Returns (score, hits)."""
    if not text:
        return None, []
    score, hits = 0, []
    for phrase, w in list(COMMENT_POSITIVE.items()) + list(COMMENT_NEGATIVE.items()):
        if w != 0 and phrase in text:
            score += w
            hits.append((phrase, w))
    return score, hits

# ---------------------------------------------------------------- helpers
def _zscores(values):
    """Within-race z-scores; values may contain None (excluded, stays None)."""
    xs = [v for v in values if v is not None]
    if len(xs) < 3:
        return [None] * len(values)
    m = sum(xs) / len(xs)
    var = sum((x - m) ** 2 for x in xs) / len(xs)
    sd = math.sqrt(var)
    if sd < 1e-9:
        return [0.0 if v is not None else None for v in values]
    return [((v - m) / sd) if v is not None else None for v in values]

GRADE_POINTS = {"A": 2.0, "B": 1.0, "C": 0.0}

# ------------------------------------------------------- speed-index trend
# User instruction (2026-11-16): analyse the time index properly, including
# whether each horse is RISING or FALLING into this race -- not just level.
#
# netkeiba's speed page gives, per horse: best (最高), 5-run average
# (5走平均) and the last three runs (3走前 / 2走前 / 前走). From those we
# derive transparent trend features (all computed from PRE-race values only;
# the sequence is the horse's past runs, never this race or later):
#
#   last          前走指数 -- the freshest level. Preferred over `best`:
#                 best is often old and set under different conditions.
#   slope         linear trend over the available recent points (per-run
#                 step). Positive = improving into this race.
#   last_minus_avg5  前走 - 5走平均 -- how far the latest run sits above or
#                 below the horse's own recent baseline (form spike / dip).
#   rise_run      consecutive increases ending at the latest run (0 if the
#                 last step was flat/down). Captures "still climbing".
#   vol           range (max-min) of the recent points -- erratic horses.
#                 Exposed as its own term with a LEARNABLE weight (expected
#                 negative); we do not hard-code a discount, validation
#                 decides the sign.
#   last_vs_best  前走 - 最高 -- headroom below the horse's demonstrated
#                 peak (0 = latest run equals its best).
#
# Dispersion of the recent average (user instruction, 2026-11-16: "when you
# use a 5-run / recent average, look at the error around that average too"):
#   sd            population SD of the recent points -- the spread itself.
#   mad           mean absolute deviation from the recent mean -- same idea,
#                 less sensitive to a single wild run than sd/range.
#   cv            sd / mean(recent) -- RELATIVE error: a spread of 10 means
#                 something different around an average of 90 vs 50.
#   mean_lb       mean(recent) - sd -- a conservative (lower-bound) level:
#                 "the level you can actually trust" for an erratic horse.
#   overlap_share computed at race level in integrate(): the share of the
#                 OTHER horses whose mean +/- sd band overlaps this horse's
#                 band. High overlap = this average does not separate the
#                 horse from the field, i.e. the average is not trustworthy
#                 as a ranking signal for this horse in this race.
# Contrast pair from Oi 2026-11-16: 11R #4 (recent 102/49/70 -- high mean,
# huge spread) vs 12R #9 (82/83/91 -- tight and rising). Any average-only
# feature treats #4 kindly; the dispersion features are what separate them.
#
# The window is at most 3 points, so slope is noisy by construction; that is
# why the trend weights default to 0 (off) until learned on a training
# window, exactly like the other terms. Design rule: no black box -- every
# feature above is a closed-form function of the published numbers.

def speed_trend_features(recent, avg5=None, best=None):
    """recent: list of past speed indices, oldest -> newest, may contain
    None for missing runs. Returns a dict of features (None when not
    computable from the available points)."""
    pts = [(i, v) for i, v in enumerate(recent or []) if v is not None]
    out = {"last": None, "slope": None, "last_minus_avg5": None,
           "rise_run": None, "rising": None, "vol": None,
           "last_vs_best": None, "n_points": len(pts),
           "mean_recent": None, "sd": None, "mad": None, "cv": None,
           "mean_lb": None}
    if not pts:
        return out
    vals = [v for _, v in pts]
    out["last"] = vals[-1]
    mean_r = sum(vals) / len(vals)
    out["mean_recent"] = mean_r
    if len(pts) >= 2:
        n = len(pts)
        mx = sum(i for i, _ in pts) / n
        my = sum(vals) / n
        denom = sum((i - mx) ** 2 for i, _ in pts)
        out["slope"] = (sum((i - mx) * (v - my) for i, v in pts) / denom
                        if denom > 0 else 0.0)
        run = 0
        for a, b in zip(vals[-2::-1], vals[::-1]):
            if b > a:
                run += 1
            else:
                break
        out["rise_run"] = run
        out["rising"] = run >= 1
        out["vol"] = max(vals) - min(vals)
        var = sum((v - mean_r) ** 2 for v in vals) / len(vals)
        out["sd"] = math.sqrt(var)
        out["mad"] = sum(abs(v - mean_r) for v in vals) / len(vals)
        out["cv"] = out["sd"] / mean_r if mean_r > 0 else None
        out["mean_lb"] = mean_r - out["sd"]
    if avg5 is not None:
        out["last_minus_avg5"] = vals[-1] - avg5
    if best is not None:
        out["last_vs_best"] = vals[-1] - best
    return out

# ------------------------------------------------- speed-index aptitude
# User instruction (2026-11-16): use EVERY column of the speed page, no
# leftovers. Beyond best / 5-run average / recent runs, the page carries:
#   dist_idx    距離指数 -- the horse's index at (around) today's distance
#   course_idx  コース指数 -- the horse's index at today's course
# Derived aptitude features (all pre-race):
#   course_minus_dist  コース - 距離 -- where the horse's edge lives:
#                      course-specific vs distance-specific aptitude.
#   fit_idx            mean of the available condition indices -- the
#                      horse's level under TODAY's conditions.
#   fit_edge           fit_idx - 5走平均 -- does the horse run better under
#                      today's conditions than its general recent level?
#                      This is the "適性" signal proper: a horse whose
#                      general numbers are mediocre but whose distance/
#                      course numbers are strong is upgraded, and vice
#                      versa. Falls back to None without a 5-run average.
#   last_vs_dist / last_vs_course  前走 - 距離指数 / コース指数 -- is the
#                      latest form above or below what the horse has shown
#                      under today's conditions (returning to a favoured
#                      setup after a poor run elsewhere, etc.).

def speed_aptitude_features(dist_idx=None, course_idx=None, last=None,
                            avg5=None):
    out = {"dist_idx": dist_idx, "course_idx": course_idx,
           "course_minus_dist": None, "fit_idx": None, "fit_edge": None,
           "last_vs_dist": None, "last_vs_course": None}
    cond = [v for v in (dist_idx, course_idx) if v is not None]
    if dist_idx is not None and course_idx is not None:
        out["course_minus_dist"] = course_idx - dist_idx
    if cond:
        out["fit_idx"] = sum(cond) / len(cond)
        if avg5 is not None:
            out["fit_edge"] = out["fit_idx"] - avg5
    if last is not None and dist_idx is not None:
        out["last_vs_dist"] = last - dist_idx
    if last is not None and course_idx is not None:
        out["last_vs_course"] = last - course_idx
    return out

def band_overlap_share(bands):
    """bands: list of (mean, sd) or None per horse. For each horse, the share
    of the OTHER horses whose mean +/- sd band overlaps this horse's band.
    None in -> None out. Needs >= 2 valid bands, else all None."""
    valid = [(i, b) for i, b in enumerate(bands) if b is not None]
    if len(valid) < 2:
        return [None] * len(bands)
    out = [None] * len(bands)
    for i, (m1, s1) in valid:
        lo1, hi1 = m1 - s1, m1 + s1
        hits = tot = 0
        for j, (m2, s2) in valid:
            if j == i:
                continue
            tot += 1
            if lo1 <= m2 + s2 and m2 - s2 <= hi1:
                hits += 1
        out[i] = hits / tot if tot else None
    return out

# --------------------------------------- jockey x horse combination
# User instruction (2026-11-16): the jockey-HORSE combination record is a
# separate material from jockey ability and from jockey changes (both of
# which were measured before and cut). Definition (own data, no reliance
# on netkeiba display): from the horse's past runs WITH jockey names,
# take the runs ridden by TODAY's jockey:
#   combo_starts   how many times this pair has raced together
#   combo_top3     their top-3 rate together
#   combo_top3_shrunk  combo_top3 shrunk toward the horse's own overall
#                  top-3 rate with prior strength m=3 rides -- a pair with
#                  1 ride and 1 win must not read as a 100% combination.
# Data status: NAR has a ride ledger (pace-linkage, 212k rides, jockey
# names attached); JRA past-run raw rows carrying jockey names per run
# still need coverage confirmation. Feature defined now, validation
# pending that confirmation. Pre-race runs only (date < race date).

def combo_features(past_rides, today_jockey, prior_strength=3.0):
    """past_rides: [{jockey, finish, field_size}] pre-race only."""
    out = {"combo_starts": 0, "combo_top3": None, "combo_top3_shrunk": None,
           "own_top3": None}
    if not past_rides:
        return out
    def top3(r):
        return 1.0 if r.get("finish") and r["finish"] <= 3 else 0.0
    own = [top3(r) for r in past_rides]
    out["own_top3"] = sum(own) / len(own)
    pair = [top3(r) for r in past_rides if r.get("jockey") == today_jockey]
    out["combo_starts"] = len(pair)
    if pair:
        out["combo_top3"] = sum(pair) / len(pair)
        m = prior_strength
        out["combo_top3_shrunk"] = ((sum(pair) + m * out["own_top3"])
                                    / (len(pair) + m))
    return out

# ------------------------------------------------------- closing (上がり)
# Recent last-3F (上がり) seconds. Own corpus HAS last3fSeconds in the raw
# past-run rows (regenerated in ranking round 4; in the ranking-learning
# context adding it did not move the ranking metrics -- measured, not
# assumed). As an overlay term on v9b it is still unvalidated.
# Features are within-horse (raw seconds are not comparable across
# distances/surfaces):
#   closing_last   latest last-3F seconds
#   closing_dev    own recent mean - latest (positive = finished FASTER
#                  than its own usual close)
#   closing_slope  slope of seconds over the recent runs (negative =
#                  getting faster)
# Race-relative versions (上がり順位, gap to the fastest closer in that
# past race) need full-field data for each past race, which per-horse
# rows do not carry; netkeiba's data-analysis pages may provide them --
# pending the collection check.

def closing_features(last3f_recent):
    """last3f_recent: seconds, oldest -> newest, may contain None."""
    pts = [(i, v) for i, v in enumerate(last3f_recent or [])
           if v is not None]
    out = {"closing_last": None, "closing_dev": None, "closing_slope": None,
           "n_points": len(pts)}
    if not pts:
        return out
    vals = [v for _, v in pts]
    out["closing_last"] = vals[-1]
    if len(pts) >= 2:
        mean_r = sum(vals) / len(vals)
        out["closing_dev"] = mean_r - vals[-1]
        n = len(pts)
        mx = sum(i for i, _ in pts) / n
        denom = sum((i - mx) ** 2 for i, _ in pts)
        out["closing_slope"] = (sum((i - mx) * (v - mean_r) for i, v in pts)
                                / denom if denom > 0 else 0.0)
    return out

# --------------------------------------- course analysis (コース分析)
# NOT a per-race runner attribute: a property of the (track, distance
# band) the race is run at, estimated WALK-FORWARD from our own corpus
# (races dated < race date only; netkeiba display is not required):
#   course_front_bias  at this course key, the historical top-3-rate
#                      contrast between front-style horses (front_rate
#                      at/above their race's median) and the rest.
#                      Positive = the course rewards going forward.
#   course_frame_bias  at this course key, the historical top-3-rate
#                      excess of the horse's own frame group
#                      (inner 1-2 / mid 3-5 / outer 6+) over the key's
#                      overall top-3 rate.
# Both are shrunk toward the track-level value and then toward 0 by
# runner counts (prior strength 30 runners) and fall back key -> track.
# The horse-level inputs below are computed by the validation harness
# (validate_overlays.py) and passed in ready-made:
#   course_front = course_front_bias * (front_rate - race mean front_rate)
#   course_frame = course_frame_bias(own frame group)
# Status: DEFINED + under validation (2026-11-16); weights default 0.

# --------------------------------------- odds movement (オッズの動き)
# v9b already blends the market level (final-odds equivalent). What it
# does NOT use is the MOVEMENT: publish-time odds (sealed snapshot) vs
# final odds, and the win/place relationship.
#   odds_drift    log(publish_win_odds / final_win_odds); positive =
#                 the odds shortened into the race (money came in).
#   odds_wp_gap   log(final_win_odds / place_mid_odds) with place_mid
#                 the midpoint of the place-odds range; a crude
#                 win-vs-place divergence gauge (large = the win price
#                 is long relative to the place price).
# Status: DEFINED + under validation (2026-11-16); weights default 0.

def odds_movement_features(publish_win=None, final_win=None,
                           place_low=None, place_high=None):
    out = {"odds_drift": None, "odds_wp_gap": None}
    if publish_win and final_win and publish_win > 0 and final_win > 0:
        out["odds_drift"] = math.log(publish_win / final_win)
    if final_win and place_low and place_high:
        mid = (place_low + place_high) / 2.0
        if mid > 0:
            out["odds_wp_gap"] = math.log(final_win / mid)
    return out

# --------------------------------------- head-to-head (対戦表) / best time
# 対戦表: past direct meetings between today's runners. The corpus
# already carries a walk-forward aggregate (h2h_ahead_rate: of the
# opponents met before, the share this horse finished ahead of),
# computed by the round-2 builder from the event ledger (records dated
# < race date only). Horse input `h2h` = that rate; z-scored in-race.
# 持ちタイム: the horse's best finishing time under today's conditions.
# Raw seconds are not comparable across tracks, so the input is the
# horse's best time at today's track AND distance (exact), expressed as
# seconds behind the fastest such time in the field is NOT assumed --
# the raw best time is passed and z-scored in-race like everything
# else; the learned weight carries the sign (lower time = better, so
# the expected sign is negative). Fallback definitions (same distance
# band, any track) are a data-side choice and must be recorded with
# the values. Status: DEFINED + under validation (2026-11-16).

# --------------------------------------- netkeiba data-analysis page
# The データ分析 pages carry per-horse items beyond combination and
# closing (exact inventory being confirmed on the collection side,
# 2026-11-16). Registry of candidate names lives here so nothing is
# silently dropped; each becomes a plain z term like nk_form_dev once
# data exists. NO data in hand yet -> all UNVALIDATED, no slots faked.
NK_DATA_ANALYSIS_CANDIDATES = []  # filled from the collection inventory

# --------------------------------------- netkeiba's own judgements
# 調子偏差値 (form deviation value), コメント分析 judgements, AI
# evaluations: candidate inputs nk_form_dev / nk_ai_score, entering as
# plain within-race z terms like the others. NO data in hand yet
# (collection side is confirming availability); slots exist so the
# adapter is a data drop-in, and the REPORT lists them as UNVALIDATED
# until numbers exist. Do not confuse "slot exists" with "measured".

DEFAULT_WEIGHTS = {  # smoke-only placeholders, NOT learned
    "comment": 0.25, "grade": 0.20, "speed": 0.15, "pace": 0.0,
    # trend terms: 0 = off until learned on the 68-race collection
    "speed_slope": 0.0, "speed_dev": 0.0, "speed_vol": 0.0,
    # dispersion terms: also 0 until learned; expected sign is negative
    # (erratic / non-separating averages get discounted), validation decides
    "speed_sd": 0.0, "speed_overlap": 0.0,
    # aptitude terms: also 0 until learned
    "speed_fit": 0.0, "speed_bias": 0.0,
    # combination / closing / netkeiba-judgement terms: 0 until learned
    "combo": 0.0, "closing": 0.0, "nk_form_dev": 0.0, "nk_ai": 0.0,
    # course-bias / odds-movement terms: 0 until learned (2026-11-16)
    "course_front": 0.0, "course_frame": 0.0,
    "odds_drift": 0.0, "odds_wp_gap": 0.0,
    # head-to-head / best-time terms: 0 until learned (2026-11-16)
    "h2h": 0.0, "mochitime": 0.0,
}

def integrate(horses, weights=None):
    """horses: list of dicts with keys
        num, v9b (prob), comment_text|None, grade|'A'/'B'/'C'/None,
        nk_speed (netkeiba recent-avg index)|None, spd2 (own speed)|None,
        nk_recent (recent index sequence, oldest->newest)|None,
        nk_avg5 (5-run average index)|None, nk_best (best index)|None,
        nk_dist (distance index)|None, nk_course (course index)|None,
        front_rate|None
    Returns (probs dict num->p, coverage dict, per-horse detail list).
    """
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)
    raw_comment = []
    for h in horses:
        s, _ = comment_score(h.get("comment_text"))
        raw_comment.append(s)
    comment_z = _zscores(raw_comment)
    grade_z = _zscores([GRADE_POINTS.get(h.get("grade")) if h.get("grade") else None
                        for h in horses])
    nk_z = _zscores([h.get("nk_speed") for h in horses])
    own_z = _zscores([h.get("spd2") for h in horses])
    speed_resid = []
    for a, b in zip(nk_z, own_z):
        if a is None:
            speed_resid.append(None)
        elif b is None:
            speed_resid.append(a)  # no own speed: fall back to nk level
        else:
            speed_resid.append(a - b)  # residual: what nk sees beyond own spd2

    # trend features from the recent-index sequence (see speed_trend_features)
    trend = [speed_trend_features(h.get("nk_recent"), h.get("nk_avg5"),
                                  h.get("nk_best")) for h in horses]
    slope_z = _zscores([t["slope"] for t in trend])
    dev_z = _zscores([t["last_minus_avg5"] for t in trend])
    vol_z = _zscores([t["vol"] for t in trend])
    sd_z = _zscores([t["sd"] for t in trend])
    overlap = band_overlap_share([
        (t["mean_recent"], t["sd"])
        if t["mean_recent"] is not None and t["sd"] is not None else None
        for t in trend])
    overlap_z = _zscores(overlap)
    apt = [speed_aptitude_features(h.get("nk_dist"), h.get("nk_course"),
                                   t["last"], h.get("nk_avg5"))
           for h, t in zip(horses, trend)]
    fit_z = _zscores([a["fit_edge"] for a in apt])
    bias_z = _zscores([a["course_minus_dist"] for a in apt])
    combo = [combo_features(h.get("past_rides"), h.get("jockey"))
             for h in horses]
    combo_z = _zscores([c["combo_top3_shrunk"] for c in combo])
    closing = [closing_features(h.get("last3f_recent")) for h in horses]
    closing_z = _zscores([c["closing_dev"] for c in closing])
    nk_form_dev_z = _zscores([h.get("nk_form_dev") for h in horses])
    nk_ai_z = _zscores([h.get("nk_ai_score") for h in horses])
    course_front_z = _zscores([h.get("course_front") for h in horses])
    course_frame_z = _zscores([h.get("course_frame") for h in horses])
    odds_feats = [odds_movement_features(h.get("publish_win_odds"),
                                         h.get("final_win_odds"),
                                         h.get("place_odds_low"),
                                         h.get("place_odds_high"))
                  for h in horses]
    odds_drift_z = _zscores([f["odds_drift"] for f in odds_feats])
    odds_wp_gap_z = _zscores([f["odds_wp_gap"] for f in odds_feats])
    h2h_z = _zscores([h.get("h2h") for h in horses])
    mochitime_z = _zscores([h.get("mochitime") for h in horses])

    logits, detail = {}, []
    for i, h in enumerate(horses):
        base = math.log(max(h["v9b"], 1e-6))
        adj = base
        terms = {}
        if comment_z[i] is not None and w["comment"]:
            terms["comment"] = w["comment"] * comment_z[i]
        if grade_z[i] is not None and w["grade"]:
            terms["grade"] = w["grade"] * grade_z[i]
        if speed_resid[i] is not None and w["speed"]:
            terms["speed"] = w["speed"] * speed_resid[i]
        if slope_z[i] is not None and w.get("speed_slope"):
            terms["speed_slope"] = w["speed_slope"] * slope_z[i]
        if dev_z[i] is not None and w.get("speed_dev"):
            terms["speed_dev"] = w["speed_dev"] * dev_z[i]
        if vol_z[i] is not None and w.get("speed_vol"):
            terms["speed_vol"] = w["speed_vol"] * vol_z[i]
        if sd_z[i] is not None and w.get("speed_sd"):
            terms["speed_sd"] = w["speed_sd"] * sd_z[i]
        if overlap_z[i] is not None and w.get("speed_overlap"):
            terms["speed_overlap"] = w["speed_overlap"] * overlap_z[i]
        if fit_z[i] is not None and w.get("speed_fit"):
            terms["speed_fit"] = w["speed_fit"] * fit_z[i]
        if bias_z[i] is not None and w.get("speed_bias"):
            terms["speed_bias"] = w["speed_bias"] * bias_z[i]
        if combo_z[i] is not None and w.get("combo"):
            terms["combo"] = w["combo"] * combo_z[i]
        if closing_z[i] is not None and w.get("closing"):
            terms["closing"] = w["closing"] * closing_z[i]
        if nk_form_dev_z[i] is not None and w.get("nk_form_dev"):
            terms["nk_form_dev"] = w["nk_form_dev"] * nk_form_dev_z[i]
        if nk_ai_z[i] is not None and w.get("nk_ai"):
            terms["nk_ai"] = w["nk_ai"] * nk_ai_z[i]
        if course_front_z[i] is not None and w.get("course_front"):
            terms["course_front"] = w["course_front"] * course_front_z[i]
        if course_frame_z[i] is not None and w.get("course_frame"):
            terms["course_frame"] = w["course_frame"] * course_frame_z[i]
        if odds_drift_z[i] is not None and w.get("odds_drift"):
            terms["odds_drift"] = w["odds_drift"] * odds_drift_z[i]
        if odds_wp_gap_z[i] is not None and w.get("odds_wp_gap"):
            terms["odds_wp_gap"] = w["odds_wp_gap"] * odds_wp_gap_z[i]
        if h2h_z[i] is not None and w.get("h2h"):
            terms["h2h"] = w["h2h"] * h2h_z[i]
        if mochitime_z[i] is not None and w.get("mochitime"):
            terms["mochitime"] = w["mochitime"] * mochitime_z[i]
        for v in terms.values():
            adj += v
        logits[h["num"]] = adj
        detail.append({"num": h["num"], "comment_raw": raw_comment[i],
                       "comment_z": comment_z[i], "grade_z": grade_z[i],
                       "speed_resid_z": speed_resid[i],
                       "speed_trend": trend[i], "speed_aptitude": apt[i],
                       "combo": combo[i], "closing": closing[i],
                       "speed_slope_z": slope_z[i], "speed_dev_z": dev_z[i],
                       "speed_vol_z": vol_z[i], "speed_sd_z": sd_z[i],
                       "speed_overlap": overlap[i],
                       "speed_overlap_z": overlap_z[i],
                       "speed_fit_z": fit_z[i], "speed_bias_z": bias_z[i],
                       "terms": terms})
    mx = max(logits.values())
    ex = {k: math.exp(v - mx) for k, v in logits.items()}
    tot = sum(ex.values())
    probs = {k: v / tot for k, v in ex.items()}
    cov = {
        "runners": len(horses),
        "comment": sum(1 for v in raw_comment if v is not None),
        "grade": sum(1 for h in horses if h.get("grade")),
        "speed": sum(1 for h in horses if h.get("nk_speed") is not None),
        "speed_trend": sum(1 for t in trend if t["slope"] is not None),
        "speed_dev": sum(1 for t in trend if t["last_minus_avg5"] is not None),
        "speed_sd": sum(1 for t in trend if t["sd"] is not None),
        "speed_overlap": sum(1 for v in overlap if v is not None),
        "speed_fit": sum(1 for a in apt if a["fit_edge"] is not None),
        "speed_bias": sum(1 for a in apt if a["course_minus_dist"] is not None),
        "combo": sum(1 for c in combo if c["combo_starts"] > 0),
        "closing": sum(1 for c in closing if c["closing_dev"] is not None),
        "nk_form_dev": sum(1 for h in horses if h.get("nk_form_dev") is not None),
        "nk_ai": sum(1 for h in horses if h.get("nk_ai_score") is not None),
        "course_front": sum(1 for h in horses if h.get("course_front") is not None),
        "course_frame": sum(1 for h in horses if h.get("course_frame") is not None),
        "odds_drift": sum(1 for f in odds_feats if f["odds_drift"] is not None),
        "odds_wp_gap": sum(1 for f in odds_feats if f["odds_wp_gap"] is not None),
        "h2h": sum(1 for h in horses if h.get("h2h") is not None),
        "mochitime": sum(1 for h in horses if h.get("mochitime") is not None),
        "front_rate": sum(1 for h in horses if h.get("front_rate") is not None),
    }
    return probs, cov, detail

# ---------------------------------------------------------------- outputs
MARKS = ["◎", "○", "▲", "△", "☆"]

def marks_from_probs(probs):
    order = sorted(probs, key=lambda n: -probs[n])
    return [(MARKS[i], n, probs[n]) for i, n in enumerate(order[:5])], order

def _harville_pair(p, a, b):
    return p[a] * p[b] / (1 - p[a]) + p[b] * p[a] / (1 - p[b])

def _harville_triple_set(p, a, b, c):
    s = 0.0
    for x, y, z in permutations((a, b, c)):
        s += p[x] * (p[y] / (1 - p[x])) * (p[z] / (1 - p[x] - p[y]))
    return s

def tickets_from_probs(probs):
    """R24 point counts (wide 6 / umaren 4 / umatan 4 / sanrenpuku 6 /
    sanrentan 24) filled with the top combos by Harville joint probability --
    the same 'top joint-probability combos' rule the current R24 uses,
    applied to the integrated probabilities."""
    order = sorted(probs, key=lambda n: -probs[n])
    top = order[:6]
    pairs = [(a, b) for i, a in enumerate(top) for b in top[i + 1:]]
    wide = sorted(pairs, key=lambda ab: -_harville_pair(probs, *ab))[:6]
    umaren = sorted(pairs, key=lambda ab: -_harville_pair(probs, *ab))[:4]
    umatan_scored = []
    for a in top[:4]:
        for b in top[:4]:
            if a != b:
                umatan_scored.append(((a, b), probs[a] * probs[b] / (1 - probs[a])))
    umatan = [ab for ab, _ in sorted(umatan_scored, key=lambda x: -x[1])[:4]]
    triples = [(a, b, c) for i, a in enumerate(top) for j, b in enumerate(top) if j > i
               for c in top[j + 1:]]
    sanrenpuku = sorted(triples, key=lambda t: -_harville_triple_set(probs, *t))[:6]
    sanrentan = []
    for t in sanrenpuku:
        sanrentan.extend(permutations(t))
    # current R24 sanrentan has 24 points = permutations of the top-4 set;
    # if Harville triples involve >4 horses, trim to the 24 highest ordered
    if len(sanrentan) > 24:
        def ord_prob(t):
            x, y, z = t
            return probs[x] * (probs[y] / (1 - probs[x])) * (probs[z] / (1 - probs[x] - probs[y]))
        sanrentan = sorted(sanrentan, key=ord_prob, reverse=True)[:24]
    return {"ワイド": [list(x) for x in wide], "馬連": [list(x) for x in umaren],
            "馬単": [list(x) for x in umatan], "3連複": [list(x) for x in sanrenpuku],
            "3連単": [list(x) for x in sanrentan]}

def pace_layer(horses):
    """horses need front_rate. Returns the pace quantities stored in the
    evaluation and used to render the text (single source)."""
    known = [(h["num"], h["front_rate"]) for h in horses if h.get("front_rate") is not None]
    if len(known) < 3:
        return {"status": "insufficient", "likely_forward": [], "pressure": None,
                "label": "位置取り材料不足"}
    pressure = sum(v for _, v in known) / len(known)
    forward = [n for n, _ in sorted(known, key=lambda x: -x[1])[:3]]
    if pressure >= 0.42:
        label = "ハイペース想定"
    elif pressure <= 0.30:
        label = "スローペース想定"
    else:
        label = "平均ペース想定"
    return {"status": "ok", "likely_forward": forward, "pressure": round(pressure, 3),
            "label": label}

def pace_text(pace, names, mark_order):
    """Render the pace text from the evaluation's own pace layer, and append
    the integrated top-3 marks with their running styles so the displayed
    scenario and the marks visibly come from one evaluation."""
    if pace["status"] != "ok":
        return "展開：過去走の位置取り材料が不足しており、想定は未確定。"
    fwd = "、".join(f"{n}番{names.get(n, '')}" for n in pace["likely_forward"])
    return f"{pace['label']}。過去走の初角位置から前に行く候補は{fwd}。"
