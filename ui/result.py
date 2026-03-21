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
            comment = "Meets required operation all year"
        else:
            comment = f"Fails in {', '.join(r['fail_months'])}"
        rows.append({
            "Device": label,
            "Result": r["status"],
            "Comment": comment,
        })
    return pd.DataFrame(rows)


def recommendation_text(results, required_hrs):
    fail_rows = []
    for key, r in results.items():
        if r["status"] == "FAIL":
            fail_rows.append((short_device_label(key), r["fail_months"]))

    if not fail_rows:
        return (
            f"All selected configurations meet the required operating profile of "
            f"{required_hrs:.1f} hrs/day across the full annual cycle."
        )

    parts = []
    for device, fail_months in fail_rows:
        months = ", ".join(fail_months) if fail_months else "one or more months"
        parts.append(f"{device} fails in {months}")

    return (
        "Some selected configurations do not meet the required daily operating profile. "
        + "; ".join(parts)
        + "."
    )


def render_result():
    st.markdown("## Decision summary")

    results = st.session_state.results
    overall = st.session_state.overall

    # Compact result banner
    c1, c2, c3 = st.columns([1, 2.2, 1.2])

    with c1:
        if overall == "PASS":
            st.success("PASS")
        else:
            st.error("FAIL")

    with c2:
        st.markdown("### Checked devices")
        summary_df = checked_devices_summary(results)

        for _, row in summary_df.iterrows():
            icon = "🟢" if row["Result"] == "PASS" else "🔴"
            st.write(f"{icon} **{row['Device']}** — {row['Result']}")
            st.caption(row["Comment"])

        st.markdown("### Conclusion")
        st.write(recommendation_text(results, st.session_state.required_hours))

    with c3:
        st.markdown("### Report")
        if st.session_state.pdf_bytes is not None:
            st.download_button(
                "Download report",
                data=st.session_state.pdf_bytes,
                file_name=st.session_state.pdf_name,
                mime="application/pdf",
                use_container_width=True,
            )
