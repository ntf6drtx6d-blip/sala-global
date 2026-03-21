# ui/weather_basis.py
# ACTION: REPLACE ENTIRE FILE

import streamlit as st


def render_weather_basis():
    st.markdown("## Weather basis")

    col, _ = st.columns([0.62, 0.38])

    with col:
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("""
            <div style="font-weight:800;font-size:1.7rem;line-height:1;">15 years</div>
            <div style="color:#667085;font-size:0.9rem;margin-top:4px;">Historical data window</div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown("""
            <div style="font-weight:800;font-size:1.7rem;line-height:1;">TMY</div>
            <div style="color:#667085;font-size:0.9rem;margin-top:4px;">Typical Meteorological Year</div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown("""
            <div style="font-weight:800;font-size:1.7rem;line-height:1;">Jan–Dec</div>
            <div style="color:#667085;font-size:0.9rem;margin-top:4px;">Full annual cycle</div>
            """, unsafe_allow_html=True)

        st.markdown("###")

        years = list(range(2010, 2025))
        box_html = "".join(
            f"""
            <div style="
                background:#5b83ad;
                width:34px;
                height:22px;
                border-radius:6px;
                display:inline-block;
                margin-right:6px;
                margin-bottom:6px;">
            </div>
            """
            for _ in years
        )
        st.markdown(box_html, unsafe_allow_html=True)

        st.markdown(
            "<div style='font-size:0.8rem;color:#667085;margin-top:2px;'>"
            + " ".join(str(y) for y in years) +
            "</div>",
            unsafe_allow_html=True
        )

        st.markdown("###")

        st.markdown("""
        <div style="
            border:1px solid #d6e0ef;
            border-radius:14px;
            padding:14px 16px;
            background:#f7faff;">
            <div style="font-weight:800;color:#12355b;margin-bottom:6px;">
                Powered by PVGIS
            </div>
            <div style="font-size:0.92rem;color:#475467;line-height:1.5;">
                <b>PVGIS — Photovoltaic Geographical Information System</b><br/>
                Joint Research Centre, European Commission<br/>
                Dataset: <b>PVGIS-SARAH3</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("###")

        st.markdown("""
        <div style="font-size:0.95rem;color:#344054;">
            Engineering relevance: results account for seasonal variation and low-solar conditions using long-term historical data.
        </div>
        """, unsafe_allow_html=True)
