import streamlit as st
import pandas as pd
import altair as alt
from typing import Any, Dict, List, Optional

# Embedded report JSON (as provided)
report: Dict[str, Any] = {
    "valid": False,
    "issues": [
        {
            "code": "missing_column",
            "severity": "error",
            "message": "Cannot compute a quarter comparison: no typed Date/DateTime column present in either table to determine 2025 Q1 vs Q2."
        }
    ],
    "summary": [
        "Cannot compare registered users and sales between 2025 Q1 and Q2 due to missing Date/DateTime columns."
    ],
    "tables": [
        {"name": "Table", "columns": ["value"], "rows": [[0]]}
    ],
    "charts": [],
    "echo": {
        "intent": "comparison_totals",
        "used": {"tables": [], "columns": []},
        "stats": {"elapsed": 0.001545059},
        "sql_present": True
    }
}

# Streamlit page config
st.set_page_config(page_title="AI Report Viewer", layout="wide")

st.title("AI Report Viewer")

# Display validation status and issues if any
if not report.get("valid", True):
    st.warning("Report marked as invalid. See issues below.")

issues: List[Dict[str, Any]] = report.get("issues", [])
if issues:
    st.subheader("Issues")
    for i, issue in enumerate(issues, start=1):
        severity = (issue.get("severity") or "info").lower()
        msg = f"[{issue.get('code', 'issue')}] {issue.get('message', '')}"
        if severity == "error":
            st.error(msg)
        elif severity == "warning":
            st.warning(msg)
        else:
            st.info(msg)

# Display summary in markdown
summary_items: List[str] = report.get("summary", [])
if summary_items:
    st.subheader("Summary")
    # Render as bullet list
    bullets = "\n".join(f"- {line}" for line in summary_items)
    st.markdown(bullets)
else:
    st.info("No summary provided.")

# Helper: build a pandas DataFrame from a generic data blob

def to_dataframe(obj: Any) -> Optional[pd.DataFrame]:
    """Attempt to convert an arbitrary object into a pandas DataFrame.

    Supported inputs:
    - dict with keys 'columns' (list[str]) and 'rows' (list[list[Any]])
    - list of records (list[dict])
    - already a DataFrame
    """
    if obj is None:
        return None
    if isinstance(obj, pd.DataFrame):
        return obj
    if isinstance(obj, dict):
        cols = obj.get("columns")
        rows = obj.get("rows")
        data = obj.get("data")
        # Some charts may nest the data under 'data'
        if cols is not None and rows is not None:
            try:
                return pd.DataFrame(rows, columns=cols)
            except Exception:
                pass
        if isinstance(data, dict) and ("columns" in data and "rows" in data):
            try:
                return pd.DataFrame(data["rows"], columns=data["columns"])
            except Exception:
                pass
        if isinstance(data, list) and all(isinstance(x, dict) for x in data):
            try:
                return pd.DataFrame(data)
            except Exception:
                pass
    if isinstance(obj, list) and all(isinstance(x, dict) for x in obj):
        try:
            return pd.DataFrame(obj)
        except Exception:
            pass
    return None

# Charts: generic Altair builder

def build_chart(spec: Dict[str, Any]) -> Optional[alt.Chart]:
    """Build an Altair chart from a simple JSON spec.

    Supported fields in spec:
    - type: 'bar' | 'line' | 'area' | 'scatter' | 'pie' | 'hist'
    - data: any supported by to_dataframe
    - encoding: dict with x, y, color, size, tooltip (optional)
    - title: string (optional)
    """
    df = to_dataframe(spec.get("data"))
    if df is None or df.empty:
        return None

    chart_type = (spec.get("type") or "bar").lower()
    enc = spec.get("encoding", {})
    title = spec.get("title")

    # Default encodings
    x = enc.get("x")
    y = enc.get("y")
    color = enc.get("color")
    size = enc.get("size")
    tooltip = enc.get("tooltip")

    # Build base chart
    base = alt.Chart(df, title=title)

    try:
        if chart_type == "line":
            ch = base.mark_line(point=True)
            if x and y:
                ch = ch.encode(x=x, y=y)
            elif x or y:
                # If only one is provided, attempt to auto-detect the other numeric field
                if not x:
                    # Use the first non-numeric column for x, if available
                    non_numeric_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
                    x = non_numeric_cols[0] if non_numeric_cols else df.columns[0]
                if not y:
                    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                    y = numeric_cols[0] if numeric_cols else df.columns[-1]
                ch = ch.encode(x=x, y=y)
        elif chart_type == "area":
            ch = base.mark_area()
            if x and y:
                ch = ch.encode(x=x, y=y)
            else:
                # Fallback mapping
                if not x:
                    non_numeric_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
                    x = non_numeric_cols[0] if non_numeric_cols else df.columns[0]
                if not y:
                    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                    y = numeric_cols[0] if numeric_cols else df.columns[-1]
                ch = ch.encode(x=x, y=y)
        elif chart_type == "scatter":
            ch = base.mark_circle()
            if x and y:
                ch = ch.encode(x=x, y=y)
            else:
                numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                if len(numeric_cols) >= 2:
                    ch = ch.encode(x=numeric_cols[0], y=numeric_cols[1])
                else:
                    return None
        elif chart_type == "pie":
            # Expect either theta and color in encoding, or infer
            theta = enc.get("theta")
            color_enc = color
            if not theta:
                # Choose first numeric column for theta
                numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                theta = numeric_cols[0] if numeric_cols else df.columns[-1]
            if not color_enc:
                # Choose first non-numeric column for color
                non_numeric_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
                color_enc = non_numeric_cols[0] if non_numeric_cols else df.columns[0]
            ch = base.mark_arc().encode(theta=alt.Theta(field=theta, type='quantitative'),
                                         color=alt.Color(field=color_enc, type='nominal'))
        elif chart_type in ("hist", "histogram"):
            # Histogram of a numeric column
            target = x or y
            if not target:
                numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                if numeric_cols:
                    target = numeric_cols[0]
                else:
                    return None
            ch = base.mark_bar().encode(x=alt.X(f"{target}:Q", bin=True), y='count()')
        else:  # default to bar
            ch = base.mark_bar()
            if x and y:
                ch = ch.encode(x=x, y=y)
            else:
                # Try to pick a categorical x and numeric y
                non_numeric_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
                numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                x_enc = x or (non_numeric_cols[0] if non_numeric_cols else df.columns[0])
                y_enc = y or (numeric_cols[0] if numeric_cols else df.columns[-1])
                ch = ch.encode(x=x_enc, y=y_enc)

        # Add optional encodings
        if color and chart_type != "pie":
            ch = ch.encode(color=color)
        if size and chart_type in ("scatter",):
            ch = ch.encode(size=size)
        if tooltip:
            ch = ch.encode(tooltip=tooltip)

        ch = ch.properties(width="container", height=400)
        return ch
    except Exception:
        return None

# Work around Altair row limit for larger datasets
alt.data_transformers.disable_max_rows()

# Render tables
tables: List[Dict[str, Any]] = report.get("tables", [])
if tables:
    st.subheader("Tables")
    for t in tables:
        name = t.get("name") or "Table"
        df = to_dataframe({"columns": t.get("columns"), "rows": t.get("rows")})
        st.markdown(f"**{name}**")
        if df is None:
            st.info("Table data unavailable or malformed.")
        else:
            st.dataframe(df, use_container_width=True)
else:
    st.info("No tables in the report.")

# Render charts (Altair)
charts: List[Dict[str, Any]] = report.get("charts", [])
if charts:
    st.subheader("Charts")
    for idx, ch_spec in enumerate(charts, start=1):
        title = ch_spec.get("title") or f"Chart {idx}"
        st.markdown(f"**{title}**")
        chart = build_chart(ch_spec)
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Unable to render this chart.")
else:
    st.info("No charts in the report.")

# Optional: echo/debug panel collapsed by default
with st.expander("Debug: Raw report JSON"):
    st.json(report)
