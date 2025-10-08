import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

# ---------------------------
# Utilities
# ---------------------------

def sanitize_columns(df: pd.DataFrame):
    """Return a copy with safe snake_case columns and a mapping from original->safe.
    Only [A-Za-z0-9_] retained; spaces and others become underscores; ensure uniqueness.
    """
    def to_safe(name):
        s = str(name).strip().lower()
        # replace non-alphanumeric with underscore
        s = pd.Series([s]).str.replace(r"[^A-Za-z0-9]+", "_", regex=True).iloc[0]
        s = s.strip("_")
        if s == "":
            s = "col"
        return s

    safe_cols = []
    used = set()
    mapping = {}
    for col in df.columns:
        base = to_safe(col)
        candidate = base
        i = 1
        while candidate in used:
            i += 1
            candidate = f"{base}_{i}"
        used.add(candidate)
        safe_cols.append(candidate)
        mapping[col] = candidate
    df_safe = df.copy()
    df_safe.columns = safe_cols
    return df_safe, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """Coerce specified columns to numeric. Strip common non-numeric chars, handle parentheses for negatives."""
    for c in cols:
        if c in df.columns:
            s = df[c].astype(str)
            # Remove spaces and commas
            s = s.str.replace(r"[\s,]", "", regex=True)
            # Convert (123) to -123
            s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
            # Remove currency and other symbols except signs, digits, decimal, exponent
            s = s.str.replace(r"[^0-9eE\+\-\.]+", "", regex=True)
            df[c] = pd.to_numeric(s, errors="coerce")
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce specified columns to datetime."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable, fallback_df: pd.DataFrame = None):
    """Safely build and render an Altair chart. On failure, warn and show sanitized table."""
    try:
        chart = chart_builder_callable()
        if chart is None:
            raise ValueError("Chart builder returned None")
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.warning("Chart unavailable")
        if fallback_df is not None and isinstance(fallback_df, pd.DataFrame) and not fallback_df.empty:
            st.dataframe(fallback_df)


# ---------------------------
# Render App
# ---------------------------

def render_app():
    # Guard page config to avoid re-setting on reruns/imports
    if not st.session_state.get("_page_config_set", False):
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_set"] = True

    alt.data_transformers.disable_max_rows()

    # The provided JSON report
    report = {
        "valid": True,
        "issues": [],
        "summary": ["Ping OK: 67978 receipts counted."],
        "tables": [
            {"name": "Ping", "columns": ["ping"], "rows": [["67978"]]}
        ],
        "charts": [
            {
                "id": "ping_kpi",
                "type": "kpi",
                "spec": {"xKey": "ping", "yKey": "ping", "series": [{"name": "ping", "yKey": "ping"}]}
            }
        ],
        "echo": {
            "intent": "single_number",
            "used": {"tables": ["`Haleon_Rewards_User_Performance_110925_SKUs`"], "columns": ["receiptid"]},
            "stats": {"elapsed": 0.00169683},
            "sql_present": True
        }
    }

    st.title("AI Report")

    # Summary section
    if isinstance(report.get("summary"), list) and report["summary"]:
        st.subheader("Summary")
        for item in report["summary"]:
            st.markdown(f"- {item}")

    # Load tables into DataFrames
    dataframes = []
    for tbl in report.get("tables", []):
        name = tbl.get("name") or "Table"
        columns = tbl.get("columns") or []
        rows = tbl.get("rows") or []
        try:
            df = pd.DataFrame(rows, columns=columns)
        except Exception:
            # Fallback: try without columns if mismatch
            df = pd.DataFrame(rows)
        dataframes.append({"name": name, "df": df})

    # Show tables (original columns)
    if dataframes:
        st.subheader("Tables")
        for obj in dataframes:
            st.markdown(f"**{obj['name']}**")
            st.dataframe(obj["df"])  # original column names

    # Helper: choose table for a chart based on presence of keys
    def choose_table_for_chart(x_key, y_key):
        # prefer table containing both keys, then either key, else first
        best = None
        for obj in dataframes:
            cols = list(obj["df"].columns)
            if x_key in cols and y_key in cols:
                return obj
            if best is None and (x_key in cols or y_key in cols):
                best = obj
        return best if best is not None else (dataframes[0] if dataframes else None)

    # Charts section
    charts = report.get("charts", [])
    if charts:
        st.subheader("Visualizations")

    # Build and render each chart
    for ch in charts:
        ch_id = ch.get("id") or "chart"
        ch_type = (ch.get("type") or "").lower()
        spec = ch.get("spec", {})
        x_key = spec.get("xKey")
        y_key = spec.get("yKey")

        st.markdown(f"**{ch_id}**")

        table_obj = choose_table_for_chart(x_key, y_key) if dataframes else None
        if table_obj is None:
            st.warning("Chart unavailable")
            continue

        df_original = table_obj["df"].copy()
        df_sanitized, mapping = sanitize_columns(df_original)

        # Resolver from original to safe, or direct if already safe
        def to_safe(col_name):
            if col_name in df_sanitized.columns:
                return col_name
            if col_name in mapping:
                return mapping[col_name]
            # try case-insensitive match
            for orig, safe in mapping.items():
                if str(orig).lower() == str(col_name).lower():
                    return safe
            return None

        # KPI rendering
        if ch_type == "kpi":
            # Pick a numeric column: prefer y_key, else x_key, else first column
            safe_val_col = None
            if y_key:
                safe_val_col = to_safe(y_key)
            if safe_val_col is None and x_key:
                safe_val_col = to_safe(x_key)
            if safe_val_col is None and len(df_sanitized.columns) > 0:
                safe_val_col = df_sanitized.columns[0]

            if safe_val_col is None:
                st.warning("Chart unavailable")
                st.dataframe(df_sanitized)
                continue

            # Coerce numeric and compute a single value
            df_num = df_sanitized.copy()
            coerce_numeric(df_num, [safe_val_col])
            series = df_num[safe_val_col].dropna()
            if series.empty:
                st.warning("Chart unavailable")
                st.dataframe(df_sanitized)
                continue

            # Use the first non-null value
            value = series.iloc[0]
            label = ch_id if y_key is None else str(y_key)
            try:
                # Format value nicely
                if pd.api.types.is_integer_dtype(series):
                    val_str = f"{int(value):,}"
                else:
                    # Show up to 2 decimals if needed
                    val_str = f"{float(value):,.2f}" if abs(value - int(value)) > 1e-9 else f"{int(value):,}"
            except Exception:
                val_str = str(value)

            st.metric(label=label, value=val_str)
            continue

        # Pie-like charts
        if ch_type in ("pie", "donut"):
            dim_col = to_safe(x_key) or (df_sanitized.columns[0] if df_sanitized.columns.size > 0 else None)
            val_col = to_safe(y_key) or None
            if dim_col is None or val_col is None:
                st.warning("Chart unavailable")
                st.dataframe(df_sanitized)
                continue

            df_chart = df_sanitized[[dim_col, val_col]].copy()
            coerce_numeric(df_chart, [val_col])
            df_chart = df_chart.dropna(subset=[dim_col, val_col])
            if df_chart.empty:
                st.warning("Chart unavailable")
                st.dataframe(df_sanitized)
                continue

            def build_pie():
                return alt.Chart(df_chart).mark_arc().encode(
                    theta=alt.Theta(val_col, type="quantitative"),
                    color=alt.Color(dim_col, type="nominal"),
                    tooltip=[dim_col, val_col]
                )

            safe_altair_chart(build_pie, fallback_df=df_chart)
            continue

        # Bar/Line/Area charts
        if ch_type in ("bar", "line", "area"):
            x_col = to_safe(x_key) or (df_sanitized.columns[0] if df_sanitized.columns.size > 0 else None)
            y_col = to_safe(y_key)

            if x_col is None or y_col is None or x_col not in df_sanitized.columns or y_col not in df_sanitized.columns:
                st.warning("Chart unavailable")
                st.dataframe(df_sanitized)
                continue

            df_chart = df_sanitized[[x_col, y_col]].copy()

            # Attempt datetime coercion for x; numeric for y
            df_chart = coerce_datetime(df_chart, [x_col])
            df_chart = coerce_numeric(df_chart, [y_col])

            # Determine x type: temporal if any datetime exists, else nominal
            x_is_datetime = pd.api.types.is_datetime64_any_dtype(df_chart[x_col]) and df_chart[x_col].notna().any()

            # Drop rows with NaN in required fields
            df_chart = df_chart.dropna(subset=[x_col, y_col])
            if df_chart.empty:
                st.warning("Chart unavailable")
                st.dataframe(df_sanitized)
                continue

            def build_mark():
                if ch_type == "bar":
                    mark = alt.Chart(df_chart).mark_bar()
                elif ch_type == "line":
                    mark = alt.Chart(df_chart).mark_line()
                else:
                    mark = alt.Chart(df_chart).mark_area()

                x_enc = alt.X(x_col, type="temporal" if x_is_datetime else "nominal")
                y_enc = alt.Y(y_col, type="quantitative")

                return mark.encode(
                    x=x_enc,
                    y=y_enc,
                    tooltip=[x_col, y_col]
                )

            safe_altair_chart(build_mark, fallback_df=df_chart)
            continue

        # Unknown chart types -> warn and show table
        st.warning("Chart unavailable")
        st.dataframe(df_sanitized)


# Note: No top-level execution. Intended usage:
# from streamlit_app import render_app
# render_app()
