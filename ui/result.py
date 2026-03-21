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

        if r["status"] == "PASS":
            comment = "Meets required daily operation all year"
        else:
            fail_months = ", ".join(r["fail_months"]) if r["fail_months"] else "one or more months"
            comment = f"Below requirement in {fail_months}"

        rows.append({
            "Device": label,
            "Result": r["status"],
            "Comment": comment,
        })

    return pd.DataFrame(rows)


def recommendation_text(results, required_hrs):
    failing = []
    passing = []

    for key, r in results.items():
        label = short_device_label(key)
        if r["status"] == "PASS":
            passing.append(label)
        else:
            failing.append((label, r["fail_months"]))

    if not failing:
        return (
            f"All selected devices meet the planned daily operating requirement "
            f"of {required_hrs:.1f} hrs/day across the full annual cycle."
        )

    parts = []
    for label, months in failing:
        month_text = ", ".join(months) if months else "one or more months"
        parts.append(f"{label} is below target in {month_text}")

    return (
        f"Some selected devices do not meet the planned daily operating requirement "
        f"of {required_hrs:.1f} hrs/day. " + "; ".join(parts) + "."
    )


def render_result():
    st.markdown("## Decision summary")

    results = st.session_state.results
    overall = st.session_state.overall
    required_hours = float(st.session_state.required_hours)

    summary_df = checked_devices_summary(results)

    # Top compact banner
    left, right = st.columns([2.5, 1])

    with left:
        if overall == "PASS":
            st.success("Annual feasibility result: PASS")
        else:
            st.error("Annual feasibility result: FAIL")

        st.write(recommendation_text(results, required_hours))

    with right:
        st.markdown("### Report")
        if st.session_state.pdf_bytes is not None:
            st.download_button(
                "Download report",
                data=st.session_state.pdf_bytes,
                file_name=st.session_state.pdf_name,
                mime="application/pdf",
                use_container_width=True,
            )

    st.markdown("### Results by device")

    # Show one clean row per device
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
