# AI Report Streamlit App
# This app renders a provided JSON report: summary (markdown), tables (dataframes), and charts (Altair).
# It embeds the given JSON report directly so it can be run standalone.

import json
from typing import Any, Dict, List, Optional

import altair as alt
import pandas as pd
import streamlit as st


# ---------------------------
# Embedded report JSON (as Python dict)
# ---------------------------
REPORT: Dict[str, Any] = {
    "valid": False,
    "issues": [
        {
            "code": "missing_column",
            "severity": "error",
            "message": "Safe fallback: unable to compute registered users by quarter because the USERS table has no time column in its heads and no reliable user_id\u2194comuserid join key exists between the tables"
        }
    ],
    "summary": [
        "Cannot compare registered users and sales between 2025 Q1 and Q2 due to missing date/time columns or join keys in the dataset."
    ],
    "tables": [
        {"name": "Table", "columns": ["value"], "rows": [[0]]}
    ],
    "charts": [],
    "echo": {
        "intent": "comparison_totals",
        "used": {"tables": [""], "columns": []},
        "stats": {"elapsed": 0.00118853},
        "sql_present": True
    }
}


# ---------------------------
# Helper functions
# ---------------------------

def to_dataframe(table_spec: Dict[str, Any]) -> pd.DataFrame:
    """Convert a table spec with 'columns' and 'rows' to a pandas DataFrame."""
    cols = table_spec.get("columns", [])
    rows = table_spec.get("rows", [])
    try:
        df = pd.DataFrame(rows, columns=cols)
    except Exception:
        # Fallback: attempt without columns
        df = pd.DataFrame(rows)
        if cols and len(cols) == df.shape[1]:
            df.columns = cols
    return df


def infer_fields_for_xy(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Heuristically infer x and y fields for generic charts when not provided."""
    x_field = None
    y_field = None
    # Prefer first non-numeric as x, first numeric as y
    for col in df.columns:
        if x_field is None and not pd.api.types.is_numeric_dtype(df[col]):
            x_field = col
    for col in df.columns:
        if y_field is None and pd.api.types.is_numeric_dtype(df[col]):
            y_field = col
    # If all numeric, use first two
    if x_field is None and len(df.columns) >= 1:
        x_field = df.columns[0]
    if y_field is None and len(df.columns) >= 2:
        y_field = df.columns[1]
    return {"x": x_field, "y": y_field}


def extract_field(enc: Any) -> Optional[str]:
    """Extract a field name from an encoding value that may be a string or dict."""
    if enc is None:
        return None
    if isinstance(enc, str):
        return enc
    if isinstance(enc, dict):
        # Common Altair-like spec uses {'field': 'col', 'type': 'quantitative'}
        return enc.get("field") or enc.get("fieldName") or enc.get("value")
    return None


def build_chart(chart_spec: Dict[str, Any]) -> Optional[alt.Chart]:
    """Build an Altair chart from a generic chart spec.
    Supported types: bar, line, area, scatter, pie.
    Data can be in chart_spec['data'] as {'columns': [...], 'rows': [...]} or list of records.
    Encodings can be provided under chart_spec['encoding'] or top-level keys like 'x', 'y', 'color'.
    """
    data_spec = chart_spec.get("data")
    df: Optional[pd.DataFrame] = None

    if isinstance(data_spec, dict) and set(["columns", "rows"]).issubset(data_spec.keys()):
        df = pd.DataFrame(data_spec.get("rows", []), columns=data_spec.get("columns", []))
    elif isinstance(data_spec, list):
        # list of records
        df = pd.DataFrame(data_spec)
    elif isinstance(chart_spec.get("table"), dict):
        # Some specs might nest a table
        df = to_dataframe(chart_spec["table"])

    if df is None or df.empty:
        return None

    ctype = str(chart_spec.get("type", "bar")).lower()
    enc = chart_spec.get("encoding", chart_spec)

    # Extract encodings if present
    x_field = extract_field(enc.get("x")) if isinstance(enc, dict) else None
    y_field = extract_field(enc.get("y")) if isinstance(enc, dict) else None
    color_field = extract_field(enc.get("color")) if isinstance(enc, dict) else None
    size_field = extract_field(enc.get("size")) if isinstance(enc, dict) else None
    tooltip = enc.get("tooltip") if isinstance(enc, dict) else None

    if not x_field or not y_field:
        inferred = infer_fields_for_xy(df)
        x_field = x_field or inferred["x"]
        y_field = y_field or inferred["y"]

    base = alt.Chart(df)

    if ctype == "pie":
        # For pie, try label/value or infer
        label_field = extract_field(enc.get("label")) if isinstance(enc, dict) else None
        value_field = extract_field(enc.get("value")) if isinstance(enc, dict) else None
        if not label_field:
            # pick first non-numeric as label
            for c in df.columns:
                if not pd.api.types.is_numeric_dtype(df[c]):
                    label_field = c
                    break
            if not label_field and len(df.columns) > 0:
                label_field = df.columns[0]
        if not value_field:
            # pick first numeric as value
            for c in df.columns:
                if pd.api.types.is_numeric_dtype(df[c]):
                    value_field = c
                    break
            if not value_field and len(df.columns) > 1:
                value_field = df.columns[1]
        if not label_field or not value_field:
            return None
        chart = base.mark_arc().encode(
            theta=alt.Theta(field=value_field, type="quantitative"),
            color=alt.Color(field=label_field, type="nominal"),
            tooltip=list(df.columns) if tooltip is None else tooltip,
        )
        return chart

    # Default mark by type
    mark_fn = {
        "bar": "mark_bar",
        "line": "mark_line",
        "area": "mark_area",
        "scatter": "mark_point",
        "point": "mark_point",
    }.get(ctype, "mark_bar")

    mark = getattr(base, mark_fn)()

    encodings = {}
    if x_field:
        encodings["x"] = alt.X(x_field, type="quantitative" if pd.api.types.is_numeric_dtype(df[x_field]) else "nominal")
    if y_field:
        encodings["y"] = alt.Y(y_field, type="quantitative" if pd.api.types.is_numeric_dtype(df[y_field]) else "nominal")
    if color_field and color_field in df.columns:
        encodings["color"] = alt.Color(color_field, type="nominal")
    if size_field and size_field in df.columns and ctype in {"scatter", "point"}:
        encodings["size"] = alt.Size(size_field, type="quantitative")
    if tooltip is None:
        encodings["tooltip"] = list(df.columns)
    elif isinstance(tooltip, list):
        encodings["tooltip"] = tooltip

    try:
        chart = mark.encode(**encodings)
    except Exception:
        # Fallback minimal encoding if something goes wrong
        if x_field and y_field:
            chart = base.mark_bar().encode(x=x_field, y=y_field)
        else:
            # As last resort, show first two columns
            cols = list(df.columns)
            if len(cols) >= 2:
                chart = base.mark_bar().encode(x=cols[0], y=cols[1])
            else:
                return None
    return chart


# ---------------------------
# Streamlit UI
# ---------------------------

def main() -> None:
    st.set_page_config(page_title="AI Report Viewer", layout="wide")
    st.title("AI Report Viewer")
    st.caption("This app displays an AI-generated report including summaries, tables, and charts.")

    report = REPORT

    # Validity and issues
    col1, col2 = st.columns([1, 2])
    with col1:
        if report.get("valid", True):
            st.success("Report validity: valid")
        else:
            st.error("Report validity: invalid")
    with col2:
        issues = report.get("issues", []) or []
        if issues:
            with st.expander(f"Issues ({len(issues)})", expanded=True):
                for i, iss in enumerate(issues, start=1):
                    code = iss.get("code", "")
                    sev = iss.get("severity", "")
                    msg = iss.get("message", "")
                    st.write(f"{i}. [{sev}] {code} - {msg}")
        else:
            st.info("No issues reported.")

    # Summary
    st.subheader("Summary")
    summary_items: List[str] = report.get("summary", []) or []
    if summary_items:
        for item in summary_items:
            st.markdown(f"- {item}")
    else:
        st.write("No summary provided.")

    # Tables
    st.subheader("Tables")
    tables: List[Dict[str, Any]] = report.get("tables", []) or []
    if not tables:
        st.info("No tables available.")
    else:
        for idx, tbl in enumerate(tables, start=1):
            name = tbl.get("name") or f"Table {idx}"
            df = to_dataframe(tbl)
            st.markdown(f"**{name}**")
            st.dataframe(df, use_container_width=True)

    # Charts
    st.subheader("Charts")
    charts: List[Dict[str, Any]] = report.get("charts", []) or []
    if not charts:
        st.info("No charts available in this report.")
    else:
        for idx, ch in enumerate(charts, start=1):
            title = ch.get("title") or ch.get("name") or f"Chart {idx}"
            st.markdown(f"**{title}**")
            chart = build_chart(ch)
            if chart is not None:
                st.altair_chart(chart, use_container_width=True)
            else:
                st.warning("Unable to render this chart with the provided specification.")

    # Echo / lineage details
    with st.expander("Report metadata (echo)"):
        echo = report.get("echo", {}) or {}
        st.write({k: v for k, v in echo.items() if k != "sql"})

    # Raw JSON
    with st.expander("Raw report JSON"):
        st.code(json.dumps(report, indent=2), language="json")


if __name__ == "__main__":
    main()
