import streamlit as st
import pandas as pd
import altair as alt
from typing import Any, Dict, List, Optional, Union

# Embedded report JSON provided by the user
REPORT: Dict[str, Any] = {
    "valid": False,
    "issues": [
        {
            "code": "missing_column",
            "severity": "error",
            "message": "Cannot compute 2025 Q1 vs Q2 because neither table has a typed Date/DateTime column (Upload_Date is a String), so quarterly buckets cannot be derived; returning placeholder value."
        }
    ],
    "summary": [
        "Cannot compare registered users and sales between 2025 Q1 and Q2 due to missing date or time columns in the dataset."
    ],
    "tables": [
        {"name": "Table", "columns": ["value"], "rows": [[0]]}
    ],
    "charts": [],
    "echo": {
        "intent": "comparison_totals",
        "used": {"tables": [], "columns": []},
        "stats": {"elapsed": 0.00179534},
        "sql_present": True
    }
}


def _to_dataframe_from_table_spec(table_spec: Dict[str, Any]) -> pd.DataFrame:
    """Convert a table spec with keys {name, columns, rows} into a pandas DataFrame."""
    columns = table_spec.get("columns")
    rows = table_spec.get("rows", [])
    # Robust construction even if column count mismatches row length
    try:
        if isinstance(columns, list) and columns:
            df = pd.DataFrame(rows, columns=columns)
        else:
            df = pd.DataFrame(rows)
    except Exception:
        df = pd.DataFrame(rows)
    return df


def _to_dataframe_from_chart_data(data_spec: Any) -> Optional[pd.DataFrame]:
    """Convert various possible data specs into a DataFrame.

    Supported forms:
    - {"columns": [...], "rows": [[...], ...]}
    - list of dict records: [{...}, {...}]
    - dict of arrays: {col: [..], ...}
    """
    if data_spec is None:
        return None
    try:
        # tables-like
        if isinstance(data_spec, dict) and "rows" in data_spec and "columns" in data_spec:
            return pd.DataFrame(data_spec.get("rows", []), columns=data_spec.get("columns", None))
        # dict of arrays
        if isinstance(data_spec, dict):
            # ensure values are list-like of same length
            return pd.DataFrame(data_spec)
        # list of records
        if isinstance(data_spec, list):
            return pd.DataFrame(data_spec)
    except Exception:
        return None
    return None


def _build_altair_chart(chart_spec: Dict[str, Any]) -> Optional[alt.Chart]:
    """Attempt to build an Altair chart from a generic chart spec.

    Expected keys may include: type, data, encoding, title.
    This function is resilient; if it cannot determine a proper chart,
    it returns None.
    """
    ctype = str(chart_spec.get("type", "")).strip().lower()
    df = _to_dataframe_from_chart_data(chart_spec.get("data"))
    if df is None or df.empty:
        return None

    enc = chart_spec.get("encoding", {}) or {}
    title = chart_spec.get("title")

    # Helper to fetch a field name from encoding by candidate keys
    def pick_field(enc_map: Dict[str, Any], candidates: List[str]) -> Optional[str]:
        for key in candidates:
            val = enc_map.get(key)
            if isinstance(val, str):
                return val
            if isinstance(val, dict):
                # Allow vega-lite-like {'field': 'col', 'type': 'quantitative'}
                field = val.get('field')
                if isinstance(field, str):
                    return field
        return None

    # Guess columns if encoding not provided
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    non_numeric_cols = [c for c in df.columns if c not in numeric_cols]

    # Select common encodings
    x_field = pick_field(enc, ["x"]) or (non_numeric_cols[0] if non_numeric_cols else (df.columns[0] if len(df.columns) > 0 else None))
    y_field = pick_field(enc, ["y"]) or (numeric_cols[0] if numeric_cols else (df.columns[1] if len(df.columns) > 1 else None))
    color_field = pick_field(enc, ["color", "category"]) or (non_numeric_cols[1] if len(non_numeric_cols) > 1 else None)
    tooltip_fields = enc.get("tooltip")
    if isinstance(tooltip_fields, str):
        tooltip_fields = [tooltip_fields]
    elif not isinstance(tooltip_fields, list):
        tooltip_fields = None

    chart = None

    try:
        if ctype in ("bar", "bar_chart") and x_field and y_field:
            chart = alt.Chart(df).mark_bar().encode(
                x=alt.X(x_field, sort=None),
                y=alt.Y(y_field),
                color=color_field if color_field else alt.value("steelblue"),
                tooltip=tooltip_fields or [x_field, y_field] + ([color_field] if color_field else []),
            )
        elif ctype in ("line", "line_chart") and x_field and y_field:
            chart = alt.Chart(df).mark_line(point=True).encode(
                x=alt.X(x_field, sort=None),
                y=alt.Y(y_field),
                color=color_field if color_field else alt.value("steelblue"),
                tooltip=tooltip_fields or [x_field, y_field] + ([color_field] if color_field else []),
            )
        elif ctype in ("area", "area_chart") and x_field and y_field:
            chart = alt.Chart(df).mark_area(opacity=0.7).encode(
                x=alt.X(x_field, sort=None),
                y=alt.Y(y_field),
                color=color_field if color_field else alt.value("steelblue"),
                tooltip=tooltip_fields or [x_field, y_field] + ([color_field] if color_field else []),
            )
        elif ctype in ("scatter", "scatterplot", "point") and x_field and y_field:
            chart = alt.Chart(df).mark_circle(size=60, opacity=0.7).encode(
                x=alt.X(x_field, sort=None),
                y=alt.Y(y_field),
                color=color_field if color_field else alt.value("steelblue"),
                tooltip=tooltip_fields or [x_field, y_field] + ([color_field] if color_field else []),
            )
        elif ctype in ("pie", "donut", "arc"):
            # Determine category/value for pie
            theta_field = pick_field(enc, ["theta", "value", "y"]) or (numeric_cols[0] if numeric_cols else None)
            category = pick_field(enc, ["color", "category", "x"]) or (non_numeric_cols[0] if non_numeric_cols else None)
            if theta_field and category:
                mark = alt.Chart(df).mark_arc(innerRadius=50 if ctype in ("donut",) else 0)
                chart = mark.encode(
                    theta=alt.Theta(theta_field, stack=True),
                    color=alt.Color(category, legend=True),
                    tooltip=tooltip_fields or [category, theta_field],
                )
        else:
            # Fallback: try bar chart if we can identify fields
            if x_field and y_field:
                chart = alt.Chart(df).mark_bar().encode(
                    x=alt.X(x_field, sort=None),
                    y=alt.Y(y_field),
                    color=color_field if color_field else alt.value("steelblue"),
                    tooltip=tooltip_fields or [x_field, y_field] + ([color_field] if color_field else []),
                )
    except Exception:
        chart = None

    if chart is not None and title:
        chart = chart.properties(title=title)

    return chart


def main():
    st.set_page_config(page_title="AI Report Viewer", layout="wide")
    st.title("AI Report Viewer")

    # Report validity and issues
    if not REPORT.get("valid", True):
        st.warning("This report is marked as invalid or incomplete. Review issues below.")
    issues = REPORT.get("issues", [])
    if issues:
        st.subheader("Issues")
        for i, iss in enumerate(issues, start=1):
            sev = str(iss.get("severity", "info")).lower()
            msg = f"[{iss.get('code', 'issue')}] {iss.get('message', '')}"
            if sev == "error":
                st.error(msg)
            elif sev == "warning":
                st.warning(msg)
            else:
                st.info(msg)

    # Summary section
    st.subheader("Summary")
    summary_items = REPORT.get("summary", [])
    if isinstance(summary_items, list) and summary_items:
        st.markdown("\n".join(f"- {s}" for s in summary_items))
    elif isinstance(summary_items, str) and summary_items:
        st.markdown(summary_items)
    else:
        st.info("No summary provided.")

    # Tables section
    st.subheader("Tables")
    tables = REPORT.get("tables", []) or []
    if len(tables) == 0:
        st.info("No tables available in this report.")
    else:
        for t in tables:
            name = t.get("name") or "Table"
            st.markdown(f"**{name}**")
            df = _to_dataframe_from_table_spec(t)
            st.dataframe(df, use_container_width=True)

    # Charts section (Altair)
    st.subheader("Charts")
    charts = REPORT.get("charts", []) or []
    if len(charts) == 0:
        st.info("No charts available in this report.")
    else:
        for idx, ch in enumerate(charts, start=1):
            title = ch.get("title") or ch.get("name") or f"Chart {idx}"
            chart_obj = _build_altair_chart(ch)
            if chart_obj is not None:
                st.markdown(f"**{title}**")
                st.altair_chart(chart_obj, use_container_width=True)
            else:
                st.warning(f"Unable to render chart: {title}")

    # Optional: Inspect raw report JSON
    with st.expander("Show raw report JSON"):
        st.json(REPORT)


if __name__ == "__main__":
    main()
