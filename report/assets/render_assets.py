import tempfile
import requests
import matplotlib.pyplot as plt


# -------------------------
# STATIC MAP
# -------------------------
def generate_static_map(lat, lon):
    url = (
        f"https://staticmap.openstreetmap.de/staticmap.php"
        f"?center={lat},{lon}&zoom=12&size=600x400"
        f"&markers={lat},{lon},red-pushpin"
    )

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    path = tmp.name

    r = requests.get(url)
    with open(path, "wb") as f:
        f.write(r.content)

    return path


# -------------------------
# MONTHLY CHART
# -------------------------
def generate_monthly_chart(result):
    data = result.get("monthly_empty_battery_days", [])
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    if not data:
        return None

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    path = tmp.name

    plt.figure(figsize=(8,3))
    plt.bar(months, data)
    plt.title("Monthly empty-battery days")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()

    return path


# -------------------------
# ANNUAL CHART
# -------------------------
def generate_annual_chart(result, required_hours):
    data = result.get("monthly_achieved_hours", [])
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    if not data:
        return None

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    path = tmp.name

    plt.figure(figsize=(8,3))
    plt.plot(months, data, marker="o")
    plt.axhline(required_hours, linestyle="--")
    plt.title("Annual operating profile")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()

    return path


# -------------------------
# MAIN
# -------------------------
def generate_all_assets(loc, results, required_hours):
    lat = loc.get("lat")
    lon = loc.get("lon")

    first = list(results.values())[0]

    map_path = generate_static_map(lat, lon)
    monthly = generate_monthly_chart(first)
    annual = generate_annual_chart(first, required_hours)

    return map_path, monthly, annual
