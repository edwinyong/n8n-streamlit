import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

# -------------------------------
# Utilities
# -------------------------------

def sanitize_columns(df: pd.DataFrame):
    """
    Return a copy of df with safe, lower_snake_case column names containing only [A-Za-z0-9_].
    Also return a mapping from original -> safe names.
    """
    def to_safe(name: str) -> str:
        s = str(name).strip().lower()
        # replace non-alphanumeric with underscore, without using regex
        safe_chars = []
        for ch in s:
            if (
                ("a" <= ch <= "z") or ("0" <= ch <= "9") or ch == "_"
            ):
                safe_chars.append(ch)
            else:
                safe_chars.append("_")
        s2 = "".join(safe_chars)
        # collapse consecutive underscores
        collapsed = []
        prev_underscore = False
        for ch in s2:
            if ch == "_":
                if not prev_underscore:
                    collapsed.append(ch)
                prev_underscore = True
            else:
                collapsed.append(ch)
                prev_underscore = False
        s3 = "".join(collapsed).strip("_")
        if not s3:
            s3 = "col"
        # cannot start with digit
        if "0" <= s3[0] <= "9":
            s3 = f"f_{s3}"
        return s3

    mapping = {}
    used = set()
    new_cols = []
    for c in df.columns:
        base = to_safe(c)
        candidate = base
        idx = 1
        while candidate in used:
            idx += 1
            candidate = f"{base}_{idx}"
        used.add(candidate)
        mapping[c] = candidate
        new_cols.append(candidate)
    df_copy = df.copy()
    df_copy.columns = new_cols
    return df_copy, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """Coerce specified columns to numeric by stripping non-numeric characters and using pd.to_numeric(errors='coerce')."""
    if not isinstance(cols, (list, tuple, set)):
        cols = [cols]
    for c in cols:
        if c in df.columns:
            # convert to string and strip non-numeric except minus and dot
            def to_numeric_safe(x):
                if pd.isna(x):
                    return pd.NA
                s = str(x)
                filtered_chars = []
                for ch in s:
                    if ("0" <= ch <= "9") or ch in ["-", "."]:
                        filtered_chars.append(ch)
                cleaned = "".join(filtered_chars)
                try:
                    return pd.to_numeric(cleaned, errors="coerce")
                except Exception:
                    return pd.NA
            df[c] = df[c].apply(to_numeric_safe)
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce specified columns to datetime with errors coerced to NaT."""
    if not isinstance(cols, (list, tuple, set)):
        cols = [cols]
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable, fallback_df: pd.DataFrame):
    """Safely build and render an Altair chart; on failure, warn and show fallback table."""
    try:
        chart = chart_builder_callable()
        if chart is None:
            st.warning("Chart unavailable")
            st.dataframe(fallback_df)
            return
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.warning("Chart unavailable")
        st.dataframe(fallback_df)


# -------------------------------
# Embedded report JSON
# -------------------------------
REPORT_DATA = {
    "valid": True,
    "issues": [],
    "summary": [
        "Total sales peaked in 2024 Q4 at 448,770.42 and remained high in 2025 Q1 at 463,266.60, indicating strong performance over these quarters.",
        "Number of purchases increased substantially from 2024 Q1 (3,702) to a peak in 2024 Q4 (10,060), then slightly declined in 2025 Q2 and Q3, potentially signaling seasonality or market saturation.",
        "Registered purchasers and buyers generally follow the same trend as purchases and sales, peaking in 2024 Q4 and 2025 Q1, with a notable dip in 2025 Q3.",
        "2025 Q3 saw a significant drop in all key metrics, which may require further investigation into causes such as market changes or external factors.",
        "To drive improvement, focus on maintaining high engagement post-peak quarters, analyze the root causes of Q3 drops, and consider promotional strategies or customer retention efforts during traditionally lower-sales quarters."
    ],
    "tables": [
        {
            "name": "Quarterly Sales Report 2024-2025",
            "columns": ["period", "registered_purchasers", "total_sales", "purchases", "buyers"],
            "rows": [
                ["2024 Q1", 2579, 259402.10999999472, 3702, 2579],
                ["2024 Q2", 3055, 299314.9499999972, 5281, 3055],
                ["2024 Q3", 2494, 300075.42999999237, 8402, 2494],
                ["2024 Q4", 5245, 448770.4200000053, 10060, 5245],
                ["2025 Q1", 4998, 463266.6000000094, 9913, 4999],
                ["2025 Q2", 3826, 371077.9300000016, 9008, 3826],
                ["2025 Q3", 1711, 210964.6999999934, 5689, 1711]
            ]
        }
    ],
    "charts": [
        {
            "id": "sales_trend",
            "type": "line",
            "spec": {"xKey": "period", "yKey": "total_sales", "series": [{"name": "Total Sales", "yKey": "total_sales"}]}
        },
        {
            "id": "purchases_buyers_bar",
            "type": "groupedBar",
            "spec": {"xKey": "period", "yKey": "purchases", "series": [{"name": "Purchases", "yKey": "purchases"}, {"name": "Buyers", "yKey": "buyers"}]}
        },
        {
            "id": "registered_purchasers_trend",
            "type": "line",
            "spec": {"xKey": "period", "yKey": "registered_purchasers", "series": [{"name": "Registered Purchasers", "yKey": "registered_purchasers"}]}
        }
    ],
    "echo": {
        "intent": "trend",
        "used": {"tables": ["Quarterly Sales Report 2024-2025"], "columns": ["period", "registered_purchasers", "total_sales", "purchases", "buyers"]},
        "stats": {"elapsed": 0},
        "sql_present": False
    }
}


# -------------------------------
# Main app renderer
# -------------------------------

def render_app():
    # Set page config safely only once per session
    if not st.session_state.get("_page_config_set", False):
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_set"] = True

    # Avoid Altair row-limit issues
    alt.data_transformers.disable_max_rows()

    st.title("AI Report")

    # Summary Section
    summary_items = REPORT_DATA.get("summary") or []
    if summary_items:
        st.subheader("Summary")
        for item in summary_items:
            st.markdown(f"- {item}")

    # Tables Section
    tables = REPORT_DATA.get("tables") or []
    dfs_by_name = {}

    if tables:
        st.subheader("Tables")
        for tbl in tables:
            name = tbl.get("name") or "Table"
            cols = tbl.get("columns") or []
            rows = tbl.get("rows") or []
            try:
                df = pd.DataFrame(rows, columns=cols)
            except Exception:
                # Fallback if data shape mismatches
                df = pd.DataFrame(rows)
            dfs_by_name[name] = df
            st.markdown(f"**{name}**")
            st.dataframe(df)

    # Choose a default DataFrame for charts (first table)
    default_df = None
    default_df_name = None
    if tables:
        default_df_name = tables[0].get("name")
        default_df = dfs_by_name.get(default_df_name)

    # Charts Section
    charts = REPORT_DATA.get("charts") or []
    if charts and default_df is not None:
        st.subheader("Charts")

        for ch in charts:
            ch_id = ch.get("id") or "Chart"
            ch_type = (ch.get("type") or "").lower()
            spec = ch.get("spec") or {}
            x_key_orig = spec.get("xKey")
            y_key_orig = spec.get("yKey")
            series = spec.get("series") or []

            st.markdown(f"**{ch_id}**")

            # Sanitize columns for charting
            df_safe, mapping = sanitize_columns(default_df)

            # Resolve safe keys
            def map_key(k):
                if k is None:
                    return None
                return mapping.get(k, None)

            x_safe = map_key(x_key_orig)

            # Determine y columns for this chart
            y_keys_orig = []
            if series:
                for s in series:
                    yk = s.get("yKey")
                    if yk and yk not in y_keys_orig:
                        y_keys_orig.append(yk)
            elif y_key_orig:
                y_keys_orig = [y_key_orig]

            y_safes = [map_key(k) for k in y_keys_orig if map_key(k) is not None]

            # Basic existence checks
            if x_safe is None or x_safe not in df_safe.columns:
                st.warning("Chart unavailable: x-axis field missing")
                st.dataframe(df_safe)
                continue
            if not y_safes:
                st.warning("Chart unavailable: y-axis field(s) missing")
                st.dataframe(df_safe)
                continue

            # Coerce numeric for all y columns
            df_for_chart = df_safe.copy()
            df_for_chart = coerce_numeric(df_for_chart, y_safes)

            # Build charts
            if ch_type in ["line", "area", "bar"] and len(y_safes) == 1:
                y_safe = y_safes[0]
                # Validate non-null data rows
                valid_mask = df_for_chart[x_safe].notna() & df_for_chart[y_safe].notna()
                if valid_mask.sum() < 1:
                    st.warning("Chart unavailable: insufficient data for plotting")
                    st.dataframe(df_for_chart)
                    continue

                # Maintain data order for discrete x
                x_order = [v for v in df_for_chart[x_safe].astype(str).tolist()]
                # Simple chart builder
                def build_chart():
                    mark = alt.MarkDef(type="line") if ch_type == "line" else (
                        alt.MarkDef(type="area") if ch_type == "area" else alt.MarkDef(type="bar")
                    )
                    chart = (
                        alt.Chart(df_for_chart)
                        .mark_line(point=True) if ch_type == "line" else (
                            alt.Chart(df_for_chart).mark_area() if ch_type == "area" else alt.Chart(df_for_chart).mark_bar()
                        )
                    )
                    chart = chart.encode(
                        x=alt.X(x_safe, type="nominal", sort=x_order, title=x_key_orig),
                        y=alt.Y(y_safe, type="quantitative", title=y_keys_orig[0] if y_keys_orig else "value"),
                        tooltip=[c for c in [x_safe, y_safe] if c in df_for_chart.columns]
                    ).properties(height=350)
                    return chart

                safe_altair_chart(build_chart, df_for_chart)

            elif ch_type in ["groupedbar", "stackedbar", "bar"] and len(y_safes) >= 1:
                # Reshape to long format for grouped bars
                cols_present = [c for c in [x_safe] + y_safes if c in df_for_chart.columns]
                if x_safe not in cols_present or not y_safes:
                    st.warning("Chart unavailable: required fields not found")
                    st.dataframe(df_for_chart)
                    continue

                df_long = pd.melt(
                    df_for_chart[cols_present],
                    id_vars=[x_safe],
                    value_vars=[c for c in y_safes if c in df_for_chart.columns],
                    var_name="metric",
                    value_name="value",
                )
                df_long = coerce_numeric(df_long, ["value"])  # ensure numeric
                df_long = df_long[df_long["value"].notna()]

                if df_long.shape[0] < 1:
                    st.warning("Chart unavailable: insufficient data for plotting")
                    st.dataframe(df_for_chart)
                    continue

                x_order = [v for v in df_for_chart[x_safe].astype(str).tolist()]

                def build_chart_bar():
                    chart = (
                        alt.Chart(df_long)
                        .mark_bar()
                        .encode(
                            x=alt.X(x_safe, type="nominal", sort=x_order, title=x_key_orig),
                            y=alt.Y("value", type="quantitative", title="value"),
                            color=alt.Color("metric", type="nominal", title="metric"),
                            tooltip=[c for c in [x_safe, "metric", "value"] if c in df_long.columns],
                        )
                        .properties(height=350)
                    )
                    return chart

                safe_altair_chart(build_chart_bar, df_long)

            else:
                # Unsupported or unrecognized type
                st.warning("Chart unavailable: unsupported chart type or invalid specification")
                st.dataframe(df_for_chart)

    else:
        if charts and default_df is None:
            st.subheader("Charts")
            st.info("No table data available to render charts.")


# Note: No top-level execution. Use from streamlit_app import render_app; render_app()
