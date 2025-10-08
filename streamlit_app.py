from datetime import datetime
import streamlit as st
import pandas as pd
import altair as alt


# ----------------------- Utilities -----------------------

def sanitize_columns(df: pd.DataFrame):
    """Return a copy of df with safe, lower_snake_case column names and a mapping.
    Only [A-Za-z0-9_] allowed; others become '_'. Ensures uniqueness.
    """
    original_cols = list(df.columns)
    safe_cols = []

    def to_safe(name: str) -> str:
        s = name.strip().lower()
        s = s.replace(" ", "_")
        out = []
        for ch in s:
            if ch.isalnum() or ch == "_":
                out.append(ch)
            else:
                out.append("_")
        safe = "".join(out)
        # collapse consecutive underscores
        while "__" in safe:
            safe = safe.replace("__", "_")
        if safe.startswith("_"):
            safe = safe[1:]
        if safe.endswith("_"):
            safe = safe[:-1]
        if safe == "":
            safe = "col"
        return safe

    used = {}
    for c in original_cols:
        base = to_safe(str(c))
        candidate = base
        idx = 1
        while candidate in used:
            idx += 1
            candidate = f"{base}_{idx}"
        used[candidate] = True
        safe_cols.append(candidate)

    mapping = {orig: safe for orig, safe in zip(original_cols, safe_cols)}
    df_copy = df.copy()
    df_copy.columns = safe_cols
    return df_copy, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """Coerce listed columns to numeric by stripping non-numeric chars first."""
    for c in cols:
        if c in df.columns:
            s = df[c].astype(str)
            # Remove anything that's not digit, minus, or dot
            s = s.str.replace(r"[^0-9\.-]", "", regex=True)
            df[c] = pd.to_numeric(s, errors="coerce")
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce listed columns to datetime."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable, fallback_df: pd.DataFrame = None):
    """Safely build and render an Altair chart. On failure, show warning and fallback table."""
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


# ----------------------- App Renderer -----------------------

def render_app():
    # Guard page config to avoid re-running in multi-import contexts
    if not st.session_state.get("_page_config_done", False):
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_done"] = True

    # Avoid Altair max rows issues
    alt.data_transformers.disable_max_rows()

    # Report data (provided JSON converted to Python dict)
    report = {
        "valid": True,
        "issues": [],
        "summary": [
            "2025 YTD sales (Jan–Sep): 1,045,309.23; average per month: 116,145.47",
            "Peak in Feb 2025: 181,249.13; lowest in Sep 2025: 18,826.01",
            "MoM change Aug→Sep: -79.29%"
        ],
        "tables": [
            {
                "name": "Monthly Sales 2025",
                "columns": ["month", "total_sales"],
                "rows": [
                    ["2025-01-01", 119626.18999999885],
                    ["2025-02-01", 181249.12999999718],
                    ["2025-03-01", 162391.27999999782],
                    ["2025-04-01", 122584.14999999863],
                    ["2025-05-01", 110036.75999999886],
                    ["2025-06-01", 138457.01999999848],
                    ["2025-07-01", 101228.30999999943],
                    ["2025-08-01", 90910.37999999947],
                    ["2025-09-01", 18826.00999999998]
                ]
            }
        ],
        "charts": [
            {
                "id": "monthly_sales_trend_2025",
                "type": "line",
                "spec": {
                    "xKey": "month",
                    "yKey": "total_sales",
                    "series": [
                        {"name": "total_sales", "yKey": "total_sales"}
                    ]
                }
            }
        ],
        "echo": {
            "intent": "trend",
            "used": {"tables": ["`Haleon_Rewards_User_Performance_110925_SKUs`"], "columns": ["Upload_Date", "Total Sales Amount"]},
            "stats": {"elapsed": 0.005879749},
            "sql_present": True
        }
    }

    st.title("AI Report")

    # Summary
    summary = report.get("summary", [])
    if summary:
        st.subheader("Summary")
        for item in summary:
            st.markdown(f"- {item}")

    # Prepare tables
    raw_tables = report.get("tables", [])
    tables_original = {}
    tables_sanitized = {}
    mappings = {}

    if raw_tables:
        st.subheader("Tables")
    for tbl in raw_tables:
        name = tbl.get("name", "Table")
        cols = tbl.get("columns", [])
        rows = tbl.get("rows", [])
        try:
            df = pd.DataFrame(rows, columns=cols)
        except Exception:
            df = pd.DataFrame()
        tables_original[name] = df

        # Show table with original column names
        st.markdown(f"**{name}**")
        st.dataframe(df)

        # Create sanitized copy for charting
        df_safe, mapping = sanitize_columns(df)
        tables_sanitized[name] = df_safe
        mappings[name] = mapping

    # Helper to find a table containing required columns (by original names)
    def find_table_with_columns(x_key, y_key):
        for name, df in tables_original.items():
            if x_key in df.columns and y_key in df.columns:
                return name
        # fallback: try case-insensitive matching
        for name, df in tables_original.items():
            cols_lower = {c.lower(): c for c in df.columns}
            if x_key.lower() in cols_lower and y_key.lower() in cols_lower:
                return name
        return None

    # Charts
    charts = report.get("charts", [])
    if charts:
        st.subheader("Charts")

    for chart_def in charts:
        ctype = chart_def.get("type", "").lower()
        spec = chart_def.get("spec", {})
        x_key = spec.get("xKey")
        y_key = spec.get("yKey")

        table_name = find_table_with_columns(x_key, y_key) if x_key and y_key else None
        if table_name is None:
            st.warning("Chart unavailable: required columns not found in any table.")
            continue

        df_orig = tables_original.get(table_name, pd.DataFrame())
        df_safe = tables_sanitized.get(table_name, pd.DataFrame()).copy()
        mapping = mappings.get(table_name, {})

        # Map original keys to sanitized keys
        safe_x = mapping.get(x_key, None)
        safe_y = mapping.get(y_key, None)

        # Validate existence
        if safe_x not in df_safe.columns or safe_y not in df_safe.columns:
            st.warning("Chart unavailable: columns missing after sanitization.")
            st.dataframe(df_safe)
            continue

        # Coerce datetime for x and numeric for y
        coerce_datetime(df_safe, [safe_x])
        coerce_numeric(df_safe, [safe_y])

        # Verify non-null rows for x and y
        non_null_mask = df_safe[safe_x].notna() & df_safe[safe_y].notna()
        df_plot = df_safe.loc[non_null_mask].copy()
        if df_plot.empty:
            st.warning("Chart unavailable: no valid data after type coercion.")
            st.dataframe(df_safe)
            continue

        # Determine x type: temporal if datetime64, else nominal
        x_is_temporal = pd.api.types.is_datetime64_any_dtype(df_plot[safe_x])
        x_type = "T" if x_is_temporal else "N"

        # Build charts based on type
        if ctype == "line":
            st.markdown(f"**{chart_def.get('id', 'Line Chart')}**")

            def build_line():
                chart = (
                    alt.Chart(df_plot)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X(f"{safe_x}:{x_type}", title=x_key),
                        y=alt.Y(f"{safe_y}:Q", title=y_key),
                        tooltip=[c for c in [safe_x, safe_y] if c in df_plot.columns],
                    )
                )
                return chart.properties(height=320)

            safe_altair_chart(build_line, fallback_df=df_safe)
        elif ctype == "bar":
            st.markdown(f"**{chart_def.get('id', 'Bar Chart')}**")

            def build_bar():
                chart = (
                    alt.Chart(df_plot)
                    .mark_bar()
                    .encode(
                        x=alt.X(f"{safe_x}:{x_type}", title=x_key),
                        y=alt.Y(f"{safe_y}:Q", title=y_key),
                        tooltip=[c for c in [safe_x, safe_y] if c in df_plot.columns],
                    )
                )
                return chart.properties(height=320)

            safe_altair_chart(build_bar, fallback_df=df_safe)
        elif ctype == "area":
            st.markdown(f"**{chart_def.get('id', 'Area Chart')}**")

            def build_area():
                chart = (
                    alt.Chart(df_plot)
                    .mark_area()
                    .encode(
                        x=alt.X(f"{safe_x}:{x_type}", title=x_key),
                        y=alt.Y(f"{safe_y}:Q", title=y_key),
                        tooltip=[c for c in [safe_x, safe_y] if c in df_plot.columns],
                    )
                )
                return chart.properties(height=320)

            safe_altair_chart(build_area, fallback_df=df_safe)
        elif ctype in ("pie", "arc"):  # pie-like
            st.markdown(f"**{chart_def.get('id', 'Pie Chart')}**")
            # For pie: x_key is category, y_key is value
            # Ensure y is numeric already, x is nominal

            def build_arc():
                chart = (
                    alt.Chart(df_plot)
                    .mark_arc()
                    .encode(
                        theta=alt.Theta(f"{safe_y}:Q"),
                        color=alt.Color(f"{safe_x}:N", title=x_key),
                        tooltip=[c for c in [safe_x, safe_y] if c in df_plot.columns],
                    )
                )
                return chart.properties(height=320)

            safe_altair_chart(build_arc, fallback_df=df_safe)
        else:
            st.warning(f"Chart type '{ctype}' not supported. Showing data table instead.")
            st.dataframe(df_safe)


# Note: do not execute render_app() on import. Run explicitly:
# from streamlit_app import render_app
# render_app()
