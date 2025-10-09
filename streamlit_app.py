import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

# ---------------------- Utilities ----------------------
def sanitize_columns(df: pd.DataFrame):
    """
    Return a copy of df with safe snake_case columns containing only [A-Za-z0-9_].
    Also return a mapping from original -> safe name. Ensures uniqueness.
    """
    def to_safe(name: str) -> str:
        s = str(name).strip().lower()
        # replace spaces and dashes with underscores
        s = s.replace(" ", "_").replace("-", "_")
        # keep only alnum and underscore
        kept = []
        for ch in s:
            if ch.isalnum() or ch == "_":
                kept.append(ch)
        s = "".join(kept)
        if not s:
            s = "col"
        # cannot start with digit
        if s[0].isdigit():
            s = f"col_{s}"
        return s

    mapping = {}
    used = set()
    safe_cols = []
    for col in df.columns:
        base = to_safe(col)
        safe = base
        idx = 1
        while safe in used:
            idx += 1
            safe = f"{base}_{idx}"
        used.add(safe)
        mapping[col] = safe
        safe_cols.append(safe)

    df_copy = df.copy()
    df_copy.columns = safe_cols
    return df_copy, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """Coerce selected columns to numeric. Strips non-numeric characters safely."""
    if not cols:
        return df

    def strip_to_numeric_like(val):
        if pd.isna(val):
            return val
        if isinstance(val, (int, float)):
            return val
        s = str(val)
        # keep digits, minus, dot, exponent markers
        kept_chars = []
        for ch in s:
            if ch.isdigit() or ch in ["-", ".", "e", "E"]:
                kept_chars.append(ch)
        s2 = "".join(kept_chars)
        if s2 in ("", "-", ".", "-."):
            return pd.NA
        return s2

    for c in cols:
        if c in df.columns:
            df[c] = df[c].map(strip_to_numeric_like)
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce selected columns to datetime if present."""
    if not cols:
        return df
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def looks_like_datetime_col(name: str) -> bool:
    n = str(name).lower()
    hints = ["date", "time", "datetime", "year", "month", "day"]
    return any(h in n for h in hints)


def safe_altair_chart(chart_builder_callable, fallback_df: pd.DataFrame = None):
    """Safely build and render an Altair chart, with fallback to table on error."""
    try:
        chart = chart_builder_callable()
        if chart is None:
            raise ValueError("Chart builder returned None")
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.warning("Chart unavailable")
        if fallback_df is not None and isinstance(fallback_df, pd.DataFrame):
            st.dataframe(fallback_df)


# ---------------------- App Renderer ----------------------
def render_app():
    # Guard page config to avoid multiple set errors
    if "_page_config_set" not in st.session_state:
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_set"] = True

    alt.data_transformers.disable_max_rows()

    # The provided JSON report embedded as a Python dict
    report = {
        "valid": True,
        "issues": [],
        "summary": [
            "Sensodyne leads with the highest total sales (808,739.14) and redeemed receipts (20,529).",
            "Scotts and Polident follow in both sales and receipts, with Scotts having 493,057.30 in sales and 11,628 receipts, and Polident with 392,956.06 in sales and 12,206 receipts.",
            "Caltrate and Centrum round out the top five brands by both sales and receipt count.",
            "Brands like Calsource and Eno have the lowest sales and redeemed receipts among the listed brands."
        ],
        "tables": [
            {
                "name": "Total Sales and Redeemed Receipts by Brand",
                "columns": ["Brand", "total_sales", "redeemed_receipts"],
                "rows": [
                    ["Sensodyne", 808739.14000007, "20529"],
                    ["Scotts", 493057.3000000183, "11628"],
                    ["Polident", 392956.0600000011, "12206"],
                    ["Caltrate", 371326.40000000445, "4592"],
                    ["Centrum", 193685.1399999982, "2444"],
                    ["Panaflex", 37043.94000000076, "2513"],
                    ["Panadol", 29882.030000000028, "416"],
                    ["Parodontax", 15701.869999999963, "498"],
                    ["Eno", 10154.350000000082, "1145"],
                    ["Calsource", 325.9099999999999, "8"]
                ]
            }
        ],
        "charts": [
            {
                "id": "main",
                "type": "bar",
                "spec": {
                    "xKey": "Brand",
                    "yKey": "total_sales",
                    "series": [{"name": "Total Sales", "yKey": "total_sales"}]
                }
            },
            {
                "id": "receipts",
                "type": "bar",
                "spec": {
                    "xKey": "Brand",
                    "yKey": "redeemed_receipts",
                    "series": [{"name": "Redeemed Receipts", "yKey": "redeemed_receipts"}]
                }
            }
        ],
        "echo": {
            "intent": "table",
            "used": {"tables": ["detail"], "columns": ["Brand", "total_sales", "redeemed_receipts"]},
            "stats": {"elapsed": 0},
            "sql_present": False
        }
    }

    # Title
    st.title("AI Report")

    # Summary section
    if isinstance(report.get("summary"), list) and report["summary"]:
        st.subheader("Summary")
        for item in report["summary"]:
            st.markdown(f"- {item}")

    # Tables section
    st.subheader("Tables")
    tables = report.get("tables", [])
    dataframes_original = []
    for tbl in tables:
        name = tbl.get("name", "Table")
        cols = tbl.get("columns", [])
        rows = tbl.get("rows", [])
        try:
            df = pd.DataFrame(rows, columns=cols)
        except Exception:
            df = pd.DataFrame()
        dataframes_original.append((name, df))
        st.markdown(f"**{name}**")
        st.dataframe(df)

    # Charts section
    st.subheader("Charts")

    charts = report.get("charts", [])

    # Choose the first table as the source for charts unless specified otherwise
    source_df = dataframes_original[0][1] if dataframes_original else pd.DataFrame()

    # Prepare sanitized copy for charting
    sanitized_df, col_map = sanitize_columns(source_df)

    # Helper to map original key to safe key
    def safe_key(original_key: str):
        if original_key in col_map:
            return col_map[original_key]
        # if already safe, return as-is if present
        if original_key in sanitized_df.columns:
            return original_key
        return None

    for ch in charts:
        ch_id = ch.get("id", "chart")
        ch_type = (ch.get("type") or "").lower()
        spec = ch.get("spec", {})
        x_key_orig = spec.get("xKey")
        y_key_orig = spec.get("yKey")

        st.markdown(f"**Chart: {ch_id}**")

        if sanitized_df.empty:
            st.warning("Chart unavailable")
            if not source_df.empty:
                st.dataframe(sanitized_df)
            continue

        x_safe = safe_key(x_key_orig) if x_key_orig else None
        y_safe = safe_key(y_key_orig) if y_key_orig else None

        # Coerce data types appropriately
        numeric_cols = []
        if y_safe:
            numeric_cols.append(y_safe)
        coerce_numeric(sanitized_df, numeric_cols)

        datetime_cols = []
        if x_key_orig and looks_like_datetime_col(x_key_orig):
            if x_safe:
                datetime_cols.append(x_safe)
        coerce_datetime(sanitized_df, datetime_cols)

        def build_chart():
            # Validate required columns
            if x_safe is None or y_safe is None:
                raise ValueError("Required columns missing for chart")
            if x_safe not in sanitized_df.columns or y_safe not in sanitized_df.columns:
                raise ValueError("Chart columns do not exist in data")

            # Prepare plotting DataFrame
            cols_needed = [x_safe, y_safe]
            df_plot = sanitized_df[cols_needed].copy()
            # Ensure numeric for y
            if not pd.api.types.is_numeric_dtype(df_plot[y_safe]):
                # final attempt to coerce
                df_plot[y_safe] = pd.to_numeric(df_plot[y_safe], errors="coerce")

            # Determine x type
            x_is_datetime = pd.api.types.is_datetime64_any_dtype(df_plot[x_safe])
            # Drop rows with nulls in required axes
            df_plot = df_plot.dropna(subset=[x_safe, y_safe])
            if df_plot.empty:
                raise ValueError("No valid data to plot")

            # Build chart according to type
            if ch_type == "pie":
                # Interpret as mark_arc with theta=sum(value) over categories in x
                chart = alt.Chart(df_plot).mark_arc().encode(
                    theta=alt.Theta(field=y_safe, type="quantitative"),
                    color=alt.Color(field=x_safe, type="nominal"),
                    tooltip=[x_safe, y_safe]
                )
                return chart
            else:
                # Default to bar/line/area support
                mark = None
                if ch_type == "line":
                    mark = alt.MarkDef(type="line")
                    chart_obj = alt.Chart(df_plot).mark_line()
                elif ch_type == "area":
                    chart_obj = alt.Chart(df_plot).mark_area()
                else:
                    # bar as default
                    chart_obj = alt.Chart(df_plot).mark_bar()

                x_enc = alt.X(field=x_safe, type=("temporal" if x_is_datetime else "nominal"))
                y_enc = alt.Y(field=y_safe, type="quantitative")
                chart = chart_obj.encode(
                    x=x_enc,
                    y=y_enc,
                    tooltip=[x_safe, y_safe]
                )
                return chart

        safe_altair_chart(build_chart, fallback_df=sanitized_df)


# Note: No top-level execution. The app runs when render_app() is called.
