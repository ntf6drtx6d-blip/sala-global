
from datetime import datetime

def build_report_data(loc, required_hours, results, overall, user_name):
    devices = []
    pass_count = 0
    max_blackout = 0

    for _, r in results.items():
        name = r.get("device_code", "Device")
        pct = float(r.get("overall_empty_battery_pct", 0))
        days = int(pct * 3.65)

        if days == 0:
            status = "PASS"; pass_count += 1
        elif days <= 3:
            status = "NEAR"
        else:
            status = "FAIL"

        max_blackout = max(max_blackout, days)

        devices.append({"name": name, "days": days, "status": status})

    return {
        "airport": loc.get("label", "Study point"),
        "coords": f"{loc.get('lat')}, {loc.get('lon')}",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "user": user_name,
        "doc_id": f"SALA-{datetime.now().strftime('%Y%m%d%H%M')}",
        "required": required_hours,
        "devices": devices,
        "pass_count": pass_count,
        "total": len(devices),
        "max_blackout": max_blackout
    }
