import json
from typing import Any, Dict, List, Optional

import altair as alt
import pandas as pd
import streamlit as st

# -------- Embedded Report JSON (as provided) --------
REPORT: Dict[str, Any] = {
    "valid": False,
    "issues": [
        {
            "code": "missing_column",
            "severity": "error",
            "message": "Safe fallback: required registration timestamps for per-quarter user counts are not available in the USERS table head, so a valid period-comparison cannot be produced",
        }
    ],
    "summary": [
        "Cannot compare registered users and sales between 2025 Q1 and Q2 due to missing date or time columns in the dataset."
    ],
    "tables": [{"name": "Table", "columns": ["value"], "rows": [[0]]}],
    "charts": [],
    "echo": {
        "intent": "single_number",
        "used": {"tables": [""], "columns": []},
        "stats": {"elapsed": 0.00115926},
        "sql_present": True,
    },
}

# -------- Helpers --------

def _make_dataframe_from_table_like(obj: Dict[str, Any]) -> Optional[pd.DataFrame]:
    """Create a DataFrame from a table-like object that may contain
    either {columns: [...], rows: [[...], ...]} or a list of dicts under "data".
    Returns None if not possible.
    """
    if obj is None:
        return None

    # Case 1: explicit columns/rows at top level
    if isinstance(obj, dict) and "columns" in obj and "rows" in obj:
        try:
            return pd.DataFrame(obj.get("rows", []), columns=obj.get("columns", []))
        except Exception:
            pass

    # Case 2: nested under key "data"
    data = obj.get("data") if isinstance(obj, dict) else None
    if isinstance(data, dict) and "columns" in data and "rows" in data:
        try:
            return pd.DataFrame(data.get("rows", []), columns=data.get("columns", []))
        except Exception:
            pass

    # Case 3: list of records
    if isinstance(data, list):
        try:
            return pd.DataFrame(data)
        except Exception:
            pass

    return None


def _guess_chart(df: pd.DataFrame, chart_type: str) -> alt.Chart:
    """Build a simple Altair chart given a DataFrame and a chart type.
    This provides a best-effort mapping for common chart types.
    """
    chart_type = (chart_type or "").lower()

    # Identify candidate columns
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    non_numeric_cols = [c for c in df.columns if c not in numeric_cols]

    # Fallbacks
    x_col = non_numeric_cols[0] if non_numeric_cols else (df.columns[0] if len(df.columns) else None)
    y_col = numeric_cols[0] if numeric_cols else (df.columns[1] if len(df.columns) > 1 else None)

    if chart_type in ("bar", "column"):
        if x_col is None or y_col is None:
            return alt.Chart(df).mark_bar().encode()
        return (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X(f"{x_col}:N", title=x_col),
                y=alt.Y(f"{y_col}:Q", title=y_col),
                tooltip=[x_col, y_col],
            )
        )

    if chart_type in ("line", "area"):
        mark = "line" if chart_type == "line" else "area"
        if x_col is None or y_col is None:
            return getattr(alt.Chart(df), f"mark_{mark}")().encode()
        return (
            getattr(alt.Chart(df), f"mark_{mark}")()
            .encode(
                x=alt.X(f"{x_col}:N", title=x_col),
                y=alt.Y(f"{y_col}:Q", title=y_col),
                tooltip=[x_col, y_col],
            )
        )

    if chart_type in ("scatter", "point"):
        x_scatter = numeric_cols[0] if len(numeric_cols) > 0 else df.columns[0]
        y_scatter = numeric_cols[1] if len(numeric_cols) > 1 else (df.columns[1] if len(df.columns) > 1 else None)
        if x_scatter is None or y_scatter is None:
            return alt.Chart(df).mark_point().encode()
        color_col = non_numeric_cols[0] if non_numeric_cols else None
        enc = {
            "x": alt.X(f"{x_scatter}:Q", title=x_scatter),
            "y": alt.Y(f"{y_scatter}:Q", title=y_scatter),
            "tooltip": list(df.columns),
        }
        if color_col:
            enc["color"] = alt.Color(f"{color_col}:N", title=color_col)
        return alt.Chart(df).mark_point().encode(**enc)

    if chart_type == "pie":
        # For a pie chart, pick a category and a value
        category = non_numeric_cols[0] if non_numeric_cols else (df.columns[0] if len(df.columns) else None)
        value = numeric_cols[0] if numeric_cols else (df.columns[1] if len(df.columns) > 1 else None)
        if category is None or value is None:
            # Cannot construct pie sensibly; return empty chart
            return alt.Chart(df).mark_arc().encode()
        return (
            alt.Chart(df)
            .mark_arc()
            .encode(
                theta=alt.Theta(f"{value}:Q", title=value),
                color=alt.Color(f"{category}:N", title=category),
                tooltip=[category, value],
            )
        )

    # Default to bar if type unknown
    if x_col is None or y_col is None:
        return alt.Chart(df).mark_bar().encode()
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_col}:N", title=x_col),
            y=alt.Y(f"{y_col}:Q", title=y_col),
            tooltip=[x_col, y_col],
        )
    )


def render_charts(charts: List[Dict[str, Any]]):
    if not charts:
        st.info("No charts available in this report.")
        return

    for i, chart_obj in enumerate(charts):
        name = chart_obj.get("name") or chart_obj.get("title") or f"Chart {i + 1}"
        st.subheader(name)

        # Build DataFrame from various possible structures
        df = _make_dataframe_from_table_like(chart_obj)
        if df is None:
            # Try a direct 'values' field or 'data' that is list of dicts
            data = chart_obj.get("values") or chart_obj.get("data")
            try:
                if isinstance(data, list):
                    df = pd.DataFrame(data)
            except Exception:
                df = None

        if df is None or df.empty:
            st.warning("Chart data is missing or empty; cannot render.")
            continue

        # Determine chart type
        chart_type = (chart_obj.get("type") or chart_obj.get("mark") or "bar").lower()

        try:
            chart = _guess_chart(df, chart_type)
            st.altair_chart(chart.properties(width="container", height=350), use_container_width=True)
        except Exception as e:
            st.error(f"Failed to render chart '{name}': {e}")
            with st.expander("Show chart data"):
                st.dataframe(df, use_container_width=True)


# -------- Streamlit App --------

def main():
    st.set_page_config(page_title="AI Report Viewer", layout="wide")
    st.title("AI Report Viewer")

    # Report validity and issues
    valid = REPORT.get("valid", True)
    issues = REPORT.get("issues", [])

    if not valid:
        st.error("This report indicates validation issues were found.")
        if issues:
            with st.expander("Show issues"):
                for issue in issues:
                    sev = issue.get("severity", "info").upper()
                    code = issue.get("code", "")
                    msg = issue.get("message", "")
                    st.markdown(f"- [{sev}] {code}: {msg}")

    # Summary
    st.header("Summary")
    summary_items = REPORT.get("summary") or []
    if summary_items:
        for item in summary_items:
            st.markdown(f"- {item}")
    else:
        st.info("No summary provided.")

    # Tables
    st.header("Tables")
    tables = REPORT.get("tables", [])
    if not tables:
        st.info("No tables available in this report.")
    else:
        for idx, table in enumerate(tables):
            t_name = table.get("name") or f"Table {idx + 1}"
            st.subheader(t_name)
            try:
                df = _make_dataframe_from_table_like(table)
                if df is None:
                    # Fall back if structure is minimal
                    rows = table.get("rows", [])
                    cols = table.get("columns", [])
                    df = pd.DataFrame(rows, columns=cols if cols else None)
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Failed to render table '{t_name}': {e}")

    # Charts
    st.header("Charts")
    render_charts(REPORT.get("charts", []))

    # Raw JSON view
    with st.expander("Show raw report JSON"):
        st.code(json.dumps(REPORT, indent=2), language="json")


if __name__ == "__main__":
    main()
