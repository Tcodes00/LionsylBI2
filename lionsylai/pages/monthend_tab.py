def _checklist():
    st.markdown("### ✅ Month-End Close Checklist")

    DEFAULT_ITEMS = [
        "Review and validate all journal entries",
        "Reconcile all bank accounts",
        "Reconcile credit card statements",
        "Post all accruals and prepayments",
        "Calculate and post depreciation",
        "Review inventory valuations",
        "Verify accounts receivable ageing",
        "Verify accounts payable ageing",
        "Prepare Profit & Loss statement",
        "Prepare Balance Sheet",
        "Prepare Cash Flow statement",
        "Intercompany reconciliation",
        "Management review and sign-off",
        "Submit regulatory filings",
        "Archive all closing documents",
    ]

    # Initialize or repair corrupted session state
    if "me_checklist" not in st.session_state:
        st.session_state["me_checklist"] = {item: False for item in DEFAULT_ITEMS}
    chk = st.session_state["me_checklist"]
    if not isinstance(chk, dict) or not chk:
        st.session_state["me_checklist"] = {item: False for item in DEFAULT_ITEMS}
        chk = st.session_state["me_checklist"]

    completed = sum(chk.values())
    total     = len(chk)
    pct       = (completed / total * 100) if total else 0

    # Progress bar
    st.markdown(f"""
    <div style="margin-bottom:16px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
        <span style="color:#9CA3AF;font-size:13px;">Close Progress</span>
        <span style="color:#F0F2FF;font-weight:700;">{completed}/{total} ({pct:.0f}%)</span>
      </div>
      <div style="height:8px;background:#252836;border-radius:4px;">
        <div style="height:8px;width:{pct}%;background:{'#10B981' if pct==100 else '#6C63FF'};
                    border-radius:4px;transition:width 0.4s;"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Group items
    categories = {
        "📓 Journal & Entries":  list(chk.keys())[:3],
        "🏦 Banking & Recon":    list(chk.keys())[3:6],
        "📦 Assets & Inventory": list(chk.keys())[6:9],
        "📊 Statements":         list(chk.keys())[9:12],
        "✍️ Review & Archive":   list(chk.keys())[12:],
    }

    for cat, items in categories.items():
        st.markdown(f"**{cat}**")
        for item in items:
            col1, col2 = st.columns([4, 1])
            with col1:
                checked = st.checkbox(item, value=chk.get(item, False), key=f"chk_{item[:20]}")
                chk[item] = checked
            with col2:
                status = "✅ Done" if checked else "⏳ Pending"
                color  = "#10B981" if checked else "#6B7280"
                st.markdown(f"<small style='color:{color};'>{status}</small>",
                            unsafe_allow_html=True)
        st.markdown("")

    # Complete button
    if pct < 100:
        remain = total - completed
        st.warning(f"⚠️ {remain} item(s) remaining before close can be completed.")
    else:
        if st.button("🎉 Mark Month-End Close COMPLETE", type="primary",
                     use_container_width=True):
            st.success("✅ Month-end close completed successfully!")
            st.balloons()
            # Reset for next month
            st.session_state["me_checklist"] = {item: False for item in DEFAULT_ITEMS}
            st.rerun()

    # Quick reset
    if st.button("🔄 Reset Checklist", use_container_width=True):
        st.session_state["me_checklist"] = {item: False for item in DEFAULT_ITEMS}
        st.rerun()
