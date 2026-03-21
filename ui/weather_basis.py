# ui/weather_basis.py
# ACTION: CREATE / REPLACE ENTIRE FILE

import streamlit as st


def render_weather_basis():
    st.markdown("## Weather validation basis")

    st.caption(
        "This assessment is not based on a single sunny-day calculation. "
        "It is based on long-term historical solar data for the selected location."
    )

    years = [
        "2010", "2011", "2012", "2013", "2014",
        "2015", "2016", "2017", "2018", "2019",
        "2020", "2021", "2022", "2023", "2024"
    ]

    # Top summary cards
    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Historical data window", "15 years")

    with c2:
        st.metric("Weather basis", "TMY")

    with c3:
        st.metric("Coverage", "Full annual cycle")

    st.markdown("### Historical data coverage")

    # Timeline-like visual
    year_cols = st.columns(len(years))
    for col, year in zip(year_cols, years):
        with col:
            st.markdown(
                f"""
                <div style="text-align:center;">
                    <div style="
                        height:42px;
                        border-radius:8px;
                        background:#1f77b4;
                        opacity:0.88;
                        margin-bottom:6px;">
                    </div>
                    <div style="font-size:0.72rem;color:#475467;">{year}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.info(
        "Typical Meteorological Year (TMY) generated from long-term historical data "
        "for this specific location."
    )

    st.markdown("### What this means")

    b1, b2 = st.columns(2)

    with b1:
        st.success("Includes low-solar winter conditions")
        st.write("The simulation covers the full annual cycle, not only summer or average conditions.")

    with b2:
        st.success("Based on real historical weather data")
        st.write("The result reflects long-term solar conditions for the selected airport location.")

    st.markdown(
        """
        <div style="
            border:1px solid #d9e2ef;
            border-radius:14px;
            padding:12px 14px;
            background:#f8fbff;
            margin-top:10px;">
            <div style="font-weight:700; color:#12355b; margin-bottom:6px;">
                Why airports care
            </div>
            <div style="font-size:0.95rem; color:#475467; line-height:1.5;">
                This means the system is checked against realistic seasonal weather variation.
                It is not assuming perfect sunshine every day.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
