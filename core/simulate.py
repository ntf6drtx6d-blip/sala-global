
def compute_monthly_percentages(monthly_generation_wh_day, usable_battery_wh, power_w, hours):
    generated_pct = []
    consumed_pct = []

    for g in monthly_generation_wh_day:
        generated_pct.append((g / usable_battery_wh) * 100)
        consumed_pct.append((power_w * hours) / usable_battery_wh * 100)

    return generated_pct, consumed_pct


def build_reserve(monthly_generated_pct, monthly_consumed_pct, monthly_empty_days, days_in_month):
    reserve = []
    current = 100

    for m in range(12):
        days = days_in_month[m]
        empty_days = int(monthly_empty_days[m])

        for d in range(days):
            if d < empty_days:
                current = 0
            else:
                current = min(100, current + monthly_generated_pct[m] - monthly_consumed_pct[m])

            reserve.append(current)

    return reserve


# ======== BATTERY GRAPH ADDITIONS ========

def compute_monthly_percentages(monthly_generation_wh_day, usable_battery_wh, power_w, hours):
    generated_pct = []
    consumed_pct = []

    for g in monthly_generation_wh_day:
        generated_pct.append((g / usable_battery_wh) * 100)
        consumed_pct.append((power_w * hours) / usable_battery_wh * 100)

    return generated_pct, consumed_pct


def build_reserve(monthly_generated_pct, monthly_consumed_pct, monthly_empty_days, days_in_month):
    reserve_month_end = []
    current = 100

    for m in range(12):
        empty_days = int(monthly_empty_days[m])

        if empty_days > 0:
            current = 0
        else:
            current = min(100, current + (monthly_generated_pct[m] - monthly_consumed_pct[m]) * 30)

        reserve_month_end.append(current)

    return reserve_month_end

