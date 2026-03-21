# ui/weather_basis.py
# ACTION: REPLACE ENTIRE FILE

import streamlit as st


def render_weather_basis():
    st.markdown("## Methodology")

    col, _ = st.columns([0.62, 0.38])

    with col:

        # --- MAIN: ENGINE (PVGIS) ---
        st.markdown("""
        <div style="
            border:1px solid #d6e0ef;
            border-radius:16px;
            padding:18px 18px;
            background:#f7faff;
            margin-bottom:14px;
        ">
            <div style="font-weight:900;font-size:1.05rem;color:#12355b;margin-bottom:6px;">
                Powered by PVGIS
            </div>

            <div style="font-size:0.95rem;color:#344054;line-height:1.5;">
                <b>PVGIS — Photovoltaic Geographical Information System</b><br/>
                Joint Research Centre, European Commission<br/>
                Dataset: <b>PVGIS-SARAH3</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- WEATHER MODEL (SECONDARY) ---
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("""
            <div style="font-weight:800;font-size:1.6rem;">15 years</div>
            <div style="color:#667085;font-size:0.9rem;">Historical data</div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown("""
            <div style="font-weight:800;font-size:1.6rem;">TMY</div>
            <div style="color:#667085;font-size:0.9rem;">Weather model</div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown("""
            <div style="font-weight:800;font-size:1.6rem;">Jan–Dec</div>
            <div style="color:#667085;font-size:0.9rem;">Full annual cycle</div>
            """, unsafe_allow_html=True)

        # --- TIMELINE ---
        st.markdown("###")

        years = list(range(2010, 2025))
        boxes = "".join(
            f"""
            <div style="
                background:#5b83ad;
                width:34px;
                height:20px;
                border-radius:6px;
                display:inline-block;
                margin-right:6px;
                margin-bottom:6px;">
            </div>
            """
            for _ in years
        )

        st.markdown(boxes, unsafe_allow_html=True)

        st.markdown(
            "<div style='font-size:0.8rem;color:#667085;'>"
            + " ".join(str(y) for y in years) +
            "</div>",
            unsafe_allow_html=True
        )

        # --- ENGINEERING INTERPRETATION ---
        st.markdown("###")

        st.markdown("""
        <div style="font-size:0.95rem;color:#344054;">
            Results are derived from long-term solar data and account for seasonal variability, including low-radiation winter conditions.
        </div>
        """, unsafe_allow_html=True)
