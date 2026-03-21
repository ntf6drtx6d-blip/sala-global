# ui/result.py
# ACTION: REPLACE ENTIRE FILE

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
        if r.get("status") == "PASS":
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
            "Result": r.get("status", "FAIL"),
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
    return f"custom operation ({hrs:.1f} hrs/day)"


def empty_battery_message(results):
    pcts = []
    for _, r in results.items():
        pct = r.get("overall_empty_battery_pct")
        if pct is not None:
            try:
                pcts.append(float(pct))
            except Exception:
                pass

    if not pcts:
        return "Days with empty battery: not available"

    worst_pct = max(pcts)
    days = round(365 * worst_pct / 100.0)

    if worst_pct <= 0:
        return "Days with empty battery: 0 days/year (0%)"

    return f"Days with empty battery: {days} days/year ({worst_pct:.1f}%)"


def main_result_message(results):
    mode_text = operating_mode_label()
    all_pass = all(r.get("status") == "PASS" for r in results.values())

    if all_pass:
        return f"All selected devices can operate in {mode_text} throughout the year."
    return f"Selected devices cannot sustain {mode_text} throughout the year."


def secondary_result_message(results):
    all_pass = all(r.get("status") == "PASS" for r in results.values())
    if all_pass:
        return "No seasonal blackout risk detected."
    return "Battery depletion risk appears during low-solar periods."


def render_result():
    st.markdown("## Decision summary")

    results = st.session_state.get("results", {})
    if not results:
        return

    summary_df = checked_devices_summary(results)

    left, right = st.columns([2.6, 1])

    with left:
        if all(r.get("status") == "PASS" for r in results.values()):
            st.success(main_result_message(results))
        else:
            st.error(main_result_message(results))

        st.write(empty_battery_message(results))
        st.caption(secondary_result_message(results))

    with right:
        st.markdown("### Report")
        if st.session_state.get("pdf_bytes") is not None:
            st.download_button(
                "Download report",
                data=st.session_state.get("pdf_bytes"),
                file_name=st.session_state.get("pdf_name", "sala_standardized_feasibility_study.pdf"),
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button("Download report", disabled=True, use_container_width=True)

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
