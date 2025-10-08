from datetime import datetime
import streamlit as st
import pandas as pd
import altair as alt

# ---------------------------
# Embedded report JSON (as Python dict)
# ---------------------------
REPORT = {
    "valid": True,
    "issues": [],
    "summary": [
        "2025 YTD sales (Jan–Sep): 1045309.23",
        "Peak month: 2025-02-01 with 181249.12999999718 in sales; trough: 2025-09-01 with 18826.00999999998.",
        "Latest MoM change (Sep vs Aug): -79.29%.",
        "Data covers Jan–Sep 2025 based on available records."
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
            "id": "monthly_sales_2025",
            "type": "line",
            "spec": {
                "xKey": "month",
                "yKey": "total_sales",
                "series": [
                    {"name": "Total Sales", "yKey": "total_sales"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "trend",
        "used": {"tables": ["`Haleon_Rewards_User_Performance_110925_SKUs`"], "columns": ["Upload_Date", "Total Sales Amount"]},
        "stats": {"elapsed": 0.00532954},
        "sql_present": True
    }
}

# ---------------------------
# Utilities
# ---------------------------

def sanitize_columns(df: pd.DataFrame):
    """Return a copy of df with safe snake_case columns and a mapping of original->safe.
    Ensures columns contain only [A-Za-z0-9_] and don't start with a digit.
    Handles duplicates by appending numeric suffixes.
    """
    def _to_safe(name: str) -> str:
        s = str(name).strip().lower()
        # replace whitespace with underscore
        s = "_".join(s.split())
        # remove invalid chars
        s = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in s)
        # collapse multiple underscores
        while "__" in s:
            s = s.replace("__", "_")
        s = s.strip("_") or "col"
        # cannot start with digit
        if s and s[0].isdigit():
            s = f"col_{s}"
        return s

    safe_cols = []
    mapping = {}
    used = {}

    for col in df.columns:
        base = _to_safe(col)
        candidate = base
        idx = 1
        while candidate in used:
            idx += 1
            candidate = f"{base}_{idx}"
        used[candidate] = True
        mapping[col] = candidate
        safe_cols.append(candidate)

    df_copy = df.copy()
    df_copy.columns = safe_cols
    return df_copy, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """Coerce specified columns to numeric, stripping non-numeric characters.
    cols can be a list or a single column name. Operates in place.
    """
    if isinstance(cols, str):
        cols = [cols]
    for col in cols:
        if col in df.columns:
            # Convert to string and strip non-numeric symbols (keep digits, +, -, .)
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"[^0-9+\-.]", "", regex=True)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce specified columns to datetime. Operates in place."""
    if isinstance(cols, str):
        cols = [cols]
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable, fallback_df: pd.DataFrame, note: str = None):
    """Safely build and render an Altair chart.
    On any failure or builder returning None, show a warning and the sanitized table instead.
    """
    try:
        chart = chart_builder_callable()
        if chart is None:
            st.warning("Chart unavailable")
            st.dataframe(fallback_df)
            return
        try:
            st.altair_chart(chart, use_container_width=True)
        except Exception:
            st.warning("Chart unavailable")
            st.dataframe(fallback_df)
    except Exception:
        st.warning("Chart unavailable")
        st.dataframe(fallback_df)


# ---------------------------
# App Renderer
# ---------------------------

def render_app():
    # Guard set_page_config to avoid re-running in multi-import contexts
    if not st.session_state.get("_page_configured", False):
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_configured"] = True

    # Disable Altair max rows limit
    try:
        alt.data_transformers.disable_max_rows()
    except Exception:
        pass

    st.title("AI Report")

    # Summary Section
    summaries = REPORT.get("summary", []) or []
    if summaries:
        st.subheader("Summary")
        for s in summaries:
            st.markdown(f"- {s}")

    # Build tables
    raw_tables = REPORT.get("tables", []) or []
    processed_tables = []  # list of dicts: name, df_orig, df_safe, mapping

    for t in raw_tables:
        name = t.get("name") or "Table"
        cols = t.get("columns", [])
        rows = t.get("rows", [])
        try:
            df_orig = pd.DataFrame(rows, columns=cols)
        except Exception:
            df_orig = pd.DataFrame(columns=cols)
        df_safe, mapping = sanitize_columns(df_orig)
        processed_tables.append({
            "name": name,
            "df_orig": df_orig,
            "df_safe": df_safe,
            "mapping": mapping,
        })

    # Display tables with original column names
    for item in processed_tables:
        st.subheader(f"Table: {item['name']}")
        st.dataframe(item["df_orig"])  # show original columns

    # Charts Section
    charts = REPORT.get("charts", []) or []
    if charts:
        st.subheader("Charts")

    def find_table_with_columns(x_key: str, y_key: str):
        for item in processed_tables:
            df_orig = item["df_orig"]
            if x_key in df_orig.columns and y_key in df_orig.columns:
                return item
        return None

    for ch in charts:
        ch_id = ch.get("id") or "chart"
        ch_type = (ch.get("type") or "").strip().lower()
        spec = ch.get("spec", {}) or {}
        x_key = spec.get("xKey")
        y_key = spec.get("yKey")
        color_key = spec.get("colorKey")  # optional

        st.markdown(f"**Chart: {ch_id} ({ch_type})**")

        # Validate keys
        if not x_key or not y_key:
            st.warning("Chart unavailable")
            # Attempt to show a related table (sanitized) if any
            if processed_tables:
                st.dataframe(processed_tables[0]["df_safe"])
            continue

        table_item = find_table_with_columns(x_key, y_key)
        if table_item is None:
            st.warning("Chart unavailable")
            if processed_tables:
                st.dataframe(processed_tables[0]["df_safe"])
            continue

        df_safe = table_item["df_safe"].copy()
        mapping = table_item["mapping"]

        safe_x = mapping.get(x_key)
        safe_y = mapping.get(y_key)
        safe_color = mapping.get(color_key) if color_key else None

        # If mapping failed (shouldn't if columns exist), fallback
        if safe_x not in df_safe.columns or safe_y not in df_safe.columns:
            st.warning("Chart unavailable")
            st.dataframe(df_safe)
            continue

        # Coercions
        # Determine if x looks like date; attempt datetime coercion regardless, will decide based on non-null count
        coerce_datetime(df_safe, [safe_x])
        coerce_numeric(df_safe, [safe_y])

        # Also ensure color (if any) is string/nominal; no coercion needed

        # Validate non-null rows for x and y
        df_plot = df_safe[[safe_x, safe_y] + ([safe_color] if safe_color else [])].copy()
        df_plot_valid = df_plot.dropna(subset=[safe_x, safe_y])

        def build_line_chart():
            # Ensure there is data
            if df_plot_valid.empty:
                return None
            # Decide x type: temporal if not all NaT after datetime coercion
            x_is_temporal = pd.api.types.is_datetime64_any_dtype(df_plot_valid[safe_x])

            enc_x = alt.X(safe_x, type='temporal' if x_is_temporal else 'nominal', title=x_key)
            enc_y = alt.Y(safe_y, type='quantitative', title=y_key)

            tooltip_fields = [safe_x, safe_y]
            tooltip_fields = [f for f in tooltip_fields if f in df_plot_valid.columns]

            chart = alt.Chart(df_plot_valid).mark_line(point=True).encode(
                x=enc_x,
                y=enc_y,
                color=alt.Color(safe_color, type='nominal', title=color_key) if safe_color and safe_color in df_plot_valid.columns else alt.value(None),
                tooltip=tooltip_fields,
            ).properties(height=300)
            return chart

        def build_bar_chart():
            if df_plot_valid.empty:
                return None
            x_is_temporal = pd.api.types.is_datetime64_any_dtype(df_plot_valid[safe_x])
            enc_x = alt.X(safe_x, type='temporal' if x_is_temporal else 'nominal', title=x_key)
            enc_y = alt.Y(safe_y, type='quantitative', title=y_key)
            tooltip_fields = [safe_x, safe_y]
            tooltip_fields = [f for f in tooltip_fields if f in df_plot_valid.columns]
            chart = alt.Chart(df_plot_valid).mark_bar().encode(
                x=enc_x,
                y=enc_y,
                color=alt.Color(safe_color, type='nominal', title=color_key) if safe_color and safe_color in df_plot_valid.columns else alt.value(None),
                tooltip=tooltip_fields,
            ).properties(height=300)
            return chart

        def build_area_chart():
            if df_plot_valid.empty:
                return None
            x_is_temporal = pd.api.types.is_datetime64_any_dtype(df_plot_valid[safe_x])
            enc_x = alt.X(safe_x, type='temporal' if x_is_temporal else 'nominal', title=x_key)
            enc_y = alt.Y(safe_y, type='quantitative', title=y_key)
            tooltip_fields = [safe_x, safe_y]
            tooltip_fields = [f for f in tooltip_fields if f in df_plot_valid.columns]
            chart = alt.Chart(df_plot_valid).mark_area().encode(
                x=enc_x,
                y=enc_y,
                color=alt.Color(safe_color, type='nominal', title=color_key) if safe_color and safe_color in df_plot_valid.columns else alt.value(None),
                tooltip=tooltip_fields,
            ).properties(height=300)
            return chart

        def build_pie_chart():
            # For pie charts: need a dimension and a value; treat x_key as category and y_key as value
            # Ensure non-null y
            df_pie = df_safe[[safe_x, safe_y]].copy()
            coerce_numeric(df_pie, [safe_y])
            df_pie = df_pie.dropna(subset=[safe_y])
            if df_pie.empty:
                return None
            chart = alt.Chart(df_pie).mark_arc().encode(
                theta=alt.Theta(field=safe_y, type='quantitative'),
                color=alt.Color(field=safe_x, type='nominal'),
                tooltip=[safe_x, safe_y],
            ).properties(height=300)
            return chart

        # Select appropriate builder
        if ch_type == "line":
            builder = build_line_chart
        elif ch_type == "bar":
            builder = build_bar_chart
        elif ch_type == "area":
            builder = build_area_chart
        elif ch_type in ("pie", "donut", "arc"):
            builder = build_pie_chart
        else:
            # Unknown chart type -> fallback
            st.warning("Chart unavailable")
            st.dataframe(df_safe)
            continue

        # Safely render chart
        safe_altair_chart(builder, df_safe)


# Note: Do not execute render_app() on import.
# The app will be run by importing render_app and calling it externally.
