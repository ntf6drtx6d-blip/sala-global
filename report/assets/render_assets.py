import tempfile
import matplotlib.pyplot as plt

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]


def generate_static_map(lat, lon):
    # fallback simple map
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

    fig, ax = plt.subplots()
    ax.scatter([0], [0])
    ax.set_title(f"{lat}, {lon}")
    ax.set_xticks([])
    ax.set_yticks([])

    fig.savefig(tmp.name)
    plt.close(fig)

    return tmp.name


def generate_monthly_chart(result):
    data = result.get("empty_battery_days_by_month")
    if not data:
        return None

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

    plt.bar(MONTHS, data)
    plt.title("Monthly empty battery days")
    plt.savefig(tmp.name)
    plt.close()

    return tmp.name


def generate_annual_profile_chart(result, required_hours):
    hours = result.get("hours")
    if not hours:
        return None

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

    plt.plot(MONTHS, hours)
    plt.axhline(required_hours)
    plt.title("Annual profile")
    plt.savefig(tmp.name)
    plt.close()

    return tmp.name


def generate_all_assets(loc, results, required_hours):
    first = list(results.values())[0]

    return (
        generate_static_map(loc["lat"], loc["lon"]),
        generate_monthly_chart(first),
        generate_annual_profile_chart(first, required_hours),
    )
