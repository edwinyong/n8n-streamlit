import streamlit as st
import pandas as pd
import altair as alt

# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------

def sanitize_columns(df: pd.DataFrame):
    """
    Return a copy of df with sanitized, Altair-safe column names and a mapping
    from original -> safe names. Safe names are lower_snake_case with only
    [A-Za-z0-9_]. Ensures uniqueness.
    """
    import re

    def to_safe(name: str) -> str:
        s = str(name)
        s = s.lower()
        s = re.sub(r"[^a-z0-9_]+", "_", s)
        s = re.sub(r"_+", "_", s).strip("_")
        if s == "":
            s = "col"
        return s

    original_cols = list(df.columns)
    safe_cols = []
    used = {}
    for c in original_cols:
        base = to_safe(c)
        candidate = base
        idx = 1
        while candidate in used:
            idx += 1
            candidate = f"{base}_{idx}"
        used[candidate] = c
        safe_cols.append(candidate)

    mapping = {orig: safe for orig, safe in zip(original_cols, safe_cols)}
    df_copy = df.copy()
    df_copy.columns = safe_cols
    return df_copy, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """
    Coerce specified columns to numeric by stripping non-numeric characters.
    Non-convertible values become NaN.
    """
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r"[^0-9.\-]", "", regex=True),
                errors="coerce",
            )
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce specified columns to datetime; non-convertible values become NaT."""
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable):
    """
    Executes the provided chart builder in a try/except. The builder may return:
      - an Altair Chart object, or
      - a tuple (chart, fallback_df)
    On exception or None chart, shows a warning and, if provided, shows fallback_df as a table.
    Returns True if chart rendered, False otherwise.
    """
    try:
        result = chart_builder_callable()
        chart = result
        fallback_df = None
        if isinstance(result, tuple) and len(result) == 2:
            chart, fallback_df = result
        if chart is None:
            st.warning("Chart unavailable")
            if fallback_df is not None and isinstance(fallback_df, pd.DataFrame):
                st.dataframe(fallback_df)
            return False
        st.altair_chart(chart, use_container_width=True)
        return True
    except Exception:
        st.warning("Chart unavailable")
        try:
            result = chart_builder_callable()
            if isinstance(result, tuple) and len(result) == 2:
                _, fallback_df = result
                if fallback_df is not None and isinstance(fallback_df, pd.DataFrame):
                    st.dataframe(fallback_df)
        except Exception:
            pass
        return False


# ------------------------------------------------------------
# Embedded report data (from the provided JSON)
# ------------------------------------------------------------

def get_report():
    return {
        "valid": True,
        "issues": [],
        "summary": [
            "Total sales increased from 259,402 in 2024 Q1 to a peak of 463,267 in 2025 Q1, then declined to 210,965 by 2025 Q3.",
            "Quarterly sales growth was strong in 2024 Q4 (+49.7%) and 2025 Q1 (+3.2%), but dropped sharply in 2025 Q2 (-19.9%) and 2025 Q3 (-43.1%).",
            "Total units sold followed a similar trend, peaking at 19,670 in 2025 Q1 before declining.",
            "Purchases and buyers both peaked in 2024 Q4 and 2025 Q1, then declined in subsequent quarters.",
            "Registered purchasers always matched buyers, indicating all buyers were registered.",
        ],
        "tables": [
            {
                "name": "Quarterly Sales Report 2024-2025",
                "columns": [
                    "period",
                    "total_sales",
                    "total_units",
                    "purchases",
                    "buyers",
                    "registered_purchasers",
                ],
                "rows": [
                    ["2024 Q1", 259402.10999999472, "9002", "3702", "2579", "2579"],
                    ["2024 Q2", 299314.9499999972, "9713", "5281", "3055", "3055"],
                    ["2024 Q3", 300075.42999999237, "13323", "8402", "2494", "2494"],
                    ["2024 Q4", 448770.4200000053, "18388", "10060", "5245", "5245"],
                    ["2025 Q1", 463266.6000000094, "19670", "9913", "4999", "4998"],
                    ["2025 Q2", 371077.9300000016, "15482", "9008", "3826", "3826"],
                    ["2025 Q3", 210964.6999999934, "8576", "5689", "1711", "1711"],
                ],
            }
        ],
        "charts": [
            {
                "id": "sales_trend",
                "type": "line",
                "spec": {
                    "xKey": "period",
                    "yKey": "total_sales",
                    "series": [{"name": "Total Sales", "yKey": "total_sales"}],
                },
            },
            {
                "id": "units_trend",
                "type": "line",
                "spec": {
                    "xKey": "period",
                    "yKey": "total_units",
                    "series": [{"name": "Total Units", "yKey": "total_units"}],
                },
            },
            {
                "id": "purchases_buyers_trend",
                "type": "groupedBar",
                "spec": {
                    "xKey": "period",
                    "yKey": "value",
                    "series": [
                        {"name": "Purchases", "yKey": "purchases"},
                        {"name": "Buyers", "yKey": "buyers"},
                    ],
                },
            },
        ],
        "echo": {
            "intent": "trend",
            "used": {
                "tables": ["Quarterly Sales Report 2024-2025"],
                "columns": [
                    "period",
                    "total_sales",
                    "total_units",
                    "purchases",
                    "buyers",
                    "registered_purchasers",
                ],
            },
            "stats": {"elapsed": 0},
            "sql_present": False,
        },
    }


# ------------------------------------------------------------
# Main render function
# ------------------------------------------------------------

def render_app():
    # Avoid multiple reconfiguration under Streamlit reruns/imports
    if not st.session_state.get("_page_config_set", False):
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_set"] = True

    # Avoid Altair row-limit issues
    alt.data_transformers.disable_max_rows()

    report = get_report()

    st.title("AI Report")

    # Summary section
    summaries = report.get("summary", [])
    if summaries:
        st.subheader("Summary")
        for item in summaries:
            st.markdown(f"- {item}")

    # Tables section
    st.subheader("Tables")
    tables = report.get("tables", [])
    dataframes_by_name = {}
    for t in tables:
        name = t.get("name", "Table")
        cols = t.get("columns", [])
        rows = t.get("rows", [])
        try:
            df = pd.DataFrame(rows, columns=cols)
        except Exception:
            df = pd.DataFrame(rows)
        dataframes_by_name[name] = df
        st.markdown(f"#### {name}")
        st.dataframe(df)

    # Determine main DataFrame for charts
    used_table_names = report.get("echo", {}).get("used", {}).get("tables", [])
    main_table_name = used_table_names[0] if used_table_names else (tables[0]["name"] if tables else None)
    main_df = dataframes_by_name.get(main_table_name) if main_table_name in dataframes_by_name else (list(dataframes_by_name.values())[0] if dataframes_by_name else pd.DataFrame())

    # Prepare sanitized and coerced data for charting
    sdf, mapping = sanitize_columns(main_df)

    # Helper to map original -> safe column name
    def safe_col(orig_name: str):
        return mapping.get(orig_name, orig_name if orig_name in sdf.columns else None)

    # Infer numeric columns (all except potential dimension columns like 'period')
    potential_numeric = [c for c in sdf.columns if c != safe_col("period")]
    coerce_numeric(sdf, potential_numeric)
    # We keep 'period' as nominal, not coercing to datetime due to quarter format

    st.subheader("Charts")

    # 1) Sales Trend (line chart)
    st.markdown("#### Sales Trend")
    def build_sales_trend():
        spec = None
        for ch in report.get("charts", []):
            if ch.get("id") == "sales_trend":
                spec = ch.get("spec", {})
                break
        x_key = spec.get("xKey", "period") if spec else "period"
        y_key = spec.get("yKey", "total_sales") if spec else "total_sales"
        x_safe = safe_col(x_key)
        y_safe = safe_col(y_key)
        if x_safe is None or y_safe is None:
            return None, sdf
        # Ensure there is data
        sdf_filtered = sdf[[x_safe, y_safe]].copy()
        sdf_filtered = sdf_filtered.dropna(subset=[x_safe, y_safe])
        if sdf_filtered[y_safe].notna().sum() < 1:
            return None, sdf
        try:
            chart = (
                alt.Chart(sdf_filtered)
                .mark_line(point=True)
                .encode(
                    x=alt.X(f"{x_safe}:N", title=x_key),
                    y=alt.Y(f"{y_safe}:Q", title=y_key),
                    tooltip=[x_safe, y_safe],
                )
            )
            chart = chart.properties(title=None)
            return chart, sdf_filtered
        except Exception:
            return None, sdf

    safe_altair_chart(build_sales_trend)

    # 2) Units Trend (line chart)
    st.markdown("#### Units Trend")
    def build_units_trend():
        spec = None
        for ch in report.get("charts", []):
            if ch.get("id") == "units_trend":
                spec = ch.get("spec", {})
                break
        x_key = spec.get("xKey", "period") if spec else "period"
        y_key = spec.get("yKey", "total_units") if spec else "total_units"
        x_safe = safe_col(x_key)
        y_safe = safe_col(y_key)
        if x_safe is None or y_safe is None:
            return None, sdf
        sdf_filtered = sdf[[x_safe, y_safe]].copy()
        sdf_filtered = sdf_filtered.dropna(subset=[x_safe, y_safe])
        if sdf_filtered[y_safe].notna().sum() < 1:
            return None, sdf
        try:
            chart = (
                alt.Chart(sdf_filtered)
                .mark_line(point=True, color="#1f77b4")
                .encode(
                    x=alt.X(f"{x_safe}:N", title=x_key),
                    y=alt.Y(f"{y_safe}:Q", title=y_key),
                    tooltip=[x_safe, y_safe],
                )
            )
            chart = chart.properties(title=None)
            return chart, sdf_filtered
        except Exception:
            return None, sdf

    safe_altair_chart(build_units_trend)

    # 3) Purchases vs Buyers (grouped bar)
    st.markdown("#### Purchases vs Buyers")
    def build_purchases_buyers():
        spec = None
        for ch in report.get("charts", []):
            if ch.get("id") == "purchases_buyers_trend":
                spec = ch.get("spec", {})
                break
        x_key = (spec or {}).get("xKey", "period")
        series_list = (spec or {}).get("series", [])
        # Required columns
        x_safe = safe_col(x_key)
        if x_safe is None:
            return None, sdf
        required_orig_cols = [s.get("yKey") for s in series_list if isinstance(s, dict) and s.get("yKey")]
        # Map to safe
        required_safe_cols = [safe_col(c) for c in required_orig_cols if c is not None]
        if not required_safe_cols or any(c is None for c in required_safe_cols):
            return None, sdf
        # Ensure numeric coercion
        coerce_numeric(sdf, required_safe_cols)
        # Melt to long format
        try:
            long_df = pd.melt(
                sdf[[x_safe] + required_safe_cols].copy(),
                id_vars=[x_safe],
                value_vars=required_safe_cols,
                var_name="metric",
                value_name="value",
            )
        except Exception:
            return None, sdf
        # Map safe metric names to nicer labels if available from spec
        safe_to_label = {}
        for s in series_list:
            orig = s.get("yKey")
            label = s.get("name", orig)
            sc = safe_col(orig)
            if sc is not None:
                safe_to_label[sc] = label
        long_df["series_label"] = long_df["metric"].map(safe_to_label).fillna(long_df["metric"])  # fallback to metric
        # Drop rows without y
        long_df = long_df.dropna(subset=["value", x_safe])
        if long_df["value"].notna().sum() < 1:
            return None, sdf
        try:
            chart = (
                alt.Chart(long_df)
                .mark_bar()
                .encode(
                    x=alt.X(f"{x_safe}:N", title=x_key),
                    y=alt.Y("value:Q", title="value"),
                    color=alt.Color("series_label:N", title="Series"),
                    tooltip=[x_safe, "series_label", "value"],
                )
            )
            chart = chart.properties(title=None)
            return chart, long_df
        except Exception:
            return None, sdf

    safe_altair_chart(build_purchases_buyers)


# Note: No top-level execution; only render_app() will run the app when called.
