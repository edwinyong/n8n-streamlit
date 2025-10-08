from datetime import datetime
import streamlit as st
import pandas as pd
import altair as alt


# -----------------------------
# Utility functions
# -----------------------------

def sanitize_columns(df: pd.DataFrame):
    """
    Return a copy of df with sanitized, safe column names and a mapping
    from original name -> safe name. Safe names are lower_snake_case and
    contain only [A-Za-z0-9_]. If collisions occur, numeric suffixes are added.
    """
    def to_safe(name: str) -> str:
        s = str(name).strip().lower()
        # Replace disallowed characters with underscore
        out = []
        for ch in s:
            if ch.isalnum() or ch == "_":
                out.append(ch)
            elif ch in [" ", "-", "/", "\\", ".", ":", ",", "|", "(", ")", "[", "]", "{", "}"]:
                out.append("_")
            else:
                out.append("_")
        s = "".join(out)
        # Collapse multiple underscores
        while "__" in s:
            s = s.replace("__", "_")
        # Trim leading/trailing underscores
        s = s.strip("_")
        if s == "":
            s = "col"
        return s

    original_cols = list(df.columns)
    safe_cols = []
    used = set()
    for col in original_cols:
        base = to_safe(col)
        candidate = base
        idx = 1
        while candidate in used:
            idx += 1
            candidate = f"{base}_{idx}"
        used.add(candidate)
        safe_cols.append(candidate)

    df_copy = df.copy()
    df_copy.columns = safe_cols
    mapping = {orig: safe for orig, safe in zip(original_cols, safe_cols)}
    return df_copy, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """
    Coerce specified columns to numeric. Strings with non-numeric
    characters (currency symbols, commas) are filtered to keep only
    digits, signs, decimal points, and exponent markers.
    """
    if df is None or not isinstance(df, pd.DataFrame):
        return df
    if not cols:
        return df

    valid_chars = set("0123456789.-+eE")

    def clean_val(v):
        if pd.isna(v):
            return v
        if isinstance(v, (int, float)):
            return v
        s = str(v)
        # Remove common grouping separators first
        s = s.replace(",", "")
        # Keep only valid numeric characters
        filtered = "".join(ch for ch in s if ch in valid_chars)
        # If filtering removed everything, return original to coerce to NaN
        return filtered if filtered != "" else s

    for c in cols:
        if c in df.columns:
            df[c] = df[c].map(clean_val)
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce specified columns to datetime (NaT on errors)."""
    if df is None or not isinstance(df, pd.DataFrame):
        return df
    if not cols:
        return df
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable, fallback_df: pd.DataFrame = None):
    """
    Execute the chart builder callable inside try/except and render via st.altair_chart.
    On error, show a warning and the provided fallback_df (sanitized table) if available.
    """
    try:
        chart = chart_builder_callable()
        if chart is None:
            raise ValueError("Chart builder returned None")
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.warning("Chart unavailable")
        if isinstance(fallback_df, pd.DataFrame) and not fallback_df.empty:
            st.dataframe(fallback_df)


# -----------------------------
# Streamlit app renderer
# -----------------------------

def render_app():
    # Guard page config so it's set only once
    if not st.session_state.get("_page_config_set", False):
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_set"] = True

    # Disable Altair row limits
    alt.data_transformers.disable_max_rows()

    # The provided JSON report (embedded as a Python dict)
    report = {
        "valid": True,
        "issues": [],
        "summary": [
            "Sensodyne leads in both buyers (11,944) and total sales (808,739.14), followed by Scotts and Polident.",
            "Total purchaser counts and sales figures decrease significantly after the top 5 brands.",
            "Calsource shows minimal activity with only 8 buyers and 325.91 in sales, indicating low market share."
        ],
        "tables": [
            {
                "name": "Table",
                "columns": ["Brand", "buyers", "purchases", "total_sales"],
                "rows": [
                    ["Sensodyne", 11944, 20529, 808739.14000007],
                    ["Scotts", 5859, 11628, 493057.3000000183],
                    ["Polident", 3476, 12206, 392956.0600000011],
                    ["Caltrate", 2863, 4592, 371326.40000000445],
                    ["Centrum", 1523, 2444, 193685.1399999982],
                    ["Panaflex", 870, 2513, 37043.94000000076],
                    ["Panadol", 316, 416, 29882.030000000028],
                    ["Parodontax", 415, 498, 15701.869999999963],
                    ["Eno", 301, 1145, 10154.350000000082],
                    ["Calsource", 8, 8, 325.9099999999999]
                ]
            }
        ],
        "charts": [
            {
                "id": "brand_purchases_sales",
                "type": "bar",
                "spec": {
                    "xKey": "Brand",
                    "yKey": "total_sales",
                    "series": [
                        {"name": "Total Sales", "yKey": "total_sales"}
                    ]
                }
            },
            {
                "id": "brand_buyers",
                "type": "bar",
                "spec": {
                    "xKey": "Brand",
                    "yKey": "buyers",
                    "series": [
                        {"name": "Buyers", "yKey": "buyers"}
                    ]
                }
            },
            {
                "id": "brand_purchases",
                "type": "bar",
                "spec": {
                    "xKey": "Brand",
                    "yKey": "purchases",
                    "series": [
                        {"name": "Purchases", "yKey": "purchases"}
                    ]
                }
            }
        ],
        "echo": {
            "intent": "composition_share",
            "used": {"tables": ["Table"], "columns": ["Brand", "buyers", "purchases", "total_sales"]},
            "stats": {"elapsed": 0},
            "sql_present": False
        }
    }

    # Title and summary
    st.title("AI Report")
    if report.get("summary"):
        st.subheader("Summary")
        for item in report["summary"]:
            st.markdown(f"- {item}")

    # Load tables
    st.subheader("Tables")
    tables_data = report.get("tables", [])
    table_name_to_frames = {}

    for t in tables_data:
        name = t.get("name", "Table")
        cols = t.get("columns", [])
        rows = t.get("rows", [])
        try:
            df_original = pd.DataFrame(rows, columns=cols)
        except Exception:
            df_original = pd.DataFrame()
        st.markdown(f"**{name}**")
        st.dataframe(df_original)
        df_sanitized, mapping = sanitize_columns(df_original)
        table_name_to_frames[name] = {
            "original": df_original,
            "sanitized": df_sanitized,
            "mapping": mapping
        }

    # Helper to build a simple bar chart
    def build_bar_chart(df_san: pd.DataFrame, x_col: str, y_col: str, title: str = None):
        # Validate columns
        if x_col not in df_san.columns or y_col not in df_san.columns:
            raise ValueError("Required columns missing for chart")
        # Coerce numeric Y
        coerce_numeric(df_san, [y_col])
        # Prepare data
        plot_df = df_san[[x_col, y_col]].copy()
        plot_df = plot_df.dropna(subset=[x_col, y_col])
        if plot_df.empty:
            raise ValueError("No data available for chart after coercion")
        # Build chart
        x_title = x_col.replace("_", " ").title()
        y_title = y_col.replace("_", " ").title()
        chart = (
            alt.Chart(plot_df)
            .mark_bar()
            .encode(
                x=alt.X(x_col, type="nominal", title=x_title),
                y=alt.Y(y_col, type="quantitative", title=y_title),
                tooltip=[c for c in [x_col, y_col] if c in plot_df.columns]
            )
            .properties(title=title)
        )
        return chart

    # Charts section
    if report.get("charts"):
        st.subheader("Charts")

        # Choose the first table as default data source if not specified
        default_table_name = tables_data[0]["name"] if tables_data else None
        df_pack = table_name_to_frames.get(default_table_name, {}) if default_table_name else {}
        df_san_default = df_pack.get("sanitized") if df_pack else None
        mapping_default = df_pack.get("mapping") if df_pack else {}

        for ch in report["charts"]:
            ch_type = ch.get("type", "").lower()
            ch_id = ch.get("id", "Chart")
            st.markdown(f"**{ch_id}**")

            # For this report, charts are based on the first/only table
            df_san = df_san_default
            mapping = mapping_default or {}
            if df_san is None or df_san.empty:
                st.warning("Chart data unavailable")
                continue

            spec = ch.get("spec", {})
            x_key_orig = spec.get("xKey")
            y_key_orig = spec.get("yKey") or (spec.get("series", [{}])[0].get("yKey") if spec.get("series") else None)

            # Map original keys to sanitized
            x_key_safe = mapping.get(x_key_orig)
            y_key_safe = mapping.get(y_key_orig)

            # Verify keys are present
            if not x_key_safe or not y_key_safe or x_key_safe not in df_san.columns or y_key_safe not in df_san.columns:
                st.warning("Chart unavailable")
                st.dataframe(df_san)
                continue

            title = None
            if ch_type == "bar":
                def builder():
                    return build_bar_chart(df_san.copy(), x_key_safe, y_key_safe, title=title)
                safe_altair_chart(builder, fallback_df=df_san)
            else:
                # Unsupported chart types fallback
                st.warning("Chart type not supported in this viewer")
                st.dataframe(df_san)


# Note: No top-level execution. The app runs only when render_app() is called.
