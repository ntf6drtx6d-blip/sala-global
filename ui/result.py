# ui/result.py
# ACTION: REPLACE ENTIRE FILE

import streamlit as st


SALA_PRIMARY = "#1f4fbf"


def short_device_label(full_name):
    if " — " in full_name:
        return full_name.split(" — ", 1)[1]
    return full_name


def operating_mode_label():
    mode = st.session_state.get("operating_profile_mode", "Custom hours per day")
    hrs = float(st.session_state.get("required_hours", 12.0))

    if mode == "24/7":
        return "24/7 operation"
    if mode == "Dusk to dawn":
        return f"Dusk-to-Dawn ({hrs:.1f} hrs/day)"
    return f"Custom mode ({hrs:.1f} hrs/day)"


def annual_empty_battery_stats(results):
    pcts = []
    for _, r in results.items():
        pct = r.get("overall_empty_battery_pct")
        if pct is not None:
            try:
                pcts.append(float(pct))
            except Exception:
                pass

    if not pcts:
        return None, None

    worst_pct = max(pcts)
    worst_days = round(365 * worst_pct / 100.0)
    return worst_days, worst_pct


def overall_conclusion_text(results):
    mode_text = operating_mode_label()
    all_pass = all(r.get("status") == "PASS" for r in results.values())

    if all_pass:
        return f"All selected devices can operate in {mode_text} throughout the year."
    return f"Selected devices cannot sustain {mode_text} throughout the year."


def overall_interpretation_text(results):
    all_pass = all(r.get("status") == "PASS" for r in results.values())
    if all_pass:
        return "No seasonal blackout risk detected."
    return "Battery depletion risk appears during low-solar periods."


def device_short_comment(r):
    fail_months = r.get("fail_months", [])

    if r.get("status") == "PASS":
        return "Meets required operation all year"

    if len(fail_months) == 12:
        return "Below requirement in all months"

    if len(fail_months) >= 9:
        return f"Below requirement in most months ({len(fail_months)}/12)"

    if len(fail_months) >= 1:
        return f"Below requirement in {', '.join(fail_months)}"

    return "Below requirement in one or more months"


def device_empty_battery_line(r):
    pct = r.get("overall_empty_battery_pct")
    if pct is None:
        return "Days with empty battery: not available"

    try:
        pct = float(pct)
    except Exception:
        return "Days with empty battery: not available"

    days = round(365 * pct / 100.0)
    return f"Days with empty battery: {days} days/year ({pct:.1f}%)"


def device_worst_month_line(r):
    monthly_days = r.get("empty_battery_days_by_month")
    if not monthly_days:
        return "Worst month: not available"

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    idx = max(range(12), key=lambda i: monthly_days[i])
    worst_days = monthly_days[idx]
    return f"Worst month: {months[idx]} ({worst_days} days)"


def render_kpi_card(title, value, subtitle=""):
    st.markdown(
        f"""
        <div style="
            border:1px solid #e6eaf0;
            border-radius:16px;
            padding:18px 20px;
            background:#ffffff;
            min-height:148px;
            box-shadow: 0 2px 10px rgba(16,24,40,0.04);
            display:flex;
            flex-direction:column;
            justify-content:space-between;">
            <div style="font-size:0.95rem;color:#667085;font-weight:700;margin-bottom:10px;">{title}</div>
            <div style="font-size:2rem;color:#1f2937;font-weight:800;line-height:1.1;word-break:break-word;">{value}</div>
            <div style="font-size:0.93rem;color:#667085;margin-top:12px;line-height:1.4;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_device_card(device_name, r):
    label = short_device_label(device_name)
    status = r.get("status", "FAIL")
    status_bg = "#ecfdf3" if status == "PASS" else "#fef3f2"
    status_fg = "#067647" if status == "PASS" else "#b42318"

    st.markdown(
        f"""
        <div style="
            border:1px solid #e6eaf0;
            border-radius:16px;
            padding:16px 18px;
            background:#ffffff;
            box-shadow: 0 2px 10px rgba(16,24,40,0.04);
            margin-bottom:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
                <div style="font-size:1.1rem;font-weight:800;color:#1f2937;">{label}</div>
                <div style="
                    background:{status_bg};
                    color:{status_fg};
                    padding:6px 12px;
                    border-radius:999px;
                    font-weight:800;
                    font-size:0.92rem;">
                    {status}
                </div>
            </div>
            <div style="font-size:0.98rem;color:#344054;margin-top:14px;">
                {device_short_comment(r)}
            </div>
            <div style="font-size:0.95rem;color:#667085;margin-top:10px;">
                {device_empty_battery_line(r)}
            </div>
            <div style="font-size:0.95rem;color:#667085;margin-top:6px;">
                {device_worst_month_line(r)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_result():
    st.markdown(
        """
        <style>
        div[data-testid="stDownloadButton"] > button {
            background: #1f4fbf !important;
            color: white !important;
            border: 1px solid #1f4fbf !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            min-height: 48px !important;
        }
        div[data-testid="stDownloadButton"] > button:hover {
            background: #183f98 !important;
            border-color: #183f98 !important;
            color: white !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("## Decision summary")

    results = st.session_state.get("results", {})
    if not results:
        return

    all_pass = all(r.get("status") == "PASS" for r in results.values())
    days, pct = annual_empty_battery_stats(results)
    airport_name = st.session_state.get("airport_label", "") or "Selected study point"
    mode_text = operating_mode_label()

    box_bg = "#ecfdf3" if all_pass else "#fef3f2"
    box_fg = "#067647" if all_pass else "#b42318"
    border = "#abefc6" if all_pass else "#fecdca"

    left, right = st.columns([2.6, 1])

    with left:
        st.markdown(
            f"""
            <div style="
                border:1px solid {border};
                border-radius:18px;
                padding:22px 24px;
                background:{box_bg};
                box-shadow: 0 2px 10px rgba(16,24,40,0.04);">
                <div style="font-size:0.92rem;color:#667085;font-weight:700;margin-bottom:10px;">
                    Overall conclusion
                </div>
                <div style="font-size:2rem;line-height:1.2;font-weight:800;color:{box_fg};margin-bottom:12px;">
                    {overall_conclusion_text(results)}
                </div>
                <div style="font-size:1rem;color:#475467;">
                    {overall_interpretation_text(results)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown("### Report")
        if st.session_state.get("pdf_bytes") is not None:
            st.download_button(
                "📄 Download PDF report",
                data=st.session_state.get("pdf_bytes"),
                file_name=st.session_state.get("pdf_name", "sala_standardized_feasibility_study.pdf"),
                mime="application/pdf",
                use_container_width=True,
                key="summary_download_pdf_report",
            )

    st.markdown("### Key takeaways")

    c1, c2, c3 = st.columns(3)

    with c1:
        render_kpi_card(
            "Airport",
            airport_name,
            "Study location used for the feasibility assessment"
        )

    with c2:
        render_kpi_card(
            "Required operating mode",
            mode_text,
            "Applied requirement used for the study"
        )

    with c3:
        if days is None or pct is None:
            render_kpi_card(
                "Days with empty battery",
                "N/A",
                "PVGIS annual depletion metric not available"
            )
        else:
            render_kpi_card(
                "Days with empty battery",
                f"{days}",
                f"{pct:.1f}% of days per year"
            )

    st.markdown("### Results by device")

    for device_name, r in results.items():
        render_device_card(device_name, r)
