import tempfile
import requests
import matplotlib.pyplot as plt


# -------------------------
# MAP (SAFE)
# -------------------------
def generate_static_map(lat, lon, zoom=12, size=(600, 400)):
    url = (
        f"https://staticmap.openstreetmap.de/staticmap.php"
        f"?center={lat},{lon}&zoom={zoom}"
        f"&size={size[0]}x{size[1]}"
        f"&markers={lat},{lon},red-pushpin"
    )

    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        r = requests.get(url, timeout=3)
        r.raise_for_status()

        with open(tmp.name, "wb") as f:
            f.write(r.content)

        return tmp.name

    except Exception:
        return None


# -------------------------
# MONTHLY EMPTY BATTERY
# -------------------------
def generate_monthly_chart(result):
    data = result.get("monthly_empty_battery_days")

    if not data:
        return None

    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

    plt.figure(figsize=(8, 3))
    plt.bar(months, data)
    plt.title("Monthly empty-battery days")
    plt.ylabel("Days")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(tmp.name)
    plt.close()

    return tmp.name


# -------------------------
# ANNUAL PROFILE
# -------------------------
def generate_annual_profile_chart(result, required_hours):
    achieved = result.get("monthly_achieved_hours")

    if not achieved:
        return None

    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

    plt.figure(figsize=(8, 3))
    plt.plot(months, achieved, marker="o")
    plt.axhline(required_hours, linestyle="--")
    plt.title("Annual operating profile")
    plt.ylabel("Hours/day")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(tmp.name)
    plt.close()

    return tmp.name


# -------------------------
# MAIN ENTRY
# -------------------------
def generate_all_assets(loc, results, required_hours):
    lat = loc.get("lat")
    lon = loc.get("lon")

    first = list(results.values())[0]

    # MAP
    try:
        map_path = generate_static_map(lat, lon)
    except:
        map_path = None

    # CHARTS
    try:
        monthly = generate_monthly_chart(first)
    except:
        monthly = None

    try:
        annual = generate_annual_profile_chart(first, required_hours)
    except:
        annual = None

    return map_path, monthly, annual
