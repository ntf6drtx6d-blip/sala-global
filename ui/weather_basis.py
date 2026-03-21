# ui/weather_basis.py
# FINAL VERSION

import streamlit as st


def render_weather_basis():
    # --- HEADER + BADGE ---
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
            <div style="font-size:2rem;font-weight:800;color:#1f2937;">Methodology</div>
            <div style="
                display:inline-block;
                padding:6px 12px;
                border-radius:999px;
                background:#eef4ff;
                border:1px solid #c7d7fe;
                color:#1d4ed8;
                font-size:0.88rem;
                font-weight:700;">
                Based on PVGIS (European Commission)
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col, _ = st.columns([0.68, 0.32])

    with col:
        # --- MAIN ENGINE BLOCK ---
        st.markdown(
            """
            <div style="
                border:1px solid #d6e0ef;
                border-radius:16px;
                padding:18px 18px;
                background:#f7faff;
                margin-top:12px;
                margin-bottom:16px;">
                <div style="
                    font-weight:900;
                    font-size:1.02rem;
                    color:#12355b;
                    margin-bottom:8px;">
                    Powered by PVGIS
                </div>
                <div style="
                    font-size:0.95rem;
                    color:#344054;
                    line-height:1.55;">
                    <b>PVGIS — Photovoltaic Geographical Information System</b><br>
                    Joint Research Centre, European Commission<br>
                    Dataset: <b>PVGIS-SARAH3</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # --- KPI CARDS ---
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown(
                """
                <div style="
                    border:1px solid #e6eaf0;
                    border-radius:14px;
                    padding:16px 16px;
                    background:#ffffff;
                    min-height:110px;
                    box-shadow:0 2px 10px rgba(16,24,40,0.04);">
                    <div style="font-size:1.7rem;font-weight:900;color:#1f2937;">15 years</div>
                    <div style="font-size:0.9rem;color:#667085;margin-top:8px;">Historical data window</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c2:
            st.markdown(
                """
                <div style="
                    border:1px solid #e6eaf0;
                    border-radius:14px;
                    padding:16px 16px;
                    background:#ffffff;
                    min-height:110px;
                    box-shadow:0 2px 10px rgba(16,24,40,0.04);">
                    <div style="font-size:1.7rem;font-weight:900;color:#1f2937;">TMY</div>
                    <div style="font-size:0.9rem;color:#667085;margin-top:8px;">Typical Meteorological Year</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c3:
            st.markdown(
                """
                <div style="
                    border:1px solid #e6eaf0;
                    border-radius:14px;
                    padding:16px 16px;
                    background:#ffffff;
                    min-height:110px;
                    box-shadow:0 2px 10px rgba(16,24,40,0.04);">
                    <div style="font-size:1.7rem;font-weight:900;color:#1f2937;">Jan–Dec</div>
                    <div style="font-size:0.9rem;color:#667085;margin-top:8px;">Full annual cycle</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # --- TIMELINE ---
        st.markdown("###")

        years = list(range(2010, 2025))

        boxes = "".join(
            """
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
            + " ".join(str(y) for y in years)
            + "</div>",
            unsafe_allow_html=True,
        )

        # --- ENGINEERING INTERPRETATION ---
        st.markdown("###")

        st.markdown(
            """
            <div style="
                border-left:4px solid #5b83ad;
                padding-left:12px;
                font-size:0.95rem;
                color:#344054;">
                The assessment is derived from long-term solar data and incorporates seasonal variability, including low-radiation winter conditions.
            </div>
            """,
            unsafe_allow_html=True,
        )
