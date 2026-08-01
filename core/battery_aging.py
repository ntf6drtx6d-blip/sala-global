# core/battery_aging.py
#
# Phase-1 rule-of-thumb battery aging model.
#
# Combines two independent, additive degradation mechanisms:
#   - Calendar aging: capacity fade from time + average site temperature,
#     independent of use ("Arrhenius / 10C rule").
#   - Cycle aging: capacity fade from actual charge/discharge cycling,
#     derated by depth of discharge (DoD) using published cycle-life-vs-DoD
#     reference points per chemistry.
#
# This is NOT a manufacturer-certified prediction. Every constant below is a
# published rule-of-thumb estimate sourced from general battery-industry
# literature (see comments per table), not a specific product's tested data.
# Report/UI surfaces built on this must be labeled as a SALA estimate, the
# same way Avlite specs are already flagged "Estimated by SALA" vs S4GA's
# "Verified by SALA".

from __future__ import annotations

# ---------------------------------------------------------------------------
# Calendar aging: capacity fade purely from elapsed time + average
# temperature, independent of cycling.
#
# Rule: "life halves for every `halving_temp_delta_c` rise above
# `reference_temp_c`" (Arrhenius approximation). For lead-acid this is a
# widely-cited, industry-standard convention for float/design-life
# derating (e.g. VRLA float-life literature: "for every 10C increase in
# temperature beyond 25C, float life is cut in half"). LiFePO4 and NiMH are
# markedly less temperature-sensitive on calendar life; those halving
# deltas are wider (gentler slope) approximations rather than a single
# crisp published constant the way the lead-acid 10C rule is.
#
# `baseline_life_years` = years to reach END_OF_LIFE_RETENTION_PCT capacity
# retention at the reference temperature, with no cycling contribution.
CALENDAR_AGING = {
    "Lead Acid": {
        "reference_temp_c": 25.0,
        "halving_temp_delta_c": 10.0,
        "baseline_life_years": 5.0,
        "confidence": "high - widely-cited Arrhenius/10C rule for lead-acid float/calendar life",
    },
    "LiFePO4": {
        "reference_temp_c": 25.0,
        "halving_temp_delta_c": 20.0,
        "baseline_life_years": 10.0,
        "confidence": "medium - LiFePO4 calendar aging is well-documented as temperature-driven, "
        "but a single halving-delta constant here is a coarser approximation than the lead-acid rule",
    },
    "NiMH": {
        "reference_temp_c": 25.0,
        "halving_temp_delta_c": 15.0,
        "baseline_life_years": 6.0,
        "confidence": "low - sparse published NiMH calendar-aging data for this application; "
        "estimated by analogy between lead-acid and lithium behavior",
    },
}

# "End of rated life" is conventionally defined in industry cycle-life
# ratings as 80% capacity retention (a 20 percentage-point fade budget).
# Used for both the calendar and cycle components below so they combine on
# a consistent basis.
END_OF_LIFE_RETENTION_PCT = 80.0
FADE_BUDGET_PCT = 100.0 - END_OF_LIFE_RETENTION_PCT

# A single shared age horizon for every chemistry, deliberately, for two
# reasons. First, comparability: devices of different chemistries need to
# land on the same x-axis to be visually compared against each other.
# Second, and more importantly, honesty about how far this model's
# confidence actually extends: LiFePO4's real-world service life depends
# heavily on factors this rule-of-thumb model doesn't capture at all (most
# notably state-of-charge during storage - cells held near-full age
# calendar-wise much faster than cells held at low charge, and a solar-
# charged battery spends a lot of its life near-full). A longer,
# chemistry-specific horizon for LiFePO4 was tried and rolled back because
# it implied more confidence in that chemistry's multi-year durability
# than the underlying published data actually supports for this
# application. Lead-acid's 5-year figure is the best-sourced of the three
# chemistries (a widely-cited Arrhenius/10C rule for lead-acid calendar
# life), so it sets the shared horizon for all of them.
DEFAULT_CHECKPOINT_YEARS = (0, 1, 2, 3, 5)


def suggested_checkpoint_years(battery_type: str) -> tuple:
    """Kept as a per-chemistry-aware function (rather than a bare
    constant) so callers don't need to change if a future revision
    reintroduces chemistry-specific horizons with better-sourced figures."""
    return DEFAULT_CHECKPOINT_YEARS

# ---------------------------------------------------------------------------
# Cycle aging: published cycle-life-vs-depth-of-discharge reference points
# per chemistry, as (dod_fraction, cycles_to_80pct_retention), DoD expressed
# as a fraction of nameplate (total) capacity cycled per day, sorted
# ascending by DoD. Interpolated linearly between points.
#
# Lead Acid figures are representative of commonly-published deep-cycle
# lead-acid ranges (roughly 1600 cycles at 20% DoD down to ~250-300 cycles
# at 80-100% DoD).
#
# LiFePO4 figures are deliberately conservative - the lower end of a wide
# manufacturer spread that runs roughly 2,500-8,000 cycles at 50-100% DoD
# depending on cell/brand - and additionally derated ~15% to reflect
# published field-vs-datasheet degradation gaps (real-world cycle life
# commonly runs 10-20% below lab datasheet ratings per NREL field studies).
#
# NiMH has the least available published data for this exact application;
# figures are an estimate by analogy, flagged low-confidence.
CYCLE_LIFE_VS_DOD = {
    "Lead Acid": [
        (0.20, 1600),
        (0.30, 1250),
        (0.50, 650),
        (0.80, 275),
        (1.00, 250),
    ],
    "LiFePO4": [
        (0.50, 4700),
        (0.80, 3400),
        (1.00, 2100),
    ],
    "NiMH": [
        (0.20, 1800),
        (0.50, 900),
        (0.80, 400),
        (1.00, 350),
    ],
}

MIN_CAPACITY_RETENTION_PCT = 40.0  # floor so the model doesn't run away toward 0%


def normalize_chemistry(battery_type: str) -> str:
    raw = str(battery_type or "").strip().upper()
    if "LIFEPO4" in raw or "LFP" in raw:
        return "LiFePO4"
    if "NIMH" in raw:
        return "NiMH"
    return "Lead Acid"


def _interpolate_cycle_life(chemistry: str, dod_fraction: float) -> float:
    points = CYCLE_LIFE_VS_DOD.get(chemistry, CYCLE_LIFE_VS_DOD["Lead Acid"])
    dod = max(0.01, min(1.0, float(dod_fraction)))

    if dod <= points[0][0]:
        return points[0][1]
    if dod >= points[-1][0]:
        return points[-1][1]

    for (d0, c0), (d1, c1) in zip(points, points[1:]):
        if d0 <= dod <= d1:
            if d1 == d0:
                return c0
            t = (dod - d0) / (d1 - d0)
            return c0 + t * (c1 - c0)
    return points[-1][1]


def calendar_fade_pct_per_year(battery_type: str, avg_site_temp_c: float) -> float:
    chemistry = normalize_chemistry(battery_type)
    params = CALENDAR_AGING[chemistry]
    accel = 2.0 ** ((float(avg_site_temp_c) - params["reference_temp_c"]) / params["halving_temp_delta_c"])
    return (FADE_BUDGET_PCT / params["baseline_life_years"]) * accel


def cycle_fade_pct_per_year(battery_type: str, dod_fraction_per_cycle: float, cycles_per_year: float) -> float:
    chemistry = normalize_chemistry(battery_type)
    rated_cycles = _interpolate_cycle_life(chemistry, dod_fraction_per_cycle)
    if rated_cycles <= 0:
        return 0.0
    return (max(0.0, float(cycles_per_year)) / rated_cycles) * FADE_BUDGET_PCT


def project_capacity_retention_pct(
    battery_type: str,
    avg_site_temp_c: float,
    dod_fraction_per_cycle: float,
    cycles_per_year: float,
    age_years: float,
) -> float:
    """Capacity retention (% of nameplate) after `age_years`, combining
    calendar and cycle fade additively - the standard simplified approach
    for this class of rule-of-thumb estimate."""
    annual_fade = calendar_fade_pct_per_year(battery_type, avg_site_temp_c) + cycle_fade_pct_per_year(
        battery_type, dod_fraction_per_cycle, cycles_per_year
    )
    retained = 100.0 - annual_fade * max(0.0, float(age_years))
    return max(MIN_CAPACITY_RETENTION_PCT, retained)


def dominant_fade_mechanism(
    battery_type: str,
    avg_site_temp_c: float,
    dod_fraction_per_cycle: float,
    cycles_per_year: float,
) -> str:
    """Which mechanism contributes more to the annual fade rate - used to
    explain *why* a device ages quickly (hot site vs. deep daily cycling)
    rather than just showing a number."""
    cal = calendar_fade_pct_per_year(battery_type, avg_site_temp_c)
    cyc = cycle_fade_pct_per_year(battery_type, dod_fraction_per_cycle, cycles_per_year)
    if cal <= 0 and cyc <= 0:
        return "none"
    return "temperature" if cal >= cyc else "cycling"


def dod_fraction_and_cycles_per_year(discharge_pct_per_day: float, cutoff_pct: float) -> tuple[float, float]:
    """Derive depth-of-discharge (as a fraction of nameplate capacity) and
    an equivalent-full-cycles-per-year estimate from data the simulation
    already computes - no new inputs needed beyond what core/simulate.py
    produces today.

    discharge_pct_per_day is expressed as % of *usable* battery capacity
    (see core/simulate.py's _battery_behavior_metrics); this converts it to
    a fraction of *nameplate* capacity, which is the basis published
    cycle-life-vs-DoD figures use. Phase 1 assumes one discharge/recharge
    cycle per day (standard for a solar-charged, nightly-discharged
    off-grid system), so cycles_per_year is simply 365.
    """
    usable_share = max(0.0, 1.0 - float(cutoff_pct or 0.0) / 100.0)
    dod_fraction = max(0.0, float(discharge_pct_per_day or 0.0)) / 100.0 * usable_share
    cycles_per_year = 365.0
    return dod_fraction, cycles_per_year
