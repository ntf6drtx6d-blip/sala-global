import os
import tempfile
import math
import requests
import matplotlib.pyplot as plt


# -------------------------
# STATIC MAP (NO BROWSER)
# -------------------------
def generate_static_map(lat, lon, zoom=12, size=(600, 400)):
    """
    Uses OpenStreetMap static tile (no API key needed).
    """

    url = (
        f"https://staticmap.openstreetmap.de/staticmap.php"
        f"?center={lat},{lon}&zoom={zoom}"
        f"&size={size[0]}x{size[1]}"
        f"&markers={lat},{lon},red-pushpin"
    )

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    path = tmp_file.name

    response = requests.get(url)
    with open(path, "wb") as f:
        f.write(response.content)

    return path


# -------------------------
# MONTHLY EMPTY BATTERY CHART
# -------------------------
def generate_monthly_chart(result):
    """
    result must contain:
    result["monthly_empty_battery_days"] = [12 values]
    """

    data = result.get("monthly_empty_battery_days", [])
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    if not data:
        return None

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    path = tmp_file.name

    plt.figure(figsize=(8, 3))
    plt.bar(months, data)
    plt.title("Monthly empty-battery days")
    plt.ylabel("Days")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(path)
    plt.close()

    return path


# -------------------------
# ANNUAL PROFILE CHART
# -------------------------
def generate_annual_profile_chart(result, required_hours):
    """
    result must contain:
    result["monthly_achieved_hours"] = [12 values]
    """

    achieved = result.get("monthly_achieved_hours", [])
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    if not achieved:
        return None

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    path = tmp_file.name

    plt.figure(figsize=(8, 3))
    plt.plot(months, achieved, marker="o")
    plt.axhline(required_hours, linestyle="--")
    plt.title("Annual operating profile")
    plt.ylabel("Hours per day")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(path)
    plt.close()

    return path


# -------------------------
# MAIN PIPELINE
# -------------------------
def generate_all_assets(loc, results, required_hours):
    """
    Returns:
    map_path, monthly_chart_path, annual_chart_path
    """

    lat = loc.get("lat")
    lon = loc.get("lon")

    # pick first device (or worst later if needed)
    first = list(results.values())[0]

    map_path = generate_static_map(lat, lon)
    monthly_chart = generate_monthly_chart(first)
    annual_chart = generate_annual_profile_chart(first, required_hours)

    return map_path, monthly_chart, annual_chart
