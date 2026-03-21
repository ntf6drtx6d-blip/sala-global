# ui/battery.py
# ACTION: REPLACE ENTIRE FILE

import streamlit as st


def short_device_label(full_name):
    if " — " in full_name:
        return full_name.split(" — ", 1)[1]
    return full_name


def calc_battery_reserve_hours(result_row):
    """
    Battery reserve = usable battery energy / consumption
    Usable battery assumed at 70%
    """
    batt = float(result_row["batt"])
    power = max(float(result_row["power"]), 0.01)
    return batt * 0.70 / power


def visual_ratio(value, scale_max):
    if scale_max <= 0:
        return 0.0
    return min(max(value / scale_max, 0.0), 1.0)


def result_badge(status):
    if status == "PASS":
        st.success("PASS")
    else:
        st.error("FAIL")


def render_battery():
    st.markdown("## Battery reserve vs daily solar sustainability")

    st.caption(
        "Battery reserve is not the same as annual solar feasibility. "
        "Battery reserve shows how long the lamp can operate from stored battery energy only. "
        "Annual solar feasibility shows whether the system can maintain the required daily operating pattern throughout the year."
    )

    results = st.session_state.results
    required_hours = float(st.session_state.required_hours)

    if not results:
        return

    for device_name, r in results.items():
        label = short_device_label(device_name)
        reserve = calc_battery_reserve_hours(r)
        annual_result = r["status"]
        fail_months = ", ".join(r["fail_months"]) if r["fail_months"] else "None"

        st.markdown(f"### {label}")

        top_left, top_mid, top_right = st.columns([1.3, 1.1, 1.0])

        with top_left:
            st.markdown("**Battery reserve**")
            st.metric("Stored energy only", f"{reserve:.1f} hrs")

        with top_mid:
            st.markdown("**Required daily operation**")
            st.metric("Target", f"{required_hours:.1f} hrs/day")

        with top_right:
            st.markdown("**Annual solar result**")
            result_badge(annual_result)

        # Visual comparison bars
        st.markdown("**Visual comparison**")

        bar_left, bar_right = st.columns([1, 1])

        # choose visual max so both bars are readable
        scale_max = max(24.0, reserve, required_hours)

        with bar_left:
            st.write("Battery reserve")
            st.progress(
                visual_ratio(reserve, scale_max),
                text=f"{reserve:.1f} hrs available from battery only"
            )

        with bar_right:
            st.write("Required daily operation")
            st.progress(
                visual_ratio(required_hours, scale_max),
                text=f"{required_hours:.1f} hrs/day required"
            )

        if annual_result == "PASS":
            st.caption(
                f"{label} has battery reserve and also passes the annual solar feasibility check. "
                f"It can sustain the required daily operation across the full year."
            )
        else:
            st.caption(
                f"{label} may still have usable battery reserve ({reserve:.1f} hrs from stored energy), "
                f"but this does not mean it can operate {required_hours:.1f} hrs/day every day throughout the year. "
                f"Annual limiting months: {fail_months}."
            )

        st.markdown("---")
