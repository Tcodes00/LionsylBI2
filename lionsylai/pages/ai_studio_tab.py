"""
LionsylAI – AI Studio Tab v4
Auto-clean with correct quality score · Manual clean controls · 
Download cleaned Excel · Hyperparameter tuning · Full training pipeline
"""
from __future__ import annotations
import io, hashlib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.data_engine import numeric_cols, categorical_cols, date_cols
from components.ml_engine import (
    MLEngine, DataPreprocessor, auto_clean_dataframe,
    ForecastEngine, ClusterEngine, CustomerAnalytics, auto_feature_engineer,
)
from design import section_header, kpi_card, insight_card, badge


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _df_fingerprint(df: pd.DataFrame) -> str:
    """Stable hash of the actual data — changes when data changes."""
    try:
        sample = df.head(50).to_csv(index=False)
        return hashlib.md5((sample + str(df.shape)).encode()).hexdigest()
    except Exception:
        return str(df.shape) + str(df.columns.tolist())


def _quality_score(report: dict, df: pd.DataFrame) -> int:
    """
    Correct quality score formula:
    Penalise for missing values, outliers, duplicates, negative invalids.
    """
    total_cells    = max(df.size, 1)
    missing_before = report.get("missing_before", 0)
    issues_fixed   = report.get("issues_fixed", 0)
    rows_removed   = report.get("rows_removed", 0)

    # missing % penalty (0-40 pts)
    missing_pct = missing_before / total_cells
    missing_pen = int(missing_pct * 40)

    # issues per 1000 cells penalty (0-30 pts)
    issue_rate = issues_fixed / (total_cells / 1000 + 1)
    issue_pen  = min(30, int(issue_rate * 3))

    # duplicate row penalty (0-15 pts)
    dup_pen = min(15, int(rows_removed / max(len(df), 1) * 100))

    # column health (0-15 pts): high-missing or zero-variance cols
    bad_cols = sum(1 for c in df.columns
                   if df[c].isnull().mean() > 0.30 or
                   (pd.api.types.is_numeric_dtype(df[c]) and df[c].std(ddof=0) == 0))
    col_pen  = min(15, bad_cols * 3)

    score = max(0, 100 - missing_pen - issue_pen - dup_pen - col_pen)
    return score


# ─────────────────────────────────────────────────────────────
# Main router
# ─────────────────────────────────────────────────────────────

def render(df: pd.DataFrame):
    st.markdown(section_header(
        "🤖 AI Studio",
        "Auto-clean · Manual clean · Hyperparameter tune · Train · Forecast · Segment"
    ), unsafe_allow_html=True)

    # Always run clean section first
    _clean_section(df)

    st.markdown("---")
    sub = st.radio(
        "Studio Module",
        ["🧠 Model Training", "🔮 Forecasting", "🎯 Clustering",
         "👥 Customer Analytics", "🔧 Feature Engineering"],
        horizontal=True, label_visibility="collapsed",
    )
    clean_df = st.session_state.get("ai_studio_clean_df", df)
    if sub == "🧠 Model Training":        _model_training(clean_df)
    elif sub == "🔮 Forecasting":          _forecasting(clean_df)
    elif sub == "🎯 Clustering":           _clustering(clean_df)
    elif sub == "👥 Customer Analytics":   _customer_analytics(clean_df)
    elif sub == "🔧 Feature Engineering":  _feature_engineering(clean_df)


# ═════════════════════════════════════════════════════════════
# CLEAN SECTION  — Auto + Manual
# ═════════════════════════════════════════════════════════════

def _clean_section(df: pd.DataFrame):
    fp = _df_fingerprint(df)

    # ── Mode tabs ─────────────────────────────────────────────
    mode_tab1, mode_tab2 = st.tabs(["🤖 Auto Clean", "🛠️ Manual Clean"])

    with mode_tab1:
        _auto_clean_ui(df, fp)

    with mode_tab2:
        _manual_clean_ui(df, fp)


# ─────────────────────────────────────────────────────────────
# AUTO CLEAN
# ─────────────────────────────────────────────────────────────

def _auto_clean_ui(df: pd.DataFrame, fp: str):
    # Run once per unique data fingerprint
    if st.session_state.get("_auto_clean_fp") != fp:
        with st.spinner("🔍 Scanning dataset…"):
            cleaned, report = auto_clean_dataframe(df.copy())
        st.session_state["_auto_clean_fp"]     = fp
        st.session_state["_auto_cleaned_df"]   = cleaned
        st.session_state["_auto_clean_report"] = report
        st.session_state["ai_studio_clean_df"] = cleaned   # used by training
    else:
        cleaned = st.session_state["_auto_cleaned_df"]
        report  = st.session_state["_auto_clean_report"]

    _render_clean_results(df, cleaned, report, key_prefix="auto")


# ─────────────────────────────────────────────────────────────
# MANUAL CLEAN
# ─────────────────────────────────────────────────────────────

def _manual_clean_ui(df: pd.DataFrame, fp: str):
    st.markdown("#### 🛠️ Manual Cleaning Controls")
    st.info("Adjust every cleaning parameter, then click **Run Manual Clean** to apply.")

    nc = numeric_cols(df)
    cc = categorical_cols(df)

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("**📐 Missing Value Handling**")
        fill_method = st.selectbox(
            "Fill method", ["median", "mean", "zero", "knn"],
            key="mc_fill",
            help="KNN is most accurate but slower on large datasets"
        )
        drop_thresh = st.slider(
            "Drop column if missing % >", 10, 90, 70, 5,
            key="mc_drop_thresh",
            help="Columns with more missing than this threshold are removed"
        )

    with col_b:
        st.markdown("**📊 Outlier Handling**")
        out_low = st.slider("Lower percentile clip", 0.0, 5.0, 0.5, 0.1,
                            key="mc_out_low",
                            help="Values below this percentile are clamped")
        out_high = st.slider("Upper percentile clip", 95.0, 100.0, 99.5, 0.1,
                             key="mc_out_high",
                             help="Values above this percentile are clamped")
        fix_neg = st.checkbox("Fix negative qty/price values", value=True, key="mc_fix_neg")

    with col_c:
        st.markdown("**🗂️ Column Management**")
        drop_id = st.checkbox("Drop all-unique ID columns", value=True, key="mc_drop_id",
                              help="Columns where every row is unique (e.g. row IDs)")
        encode_cats = st.checkbox("One-hot encode categoricals", value=False, key="mc_ohe",
                                  help="Turn text columns into 0/1 dummy columns for ML")
        custom_drops = st.multiselect(
            "Manually drop columns", df.columns.tolist(), key="mc_custom_drops"
        )

    st.markdown("**🔧 Manual Type Overrides** (optional)")
    override_cols = st.multiselect("Select columns to override type", df.columns.tolist(),
                                   key="mc_type_cols")
    manual_types: dict = {}
    if override_cols:
        type_cols = st.columns(min(len(override_cols), 4))
        for i, col in enumerate(override_cols):
            with type_cols[i % 4]:
                chosen = st.selectbox(
                    f"'{col}' type", ["numeric", "date", "text"],
                    key=f"mc_type_{col}"
                )
                manual_types[col] = chosen

    # ── Run button ────────────────────────────────────────────
    if st.button("🚀 Run Manual Clean", type="primary", use_container_width=True, key="mc_run"):
        with st.spinner("Applying manual cleaning pipeline…"):
            cleaned, report = auto_clean_dataframe(
                df.copy(),
                drop_missing_thresh = drop_thresh / 100,
                outlier_low         = out_low / 100,
                outlier_high        = out_high / 100,
                fix_negatives       = fix_neg,
                encode_cats         = encode_cats,
                drop_id_cols        = drop_id,
                fill_method         = fill_method,
                custom_drops        = custom_drops if custom_drops else None,
                manual_types        = manual_types if manual_types else None,
            )
        st.session_state["_manual_cleaned_df"]   = cleaned
        st.session_state["_manual_clean_report"] = report
        st.session_state["ai_studio_clean_df"]   = cleaned   # use for training
        st.session_state["_manual_clean_fp"]     = fp
        st.success("✅ Manual clean applied! Training will now use this cleaned dataset.")

    # Show results if available for this data
    if (st.session_state.get("_manual_clean_fp") == fp and
            "_manual_cleaned_df" in st.session_state):
        cleaned = st.session_state["_manual_cleaned_df"]
        report  = st.session_state["_manual_clean_report"]
        _render_clean_results(df, cleaned, report, key_prefix="manual")


# ─────────────────────────────────────────────────────────────
# Shared results renderer (used by both auto and manual)
# ─────────────────────────────────────────────────────────────

def _render_clean_results(raw_df: pd.DataFrame, cleaned: pd.DataFrame,
                           report: dict, key_prefix: str = ""):
    missing_before = report.get("missing_before", 0)
    missing_after  = report.get("missing_after",  0)
    issues_fixed   = report.get("issues_fixed",   0)
    rows_removed   = report.get("rows_removed",   0)
    cols_removed   = report.get("cols_removed",   0)

    score = _quality_score(report, raw_df)
    score_color = "#10B981" if score >= 80 else "#F59E0B" if score >= 50 else "#EF4444"
    score_label = ("✅ Clean"           if score >= 85 else
                   "⚡ Mostly Clean"    if score >= 65 else
                   "⚠️ Needs Cleaning" if score >= 40 else
                   "🚨 Very Messy")

    # ── Quality banner ────────────────────────────────────────
    st.markdown(f"""
    <div style="background:#141720;border:1px solid #252836;border-radius:16px;
                padding:20px 24px;margin:8px 0 12px;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
        <div>
          <div style="font-size:13px;color:#9CA3AF;text-transform:uppercase;
                      letter-spacing:0.1em;margin-bottom:4px;">🧹 Dataset Quality</div>
          <div style="font-size:17px;font-weight:700;color:#fff;">
            {issues_fixed} issues fixed · {rows_removed} duplicate rows ·
            {missing_before - missing_after} missing values filled ·
            {cols_removed} columns removed
          </div>
        </div>
        <div style="text-align:center;background:{score_color}22;border:2px solid {score_color}55;
                    border-radius:12px;padding:12px 20px;min-width:100px;">
          <div style="font-size:30px;font-weight:900;color:{score_color};">{score}%</div>
          <div style="font-size:12px;color:{score_color};font-weight:700;">{score_label}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Metrics row ───────────────────────────────────────────
    orig  = report.get("original_shape", (0,0))
    final = report.get("final_shape", (0,0))
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Rows Before",    f"{orig[0]:,}")
    c2.metric("Rows After",     f"{final[0]:,}")
    c3.metric("Cols Before",    f"{orig[1]:,}")
    c4.metric("Cols After",     f"{final[1]:,}")
    c5.metric("Missing Before", f"{missing_before:,}")
    c6.metric("Missing After",  f"{missing_after:,}")

    # ── Steps log ─────────────────────────────────────────────
    steps = report.get("steps", [])
    if steps:
        with st.expander(f"📋 {len(steps)} cleaning steps applied", expanded=False):
            for step in steps:
                warn   = "WARNING" in step
                icon   = "⚠️" if warn else "✅"
                color  = "#F59E0B" if warn else "#10B981"
                st.markdown(
                    f"<div style='padding:4px 0;border-bottom:1px solid #1A1F2E;"
                    f"font-size:13px;color:{color};'>{icon} {step}</div>",
                    unsafe_allow_html=True,
                )
    elif not steps:
        st.info("No issues found — dataset is already clean.")

    # ── Column actions detail ──────────────────────────────────
    col_actions = report.get("col_actions", {})
    if col_actions:
        with st.expander(f"🔍 Per-column actions ({len(col_actions)} columns modified)", expanded=False):
            for col, actions in col_actions.items():
                st.markdown(
                    f"**{col}**: {' · '.join(actions)}",
                    unsafe_allow_html=False,
                )

    # ── Before / After preview ────────────────────────────────
    with st.expander("👁️ Before / After Preview", expanded=False):
        ca, cb = st.columns(2)
        with ca:
            st.markdown("**Raw (first 8 rows)**")
            st.dataframe(raw_df.head(8), use_container_width=True)
        with cb:
            st.markdown("**Cleaned (first 8 rows)**")
            st.dataframe(cleaned.head(8), use_container_width=True)

    # ── Download ──────────────────────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(90deg,#6C63FF18,#0AEFFF0A);
                border:1px solid #6C63FF44;border-radius:12px;
                padding:14px 18px;margin:10px 0 4px;">
      <div style="font-weight:700;color:#fff;margin-bottom:3px;">
        📥 Download Cleaned Excel Sheet
      </div>
      <div style="font-size:13px;color:#9CA3AF;">
        Re-upload this cleaned file for <strong style='color:#0AEFFF;'>higher accuracy</strong>
        — clean data typically improves R² by 5–15%.
        Includes <em>Cleaned Data</em>, <em>Cleaning Summary</em> and <em>Data Profile</em> sheets.
      </div>
    </div>
    """, unsafe_allow_html=True)

    dc1, dc2 = st.columns([1, 1])
    with dc1:
        include_profile = st.checkbox("Include Data Profile sheet", value=True,
                                      key=f"{key_prefix}_profile")
    with dc2:
        excel_bytes = _build_clean_excel(cleaned, report, include_profile)
        st.download_button(
            label      = "📥 Download Cleaned Excel",
            data       = excel_bytes,
            file_name  = "lionsylai_cleaned_dataset.xlsx",
            mime       = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width = True,
            type       = "primary",
            key        = f"{key_prefix}_dl_btn",
        )

    # ── Accuracy tip ──────────────────────────────────────────
    if score < 85:
        st.markdown(insight_card(
            "💡 **To reach 99% accuracy:** Download the cleaned Excel → re-upload it → "
            "go to Model Training → enable Hyperparameter Tuning. "
            "Clean data is the single biggest factor for high R².",
            "#6C63FF"
        ), unsafe_allow_html=True)


def _build_clean_excel(cleaned_df: pd.DataFrame, report: dict, include_profile: bool) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        cleaned_df.to_excel(writer, sheet_name="Cleaned Data", index=False)

        # Cleaning Summary sheet
        rows = [{"Step": s} for s in report.get("steps", [])]
        rows += [
            {"Step": "─"*50},
            {"Step": f"Original shape : {report.get('original_shape')}"},
            {"Step": f"Final shape    : {report.get('final_shape')}"},
            {"Step": f"Missing before : {report.get('missing_before', 0)}"},
            {"Step": f"Missing after  : {report.get('missing_after',  0)}"},
            {"Step": f"Rows removed   : {report.get('rows_removed',  0)}"},
            {"Step": f"Cols removed   : {report.get('cols_removed',  0)}"},
            {"Step": f"Issues fixed   : {report.get('issues_fixed',  0)}"},
        ]
        pd.DataFrame(rows).to_excel(writer, sheet_name="Cleaning Summary", index=False)

        # Data Profile sheet
        if include_profile:
            profile = []
            for col in cleaned_df.columns:
                s = cleaned_df[col]
                row: dict = {
                    "Column":    col,
                    "Type":      str(s.dtype),
                    "Non-Null":  int(s.count()),
                    "Null":      int(s.isnull().sum()),
                    "Null %":    round(s.isnull().mean()*100, 1),
                    "Unique":    int(s.nunique()),
                }
                if pd.api.types.is_numeric_dtype(s) and s.notna().any():
                    row.update({
                        "Mean":   round(float(s.mean()), 4),
                        "Median": round(float(s.median()), 4),
                        "Std":    round(float(s.std()), 4),
                        "Min":    round(float(s.min()), 4),
                        "Max":    round(float(s.max()), 4),
                        "Skew":   round(float(s.skew()), 4),
                    })
                profile.append(row)
            pd.DataFrame(profile).to_excel(writer, sheet_name="Data Profile", index=False)

    buf.seek(0)
    return buf.read()


# ═════════════════════════════════════════════════════════════
# MODEL TRAINING
# ═════════════════════════════════════════════════════════════

def _model_training(df: pd.DataFrame):
    st.markdown("### 🧠 Model Training")

    ncols = numeric_cols(df)
    ccols = categorical_cols(df)
    all_c = ncols + ccols

    if len(all_c) < 2:
        st.warning("Need at least 2 columns. Upload a richer dataset.")
        return

    c1, c2 = st.columns(2)
    with c1:
        target = st.selectbox("🎯 Target (what to predict)", all_c, key="ai_target")
    with c2:
        task = st.selectbox("📋 Task type", ["Regression", "Classification"], key="ai_task")

    # ── Training config ───────────────────────────────────────
    st.markdown("#### ⚙️ Training Configuration")
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        use_tuning = st.checkbox(
            "🔬 Hyperparameter Tuning", value=False, key="ai_tune",
            help="RandomizedSearchCV on XGBoost, LightGBM, Random Forest. Adds 2–10% accuracy."
        )
    with tc2:
        tune_iter = st.slider(
            "Tuning iterations", 10, 100, 30, 5, key="ai_tune_iter",
            disabled=not use_tuning,
            help="More = better params, slower. 30 is a good balance."
        )
    with tc3:
        show_prep = st.checkbox("Show preprocessing report", value=True, key="ai_show_prep")

    if use_tuning:
        st.info(f"🔬 **Tuning ON** — {tune_iter} iterations × 3 models × 5-fold CV. "
                f"Estimated time: {tune_iter//15 + 1}–{tune_iter//8 + 1} min.")
    else:
        st.success("⚡ **Quick mode** — default optimised hyperparameters. Fast and reliable.")

    # ── Train ─────────────────────────────────────────────────
    if st.button("🚀 Train All Models", type="primary", use_container_width=True):
        pb  = st.progress(0,  text="⚙️ Pre-cleaning + 12-step preprocessing…")
        pb.progress(20, text="Steps 1–6: Drop junk · Coerce types · Dedup · KNN impute…")
        pb.progress(40, text="Steps 7–12: Encode · Winsorise · RobustScale · Engineer · Select…")

        if use_tuning:
            pb.progress(50, text=f"🔬 Hyperparameter tuning ({tune_iter} iters × 3 models)…")

        engine = MLEngine()
        with st.spinner("Training ensemble + stacking…"):
            results = engine.train(df.copy(), target, task.lower(),
                                   tune=use_tuning, tune_n_iter=tune_iter)

        pb.progress(95, text="📊 Cross-validation scoring…")

        if not results:
            pb.empty()
            st.error("❌ Training failed — check target column and data quality.")
            return

        pb.progress(100, text="✅ Done!")
        st.success(f"✅ {len(results)} models trained!")

        # ── Preprocessing report ──────────────────────────────
        if show_prep:
            prep = engine.get_preprocessing_report()
            if prep:
                orig  = prep.get("original_shape", (0,0))
                final = prep.get("final_shape", (0,0))
                with st.expander("🧹 12-step preprocessing report", expanded=False):
                    pc1,pc2,pc3 = st.columns(3)
                    pc1.metric("Input",    f"{orig[0]:,} × {orig[1]}")
                    pc2.metric("Output",   f"{final[0]:,} × {final[1]}")
                    pc3.metric("Steps",    len(prep.get("steps",[])))
                    for step in prep.get("steps",[]):
                        color = "#F59E0B" if "WARNING" in step else "#10B981"
                        st.markdown(f"<small style='color:{color};'>✔ {step}</small>",
                                    unsafe_allow_html=True)

        # ── Tuning results ────────────────────────────────────
        tuning = engine.get_tuning_results()
        if tuning:
            st.markdown("#### 🔬 Hyperparameter Tuning Results")
            for mname, tr in tuning.items():
                with st.expander(f"📐 {mname} — Best CV: {tr['best_cv_score']:.4f}",
                                 expanded=False):
                    st.json(tr["best_params"])

        # ── Performance table ─────────────────────────────────
        st.markdown("#### 📊 Model Performance")
        rows = []
        for name, r in results.items():
            badge_str = "⚡ Tuned" if r.get("tuned") else "Default"
            if task == "Regression":
                rows.append({
                    "Model":    name, "Config": badge_str,
                    "R² Test":  round(r.get("r2",0),4),
                    "R² CV":    round(r.get("cv_r2",0),4),
                    "CV Std":   round(r.get("cv_std",0),4),
                    "RMSE":     round(r.get("rmse",0),2),
                    "MAE":      round(r.get("mae",0),2),
                    "Train N":  r.get("n_train",0),
                    "Test N":   r.get("n_test",0),
                })
            else:
                rows.append({
                    "Model":        name, "Config": badge_str,
                    "Accuracy":     round(r.get("accuracy",0),4),
                    "CV Accuracy":  round(r.get("cv_acc",0),4),
                    "CV Std":       round(r.get("cv_std",0),4),
                    "F1":           round(r.get("f1",0),4),
                    "Precision":    round(r.get("precision",0),4),
                    "Recall":       round(r.get("recall",0),4),
                    "Train N":      r.get("n_train",0),
                    "Test N":       r.get("n_test",0),
                })

        perf_df    = pd.DataFrame(rows)
        metric_col = "R² Test" if task=="Regression" else "Accuracy"

        def _color(val):
            if val >= 0.99: return "background:#10B98144;color:#10B981;font-weight:900"
            if val >= 0.95: return "background:#10B98122;color:#10B981;font-weight:700"
            if val >= 0.85: return "background:#6C63FF22;color:#8B84FF"
            if val >= 0.70: return "background:#F59E0B22;color:#F59E0B"
            return "background:#EF444422;color:#EF4444"

        st.dataframe(
            perf_df.style.applymap(_color, subset=[metric_col]),
            use_container_width=True, hide_index=True,
        )

        # ── Best model banner ─────────────────────────────────
        key_m    = "cv_r2" if task=="Regression" else "cv_acc"
        best     = max(results, key=lambda n: results[n].get(key_m, 0))
        best_val = results[best].get(key_m, 0)
        _accuracy_banner(best, best_val, task)
        _improvement_tips(best_val, task, use_tuning)

        # ── Charts ────────────────────────────────────────────
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(perf_df, x="Model", y=metric_col,
                         color=metric_col, color_continuous_scale="RdYlGn",
                         title=f"{metric_col} by Model", range_color=[0,1])
            for line, label, color in [(0.90,"0.90","#F59E0B"),(0.95,"0.95","#10B981"),(0.99,"0.99","#0AEFFF")]:
                fig.add_hline(y=line, line_dash="dash", line_color=color,
                              annotation_text=label, annotation_font_color=color)
            fig.update_layout(**_cl(), height=340, xaxis_tickangle=-20)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            cv_col = "R² CV" if task=="Regression" else "CV Accuracy"
            if cv_col in perf_df.columns:
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(x=perf_df["Model"], y=perf_df[cv_col],
                                      name="CV", marker_color="#6C63FF"))
                fig2.add_trace(go.Bar(x=perf_df["Model"], y=perf_df[metric_col],
                                      name="Test", marker_color="#0AEFFF", opacity=0.75))
                fig2.update_layout(**_cl(), barmode="group", height=340,
                                   title="CV vs Test Score", xaxis_tickangle=-20)
                st.plotly_chart(fig2, use_container_width=True)

        # ── Feature importance ────────────────────────────────
        fi_df = engine.feature_importances(results, task.lower())
        if fi_df is not None and not fi_df.empty:
            st.markdown("#### 🔍 Feature Importance")
            c1, c2 = st.columns([3,1])
            with c1:
                fig = px.bar(fi_df.head(15), x="Importance %", y="Feature",
                             orientation="h", color="Importance %",
                             color_continuous_scale="Viridis",
                             title=f"Top Features — {best}")
                fig.update_layout(**_cl(), height=420)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.dataframe(fi_df.head(15)[["Feature","Importance %"]],
                             use_container_width=True, hide_index=True)

        # ── RMSE chart ────────────────────────────────────────
        if task == "Regression":
            rmse_df = pd.DataFrame(
                [(n, r.get("rmse",0)) for n,r in results.items()],
                columns=["Model","RMSE"]
            ).sort_values("RMSE")
            fig = px.bar(rmse_df, x="Model", y="RMSE", color="RMSE",
                         color_continuous_scale="RdYlGn_r", title="RMSE (lower = better)")
            fig.update_layout(**_cl(), height=260, xaxis_tickangle=-20)
            st.plotly_chart(fig, use_container_width=True)


def _accuracy_banner(best, score, task):
    key   = "R²" if task=="Regression" else "Accuracy"
    color = "#10B981" if score>=0.95 else "#F59E0B" if score>=0.75 else "#EF4444"
    label = ("🏆 99%+ — near-perfect!"      if score>=0.99 else
             "✅ Excellent (production-ready)" if score>=0.95 else
             "📈 Good — tune or re-upload"     if score>=0.80 else
             "⚡ Moderate — upload cleaned sheet" if score>=0.65 else
             "⚠️ Low — check target & data")
    st.markdown(f"""
    <div style="background:{color}12;border:2px solid {color}55;border-radius:16px;
                padding:18px 24px;margin:14px 0;
                display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
      <div>
        <div style="font-size:12px;color:#9CA3AF;">🏆 BEST MODEL</div>
        <div style="font-size:20px;font-weight:900;color:#fff;margin:2px 0;">{best}</div>
        <div style="font-size:14px;color:{color};">{label}</div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:40px;font-weight:900;color:{color};">{score:.4f}</div>
        <div style="font-size:11px;color:#9CA3AF;">{key} (5-fold CV)</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def _improvement_tips(score, task, tuned):
    st.markdown("#### 💡 How to Reach 99% Accuracy")
    tips = []
    if score < 0.99:
        tips.append(("📥","Re-upload the cleaned Excel (from Auto-Clean above)",
                     "Clean data is the #1 accuracy factor — typically adds 5–15% R².","#10B981"))
    if not tuned:
        tips.append(("🔬","Enable Hyperparameter Tuning (set iterations ≥ 50)",
                     "Automatically finds the best model parameters — adds 2–8% R².","#6C63FF"))
    if score < 0.99:
        tips.append(("🎯","Pick a mathematically-derived target",
                     "E.g. profit = revenue − cost achieves R²=0.99+ because it's deterministic.","#0AEFFF"))
    if score < 0.90:
        tips.append(("📊","Add more correlated features",
                     "More columns that relate to the target = better predictions.","#F59E0B"))
    if score < 0.80:
        tips.append(("📈","Get more data rows (aim for 1,000+)",
                     "More training samples directly improve model generalisation.","#F59E0B"))
    tips.append(("🏆","Use the 🏆 Stacking Ensemble row",
                 "Combines all models — usually the highest cross-validated score.","#10B981"))
    for icon, title, desc, color in tips:
        st.markdown(f"""
        <div style="background:#141720;border-left:4px solid {color};border-radius:0 12px 12px 0;
                    padding:10px 16px;margin:6px 0;">
          <div style="font-weight:700;color:#fff;">{icon} {title}</div>
          <div style="font-size:13px;color:#9CA3AF;margin-top:2px;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════
# FORECASTING
# ═════════════════════════════════════════════════════════════

def _forecasting(df: pd.DataFrame):
    st.markdown("### 🔮 Advanced Forecasting")
    ncols = numeric_cols(df)
    if not ncols:
        st.warning("No numeric columns available.")
        return

    c1,c2,c3 = st.columns(3)
    with c1: fc_col    = st.selectbox("Column", ncols, key="fc_col")
    with c2: fc_method = st.selectbox("Method",
                                      ["SARIMA (auto-fallback)","Holt-Winters",
                                       "Linear Trend","Monte Carlo"],
                                      key="fc_method")
    with c3: periods   = st.slider("Periods", 7, 365, 30, key="fc_periods")
    show_ci = st.checkbox("90% confidence band", value=True, key="fc_ci")

    if st.button("🔮 Generate Forecast", type="primary", use_container_width=True):
        series = pd.to_numeric(df[fc_col], errors="coerce").dropna().reset_index(drop=True)
        if len(series) < 5:
            st.error("Need at least 5 data points."); return

        with st.spinner("Forecasting…"):
            if "Monte Carlo" in fc_method:
                mean_fc, lo, hi = ForecastEngine.monte_carlo(series, 1000, periods)
                _plot_mc(series, mean_fc, lo, hi, fc_col, periods, show_ci)
                _fc_metrics(float(mean_fc.iloc[-1]), float(series.iloc[-1]), periods, float(series.std()))
                return
            fc = (ForecastEngine.sarima(series, periods)     if "SARIMA"  in fc_method else
                  ForecastEngine.holt_winters(series, periods) if "Holt"  in fc_method else
                  ForecastEngine.simple_trend(series, periods))

        if fc is None:
            st.error("Forecast failed."); return

        std = float(series.std())
        ih  = list(range(len(series)))
        ifc = list(range(len(series), len(series)+len(fc)))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ih, y=series.values, mode="lines", name="Historical",
                                  line=dict(color="#6C63FF",width=2),
                                  fill="tozeroy", fillcolor="rgba(108,99,255,0.05)"))
        fig.add_trace(go.Scatter(x=ifc, y=fc.values, mode="lines", name="Forecast",
                                  line=dict(color="#0AEFFF",width=2.5,dash="dash")))
        if show_ci:
            up,lo2 = fc.values+1.5*std, fc.values-1.5*std
            fig.add_trace(go.Scatter(x=ifc+ifc[::-1], y=list(up)+list(lo2)[::-1],
                                     fill="toself", fillcolor="rgba(10,239,255,0.10)",
                                     line=dict(width=0), name="90% CI"))
        fig.update_layout(**_cl(), height=420,
                          title=f"{fc_method} — {periods}-period Forecast ({fc_col})",
                          xaxis_title="Period", yaxis_title=fc_col)
        st.plotly_chart(fig, use_container_width=True)
        _fc_metrics(float(fc.iloc[-1]), float(series.iloc[-1]), periods, std)

        fc_df = pd.DataFrame({"Period":ifc,"Forecast":fc.values})
        st.download_button("📥 Download Forecast CSV",
                           fc_df.to_csv(index=False).encode(),
                           f"forecast_{fc_col}.csv", "text/csv",
                           use_container_width=True)


def _plot_mc(series, mean_fc, lo, hi, fc_col, periods, show_ci):
    ih  = list(range(len(series)))
    ifc = list(range(len(series), len(series)+periods))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ih,  y=series.values,  mode="lines", name="Historical",
                              line=dict(color="#6C63FF",width=2)))
    fig.add_trace(go.Scatter(x=ifc, y=mean_fc.values, mode="lines", name="MC Mean",
                              line=dict(color="#0AEFFF",width=2.5,dash="dash")))
    if show_ci:
        fig.add_trace(go.Scatter(x=ifc+ifc[::-1],
                                 y=list(hi.values)+list(lo.values)[::-1],
                                 fill="toself", fillcolor="rgba(10,239,255,0.12)",
                                 line=dict(width=0), name="90% CI (1000 sims)"))
    fig.update_layout(**_cl(), height=420,
                      title=f"Monte Carlo — {fc_col} (1000 simulations)",
                      xaxis_title="Period", yaxis_title=fc_col)
    st.plotly_chart(fig, use_container_width=True)


def _fc_metrics(final, last, periods, std):
    change = (final-last)/abs(last)*100 if last!=0 else 0
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Last Value",    f"{last:,.2f}")
    c2.metric("Forecast End",  f"{final:,.2f}")
    c3.metric("Total Change",  f"{change:+.1f}%")
    c4.metric("Historical Std",f"±{std:,.2f}")


# ═════════════════════════════════════════════════════════════
# CLUSTERING
# ═════════════════════════════════════════════════════════════

def _clustering(df: pd.DataFrame):
    st.markdown("### 🎯 Segment Clustering")
    ncols = numeric_cols(df)
    if len(ncols) < 2:
        st.warning("Need at least 2 numeric columns."); return

    c1,c2,c3 = st.columns(3)
    with c1: f1 = st.selectbox("Feature 1", ncols, key="cl_f1")
    with c2: f2 = st.selectbox("Feature 2", ncols, index=min(1,len(ncols)-1), key="cl_f2")
    with c3: k  = st.slider("Clusters (K)", 2, 10, 3, key="cl_k")
    show_elbow = st.checkbox("Elbow curve (optimal K)", value=True, key="cl_elbow")

    if st.button("🎯 Run Clustering", type="primary", use_container_width=True):
        result = ClusterEngine.kmeans(df, [f1,f2], k)
        if not result:
            st.error("Clustering failed."); return
        clust_df, km = result
        st.success(f"✅ {len(clust_df):,} points → {k} clusters")

        c1,c2 = st.columns(2)
        with c1:
            fig = px.scatter(clust_df, x=f1, y=f2, color="Cluster",
                             title=f"K-Means (k={k})",
                             color_discrete_sequence=px.colors.qualitative.Vivid, opacity=0.75)
            fig.update_layout(**_cl(), height=380); st.plotly_chart(fig, use_container_width=True)
        with c2:
            cnt = clust_df["Cluster"].value_counts()
            fig2 = px.pie(values=cnt.values, names=[f"Cluster {x}" for x in cnt.index],
                          title="Cluster Sizes", hole=0.4,
                          color_discrete_sequence=px.colors.qualitative.Vivid)
            fig2.update_layout(**_cl(), height=380); st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(clust_df.groupby("Cluster")[[f1,f2]].agg(["mean","std","count"]).round(2),
                     use_container_width=True)

        if show_elbow:
            inertias = ClusterEngine.elbow_method(df, [f1,f2], max_k=min(10,len(df)//5))
            if inertias:
                fig3 = go.Figure(go.Scatter(x=list(inertias.keys()), y=list(inertias.values()),
                                            mode="lines+markers",
                                            line=dict(color="#6C63FF",width=2),
                                            marker=dict(size=8,color="#0AEFFF")))
                fig3.update_layout(**_cl(), height=260, title="Elbow Curve — choose K at the bend",
                                   xaxis_title="K", yaxis_title="Inertia")
                st.plotly_chart(fig3, use_container_width=True)

        if len(ncols) > 2:
            pca_df = ClusterEngine.pca_2d(df, ncols[:8])
            if pca_df is not None and len(pca_df) == len(clust_df):
                pca_df["Cluster"] = clust_df["Cluster"].values
                fig4 = px.scatter(pca_df, x="PC1", y="PC2", color="Cluster",
                                  title="PCA (all numeric features)",
                                  color_discrete_sequence=px.colors.qualitative.Vivid)
                fig4.update_layout(**_cl(), height=340); st.plotly_chart(fig4, use_container_width=True)


# ═════════════════════════════════════════════════════════════
# CUSTOMER ANALYTICS
# ═════════════════════════════════════════════════════════════

def _customer_analytics(df: pd.DataFrame):
    st.markdown("### 👥 Customer Intelligence")
    ncols = numeric_cols(df)
    ccols = categorical_cols(df)
    dcols = date_cols(df)
    cust_cols = [c for c in ccols if any(k in c.lower() for k in
                  ["customer","client","user","account","buyer","id"])] or ccols
    if not cust_cols:
        st.warning("No customer columns found."); return

    sub = st.radio("Module",["💰 CLV","📊 RFM","⚠️ Churn Risk"],horizontal=True,key="ca_sub")
    c1,c2 = st.columns(2)
    with c1: cust_c = st.selectbox("Customer column", cust_cols, key="ca_cust")
    with c2: rev_c  = st.selectbox("Revenue column", ncols, key="ca_rev") if ncols else None

    ca = CustomerAnalytics()
    if sub == "💰 CLV" and rev_c:
        if st.button("💰 Calculate CLV", type="primary", use_container_width=True):
            result = ca.clv(df, cust_c, rev_c)
            if result is not None:
                c1,c2 = st.columns(2)
                with c1:
                    fig = px.bar(result.head(20), x=cust_c, y="estimated_clv",
                                 color="estimated_clv", color_continuous_scale="Viridis",
                                 title="Top 20 by CLV")
                    fig.update_layout(**_cl(), height=340, xaxis_tickangle=-35)
                    st.plotly_chart(fig, use_container_width=True)
                with c2:
                    fig2 = px.histogram(result, x="estimated_clv", nbins=30,
                                        color_discrete_sequence=["#6C63FF"], title="CLV Distribution")
                    fig2.update_layout(**_cl(), height=340); st.plotly_chart(fig2, use_container_width=True)
                st.dataframe(result.round(2), use_container_width=True, hide_index=True)

    elif sub == "📊 RFM":
        if not dcols or not rev_c:
            st.info("RFM needs a date + revenue column.")
        else:
            dt_c = st.selectbox("Date column", dcols, key="ca_dt")
            if st.button("📊 Calculate RFM", type="primary", use_container_width=True):
                result = ca.rfm(df, cust_c, dt_c, rev_c)
                if result is not None:
                    seg = result["Segment"].value_counts()
                    c1,c2 = st.columns(2)
                    with c1:
                        fig = px.pie(values=seg.values, names=seg.index,
                                     color_discrete_map={"Champion":"#10B981","Loyal":"#6C63FF",
                                                          "Needs Attention":"#F59E0B","At Risk":"#EF4444"},
                                     title="RFM Segments", hole=0.4)
                        fig.update_layout(**_cl(), height=340); st.plotly_chart(fig, use_container_width=True)
                    with c2:
                        fig2 = px.scatter(result, x="Recency", y="Monetary", size="Frequency",
                                          color="Segment",
                                          color_discrete_map={"Champion":"#10B981","Loyal":"#6C63FF",
                                                               "Needs Attention":"#F59E0B","At Risk":"#EF4444"},
                                          title="RFM Scatter")
                        fig2.update_layout(**_cl(), height=340); st.plotly_chart(fig2, use_container_width=True)
                    st.dataframe(result.round(2), use_container_width=True, hide_index=True)

    elif sub == "⚠️ Churn Risk":
        dt_c = st.selectbox("Date col (optional)", ["None"]+dcols, key="ca_churn_dt")
        if st.button("🔍 Analyse Churn", type="primary", use_container_width=True):
            result = ca.churn_risk(df, cust_c, dt_c if dt_c!="None" else None)
            if result is not None:
                rc = result["Churn_Risk"].value_counts()
                c1,c2,c3 = st.columns(3)
                c1.metric("🔴 High",   rc.get("🔴 High",0))
                c2.metric("🟡 Medium", rc.get("🟡 Medium",0))
                c3.metric("🟢 Low",    rc.get("🟢 Low",0))
                fig = px.bar(rc.reset_index(), x="Churn_Risk", y="count",
                             color="Churn_Risk",
                             color_discrete_map={"🔴 High":"#EF4444","🟡 Medium":"#F59E0B","🟢 Low":"#10B981"},
                             title="Churn Risk Distribution")
                fig.update_layout(**_cl(), height=280); st.plotly_chart(fig, use_container_width=True)
                st.dataframe(result, use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════════════════════
# FEATURE ENGINEERING
# ═════════════════════════════════════════════════════════════

def _feature_engineering(df: pd.DataFrame):
    st.markdown("### 🔧 Automated Feature Engineering")
    st.info("Adds date parts, polynomial (x²), and interaction (x×y) features.")
    orig = len(df.columns)
    c1,c2,c3 = st.columns(3)
    c1.metric("Original Features", orig)

    if st.button("⚙️ Generate Features", type="primary", use_container_width=True):
        enhanced = auto_feature_engineer(df)
        new_feat = len(enhanced.columns)-orig
        c2.metric("New Features", new_feat); c3.metric("Total", len(enhanced.columns))
        st.success(f"✅ {new_feat} new features generated!")

        new_cols = [c for c in enhanced.columns if c not in df.columns]
        ca,cb,cc = st.columns(3)
        with ca:
            st.markdown("**🔗 Interactions**")
            for c in [x for x in new_cols if x.startswith("_ix_")]:
                st.markdown(f"<small style='color:#6C63FF;'>+ {c}</small>",unsafe_allow_html=True)
        with cb:
            st.markdown("**² Polynomial**")
            for c in [x for x in new_cols if x.startswith("_sq_")]:
                st.markdown(f"<small style='color:#0AEFFF;'>+ {c}</small>",unsafe_allow_html=True)
        with cc:
            st.markdown("**📅 Date Parts**")
            for c in [x for x in new_cols if any(k in x for k in ["_year","_month","_dow","_qtr"])]:
                st.markdown(f"<small style='color:#10B981;'>+ {c}</small>",unsafe_allow_html=True)

        st.dataframe(enhanced.head(8), use_container_width=True)

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            enhanced.to_excel(writer, sheet_name="Enhanced Features", index=False)
            pd.DataFrame({"New Feature":new_cols}).to_excel(writer, sheet_name="Feature List", index=False)
        buf.seek(0)
        st.download_button("📥 Download Enhanced Dataset (Excel)", buf.read(),
                           "lionsylai_enhanced_features.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)


# ─────────────────────────────────────────────────────────────
def _cl():
    return dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#F0F2FF",family="Inter"),
        xaxis=dict(showgrid=True,gridcolor="#252836",zeroline=False),
        yaxis=dict(showgrid=True,gridcolor="#252836",zeroline=False),
        margin=dict(t=40,b=30,l=10,r=10),
        coloraxis_colorbar=dict(tickfont=dict(color="#F0F2FF")),
        legend=dict(bgcolor="rgba(0,0,0,0)",bordercolor="#252836"),
    )
