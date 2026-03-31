from pathlib import Path
import tempfile
import requests
import matplotlib.pyplot as plt


def generate_static_map(lat: float, lon: float):
    url = (
        f"https://staticmap.openstreetmap.de/staticmap.php"
        f"?center={lat},{lon}&zoom=10&size=700x380"
        f"&markers={lat},{lon},red-pushpin"
    )
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "SALA-Feasibility-Study/1.0"})
        resp.raise_for_status()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        Path(tmp.name).write_bytes(resp.content)
        return tmp.name
    except Exception:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        fig, ax = plt.subplots(figsize=(7, 3.8))
        ax.set_facecolor("#F8FAFC")
        ax.scatter([lon], [lat], s=110)
        ax.annotate(f"{lat:.4f}, {lon:.4f}", (lon, lat), xytext=(8, 8), textcoords="offset points")
        ax.set_title("Study point")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        fig.tight_layout()
        fig.savefig(tmp.name, dpi=180, bbox_inches="tight")
        plt.close(fig)
        return tmp.name
