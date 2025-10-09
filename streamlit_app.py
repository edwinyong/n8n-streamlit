import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import re


# -----------------------------
# Utilities
# -----------------------------

def sanitize_columns(df: pd.DataFrame):
    """
    Return a copy of df with sanitized column names (lower_snake_case, [A-Za-z0-9_])
    and a mapping from original -> safe.
    """
    def to_safe(name: str) -> str:
        safe = name.strip().lower()
        safe = re.sub(r"\s+", "_", safe)
        safe = re.sub(r"[^a-z0-9_]", "_", safe)
        safe = re.sub(r"_+", "_", safe)
        safe = safe.strip("_")
        if not safe:
            safe = "col"
        return safe

    mapping = {}
    used = set()
    for col in df.columns:
        base = to_safe(str(col))
        safe = base
        i = 1
        while safe in used:
            safe = f"{base}_{i}"
            i += 1
        mapping[col] = safe
        used.add(safe)
    df_copy = df.copy()
    df_copy.columns = [mapping[c] for c in df.columns]
    return df_copy, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """Coerce listed columns to numeric by stripping non-numeric characters and using to_numeric."""
    for c in cols:
        if c in df.columns:
            # Convert to string, strip non-numeric (keep digits, . - and scientific notation e/E)
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace(r"[^0-9eE+\-\.]", "", regex=True),
                errors="coerce",
            )
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce listed columns to datetime with errors coerced to NaT."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable):
    """
    Execute chart builder inside try/except. The builder should return (chart, fallback_df).
    On any exception or if chart is None, show a warning and display fallback_df instead.
    """
    try:
        result = chart_builder_callable()
        if isinstance(result, tuple) and len(result) == 2:
            chart, fallback_df = result
        else:
            chart, fallback_df = result, None

        if chart is None:
            st.warning("Chart unavailable")
            if isinstance(fallback_df, pd.DataFrame) and not fallback_df.empty:
                st.dataframe(fallback_df, use_container_width=True)
            return

        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.warning("Chart unavailable")
        try:
            # Attempt to fetch fallback again in case builder returned it
            result = chart_builder_callable()
            if isinstance(result, tuple) and len(result) == 2:
                _, fallback_df = result
                if isinstance(fallback_df, pd.DataFrame) and not fallback_df.empty:
                    st.dataframe(fallback_df, use_container_width=True)
        except Exception:
            pass


# -----------------------------
# Embedded report data (provided JSON)
# -----------------------------
report_data = {
    "valid": True,
    "issues": [],
    "summary": [
        "Total sales and registered users are shown for each of the past 6 months.",
        "Sales peaked in June 2025 at 138,457.02, then declined sharply by September 2025.",
        "Registered users followed a similar trend, peaking in June 2025 at 1,491 and dropping to 194 by September 2025."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["month", "total_sales", "registered_users"],
            "rows": [
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
            "id": "sales_users_trend",
            "type": "line",
            "spec": {
                "xKey": "month",
                "yKey": "value",
                "series": [
                    {"name": "total_sales", "yKey": "total_sales"},
                    {"name": "registered_users", "yKey": "registered_users"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "trend",
        "used": {"tables": ["detail"], "columns": ["month", "total_sales", "registered_users"]},
        "stats": {"elapsed": 0},
        "sql_present": False
    }
}


# -----------------------------
# Main App Renderer
# -----------------------------

def render_app():
    # Page config guard to avoid duplicate set on reruns/imports
    if not st.session_state.get("_page_config_set", False):
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_set"] = True

    alt.data_transformers.disable_max_rows()

    st.title("AI Report")

    # Summary Section
    summaries = report_data.get("summary", [])
    if summaries:
        st.subheader("Summary")
        for s in summaries:
            st.markdown(f"- {s}")

    # Load Tables
    st.subheader("Tables")
    table_entries = report_data.get("tables", [])
    table_dfs = []
    for idx, t in enumerate(table_entries):
        name = t.get("name") or f"Table {idx+1}"
        cols = t.get("columns", [])
        rows = t.get("rows", [])
        try:
            df = pd.DataFrame(rows, columns=cols)
        except Exception:
            df = pd.DataFrame(rows)
        st.markdown(f"**{name}**")
        st.dataframe(df, use_container_width=True)
        table_dfs.append((name, df))

    # Helper to get the primary DataFrame for charts (use first table if present)
    base_df = table_dfs[0][1] if table_dfs else pd.DataFrame()

    # Charts Section
    charts = report_data.get("charts", [])
    if charts:
        st.subheader("Charts")

    for ch in charts:
        ch_type = (ch.get("type") or "").lower()
        ch_id = ch.get("id", "Chart")
        spec = ch.get("spec", {})

        st.markdown(f"**{ch_id}**")

        if base_df.empty:
            st.warning("Chart unavailable")
            continue

        # Sanitize and prepare data for charting
        df_sanitized, mapping = sanitize_columns(base_df)

        # Builder for a line chart with optional multiple series
        if ch_type == "line":
            def builder():
                x_key_raw = spec.get("xKey")
                series = spec.get("series", [])
                # Map original keys to sanitized
                x_col = mapping.get(x_key_raw, None)
                y_cols = []
                legend_names = []
                for s in series:
                    y_raw = s.get("yKey")
                    if y_raw in mapping:
                        y_cols.append(mapping[y_raw])
                        legend_names.append(y_raw)

                # Validate presence of required columns
                if not x_col or x_col not in df_sanitized.columns:
                    raise ValueError("X column missing for chart")
                if not y_cols:
                    raise ValueError("No valid Y series for chart")

                # Coerce types
                coerce_datetime(df_sanitized, [x_col])
                coerce_numeric(df_sanitized, y_cols)

                # Prepare long format for Altair (metric, value)
                cols_for_melt = [x_col] + y_cols
                df_long = pd.melt(
                    df_sanitized[cols_for_melt].copy(),
                    id_vars=[x_col],
                    value_vars=y_cols,
                    var_name="metric",
                    value_name="value",
                )

                # Optionally map sanitized metric names back to original for legend readability
                # Create inverse mapping from safe -> original
                inv_map = {v: k for k, v in mapping.items()}
                df_long["metric"] = df_long["metric"].map(lambda m: inv_map.get(m, m))

                # Drop NaNs
                df_long = df_long.dropna(subset=[x_col, "value"]).copy()

                # Ensure we have at least one valid row
                if df_long.empty:
                    raise ValueError("No data rows available for chart after coercion")

                # Determine x encoding type
                x_encoding = alt.X(f"{x_col}:T", title=x_key_raw if x_key_raw else x_col)

                chart = (
                    alt.Chart(df_long)
                    .mark_line(point=True)
                    .encode(
                        x=x_encoding,
                        y=alt.Y("value:Q", title="Value"),
                        color=alt.Color("metric:N", title="Metric"),
                        tooltip=[
                            alt.Tooltip(f"{x_col}:T", title=x_key_raw if x_key_raw else x_col),
                            alt.Tooltip("metric:N", title="Metric"),
                            alt.Tooltip("value:Q", title="Value"),
                        ],
                    )
                )
                chart = chart.properties(height=380)
                return chart, df_sanitized

            safe_altair_chart(builder)

        # Basic bar/area/pie handlers if ever present in input (defensive, though not used here)
        elif ch_type == "bar":
            def builder():
                x_key_raw = spec.get("xKey")
                y_key_raw = spec.get("yKey")
                x_col = mapping.get(x_key_raw, None)
                y_col = mapping.get(y_key_raw, None)
                if not x_col or x_col not in df_sanitized.columns:
                    raise ValueError("X column missing for bar chart")
                if not y_col or y_col not in df_sanitized.columns:
                    raise ValueError("Y column missing for bar chart")
                coerce_datetime(df_sanitized, [x_col])
                coerce_numeric(df_sanitized, [y_col])
                df_plot = df_sanitized[[x_col, y_col]].dropna()
                if df_plot.empty:
                    raise ValueError("No data rows available for bar chart after coercion")
                # If datetime-like, treat as temporal; else nominal
                if pd.api.types.is_datetime64_any_dtype(df_plot[x_col]):
                    x_enc = alt.X(f"{x_col}:T", title=x_key_raw)
                else:
                    x_enc = alt.X(f"{x_col}:N", title=x_key_raw)
                chart = (
                    alt.Chart(df_plot)
                    .mark_bar()
                    .encode(
                        x=x_enc,
                        y=alt.Y(f"{y_col}:Q", title=y_key_raw),
                        tooltip=[
                            alt.Tooltip(f"{x_col}:{'T' if pd.api.types.is_datetime64_any_dtype(df_plot[x_col]) else 'N'}", title=x_key_raw),
                            alt.Tooltip(f"{y_col}:Q", title=y_key_raw),
                        ],
                    )
                )
                return chart, df_sanitized
            safe_altair_chart(builder)

        elif ch_type == "area":
            def builder():
                x_key_raw = spec.get("xKey")
                y_key_raw = spec.get("yKey")
                x_col = mapping.get(x_key_raw, None)
                y_col = mapping.get(y_key_raw, None)
                if not x_col or x_col not in df_sanitized.columns:
                    raise ValueError("X column missing for area chart")
                if not y_col or y_col not in df_sanitized.columns:
                    raise ValueError("Y column missing for area chart")
                coerce_datetime(df_sanitized, [x_col])
                coerce_numeric(df_sanitized, [y_col])
                df_plot = df_sanitized[[x_col, y_col]].dropna()
                if df_plot.empty:
                    raise ValueError("No data rows available for area chart after coercion")
                if pd.api.types.is_datetime64_any_dtype(df_plot[x_col]):
                    x_enc = alt.X(f"{x_col}:T", title=x_key_raw)
                else:
                    x_enc = alt.X(f"{x_col}:N", title=x_key_raw)
                chart = (
                    alt.Chart(df_plot)
                    .mark_area()
                    .encode(
                        x=x_enc,
                        y=alt.Y(f"{y_col}:Q", title=y_key_raw),
                        tooltip=[
                            alt.Tooltip(f"{x_col}:{'T' if pd.api.types.is_datetime64_any_dtype(df_plot[x_col]) else 'N'}", title=x_key_raw),
                            alt.Tooltip(f"{y_col}:Q", title=y_key_raw),
                        ],
                    )
                )
                return chart, df_sanitized
            safe_altair_chart(builder)

        elif ch_type in ("pie", "donut", "arc"):
            def builder():
                dim_raw = spec.get("categoryKey") or spec.get("xKey")
                val_raw = spec.get("valueKey") or spec.get("yKey")
                dim_col = mapping.get(dim_raw, None)
                val_col = mapping.get(val_raw, None)
                if not dim_col or dim_col not in df_sanitized.columns:
                    raise ValueError("Category column missing for pie chart")
                if not val_col or val_col not in df_sanitized.columns:
                    raise ValueError("Value column missing for pie chart")
                coerce_numeric(df_sanitized, [val_col])
                df_plot = df_sanitized[[dim_col, val_col]].dropna()
                if df_plot.empty:
                    raise ValueError("No data rows available for pie chart after coercion")
                chart = (
                    alt.Chart(df_plot)
                    .mark_arc()
                    .encode(
                        theta=alt.Theta(f"{val_col}:Q", stack=True),
                        color=alt.Color(f"{dim_col}:N", title=dim_raw),
                        tooltip=[
                            alt.Tooltip(f"{dim_col}:N", title=dim_raw),
                            alt.Tooltip(f"{val_col}:Q", title=val_raw),
                        ],
                    )
                )
                chart = chart.properties(height=380)
                return chart, df_sanitized
            safe_altair_chart(builder)

        else:
            st.warning("Unsupported chart type; showing data table instead.")
            st.dataframe(df_sanitized, use_container_width=True)


# The module is import-safe; nothing runs on import. Call render_app() from your Streamlit entrypoint.
