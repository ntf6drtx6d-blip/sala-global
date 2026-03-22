def render_top_action_bar():
    st.markdown('<div class="top-action-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="top-action-title">Actions</div>', unsafe_allow_html=True)

    ready = bool(st.session_state.get("study_ready", False))
    has_results = st.session_state.get("results") is not None
    is_running = bool(st.session_state.get("running", False))

    if is_running:
        progress_pct = float(st.session_state.get("run_progress", 0))
        stage = st.session_state.get("run_stage", "Preparing simulation")

        st.markdown(
            '<div class="secondary-note" style="margin-bottom:10px;"><b>Simulation in progress</b></div>',
            unsafe_allow_html=True,
        )
        st.progress(progress_pct)
        st.markdown(
            f'<div class="secondary-note" style="margin-top:10px;">{stage}</div>',
            unsafe_allow_html=True,
        )

    elif not has_results:
        c1, c2 = st.columns([1.4, 4])

        with c1:
            if st.button(
                "Run simulation",
                type="primary",
                use_container_width=True,
                disabled=not ready,
                key="top_run_simulation",
            ):
                _trigger_simulation()

        with c2:
            if ready:
                st.markdown(
                    '<div class="secondary-note">Setup is complete. You can start the feasibility check.</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="secondary-note">Select an airport or study point and at least one device to enable simulation.</div>',
                    unsafe_allow_html=True,
                )

    else:
        c1, c2, c3 = st.columns([1.2, 1.2, 1.2])

        with c1:
            if st.session_state.get("pdf_bytes") is not None:
                st.download_button(
                    "📄 Download PDF report",
                    data=st.session_state.get("pdf_bytes"),
                    file_name=st.session_state.get("pdf_name", "sala_standardized_feasibility_study.pdf"),
                    mime="application/pdf",
                    use_container_width=True,
                    key="top_download_pdf_report",
                )

        with c2:
            if st.button(
                "Run updated simulation",
                type="primary",
                use_container_width=True,
                disabled=not ready,
                key="top_run_updated_simulation",
            ):
                _trigger_simulation()

        with c3:
            st.markdown(
                """
                <style>
                div[data-testid="stButton"] button[key="top_start_new_study"] {
                    background: #fff7db !important;
                    border: 1px solid #f5c451 !important;
                    color: #7a5a00 !important;
                    border-radius: 12px !important;
                    min-height: 46px !important;
                    font-weight: 700 !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                "Start new study",
                use_container_width=True,
                key="top_start_new_study",
            ):
                reset_study()

        st.markdown(
            '<div class="secondary-note">You can keep the same location, update devices or operating profile, and run the study again.</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)
