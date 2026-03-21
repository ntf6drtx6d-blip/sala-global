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


def reserve_progress_value(hours):
    """
    Cap visual bar at 48h for readability.
    """
    return min(hours / 48.0, 1.0)


def render_battery():
    st.markdown("## Battery reserve vs annual solar feasibility")

    st.caption(
        "Battery reserve shows how long the lamp can operate from stored battery energy only. "
        "This is not the same as annual solar feasibility."
    )

    results = st.session_state.results
    required_hours = float(st.session_state.required_hours)

    for device_name, r in results.items():
        label = short_device_label(device_name)
        reserve = calc_battery_reserve_hours(r)
        annual_result = r["status"]

        st.markdown(f"### {label}")

        c1, c2, c3 = st.columns([1.5, 1, 1.2])

        with c1:
            st.progress(
                reserve_progress_value(reserve),
                text=f"Battery reserve: {reserve:.1f} hrs"
            )

        with c2:
            st.metric("Battery reserve", f"{reserve:.1f} hrs")

        with c3:
            st.metric("Annual solar check", annual_result)

        if annual_result == "PASS":
            st.caption(
                f"{label} has stored battery reserve and also meets the required "
                f"daily operating profile of {required_hours:.1f} hrs/day across the year."
            )
        else:
            fail_months = ", ".join(r["fail_months"]) if r["fail_months"] else "one or more months"
            st.caption(
                f"{label} may have usable battery reserve, but still cannot sustain "
                f"{required_hours:.1f} hrs/day throughout the year. "
                f"Limiting months: {fail_months}."
            )

        st.markdown("---")
