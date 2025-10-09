from datetime import datetime
import pandas as pd
import altair as alt
import streamlit as st


# ---------------------- Utilities ----------------------
def sanitize_columns(df: pd.DataFrame):
    """Return a copy of df with safe snake_case columns and a mapping original->safe.
    Only [A-Za-z0-9_] allowed. Ensures uniqueness by appending numeric suffixes when needed.
    """
    def to_safe(name: str) -> str:
        s = str(name).strip().lower()
        # replace common separators with underscore
        s = s.replace("-", "_").replace(" ", "_").replace("/", "_").replace("\\", "_")
        # keep only alnum and underscore
        safe_chars = []
        for ch in s:
            if ("a" <= ch <= "z") or ("0" <= ch <= "9") or ch == "_":
                safe_chars.append(ch)
        s = "".join(safe_chars)
        # collapse multiple underscores
        while "__" in s:
            s = s.replace("__", "_")
        s = s.strip("_")
        if s == "":
            s = "col"
        return s

    original_cols = list(df.columns)
    used = {}
    mapping = {}
    safe_cols = []
    for col in original_cols:
        base = to_safe(col)
        candidate = base
        i = 1
        while candidate in used:
            i += 1
            candidate = f"{base}_{i}"
        used[candidate] = True
        mapping[col] = candidate
        safe_cols.append(candidate)
    df_copy = df.copy()
    df_copy.columns = safe_cols
    return df_copy, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """Coerce specified columns to numeric. Strips common non-numeric characters like currency symbols and commas."""
    if not isinstance(cols, (list, tuple)):
        cols = [cols]

    def clean_value(x):
        if pd.isna(x):
            return x
        if isinstance(x, (int, float)):
            return x
        s = str(x).strip()
        # Remove common currency symbols and grouping
        for token in [",", "$", "€", "£", "₹", "¥", "RM", "%"]:
            s = s.replace(token, "")
        # Keep only digits, sign, dot, and exponent markers
        cleaned = []
        valid = set("0123456789.-+eE")
        for ch in s:
            if ch in valid:
                cleaned.append(ch)
        s = "".join(cleaned)
        return s if s != "" else None

    for c in cols:
        if c in df.columns:
            df[c] = df[c].map(clean_value)
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce specified columns to datetime."""
    if not isinstance(cols, (list, tuple)):
        cols = [cols]
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable, fallback_df: pd.DataFrame):
    """Execute builder to get an Altair chart and render it safely; on any error, show a warning and the fallback table."""
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


# ---------------------- App Renderer ----------------------

def render_app():
    # Guard page config for multi-import contexts
    if not st.session_state.get("_page_configured", False):
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_configured"] = True

    alt.data_transformers.disable_max_rows()

    # The provided JSON report
    report = {
        "valid": True,
        "issues": [],
        "summary": [
            "Total sales for the past 6 months: 538,181.64",
            "Total registered users for the past 6 months: 4,592"
        ],
        "tables": [
            {
                "name": "Table",
                "columns": ["total_sales", "registered_users"],
                "rows": [
                    [538181.6399999999, "4592"]
                ]
            }
        ],
        "charts": [
            {
                "id": "main",
                "type": "kpi",
                "spec": {
                    "xKey": "Metric",
                    "yKey": "Value",
                    "series": [
                        {"name": "Total Sales", "yKey": "total_sales"},
                        {"name": "Registered Users", "yKey": "registered_users"}
                    ]
                }
            }
        ],
        "echo": {
            "intent": "comparison_totals",
            "used": {"tables": [], "columns": ["total_sales", "registered_users"]},
            "stats": {"elapsed": 0},
            "sql_present": False
        }
    }

    # Title
    st.title("AI Report")

    # Summary
    st.subheader("Summary")
    if report.get("summary"):
        for item in report["summary"]:
            st.markdown(f"- {item}")
    else:
        st.write("No summary available.")

    # Tables
    st.subheader("Tables")
    if report.get("tables"):
        for t in report["tables"]:
            name = t.get("name") or "Table"
            cols = t.get("columns", [])
            rows = t.get("rows", [])
            try:
                df = pd.DataFrame(rows, columns=cols)
            except Exception:
                # Fallback if rows malformed
                df = pd.DataFrame(rows)
            st.markdown(f"**{name}**")
            st.dataframe(df)
    else:
        st.write("No tables available.")

    # Helper: collect first-row values across tables for quick lookup
    value_lookup = {}
    for t in report.get("tables", []):
        cols = t.get("columns", [])
        rows = t.get("rows", [])
        if rows and cols and len(rows[0]) == len(cols):
            first = rows[0]
            for i, c in enumerate(cols):
                value_lookup[c] = first[i]

    # Charts
    st.subheader("Charts")
    charts = report.get("charts", [])

    if not charts:
        st.write("No charts available.")
        return

    for ch in charts:
        chart_id = ch.get("id", "chart")
        chart_type = (ch.get("type") or "").lower()
        st.markdown(f"**Chart: {chart_id}**")

        if chart_type == "kpi":
            spec = ch.get("spec", {})
            series = spec.get("series", [])

            # Build a small DataFrame with Metric/Value from the series list
            rows = []
            for s in series:
                y_key = s.get("yKey")
                name = s.get("name") or (y_key or "")
                if y_key in value_lookup:
                    rows.append({"Metric": name, "Value": value_lookup.get(y_key)})

            if not rows:
                st.warning("Chart unavailable")
                st.dataframe(pd.DataFrame(columns=["Metric", "Value"]))
                continue

            kpi_df = pd.DataFrame(rows)
            kpi_sanitized, cmap = sanitize_columns(kpi_df)
            metric_col = cmap.get("Metric", "metric")
            value_col = cmap.get("Value", "value")

            # Coerce value to numeric
            coerce_numeric(kpi_sanitized, [value_col])

            # Filter to non-null rows for both fields
            kpi_valid = kpi_sanitized.copy()
            if metric_col not in kpi_valid.columns or value_col not in kpi_valid.columns:
                st.warning("Chart unavailable")
                st.dataframe(kpi_sanitized)
                continue

            kpi_valid = kpi_valid[kpi_valid[metric_col].notna() & kpi_valid[value_col].notna()]
            if kpi_valid.empty:
                st.warning("Chart unavailable")
                st.dataframe(kpi_sanitized)
                continue

            def build_chart():
                chart = (
                    alt.Chart(kpi_valid)
                    .mark_bar()
                    .encode(
                        x=alt.X(metric_col, type="nominal", title="Metric"),
                        y=alt.Y(value_col, type="quantitative", title="Value"),
                        color=alt.Color(metric_col, type="nominal", legend=None),
                        tooltip=[metric_col, value_col],
                    )
                )
                return chart.properties(height=300)

            safe_altair_chart(build_chart, kpi_sanitized)
        else:
            # Unsupported chart type; warn and show available data context
            st.warning("Chart unavailable")
            # Show a combined view of first table (if available) for context
            if report.get("tables"):
                t0 = report["tables"][0]
                try:
                    df0 = pd.DataFrame(t0.get("rows", []), columns=t0.get("columns", []))
                except Exception:
                    df0 = pd.DataFrame(t0.get("rows", []))
                st.dataframe(df0)
            else:
                st.dataframe(pd.DataFrame())


# Note: This module exposes render_app() and does not execute on import.
