# ui/result.py
# ACTION: REPLACE ENTIRE FILE

import math
import streamlit as st
import pandas as pd


def short_device_label(full_name):
    if " — " in full_name:
        return full_name.split(" — ", 1)[1]
    return full_name


def checked_devices_summary(results):
    rows = []
    for key, r in results.items():
        label = short_device_label(key)

        fail_months = r.get("fail_months", [])
        if r["status"] == "PASS":
            comment = "Meets required operation all year"
        else:
            if len(fail_months) == 12:
                comment = "Below requirement in all months"
            elif fail_months:
                comment = f"Below requirement in {', '.join(fail_months)}"
            else:
                comment = "Below requirement in one or more months"

        rows.append({
            "Device": label,
            "Result": r["status"],
            "Comment": comment,
        })

    return pd.DataFrame(rows)


def operating_mode_label():
    mode = st.session_state.get("operating_profile_mode", "Custom hours per day")
    hrs = float(st.session_state.get("required_hours", 12.0))

    if mode == "24/7":
        return "24/7 operation"
    if mode == "Dusk to dawn":
        return f"Dusk-to-Dawn operation ({hrs:.1f} hrs/day)"
    return f"Custom operation ({hrs:.1f} hrs/day)"


def estimate_empty_battery_days(results):
    """
    Conservative but simple UI-facing metric:
    count device-month failures and convert to a percentage of device-months.
    Also estimate equivalent days/year for communication.
    """
    total_devices = max(len(results), 1)
    total_month_slots = total_devices * 12

    failed_month_slots = 0
    for _, r in results.items():
        failed_month_slots += len(r.get("fail_months", []))

    pct = (failed_month_slots / total_month_slots) * 100.0 if total_month_slots else 0.0

    # Convert month-slot failure proportion into approximate days/year.
    # UI metric only; keeps communication simple and intuitive.
    approx_days = round((pct / 100.0) * 365)

    return approx_days, pct


def main_result_message(results):
    mode_text = operating_mode_label()
    all_pass = all(r["status"] == "PASS" for r in results.values())

    if all_pass:
        return f"All selected devices can operate in {mode_text} throughout the year."
    return f"Selected devices cannot sustain {mode_text} throughout the year."


def secondary_result_message(results):
    approx_days, pct = estimate_empty_battery_days(results)

    if approx_days == 0:
        return "Days with empty battery: 0 days/year (0%)"
    return f"Days with empty battery: {approx_days} days/year ({pct:.1f}%)"


def tertiary_result_message(results):
    all_pass = all(r["status"] == "PASS" for r in results.values())
    if all_pass:
        return "No seasonal blackout risk detected."
    return "Battery depletion risk appears during low-solar periods."


def render_result():
    st.markdown("## Decision summary")

    results = st.session_state.results
    if not results:
        return

    summary_df = checked_devices_summary(results)

    left, right = st.columns([2.6, 1])

    with left:
        if all(r["status"] == "PASS" for r in results.values()):
            st.success(main_result_message(results))
        else:
            st.error(main_result_message(results))

        st.write(secondary_result_message(results))
        st.caption(tertiary_result_message(results))

    with right:
        st.markdown("### Report")
        if st.session_state.get("pdf_bytes") is not None:
            st.download_button(
                "Download report",
                data=st.session_state.pdf_bytes,
                file_name=st.session_state.pdf_name,
                mime="application/pdf",
                use_container_width=True,
            )

    st.markdown("### Results by device")

    for _, row in summary_df.iterrows():
        c1, c2, c3 = st.columns([1.2, 1, 3])

        with c1:
            st.markdown(f"**{row['Device']}**")

        with c2:
            if row["Result"] == "PASS":
                st.success("PASS")
            else:
                st.error("FAIL")

        with c3:
            st.write(row["Comment"])
