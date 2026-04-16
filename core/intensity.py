from __future__ import annotations


def format_intensity_summary(
    intensity_mode: str = "fixed",
    intensity_pct: float | int = 100,
    mixed_share_pct: float | int = 50,
    mixed_intensity_a: float | int = 30,
    mixed_intensity_b: float | int = 100,
    effective_intensity_pct: float | int | None = None,
    language: str = "en",
) -> str:
    mode = str(intensity_mode or "fixed").lower()
    fixed = float(intensity_pct or 100)
    share_a = max(0.0, min(100.0, float(mixed_share_pct or 0)))
    share_b = max(0.0, 100.0 - share_a)
    a = float(mixed_intensity_a or 0)
    b = float(mixed_intensity_b or 0)
    avg = float(effective_intensity_pct if effective_intensity_pct is not None else fixed)

    if mode == "mixed":
        options = {
            "en": f"{share_a:.0f}% of day at {a:.0f}% + {share_b:.0f}% at {b:.0f}% (avg {avg:.1f}%)",
            "es": f"{share_a:.0f}% del día al {a:.0f}% + {share_b:.0f}% al {b:.0f}% (prom. {avg:.1f}%)",
            "fr": f"{share_a:.0f}% de la journée à {a:.0f}% + {share_b:.0f}% à {b:.0f}% (moy. {avg:.1f}%)",
        }
        return options.get(language, options["en"])

    options = {
        "en": f"Fixed {fixed:.0f}%",
        "es": f"Fijo {fixed:.0f}%",
        "fr": f"Fixe {fixed:.0f}%",
    }
    return options.get(language, options["en"])
