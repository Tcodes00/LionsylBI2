"""
LionsylAI ML Engine v4 — Production
12-step DataPreprocessor · HyperparamTuner · MLEngine · auto_clean_dataframe
"""
from __future__ import annotations
import logging, warnings, io
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
log = logging.getLogger("lionsylai.ml")

from sklearn.ensemble import (
    RandomForestRegressor, RandomForestClassifier,
    HistGradientBoostingRegressor, HistGradientBoostingClassifier,
    StackingRegressor, StackingClassifier,
)
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.preprocessing import RobustScaler, LabelEncoder
from sklearn.impute import KNNImputer
from sklearn.model_selection import train_test_split, cross_val_score, RandomizedSearchCV
from sklearn.metrics import (
    mean_squared_error, r2_score, mean_absolute_error,
    accuracy_score, f1_score, precision_score, recall_score,
)
from sklearn.feature_selection import SelectKBest, mutual_info_regression, mutual_info_classif
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

try:
    import xgboost as xgb; XGB_OK = True
except ImportError:
    XGB_OK = False
try:
    import lightgbm as lgb; LGB_OK = True
except ImportError:
    LGB_OK = False
try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    STATS_OK = True
except ImportError:
    STATS_OK = False


# ═══════════════════════════════════════════════════════════
# AUTO CLEAN  (standalone — no ML needed)
# ═══════════════════════════════════════════════════════════

def auto_clean_dataframe(
    df: pd.DataFrame,
    # Manual overrides (None = auto)
    drop_missing_thresh: float = 0.70,   # drop col if >70% missing
    outlier_low: float         = 0.005,  # bottom 0.5% winsorise
    outlier_high: float        = 0.995,  # top 99.5% winsorise
    fix_negatives: bool        = True,   # abs() on qty/price cols
    encode_cats: bool          = False,  # OHE categoricals (off for clean sheet)
    drop_id_cols: bool         = True,   # drop all-unique text cols
    fill_method: str           = "median",  # "median" | "mean" | "zero" | "knn"
    custom_drops: List[str]    = None,   # user-specified cols to drop
    manual_types: Dict[str,str]= None,   # {"col": "numeric"/"date"/"text"}
) -> Tuple[pd.DataFrame, Dict]:
    """
    Comprehensive standalone cleaner.
    Returns (cleaned_df, report_dict).
    """
    report = {
        "original_shape": df.shape,
        "steps": [], "warnings": [],
        "missing_before": int(df.isnull().sum().sum()),
        "missing_after": 0,
        "rows_removed": 0,
        "cols_removed": 0,
        "issues_fixed": 0,
        "col_actions": {},   # per-column record
    }
    out = df.copy()

    def _log(msg, warn=False):
        report["steps"].append(msg)
        if warn:
            report["warnings"].append(msg)

    # ── 1. Manual type overrides ─────────────────────────────
    if manual_types:
        for col, dtype in (manual_types or {}).items():
            if col not in out.columns:
                continue
            if dtype == "numeric":
                out[col] = pd.to_numeric(out[col], errors="coerce")
                _log(f"Forced '{col}' → numeric")
            elif dtype == "date":
                out[col] = pd.to_datetime(out[col], errors="coerce", infer_datetime_format=True)
                _log(f"Forced '{col}' → datetime")
            elif dtype == "text":
                out[col] = out[col].astype(str)
                _log(f"Forced '{col}' → text")

    # ── 2. Drop user-specified columns ───────────────────────
    for col in (custom_drops or []):
        if col in out.columns:
            out = out.drop(columns=[col])
            _log(f"User-dropped column: '{col}'")
            report["issues_fixed"] += 1

    # ── 3. Drop fully-empty rows / cols ──────────────────────
    before_r, before_c = out.shape
    out = out.dropna(how="all").dropna(axis=1, how="all")
    dr = before_r - out.shape[0]
    dc = before_c - out.shape[1]
    if dr: _log(f"Removed {dr} fully-empty rows"); report["issues_fixed"] += 1
    if dc: _log(f"Removed {dc} fully-empty columns"); report["issues_fixed"] += 1

    # ── 4. Drop unnamed index columns ────────────────────────
    unnamed = [c for c in out.columns if str(c).startswith("Unnamed")]
    if unnamed:
        out = out.drop(columns=unnamed)
        _log(f"Dropped {len(unnamed)} Unnamed index columns: {unnamed[:4]}")
        report["issues_fixed"] += 1

    # ── 5. Drop high-missing columns ─────────────────────────
    miss_pct = out.isnull().mean()
    high_miss = miss_pct[miss_pct > drop_missing_thresh].index.tolist()
    if high_miss:
        out = out.drop(columns=high_miss)
        _log(f"Dropped {len(high_miss)} cols with >{drop_missing_thresh*100:.0f}% missing: {high_miss[:4]}")
        report["issues_fixed"] += 1

    # ── 6. Auto-detect and drop ID columns ──────────────────
    if drop_id_cols:
        id_cols = []
        for col in out.columns:
            if out[col].dtype == object and out[col].nunique() == len(out) and len(out) > 50:
                id_cols.append(col)
        if id_cols:
            out = out.drop(columns=id_cols)
            _log(f"Dropped {len(id_cols)} ID/key cols (all unique): {id_cols[:4]}")
            report["issues_fixed"] += 1

    # ── 7. Coerce types (dates, numeric strings) ─────────────
    coerced = []
    for col in out.select_dtypes(include=["object"]).columns:
        # Try date
        if any(k in col.lower() for k in ["date","time","stamp","month","year","period","dt"]):
            try:
                p = pd.to_datetime(out[col], errors="coerce", infer_datetime_format=True)
                if p.notna().mean() > 0.50:
                    out[col] = p; coerced.append(f"{col}→date"); continue
            except Exception:
                pass
        # Try numeric
        try:
            converted = pd.to_numeric(out[col], errors="coerce")
            if converted.notna().mean() > 0.70:
                out[col] = converted; coerced.append(f"{col}→num")
        except Exception:
            pass
    if coerced:
        _log(f"Type-coerced {len(coerced)} columns: {coerced[:6]}")
        report["issues_fixed"] += 1

    # ── 8. Remove duplicate rows ─────────────────────────────
    before = len(out)
    out = out.drop_duplicates()
    n_dup = before - len(out)
    if n_dup:
        _log(f"Removed {n_dup} duplicate rows")
        report["issues_fixed"] += n_dup
    report["rows_removed"] = df.shape[0] - out.shape[0]
    report["cols_removed"] = df.shape[1] - out.shape[1]

    # ── 9. Fill numeric NaN ──────────────────────────────────
    num_cols = out.select_dtypes(include=[np.number]).columns.tolist()
    total_num_nan = 0
    for col in num_cols:
        n_nan = int(out[col].isnull().sum())
        if n_nan == 0:
            continue
        total_num_nan += n_nan
        if fill_method == "mean":
            fill_val = float(out[col].mean())
        elif fill_method == "zero":
            fill_val = 0.0
        elif fill_method == "knn":
            try:
                out[[col]] = KNNImputer(n_neighbors=5).fit_transform(out[[col]])
                _log(f"KNN-filled {n_nan} NaN in '{col}'")
                report["issues_fixed"] += n_nan
                continue
            except Exception:
                fill_val = float(out[col].median()) if out[col].notna().any() else 0.0
        else:  # median (default)
            fill_val = float(out[col].median()) if out[col].notna().any() else 0.0
        out[col] = out[col].fillna(fill_val)
        _log(f"Filled {n_nan} NaN in '{col}' with {fill_method}={fill_val:.4g}")
        report["issues_fixed"] += n_nan
        report["col_actions"][col] = report["col_actions"].get(col, []) + [f"filled {n_nan} NaN"]

    # ── 10. Fix invalid / impossible values ──────────────────
    if fix_negatives:
        for col in num_cols:
            neg_mask = out[col] < 0
            n_neg    = int(neg_mask.sum())
            if n_neg > 0 and any(k in col.lower() for k in
                                  ["qty","quantity","count","age","price","revenue",
                                   "cost","units","sales","amount","volume"]):
                out[col] = out[col].abs()
                _log(f"Fixed {n_neg} negative values in '{col}' → |absolute|")
                report["issues_fixed"] += n_neg
                report["col_actions"][col] = report["col_actions"].get(col, []) + [f"fixed {n_neg} negatives"]

    # ── 11. Winsorise outliers ───────────────────────────────
    for col in num_cols:
        if col not in out.columns:
            continue
        s = out[col].dropna()
        if len(s) < 10:
            continue
        q_lo  = float(s.quantile(outlier_low))
        q_hi  = float(s.quantile(outlier_high))
        n_out = int(((out[col] < q_lo) | (out[col] > q_hi)).sum())
        if n_out > 0:
            out[col] = out[col].clip(lower=q_lo, upper=q_hi)
            _log(f"Capped {n_out} outliers in '{col}' [{q_lo:.4g} – {q_hi:.4g}]")
            report["issues_fixed"] += n_out
            report["col_actions"][col] = report["col_actions"].get(col, []) + [f"capped {n_out} outliers"]

    # ── 12. Fill categorical NaN ─────────────────────────────
    cat_cols = out.select_dtypes(include=["object","category"]).columns.tolist()
    for col in cat_cols:
        n_nan = int(out[col].isnull().sum())
        if n_nan > 0:
            mode = out[col].mode()
            fill = mode[0] if len(mode) > 0 else "Unknown"
            out[col] = out[col].fillna(fill)
            _log(f"Filled {n_nan} NaN in '{col}' with mode='{fill}'")
            report["issues_fixed"] += n_nan
        out[col] = out[col].astype(str).str.strip()
        # Standardise empty-ish strings
        out[col] = out[col].replace(
            {"nan":"Unknown","None":"Unknown","<NA>":"Unknown","":"Unknown","NaN":"Unknown"})

    # ── 13. Optional OHE ─────────────────────────────────────
    if encode_cats:
        for col in list(out.select_dtypes(include=["object","category"]).columns):
            if out[col].nunique() <= 15:
                dummies = pd.get_dummies(out[col], prefix=col, drop_first=True, dtype=float)
                out = out.drop(columns=[col])
                out = pd.concat([out, dummies], axis=1)
                _log(f"One-hot encoded '{col}' → {len(dummies.columns)} dummy cols")

    # ── 14. Drop zero-variance columns ──────────────────────
    num_now = out.select_dtypes(include=[np.number]).columns.tolist()
    zero_var = [c for c in num_now if out[c].std(ddof=0) == 0]
    if zero_var:
        out = out.drop(columns=zero_var)
        _log(f"Dropped {len(zero_var)} zero-variance columns: {zero_var[:4]}")
        report["issues_fixed"] += 1

    # ── 15. Final safety: no remaining NaN ──────────────────
    still_nan = int(out.isnull().sum().sum())
    if still_nan > 0:
        for col in out.columns:
            if out[col].isnull().any():
                if pd.api.types.is_numeric_dtype(out[col]):
                    out[col] = out[col].fillna(0.0)
                else:
                    out[col] = out[col].fillna("Unknown")
        _log(f"Final safety fill: {still_nan} remaining NaN → 0 / 'Unknown'", warn=True)

    report["missing_after"]  = int(out.isnull().sum().sum())
    report["final_shape"]    = out.shape
    return out, report


# ═══════════════════════════════════════════════════════════
# 12-STEP DATA PREPROCESSOR  (for ML pipeline)
# ═══════════════════════════════════════════════════════════

class DataPreprocessor:
    def __init__(self, task="regression", verbose=False):
        self.task    = task
        self.verbose = verbose
        self.report  = {"steps":[],"warnings":[]}
        self.label_encoders: Dict[str,LabelEncoder] = {}
        self._ohe_cols:  Dict[str,List[str]] = {}
        self._cat_fills: Dict[str,str] = {}
        self._num_low_fill  = None
        self._knn_imp       = None
        self._out_bounds:   Dict[str,Tuple] = {}
        self._scaler        = None
        self._selected_features: List[str] = []
        self.feature_names_out: List[str] = []

    def fit_transform(self, df: pd.DataFrame, target: str) -> Tuple[pd.DataFrame, pd.Series]:
        df = df.copy()
        self.report = {"target":target,"original_shape":df.shape,"steps":[],"warnings":[]}
        df, y = self._split_target(df, target)
        df    = self._s1_drop_useless(df)
        df    = self._s2_coerce(df)
        df    = self._s3_dedup(df)
        y     = self._s4_clean_y(y)
        df, y = self._s5_align(df, y)
        df    = self._s6_impute_num(df, fit=True)
        df    = self._s7_impute_cat(df, fit=True)
        df    = self._s8_encode(df, fit=True)
        df    = self._s9_outliers(df, fit=True)
        df    = self._s10_scale(df, fit=True)
        df    = self._s11_engineer(df)
        df    = self._s12_select(df, y, fit=True)
        self.feature_names_out = df.columns.tolist()
        self.report["final_shape"] = df.shape
        return df, y

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = self._s2_coerce(df)
        df = self._s6_impute_num(df, fit=False)
        df = self._s7_impute_cat(df, fit=False)
        df = self._s8_encode(df, fit=False)
        df = self._s9_outliers(df, fit=False)
        df = self._s10_scale(df, fit=False)
        df = self._s11_engineer(df)
        for col in self.feature_names_out:
            if col not in df.columns:
                df[col] = 0.0
        return df[self.feature_names_out]

    def get_report(self): return self.report
    def _log(self, msg): self.report["steps"].append(msg)

    def _split_target(self, df, target):
        y = df[target].copy(); df = df.drop(columns=[target])
        self._log(f"Target='{target}' | Features={len(df.columns)}")
        return df, y

    def _s1_drop_useless(self, df):
        drop = []
        for col in df.columns:
            if df[col].isnull().mean() > 0.70:            drop.append(col); continue
            if df[col].dtype in [np.float64,np.int64,float,int]:
                if df[col].dropna().std(ddof=0) == 0:     drop.append(col); continue
            if df[col].dtype == object and df[col].nunique() == len(df) and len(df) > 50:
                drop.append(col)
        if drop:
            df = df.drop(columns=drop, errors="ignore")
            self._log(f"S1: Dropped {len(drop)} useless cols")
        return df

    def _s2_coerce(self, df):
        for col in df.select_dtypes(include=["object"]).columns:
            if any(k in col.lower() for k in ["date","time","stamp","month","year","period","dt"]):
                try:
                    p = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
                    if p.notna().mean() > 0.5: df[col] = p; continue
                except Exception: pass
            try:
                c2 = pd.to_numeric(df[col], errors="coerce")
                if c2.notna().mean() > 0.70: df[col] = c2
            except Exception: pass
        self._log("S2: Types coerced")
        return df

    def _s3_dedup(self, df):
        b = len(df); df = df.drop_duplicates()
        if len(df) < b: self._log(f"S3: Removed {b-len(df)} duplicates")
        return df

    def _s4_clean_y(self, y):
        if self.task == "regression":
            y = pd.to_numeric(y, errors="coerce")
            if y.isnull().any():
                med = float(y.median()); n = int(y.isnull().sum())
                y = y.fillna(med); self._log(f"S4: Filled {n} target NaN (median={med:.2f})")
            y = y.replace([np.inf,-np.inf], float(y.median()))
        else:
            if y.dtype == object or str(y.dtype) == "category":
                le = LabelEncoder()
                y = pd.Series(le.fit_transform(y.fillna("Unknown").astype(str)), name=y.name)
                self.label_encoders["__target__"] = le
            y = y.fillna(y.mode()[0] if len(y.mode()) > 0 else 0)
        self._log("S4: Target cleaned")
        return y

    def _s5_align(self, df, y):
        valid = y.dropna().index.intersection(df.index)
        before = len(df); df = df.loc[valid]; y = y.loc[valid]
        if len(df) < before: self._log(f"S5: Aligned {len(df)}/{before} rows")
        return df, y

    def _s6_impute_num(self, df, fit=True):
        # Extract datetime features
        for col in df.select_dtypes(include=["datetime64"]).columns:
            df[f"{col}_year"]  = df[col].dt.year.astype(float)
            df[f"{col}_month"] = df[col].dt.month.astype(float)
            df[f"{col}_dow"]   = df[col].dt.dayofweek.astype(float)
            df[f"{col}_qtr"]   = df[col].dt.quarter.astype(float)
            df = df.drop(columns=[col])
        num = df.select_dtypes(include=[np.number]).columns.tolist()
        if not num: return df
        miss = df[num].isnull().mean()
        low  = miss[miss <= 0.15].index.tolist()
        high = miss[(miss > 0.15) & (miss <= 0.60)].index.tolist()
        if low:
            if fit: self._num_low_fill = df[low].median()
            df[low] = df[low].fillna(self._num_low_fill if self._num_low_fill is not None else df[low].median())
        if high:
            try:
                if fit:
                    self._knn_imp = KNNImputer(n_neighbors=5)
                    df[high] = self._knn_imp.fit_transform(df[high])
                else:
                    df[high] = self._knn_imp.transform(df[high])
            except Exception:
                df[high] = df[high].fillna(df[high].median())
        rem = df.select_dtypes(include=[np.number]).columns
        df[rem] = df[rem].fillna(0)
        self._log(f"S6: Numeric imputed → {int(df.isnull().sum().sum())} NaN remain")
        return df

    def _s7_impute_cat(self, df, fit=True):
        for col in df.select_dtypes(include=["object","category"]).columns:
            if df[col].isnull().any():
                if fit:
                    mode = df[col].mode()
                    self._cat_fills[col] = mode[0] if len(mode) > 0 else "Unknown"
                df[col] = df[col].fillna(self._cat_fills.get(col,"Unknown"))
            df[col] = df[col].astype(str).replace(
                {"nan":"Unknown","None":"Unknown","<NA>":"Unknown","":"Unknown","NaN":"Unknown"})
        self._log("S7: Categorical imputed")
        return df

    def _s8_encode(self, df, fit=True):
        for col in list(df.select_dtypes(include=["object","category"]).columns):
            n_unique = df[col].nunique()
            if n_unique <= 12:
                try:
                    dummies = pd.get_dummies(df[col], prefix=col, drop_first=True, dtype=float)
                    if fit: self._ohe_cols[col] = dummies.columns.tolist()
                    else:
                        exp = self._ohe_cols.get(col, dummies.columns.tolist())
                        dummies = dummies.reindex(columns=exp, fill_value=0.0)
                    df = df.drop(columns=[col])
                    df = pd.concat([df, dummies], axis=1)
                    continue
                except Exception: pass
            if fit:
                le = LabelEncoder(); df[col] = le.fit_transform(df[col].astype(str))
                self.label_encoders[col] = le
            else:
                le = self.label_encoders.get(col)
                if le:
                    known = set(le.classes_)
                    df[col] = df[col].astype(str).apply(lambda x: x if x in known else le.classes_[0])
                    df[col] = le.transform(df[col])
                else: df[col] = 0
        self._log("S8: Categoricals encoded")
        return df

    def _s9_outliers(self, df, fit=True):
        capped = 0
        for col in df.select_dtypes(include=[np.number]).columns:
            if fit:
                self._out_bounds[col] = (float(df[col].quantile(0.005)),
                                          float(df[col].quantile(0.995)))
            lo, hi = self._out_bounds.get(col, (float(df[col].quantile(0.005)),
                                                  float(df[col].quantile(0.995))))
            n = int(((df[col] < lo) | (df[col] > hi)).sum())
            df[col] = df[col].clip(lower=lo, upper=hi); capped += n
        if capped: self._log(f"S9: Winsorised {capped} outliers")
        return df

    def _s10_scale(self, df, fit=True):
        num = df.select_dtypes(include=[np.number]).columns.tolist()
        if not num: return df
        if fit:
            self._scaler = RobustScaler()
            df[num] = self._scaler.fit_transform(df[num])
        else:
            df[num] = self._scaler.transform(df[num])
        self._log(f"S10: RobustScaler on {len(num)} cols")
        return df

    def _s11_engineer(self, df):
        num = df.select_dtypes(include=[np.number]).columns.tolist()
        n_added = 0
        if len(num) >= 2 and len(df.columns) < 40:
            for i,c1 in enumerate(num[:4]):
                for c2 in num[:4][i+1:]:
                    df[f"_ix_{c1[:8]}_{c2[:8]}"] = df[c1]*df[c2]; n_added += 1
        if len(num) >= 1 and len(df.columns) < 50:
            for col in num[:3]:
                df[f"_sq_{col[:8]}"] = df[col]**2; n_added += 1
        if n_added: self._log(f"S11: +{n_added} engineered features")
        return df

    def _s12_select(self, df, y, fit=True):
        num = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(num) <= 20: return df
        k = min(25, len(num))
        try:
            if fit:
                fn = mutual_info_regression if self.task=="regression" else mutual_info_classif
                sel = SelectKBest(fn, k=k)
                sel.fit(df[num].fillna(0), y)
                self._selected_features = [c for c,m in zip(num, sel.get_support()) if m]
            keep = [c for c in df.columns if c not in num] + self._selected_features
            self._log(f"S12: Selected {len(keep)}/{len(df.columns)} features")
            return df[keep]
        except Exception as e:
            log.warning(f"S12 selection skipped: {e}"); return df


# ═══════════════════════════════════════════════════════════
# HYPERPARAMETER TUNER
# ═══════════════════════════════════════════════════════════

class HyperparamTuner:
    XGB_PARAMS = {
        "n_estimators":     [200,400,600,800],
        "learning_rate":    [0.01,0.03,0.05,0.08,0.1],
        "max_depth":        [4,5,6,7,8,10],
        "min_child_weight": [1,3,5,7],
        "subsample":        [0.7,0.8,0.85,0.9,1.0],
        "colsample_bytree": [0.7,0.8,0.85,0.9,1.0],
        "reg_alpha":        [0,0.01,0.1,0.5,1.0],
        "reg_lambda":       [0.5,1.0,1.5,2.0,3.0],
        "gamma":            [0,0.05,0.1,0.2,0.3],
    }
    LGB_PARAMS = {
        "n_estimators":     [200,400,600,800],
        "learning_rate":    [0.01,0.03,0.05,0.08,0.1],
        "num_leaves":       [31,63,127,255],
        "min_child_samples":[5,10,20,30],
        "subsample":        [0.7,0.8,0.9,1.0],
        "colsample_bytree": [0.7,0.8,0.9,1.0],
        "reg_alpha":        [0,0.1,0.5,1.0],
        "reg_lambda":       [0.5,1.0,2.0,3.0],
    }
    RF_PARAMS = {
        "n_estimators":     [200,400,600],
        "max_depth":        [None,10,20,30],
        "min_samples_leaf": [1,2,5],
        "max_features":     ["sqrt","log2",0.5,0.8],
    }

    @staticmethod
    def tune(model_name, X, y, task="regression", n_iter=30):
        scoring = "r2" if task=="regression" else "accuracy"
        if model_name == "XGBoost" and XGB_OK:
            base_cls = xgb.XGBRegressor if task=="regression" else xgb.XGBClassifier
            base = base_cls(random_state=42, verbosity=0,
                            eval_metric="rmse" if task=="regression" else "logloss")
            params = HyperparamTuner.XGB_PARAMS
        elif model_name == "LightGBM" and LGB_OK:
            base_cls = lgb.LGBMRegressor if task=="regression" else lgb.LGBMClassifier
            base = base_cls(random_state=42, verbose=-1)
            params = HyperparamTuner.LGB_PARAMS
        elif model_name == "Random Forest":
            base_cls = RandomForestRegressor if task=="regression" else RandomForestClassifier
            base = base_cls(random_state=42, n_jobs=-1)
            params = HyperparamTuner.RF_PARAMS
        else:
            return None
        rs = RandomizedSearchCV(base, params, n_iter=n_iter, scoring=scoring,
                                cv=5, n_jobs=-1, random_state=42, refit=True)
        rs.fit(X, y)
        return rs.best_estimator_, float(rs.best_score_), rs.best_params_


# ═══════════════════════════════════════════════════════════
# FULL ML ENGINE
# ═══════════════════════════════════════════════════════════

class MLEngine:
    def __init__(self):
        self.preprocessor: Optional[DataPreprocessor] = None
        self._feature_names: List[str] = []
        self._task  = "regression"
        self._tuning_results: Dict = {}

    def train(self, df: pd.DataFrame, target: str,
              task: str = "regression",
              tune: bool = False,
              tune_n_iter: int = 30) -> Optional[Dict[str,Any]]:
        self._task = task
        try:
            # Pre-clean
            pre_cleaned, _ = auto_clean_dataframe(df.copy())
            # Preprocess
            self.preprocessor = DataPreprocessor(task=task, verbose=False)
            X, y = self.preprocessor.fit_transform(pre_cleaned.copy(), target)
            X = X.fillna(0).replace([np.inf,-np.inf], 0)
            if task == "regression":
                y = pd.to_numeric(y, errors="coerce")
                med = float(y.median()) if y.notna().any() else 0.0
                y = y.fillna(med).replace([np.inf,-np.inf], med)
            if len(X) == 0 or len(y) == 0: return None
            self._feature_names = X.columns.tolist()

            # Split
            test_size = min(0.20, max(0.10, 50/len(X)))
            strat = y if (task=="classification" and y.nunique() <= 20) else None
            try:
                X_tr,X_te,y_tr,y_te = train_test_split(X,y,test_size=test_size,
                                                        random_state=42,stratify=strat)
            except Exception:
                X_tr,X_te,y_tr,y_te = train_test_split(X,y,test_size=test_size,random_state=42)

            n_cv = min(5, max(3, len(X_tr)//50))

            # Models
            models = self._tune_models(X,y,task,tune_n_iter) if tune else self._default_models(task,len(X_tr))

            # Train
            results: Dict[str,Any] = {}
            for name, model in models.items():
                try:
                    model.fit(X_tr, y_tr)
                    pred = model.predict(X_te)
                    scoring = "r2" if task=="regression" else "accuracy"
                    cv = cross_val_score(model,X,y,cv=n_cv,scoring=scoring,n_jobs=-1)
                    if task == "regression":
                        results[name] = {
                            "model":   model,
                            "r2":      float(r2_score(y_te,pred)),
                            "cv_r2":   float(cv.mean()),
                            "cv_std":  float(cv.std()),
                            "rmse":    float(np.sqrt(mean_squared_error(y_te,pred))),
                            "mae":     float(mean_absolute_error(y_te,pred)),
                            "n_train": len(X_tr), "n_test": len(X_te),
                            "tuned":   name in self._tuning_results,
                        }
                    else:
                        results[name] = {
                            "model":     model,
                            "accuracy":  float(accuracy_score(y_te,pred)),
                            "cv_acc":    float(cv.mean()),
                            "cv_std":    float(cv.std()),
                            "f1":        float(f1_score(y_te,pred,average="weighted",zero_division=0)),
                            "precision": float(precision_score(y_te,pred,average="weighted",zero_division=0)),
                            "recall":    float(recall_score(y_te,pred,average="weighted",zero_division=0)),
                            "n_train":   len(X_tr), "n_test": len(X_te),
                            "tuned":     name in self._tuning_results,
                        }
                except Exception as e:
                    log.warning(f"{name} failed: {e}")

            # Stacker
            if len(results) >= 2:
                try:
                    stack = (StackingRegressor(
                                estimators=[(n,r["model"]) for n,r in results.items()],
                                final_estimator=Ridge(alpha=1.0), cv=3, n_jobs=-1)
                             if task=="regression" else
                             StackingClassifier(
                                estimators=[(n,r["model"]) for n,r in results.items()],
                                final_estimator=LogisticRegression(max_iter=500),
                                cv=3, n_jobs=-1, stack_method="predict_proba"))
                    stack.fit(X_tr, y_tr)
                    pred_s = stack.predict(X_te)
                    scoring = "r2" if task=="regression" else "accuracy"
                    cv_s = cross_val_score(stack,X,y,cv=n_cv,scoring=scoring,n_jobs=-1)
                    if task == "regression":
                        results["🏆 Stacking Ensemble"] = {
                            "model": stack,
                            "r2":    float(r2_score(y_te,pred_s)),
                            "cv_r2": float(cv_s.mean()), "cv_std": float(cv_s.std()),
                            "rmse":  float(np.sqrt(mean_squared_error(y_te,pred_s))),
                            "mae":   float(mean_absolute_error(y_te,pred_s)),
                            "n_train":len(X_tr),"n_test":len(X_te),"tuned":tune,
                        }
                    else:
                        results["🏆 Stacking Ensemble"] = {
                            "model":    stack,
                            "accuracy": float(accuracy_score(y_te,pred_s)),
                            "cv_acc":   float(cv_s.mean()), "cv_std": float(cv_s.std()),
                            "f1":       float(f1_score(y_te,pred_s,average="weighted",zero_division=0)),
                            "precision":float(precision_score(y_te,pred_s,average="weighted",zero_division=0)),
                            "recall":   float(recall_score(y_te,pred_s,average="weighted",zero_division=0)),
                            "n_train":len(X_tr),"n_test":len(X_te),"tuned":tune,
                        }
                except Exception as e:
                    log.warning(f"Stacking failed: {e}")

            return results or None
        except Exception as e:
            log.error(f"MLEngine.train: {e}", exc_info=True); return None

    def _default_models(self, task, n):
        e = 300 if n > 200 else 100
        if task == "regression":
            m = {}
            if XGB_OK: m["XGBoost"] = xgb.XGBRegressor(
                n_estimators=e,learning_rate=0.05,max_depth=6,min_child_weight=3,
                subsample=0.8,colsample_bytree=0.8,reg_alpha=0.1,reg_lambda=1.0,
                random_state=42,verbosity=0,n_jobs=-1)
            if LGB_OK: m["LightGBM"] = lgb.LGBMRegressor(
                n_estimators=e,learning_rate=0.05,num_leaves=63,min_child_samples=5,
                subsample=0.8,colsample_bytree=0.8,reg_alpha=0.1,reg_lambda=1.0,
                random_state=42,verbose=-1,n_jobs=-1)
            m["Random Forest"] = RandomForestRegressor(
                n_estimators=e,min_samples_leaf=2,max_features="sqrt",random_state=42,n_jobs=-1)
            m["HistGradBoost"] = HistGradientBoostingRegressor(
                max_iter=e,learning_rate=0.05,max_depth=6,min_samples_leaf=5,
                l2_regularization=0.1,random_state=42)
            return m
        else:
            m = {}
            if XGB_OK: m["XGBoost"] = xgb.XGBClassifier(
                n_estimators=e,learning_rate=0.05,max_depth=6,min_child_weight=3,
                subsample=0.8,colsample_bytree=0.8,reg_alpha=0.1,
                random_state=42,verbosity=0,n_jobs=-1)
            if LGB_OK: m["LightGBM"] = lgb.LGBMClassifier(
                n_estimators=e,learning_rate=0.05,num_leaves=63,min_child_samples=5,
                subsample=0.8,colsample_bytree=0.8,random_state=42,verbose=-1,n_jobs=-1)
            m["Random Forest"] = RandomForestClassifier(
                n_estimators=e,min_samples_leaf=2,max_features="sqrt",
                class_weight="balanced",random_state=42,n_jobs=-1)
            m["HistGradBoost"] = HistGradientBoostingClassifier(
                max_iter=e,learning_rate=0.05,max_depth=6,min_samples_leaf=5,
                l2_regularization=0.1,class_weight="balanced",random_state=42)
            return m

    def _tune_models(self, X, y, task, n_iter):
        models = {}; self._tuning_results = {}
        for name in ["XGBoost","LightGBM","Random Forest"]:
            try:
                res = HyperparamTuner.tune(name, X, y, task=task, n_iter=n_iter)
                if res:
                    best_model, best_score, best_params = res
                    key = f"⚡ {name} (Tuned)"
                    models[key] = best_model
                    self._tuning_results[key] = {"best_cv_score":best_score,"best_params":best_params}
            except Exception as e:
                log.warning(f"Tuning {name}: {e}")
        for n,m in self._default_models(task, len(X)).items():
            if f"⚡ {n} (Tuned)" not in models:
                models[n] = m
        return models

    def feature_importances(self, results, task):
        if not results or not self._feature_names: return None
        key = "cv_r2" if task=="regression" else "cv_acc"
        # Only consider non-stacking models that have feature_importances_ or coef_
        non_stack = {k:v for k,v in results.items() if "Stacking" not in k}
        candidates = {
            k:v for k,v in non_stack.items()
            if hasattr(v["model"],"feature_importances_") or hasattr(v["model"],"coef_")
        }
        if not candidates:
            return None
        best_name = max(candidates, key=lambda n: candidates[n].get(key, 0))
        model = candidates[best_name]["model"]
        fi = None
        if hasattr(model,"feature_importances_"):
            fi = model.feature_importances_
        elif hasattr(model,"coef_"):
            fi = np.abs(model.coef_).flatten()
        if fi is None:
            return None
        # Align lengths (safety)
        fn = self._feature_names
        min_len = min(len(fi), len(fn))
        df = pd.DataFrame({"Feature": fn[:min_len], "Importance": fi[:min_len]})
        df = df.sort_values("Importance", ascending=False).head(20)
        total = df["Importance"].sum()
        df["Importance %"] = (df["Importance"] / total * 100).round(1) if total > 0 else 0.0
        return df

    def get_tuning_results(self): return self._tuning_results
    def get_preprocessing_report(self):
        return self.preprocessor.get_report() if self.preprocessor else {}


# ═══════════════════════════════════════════════════════════
# FORECASTING  /  CLUSTERING  /  CUSTOMER ANALYTICS
# ═══════════════════════════════════════════════════════════

class ForecastEngine:
    @staticmethod
    def sarima(series, periods=30):
        s = pd.to_numeric(series,errors="coerce").dropna()
        if not STATS_OK or len(s)<20: return ForecastEngine.simple_trend(s,periods)
        try:
            m = SARIMAX(s,order=(1,1,1),seasonal_order=(1,1,1,min(12,len(s)//4)),
                        enforce_stationarity=False,enforce_invertibility=False)
            return m.fit(disp=False,maxiter=300).forecast(steps=periods)
        except Exception: return ForecastEngine.holt_winters(s,periods)

    @staticmethod
    def holt_winters(series,periods=30):
        s = pd.to_numeric(series,errors="coerce").dropna()
        if not STATS_OK or len(s)<10: return ForecastEngine.simple_trend(s,periods)
        try: return ExponentialSmoothing(s,trend="add",seasonal=None).fit().forecast(periods)
        except Exception: return ForecastEngine.simple_trend(s,periods)

    @staticmethod
    def simple_trend(series,periods=30):
        s = pd.to_numeric(series,errors="coerce").dropna()
        if len(s)<2: return pd.Series([float(s.iloc[-1]) if len(s) else 0]*periods)
        slope,intercept = np.polyfit(np.arange(len(s)),s.values,1)
        return pd.Series(slope*np.arange(len(s),len(s)+periods)+intercept,name="forecast")

    @staticmethod
    def monte_carlo(series,simulations=1000,periods=30):
        s = pd.to_numeric(series,errors="coerce").dropna()
        ret = s.pct_change().dropna().replace([np.inf,-np.inf],np.nan).dropna()
        if len(ret)==0:
            z=pd.Series([float(s.iloc[-1])]*periods); return z,z,z
        mu,sigma,last = float(ret.mean()),float(ret.std()),float(s.iloc[-1])
        np.random.seed(42)
        sims = np.zeros((simulations,periods))
        for i in range(simulations):
            sims[i] = last*np.cumprod(1+np.clip(np.random.normal(mu,sigma,periods),-0.5,0.5))
        df_s = pd.DataFrame(sims)
        return df_s.mean(axis=0),df_s.quantile(0.05,axis=0),df_s.quantile(0.95,axis=0)


class ClusterEngine:
    @staticmethod
    def kmeans(df,features,k=3):
        try:
            X = df[features].apply(pd.to_numeric,errors="coerce").fillna(0).replace([np.inf,-np.inf],0)
            if len(X)<k: return None
            Xs = RobustScaler().fit_transform(X)
            km = KMeans(n_clusters=k,random_state=42,n_init=20,max_iter=500)
            result = X.copy(); result["Cluster"] = km.fit_predict(Xs).astype(str)
            return result,km
        except Exception as e: log.warning(f"KMeans: {e}"); return None

    @staticmethod
    def pca_2d(df,features):
        try:
            X = df[features].apply(pd.to_numeric,errors="coerce").fillna(0).replace([np.inf,-np.inf],0)
            if X.shape[1]<2: return None
            comps = PCA(n_components=2,random_state=42).fit_transform(RobustScaler().fit_transform(X))
            return pd.DataFrame(comps,columns=["PC1","PC2"],index=df.index[:len(comps)])
        except Exception as e: log.warning(f"PCA: {e}"); return None

    @staticmethod
    def elbow_method(df,features,max_k=10):
        try:
            X = df[features].apply(pd.to_numeric,errors="coerce").fillna(0)
            Xs = RobustScaler().fit_transform(X)
            return {k:KMeans(n_clusters=k,random_state=42,n_init=10).fit(Xs).inertia_
                    for k in range(2,min(max_k+1,len(X)))}
        except Exception as e: log.warning(f"Elbow: {e}"); return {}


class CustomerAnalytics:
    @staticmethod
    def clv(df,customer_col,revenue_col):
        try:
            rev = pd.to_numeric(df[revenue_col],errors="coerce")
            valid = df[rev.notna()].copy(); valid[revenue_col]=rev[rev.notna()]
            g = valid.groupby(customer_col)[revenue_col].agg(
                total_revenue="sum",avg_order_value="mean",order_count="count").reset_index()
            g["estimated_clv"]=g["avg_order_value"]*g["order_count"]*(1+np.log1p(g["order_count"]))
            return g.sort_values("estimated_clv",ascending=False)
        except Exception as e: log.warning(f"CLV: {e}"); return None

    @staticmethod
    def rfm(df,customer_col,date_col,revenue_col):
        try:
            tmp=df.copy()
            tmp[date_col]=pd.to_datetime(tmp[date_col],errors="coerce")
            tmp[revenue_col]=pd.to_numeric(tmp[revenue_col],errors="coerce")
            tmp=tmp.dropna(subset=[date_col,revenue_col])
            if len(tmp)<5: return None
            now=tmp[date_col].max()+pd.Timedelta(days=1)
            rfm=tmp.groupby(customer_col).agg(
                Recency=(date_col,lambda x:(now-x.max()).days),
                Frequency=(date_col,"count"),Monetary=(revenue_col,"sum")).reset_index()
            def _qcut(s,labels):
                try: return pd.qcut(s.rank(method="first"),q=4,labels=labels)
                except: return pd.cut(s,bins=4,labels=labels)
            rfm["R_Score"]=_qcut(rfm["Recency"],[4,3,2,1])
            rfm["F_Score"]=_qcut(rfm["Frequency"],[1,2,3,4])
            rfm["M_Score"]=_qcut(rfm["Monetary"],[1,2,3,4])
            for c in ["R_Score","F_Score","M_Score"]:
                rfm[c]=pd.to_numeric(rfm[c],errors="coerce").fillna(2).astype(int)
            rfm["RFM_Score"]=rfm["R_Score"]+rfm["F_Score"]+rfm["M_Score"]
            rfm["Segment"]=pd.cut(rfm["RFM_Score"],bins=[0,4,7,10,12],
                labels=["At Risk","Needs Attention","Loyal","Champion"])
            return rfm.sort_values("RFM_Score",ascending=False)
        except Exception as e: log.warning(f"RFM: {e}"); return None

    @staticmethod
    def churn_risk(df,customer_col,date_col=None):
        try:
            if date_col and date_col in df.columns:
                tmp=df.copy(); tmp[date_col]=pd.to_datetime(tmp[date_col],errors="coerce")
                tmp=tmp.dropna(subset=[date_col])
                now=tmp[date_col].max()
                last=tmp.groupby(customer_col)[date_col].max()
                days=(now-last).dt.days
                tx=tmp.groupby(customer_col).size().rename("tx")
                result=pd.DataFrame({"Customer":last.index,"Days_Inactive":days.values,
                                      "TX_Count":tx.reindex(last.index,fill_value=1).values})
            else:
                tx=df.groupby(customer_col).size()
                result=pd.DataFrame({"Customer":tx.index,"Days_Inactive":np.nan,"TX_Count":tx.values})
            def _risk(row):
                d,t=row.get("Days_Inactive",np.nan),row.get("TX_Count",1)
                if pd.notna(d):
                    if d>90: return "🔴 High"
                    if d>30: return "🟡 Medium"
                if t<=1: return "🔴 High"
                if t<=3: return "🟡 Medium"
                return "🟢 Low"
            result["Churn_Risk"]=result.apply(_risk,axis=1)
            return result.sort_values("Churn_Risk")
        except Exception as e: log.warning(f"Churn: {e}"); return None


def auto_feature_engineer(df):
    out=df.copy()
    for col in out.select_dtypes(include=["datetime64"]).columns:
        out[f"{col}_year"]=out[col].dt.year; out[f"{col}_month"]=out[col].dt.month
        out[f"{col}_quarter"]=out[col].dt.quarter; out[f"{col}_dow"]=out[col].dt.dayofweek
        out[f"{col}_is_wknd"]=(out[col].dt.dayofweek>=5).astype(int)
    num=out.select_dtypes(include=[np.number]).columns[:3].tolist()
    for i,c1 in enumerate(num):
        for c2 in num[i+1:]:
            out[f"{c1}_x_{c2}"]=out[c1]*out[c2]
            out[f"{c1}_div_{c2}"]=out[c1]/(out[c2].replace(0,np.nan))
    if len(num)>1:
        out["_num_row_mean"]=out[num].mean(axis=1); out["_num_row_std"]=out[num].std(axis=1)
    return out
