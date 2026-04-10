
from typing import Dict, List

def _safe_div(a, b):
    return a / b if b else 0.0

def _expand_monthly_to_daily(monthly_values: List[float], days_in_month: List[int]) -> List[float]:
    daily = []
    for m, v in enumerate(monthly_values):
        d = days_in_month[m] if m < len(days_in_month) else 30
        daily.extend([v] * d)
    return daily

def _aggregate_weekly(series: List[float]) -> List[float]:
    weeks = []
    for i in range(0, len(series), 7):
        chunk = series[i:i+7]
        if chunk:
            weeks.append(sum(chunk) / len(chunk))
    return weeks

def build_weekly_battery_behavior(
    monthly_generation_wh_day: List[float],
    monthly_days: List[int],
    load_wh_per_day: float,
    battery_wh: float,
    cutoff_pct: float,
) -> Dict[str, List[float]]:

    usable_wh = battery_wh * (1.0 - cutoff_pct)
    if usable_wh <= 0:
        return {"weekly_soc": [], "weekly_recharge": [], "weekly_discharge": []}

    daily_gen = _expand_monthly_to_daily(monthly_generation_wh_day, monthly_days)

    soc = usable_wh
    soc_series = []
    recharge_series = []
    discharge_series = []

    for g in daily_gen:
        recharge_wh = max(g, 0.0)
        discharge_wh = max(load_wh_per_day, 0.0)

        net = recharge_wh - discharge_wh
        soc += net

        if soc > usable_wh:
            soc = usable_wh
        if soc < 0:
            soc = 0

        soc_pct = _safe_div(soc, usable_wh) * 100.0
        recharge_pct = _safe_div(recharge_wh, usable_wh) * 100.0
        discharge_pct = _safe_div(discharge_wh, usable_wh) * 100.0

        soc_series.append(soc_pct)
        recharge_series.append(recharge_pct)
        discharge_series.append(discharge_pct)

    return {
        "weekly_soc": _aggregate_weekly(soc_series),
        "weekly_recharge": _aggregate_weekly(recharge_series),
        "weekly_discharge": _aggregate_weekly(discharge_series),
    }
