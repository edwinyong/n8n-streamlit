from datetime import datetime
import streamlit as st
import pandas as pd
import altair as alt


# ----------------------- Utilities -----------------------
def sanitize_columns(df: pd.DataFrame):
    """
    Return a copy of df with sanitized, safe column names and a mapping from original->safe.
    Safe names: lower_snake_case using only [A-Za-z0-9_]. Ensures uniqueness.
    """
    original_cols = list(df.columns)
    safe_cols = []
    mapping = {}

    def to_safe(name: str) -> str:
        # lower, replace non-alnum with underscore, collapse repeats
        s = name.lower()
        s = ''.join(ch if ch.isalnum() else '_' for ch in s)
        # collapse multiple underscores
        while '__' in s:
            s = s.replace('__', '_')
        # strip leading/trailing underscores
        s = s.strip('_')
        # fall back if empty
        if not s:
            s = 'col'
        return s

    used = {}
    for col in original_cols:
        base = to_safe(str(col))
        candidate = base
        idx = 1
        while candidate in used:
            idx += 1
            candidate = f"{base}_{idx}"
        used[candidate] = True
        mapping[col] = candidate
        safe_cols.append(candidate)

    df_safe = df.copy()
    df_safe.columns = safe_cols
    return df_safe, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """Coerce specified columns to numeric, stripping common non-numeric characters."""
    for col in cols:
        if col in df.columns:
            # Convert values to strings and keep only digits, sign, decimal point, exponent
            def clean_val(v):
                if pd.isna(v):
                    return v
                s = str(v)
                # fast path: if already numeric-like, keep
                # Otherwise, strip unwanted characters
                kept = []
                for ch in s:
                    if ch.isdigit() or ch in ['.', '-', 'e', 'E']:
                        kept.append(ch)
                s2 = ''.join(kept)
                # If empty after cleaning, return NaN
                return s2 if s2 not in (None, '') else None
            df[col] = pd.to_numeric(df[col].map(clean_val), errors='coerce')
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce specified columns to datetime where possible."""
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df


def safe_altair_chart(chart_builder_callable, fallback_df: pd.DataFrame, warning_message: str = "Chart unavailable"):
    """
    Executes chart_builder_callable() inside try/except; on failure, warns and shows fallback_df.
    chart_builder_callable should return an Altair chart object.
    """
    try:
        chart = chart_builder_callable()
        if chart is None:
            raise ValueError("Chart builder returned None")
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.warning(warning_message)
        st.dataframe(fallback_df)


# ----------------------- Report Data -----------------------
REPORT = {
    "valid": True,
    "issues": [],
    "summary": [
        "Total sales peaked in 2025 Q1 at 463,266.60, with a significant increase from 2024 Q4 (448,770.42).",
        "Registered purchasers and buyers followed similar trends, peaking in 2024 Q4 and 2025 Q1, then declining sharply in 2025 Q3.",
        "Total units sold and number of purchases also peaked in 2025 Q1, indicating strong demand before a notable drop in 2025 Q2 and Q3.",
        "2024 Q4 and 2025 Q1 were periods of highest activity across all metrics, suggesting seasonal or campaign-driven spikes.",
        "2025 Q3 saw the lowest figures across all metrics, with total sales dropping to 210,964.70 and registered purchasers down to 1,711."
    ],
    "tables": [
        {
            "name": "Quarterly Sales Data 2024-2025",
            "columns": ["period", "registered_purchasers", "total_sales", "total_units", "purchases", "buyers"],
            "rows": [
                ["2024 Q1", 2579, 259402.10999999472, "9002", 3702, 2579],
                ["2024 Q2", 3055, 299314.9499999972, "9713", 5281, 3055],
                ["2024 Q3", 2494, 300075.42999999237, "13323", 8402, 2494],
                ["2024 Q4", 5245, 448770.4200000053, "18388", 10060, 5245],
                ["2025 Q1", 4998, 463266.6000000094, "19670", 9913, 4999],
                ["2025 Q2", 3826, 371077.9300000016, "15482", 9008, 3826],
                ["2025 Q3", 1711, 210964.6999999934, "8576", 5689, 1711]
            ]
        }
    ],
    "charts": [
        {
            "id": "sales_trend",
            "type": "line",
            "spec": {
                "xKey": "period",
                "yKey": "total_sales",
                "series": [
                    {"name": "Total Sales", "yKey": "total_sales"}
                ]
            }
        },
        {
            "id": "purchasers_trend",
            "type": "line",
            "spec": {
                "xKey": "period",
                "yKey": "registered_purchasers",
                "series": [
                    {"name": "Registered Purchasers", "yKey": "registered_purchasers"}
                ]
            }
        },
        {
            "id": "units_trend",
            "type": "line",
            "spec": {
                "xKey": "period",
                "yKey": "total_units",
                "series": [
                    {"name": "Total Units", "yKey": "total_units"}
                ]
            }
        },
        {
            "id": "purchases_trend",
            "type": "line",
            "spec": {
                "xKey": "period",
                "yKey": "purchases",
                "series": [
                    {"name": "Purchases", "yKey": "purchases"}
                ]
            }
        },
        {
            "id": "buyers_trend",
            "type": "line",
            "spec": {
                "xKey": "period",
                "yKey": "buyers",
                "series": [
                    {"name": "Buyers", "yKey": "buyers"}
                ]
            }
        }
    ]
}


# ----------------------- App Renderer -----------------------
def render_app():
    # Prevent page config being set multiple times in environments where render_app could be re-run.
    if "_page_config_set" not in st.session_state:
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_set"] = True

    # Altair settings to avoid row-limit issues
    alt.data_transformers.disable_max_rows()

    st.title("AI Report")

    # Summary Section
    if REPORT.get("summary"):
        st.subheader("Summary")
        for item in REPORT["summary"]:
            st.markdown(f"- {item}")

    # Tables Section
    table_dfs = []
    if REPORT.get("tables"):
        for table in REPORT["tables"]:
            name = table.get("name", "Table")
            cols = table.get("columns", [])
            rows = table.get("rows", [])
            try:
                df = pd.DataFrame(rows, columns=cols)
            except Exception:
                df = pd.DataFrame(rows)
            table_dfs.append((name, df))

        for name, df in table_dfs:
            st.subheader(name)
            st.dataframe(df)

    # Charts Section
    st.subheader("Charts")

    # Build a lookup of sanitized dataframes per original table name
    sanitized_tables = {}
    for name, df in table_dfs:
        df_safe, mapping = sanitize_columns(df)
        sanitized_tables[name] = (df, df_safe, mapping)

    # Helper to get sanitized column name from original
    def get_safe(mapping, original_name):
        return mapping.get(original_name, original_name)

    # Attempt to draw charts from the first (and only) table by default
    base_table_name = table_dfs[0][0] if table_dfs else None

    if REPORT.get("charts") and base_table_name and base_table_name in sanitized_tables:
        original_df, safe_df, col_map = sanitized_tables[base_table_name]

        # Identify numeric columns to coerce based on known fields in the report
        numeric_original_cols = [
            "registered_purchasers",
            "total_sales",
            "total_units",
            "purchases",
            "buyers",
        ]
        numeric_safe_cols = [get_safe(col_map, c) for c in numeric_original_cols if get_safe(col_map, c) in safe_df.columns]
        safe_df = coerce_numeric(safe_df, numeric_safe_cols)
        # We won't coerce 'period' to datetime since it's a quarter label; keep nominal.

        for chart in REPORT["charts"]:
            ctype = chart.get("type", "bar")
            spec = chart.get("spec", {})
            x_key = spec.get("xKey")
            y_key = spec.get("yKey")
            if not x_key or not y_key:
                st.warning("Chart spec missing x or y key; displaying table instead.")
                st.dataframe(safe_df)
                continue

            x_safe = get_safe(col_map, x_key)
            y_safe = get_safe(col_map, y_key)

            # Builder function for safe_altair_chart
            def make_builder(df_ref: pd.DataFrame, x_col: str, y_col: str, title: str):
                def builder():
                    # Validate columns exist
                    if x_col not in df_ref.columns or y_col not in df_ref.columns:
                        raise ValueError("Required columns not found for chart")

                    # Ensure at least one valid row for x and y
                    plot_df = df_ref[[x_col, y_col]].copy()
                    # Drop rows with NaN in y
                    plot_df = plot_df.dropna(subset=[x_col, y_col])
                    if plot_df.shape[0] == 0:
                        raise ValueError("No valid data points for chart")

                    # Decide x encoding type: temporal if datetime dtype, else nominal
                    if pd.api.types.is_datetime64_any_dtype(plot_df[x_col]):
                        x_enc = alt.X(f"{x_col}:T", title=x_key)
                        tooltip_x = alt.Tooltip(f"{x_col}:T", title=x_key)
                    else:
                        x_enc = alt.X(f"{x_col}:N", sort=None, title=x_key)
                        tooltip_x = alt.Tooltip(f"{x_col}:N", title=x_key)

                    y_enc = alt.Y(f"{y_col}:Q", title=y_key)
                    tooltip_y = alt.Tooltip(f"{y_col}:Q", title=y_key)

                    if ctype == "line":
                        chart_obj = alt.Chart(plot_df).mark_line(point=True).encode(
                            x=x_enc,
                            y=y_enc,
                            tooltip=[tooltip_x, tooltip_y],
                        )
                    elif ctype == "area":
                        chart_obj = alt.Chart(plot_df).mark_area().encode(
                            x=x_enc,
                            y=y_enc,
                            tooltip=[tooltip_x, tooltip_y],
                        )
                    elif ctype == "bar":
                        chart_obj = alt.Chart(plot_df).mark_bar().encode(
                            x=x_enc,
                            y=y_enc,
                            tooltip=[tooltip_x, tooltip_y],
                        )
                    elif ctype == "pie":
                        # Implement simple pie via arc: expects y as value, x as category (optional)
                        theta_field = y_col
                        color_field = x_col if x_col in plot_df.columns else None
                        enc = {
                            'theta': alt.Theta(f"{theta_field}:Q"),
                        }
                        if color_field is not None:
                            enc['color'] = alt.Color(f"{color_field}:N")
                        chart_obj = alt.Chart(plot_df).mark_arc().encode(**enc)
                    else:
                        # default to bar if unknown
                        chart_obj = alt.Chart(plot_df).mark_bar().encode(
                            x=x_enc,
                            y=y_enc,
                            tooltip=[tooltip_x, tooltip_y],
                        )

                    return chart_obj.properties(title=title)

                return builder

            title = f"{y_key.replace('_', ' ').title()} over {x_key.replace('_', ' ').title()}"
            safe_altair_chart(
                make_builder(safe_df, x_safe, y_safe, title),
                fallback_df=safe_df,
                warning_message="Chart unavailable"
            )
    else:
        st.info("No chart data available.")


# Note: No top-level execution; render_app() should be called by the runner.
