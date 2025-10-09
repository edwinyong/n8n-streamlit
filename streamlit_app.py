import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

# Embedded report data
REPORT_DATA = {
    "valid": True,
    "issues": [],
    "summary": [
        "Monthly sales and registered users show significant fluctuations over the observed period.",
        "Sales peak in some months (e.g., Jan 2024, Jun 2025) and dip notably in others (e.g., Sep 2025).",
        "Registered users generally follow a similar pattern to sales, with higher numbers in months of high sales.",
        "Both metrics exhibit seasonality and volatility, suggesting external factors or campaigns may drive spikes.",
        "Prediction: If the current pattern continues, expect periodic peaks and troughs in both sales and registrations, with possible growth in peak values over time."
    ],
    "tables": [
        {
            "name": "Monthly Sales and Registered Users",
            "columns": ["month", "total_sales", "registered_users"],
            "rows": [
                ["2024-01-01", 155716.77999999866, "1559"],
                ["2024-02-01", 69937.42000000055, "755"],
                ["2024-03-01", 33747.91000000003, "384"],
                ["2024-04-01", 115891.65999999913, "1355"],
                ["2024-05-01", 82326.92000000003, "740"],
                ["2024-06-01", 196680.455, "2754"],
                ["2024-07-01", 133218.41, "1559"],
                ["2024-08-01", 27448.335, "194"],
                ["2024-09-01", 144934.81999999983, "1557"],
                ["2024-10-01", 134927.2999999998, "1491"],
                ["2024-11-01", 120987.43999999948, "1356"],
                ["2024-12-01", 128732.12999999955, "1355"],
                ["2025-01-01", 155716.77999999866, "1559"],
                ["2025-02-01", 69937.42000000055, "755"],
                ["2025-03-01", 33747.91000000003, "384"],
                ["2025-04-01", 115891.65999999913, "1355"],
                ["2025-05-01", 110036.75999999886, "1096"],
                ["2025-06-01", 138457.01999999848, "1491"],
                ["2025-07-01", 101228.30999999943, "1036"],
                ["2025-08-01", 90910.37999999947, "762"],
                ["2025-09-01", 18826.00999999998, "194"]
            ]
        }
    ],
    "charts": [
        {
            "id": "trend_sales_users",
            "type": "line",
            "spec": {
                "xKey": "month",
                "yKey": "value",
                "series": [
                    {"name": "Total Sales", "yKey": "total_sales"},
                    {"name": "Registered Users", "yKey": "registered_users"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "trend",
        "used": {"tables": ["Monthly Sales and Registered Users"], "columns": ["month", "total_sales", "registered_users"]},
        "stats": {"elapsed": 0},
        "sql_present": False
    }
}


def sanitize_columns(df: pd.DataFrame):
    """Return a copy of df with safe lower_snake_case column names and a mapping original->safe.
    Ensures only [A-Za-z0-9_] and uniqueness.
    """
    import re
    mapping = {}
    used = set()
    for col in df.columns:
        safe = col.strip().lower()
        safe = re.sub(r"[\s\-/]+", "_", safe)
        safe = re.sub(r"[^0-9a-zA-Z_]", "", safe)
        safe = re.sub(r"_+", "_", safe).strip("_")
        if safe == "":
            safe = "col"
        base = safe
        i = 1
        while safe in used:
            i += 1
            safe = f"{base}_{i}"
        used.add(safe)
        mapping[col] = safe
    df_safe = df.rename(columns=mapping).copy()
    return df_safe, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """Coerce specified columns to numeric by stripping non-numeric characters."""
    import re
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c]
                .astype(str)
                .str.replace(r"[^0-9\.-]", "", regex=True)
                .replace({"": None}),
                errors="coerce",
            )
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce specified columns to datetime with errors coerced to NaT."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable, fallback_df: pd.DataFrame = None):
    """Safely build and render an Altair chart. On failure, show a warning and optional fallback table."""
    try:
        chart = chart_builder_callable()
        if chart is None:
            st.warning("Chart unavailable")
            if fallback_df is not None:
                st.dataframe(fallback_df)
            return
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.warning("Chart unavailable")
        if fallback_df is not None:
            st.dataframe(fallback_df)


def _load_tables(report):
    """Create a dict of DataFrames from report tables keyed by table name."""
    tables = report.get("tables", [])
    df_map = {}
    for t in tables:
        name = t.get("name", "Table")
        cols = t.get("columns", [])
        rows = t.get("rows", [])
        try:
            df = pd.DataFrame(rows, columns=cols)
        except Exception:
            # Fallback if columns mismatch
            df = pd.DataFrame(rows)
        df_map[name] = df
    return df_map


def render_app():
    # Guard page config to avoid duplication on reruns/imports
    if not st.session_state.get("_page_config_set", False):
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_set"] = True

    # Altair setup
    alt.data_transformers.disable_max_rows()

    st.title("AI Report")

    # Summary
    summary = REPORT_DATA.get("summary", [])
    if summary:
        st.subheader("Summary")
        for s in summary:
            st.markdown(f"- {s}")

    # Tables
    df_map = _load_tables(REPORT_DATA)
    if df_map:
        st.subheader("Data Tables")
        for name, df in df_map.items():
            st.markdown(f"**{name}**")
            st.dataframe(df)

    # Charts
    charts = REPORT_DATA.get("charts", [])
    if charts:
        st.subheader("Charts")

    # Helper to resolve a table for a chart based on required columns
    def resolve_table(required_cols):
        # Try to use echo.used.tables if available
        used_tables = REPORT_DATA.get("echo", {}).get("used", {}).get("tables", [])
        for ut in used_tables:
            if ut in df_map:
                df_candidate = df_map[ut]
                if all(c in df_candidate.columns for c in required_cols):
                    return ut, df_candidate
        # Otherwise search any table containing required columns
        for name, df in df_map.items():
            if all(c in df.columns for c in required_cols):
                return name, df
        # Fallback: first table if exists
        if df_map:
            name = list(df_map.keys())[0]
            return name, df_map[name]
        return None, None

    for ch in charts:
        ch_type = ch.get("type", "").lower()
        spec = ch.get("spec", {})

        if ch_type == "line":
            # Expected: multi-series with xKey and series list; we'll reshape to long
            x_key = spec.get("xKey")
            series = spec.get("series", [])
            y_original_cols = [s.get("yKey") for s in series if s.get("yKey")]
            series_name_map = {s.get("yKey"): s.get("name", s.get("yKey")) for s in series if s.get("yKey")}

            required = []
            if x_key:
                required.append(x_key)
            required.extend(y_original_cols)
            table_name, df_raw = resolve_table(required)

            st.markdown("**Trend: Sales and Registered Users**")

            if df_raw is None or not required or any(c not in (df_raw.columns if df_raw is not None else []) for c in required):
                st.warning("Chart unavailable")
                # Show sanitized (fallback requirement) if possible
                if df_raw is not None:
                    df_s, _ = sanitize_columns(df_raw)
                    st.dataframe(df_s)
                continue

            # Sanitize columns for charting
            df_sanitized, mapping = sanitize_columns(df_raw)

            # Resolve safe column names
            safe_x = mapping.get(x_key, x_key)
            safe_y_cols = [mapping.get(c, c) for c in y_original_cols]

            # Coerce types
            df_sanitized = coerce_datetime(df_sanitized, [safe_x])
            df_sanitized = coerce_numeric(df_sanitized, safe_y_cols)

            # Build long-form dataframe
            try:
                long_df = df_sanitized.melt(
                    id_vars=[safe_x],
                    value_vars=[c for c in safe_y_cols if c in df_sanitized.columns],
                    var_name="metric",
                    value_name="value",
                )
            except Exception:
                long_df = pd.DataFrame(columns=[safe_x, "metric", "value"])  # empty fall-back

            # Map metric (safe col names) to friendly series names
            # Build a mapping from safe y col -> series display name
            safe_to_series_name = {}
            for orig, disp in series_name_map.items():
                safe_to_series_name[mapping.get(orig, orig)] = disp
            long_df["series_name"] = long_df["metric"].map(lambda v: safe_to_series_name.get(v, v))

            # Validate non-null rows for x and y
            valid_df = long_df[[safe_x, "value", "series_name"]].dropna(subset=[safe_x, "value"]) if not long_df.empty else long_df

            def build_chart():
                if valid_df is None or valid_df.empty:
                    return None
                # Basic altair line chart with color for series
                chart = (
                    alt.Chart(valid_df)
                    .mark_line(point=False)
                    .encode(
                        x=alt.X(f"{safe_x}:temporal", title=x_key),
                        y=alt.Y("value:quantitative", title="Value"),
                        color=alt.Color("series_name:N", title="Series"),
                        tooltip=[safe_x + ":temporal", "series_name:N", "value:quantitative"],
                    )
                    .properties(title=f"{table_name} — Trend")
                )
                return chart

            # Render chart safely; fallback shows sanitized table
            safe_altair_chart(build_chart, fallback_df=df_sanitized)

        elif ch_type in {"bar", "area"}:
            # Not present in current report, but keep a safe generic path
            x_key = spec.get("xKey")
            y_key = None
            # Try to deduce y from spec
            if isinstance(spec.get("series"), list) and spec["series"]:
                y_key = spec["series"][0].get("yKey")
            else:
                y_key = spec.get("yKey")

            required = [c for c in [x_key, y_key] if c]
            table_name, df_raw = resolve_table(required)

            if df_raw is None or any(c not in df_raw.columns for c in required):
                st.warning("Chart unavailable")
                if df_raw is not None:
                    df_s, _ = sanitize_columns(df_raw)
                    st.dataframe(df_s)
                continue

            df_sanitized, mapping = sanitize_columns(df_raw)
            safe_x = mapping.get(x_key, x_key)
            safe_y = mapping.get(y_key, y_key)

            df_sanitized = coerce_datetime(df_sanitized, [safe_x])
            df_sanitized = coerce_numeric(df_sanitized, [safe_y])

            valid_df = df_sanitized[[safe_x, safe_y]].dropna(subset=[safe_x, safe_y])

            def build_chart():
                if valid_df.empty:
                    return None
                mark = alt.MarkDef(type="bar") if ch_type == "bar" else alt.MarkDef(type="area")
                chart = (
                    alt.Chart(valid_df)
                    .mark_bar() if ch_type == "bar" else alt.Chart(valid_df).mark_area()
                )
                chart = chart.encode(
                    x=alt.X(f"{safe_x}:temporal", title=x_key),
                    y=alt.Y(f"{safe_y}:quantitative", title=y_key),
                    tooltip=[safe_x + ":temporal", safe_y + ":quantitative"],
                )
                return chart

            safe_altair_chart(build_chart, fallback_df=df_sanitized)

        elif ch_type == "pie":
            # Implement as arc chart if ever present
            dim = spec.get("category") or spec.get("dimension") or spec.get("xKey")
            val = spec.get("value") or spec.get("yKey")
            required = [c for c in [dim, val] if c]
            table_name, df_raw = resolve_table(required)

            if df_raw is None or any(c not in df_raw.columns for c in required):
                st.warning("Chart unavailable")
                if df_raw is not None:
                    df_s, _ = sanitize_columns(df_raw)
                    st.dataframe(df_s)
                continue

            df_sanitized, mapping = sanitize_columns(df_raw)
            safe_dim = mapping.get(dim, dim)
            safe_val = mapping.get(val, val)

            df_sanitized = coerce_numeric(df_sanitized, [safe_val])

            valid_df = df_sanitized[[safe_dim, safe_val]].dropna(subset=[safe_val])

            def build_chart():
                if valid_df.empty:
                    return None
                chart = (
                    alt.Chart(valid_df)
                    .mark_arc()
                    .encode(
                        theta=alt.Theta(f"{safe_val}:quantitative", aggregate="sum"),
                        color=alt.Color(f"{safe_dim}:nominal"),
                        tooltip=[safe_dim + ":nominal", safe_val + ":quantitative"],
                    )
                )
                return chart

            safe_altair_chart(build_chart, fallback_df=df_sanitized)
        else:
            # Unknown chart type; skip safely
            st.warning("Chart unavailable")


# Note: Do not execute render_app() on import; it will be called by the runner.
