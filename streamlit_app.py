import streamlit as st
import pandas as pd
import altair as alt
from typing import Any, Dict, List, Optional

# Embedded report JSON converted to a Python dict
REPORT: Dict[str, Any] = {
    "valid": False,
    "issues": [
        {
            "code": "missing_column",
            "severity": "error",
            "message": "Requested time-based comparison cannot be computed because the dataset head does not include a date/time column."
        }
    ],
    "summary": [
        "Cannot compare registered users and sales between 2025 Q1 and Q2 due to missing date or time columns in the dataset."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["value"],
            "rows": [[0]]
        }
    ],
    "charts": [],
    "echo": {
        "intent": "single_number",
        "used": {"tables": [""], "columns": []},
        "stats": {"elapsed": 0.00128717},
        "sql_present": True
    }
}

st.set_page_config(page_title="AI Report Viewer", layout="wide")
st.title("AI Report Viewer")

# Helper: map issues to appropriate Streamlit call
SEVERITY_TO_ST = {
    "error": st.error,
    "warning": st.warning,
    "info": st.info,
}

# Helper: build a dataframe from a table-like spec
def table_to_df(tbl: Dict[str, Any]) -> pd.DataFrame:
    cols = tbl.get("columns", [])
    rows = tbl.get("rows", [])
    try:
        df = pd.DataFrame(rows, columns=cols)
    except Exception:
        # Fallback if malformed
        df = pd.DataFrame(rows)
        if cols and len(cols) == df.shape[1]:
            df.columns = cols
    return df

# Helper: get a dataframe for a chart spec
def chart_data_to_df(chart: Dict[str, Any], tables_by_name: Dict[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
    # Priority: explicit data -> columns/rows -> referenced table name
    data = chart.get("data")
    if isinstance(data, list):
        # list of dicts or list of lists
        if len(data) > 0 and isinstance(data[0], dict):
            return pd.DataFrame(data)
        else:
            # If also has columns
            cols = chart.get("columns")
            if cols:
                return pd.DataFrame(data, columns=cols)
            return pd.DataFrame(data)
    if "columns" in chart and "rows" in chart:
        return pd.DataFrame(chart.get("rows", []), columns=chart.get("columns", []))
    # Refer to a table by name or key
    ref_keys = ["table", "source", "source_table", "name"]
    for key in ref_keys:
        if key in chart and isinstance(chart[key], str):
            ref = chart[key]
            if ref in tables_by_name:
                return tables_by_name[ref]
    # Fallback: if only one table exists, use it
    if len(tables_by_name) == 1:
        return list(tables_by_name.values())[0]
    return None

# Helper: render a chart with Altair
def render_chart(chart: Dict[str, Any], df: pd.DataFrame) -> Optional[alt.Chart]:
    if df is None or df.empty:
        return None

    chart_type = str(chart.get("type", "bar")).lower()
    title = chart.get("title")

    # Encoding hints
    x = chart.get("x")
    y = chart.get("y")
    color = chart.get("color")
    size = chart.get("size")
    tooltip = chart.get("tooltip")
    column = chart.get("column")  # for faceting
    row = chart.get("row")        # for faceting
    order = chart.get("order")

    # Sensible defaults if not provided
    cols = list(df.columns)
    if x is None and len(cols) >= 1:
        x = cols[0]
    if y is None and len(cols) >= 2:
        y = cols[1]

    # Build base chart
    base = alt.Chart(df).properties(title=title)

    # Build encodings
    encodings = {}
    if x is not None and x in df.columns:
        encodings['x'] = alt.X(x)
    if y is not None and y in df.columns:
        encodings['y'] = alt.Y(y)
    if color is not None and color in df.columns:
        encodings['color'] = alt.Color(color)
    if size is not None and size in df.columns:
        encodings['size'] = alt.Size(size)
    if order is not None and order in df.columns:
        encodings['order'] = alt.Order(order)
    if tooltip is not None:
        if isinstance(tooltip, list):
            encodings['tooltip'] = [alt.Tooltip(t) for t in tooltip if t in df.columns]
        elif isinstance(tooltip, str) and tooltip in df.columns:
            encodings['tooltip'] = alt.Tooltip(tooltip)

    # Create chart according to type
    chart_obj: Optional[alt.Chart] = None

    if chart_type in ["bar", "column"]:
        chart_obj = base.mark_bar().encode(**encodings)
    elif chart_type in ["line"]:
        chart_obj = base.mark_line(point=True).encode(**encodings)
    elif chart_type in ["area"]:
        chart_obj = base.mark_area().encode(**encodings)
    elif chart_type in ["scatter", "point"]:
        if 'size' not in encodings and x and y:
            # Provide a default point size if not specified
            chart_obj = base.mark_point(filled=True, size=60).encode(**encodings)
        else:
            chart_obj = base.mark_point(filled=True).encode(**encodings)
    elif chart_type in ["pie", "donut", "arc"]:
        # Determine fields for pie
        # Prefer y as value and x as category; if not, guess two columns
        category_field = x if x in df.columns else (cols[0] if len(cols) >= 1 else None)
        value_field = y if y in df.columns else (cols[1] if len(cols) >= 2 else None)
        if category_field is None or value_field is None:
            # Cannot build pie chart without two fields
            return None
        pie_enc = {
            'theta': alt.Theta(field=value_field, type='quantitative'),
            'color': alt.Color(field=category_field, type='nominal')
        }
        if tooltip is not None:
            if isinstance(tooltip, list):
                pie_enc['tooltip'] = [alt.Tooltip(t) for t in tooltip if t in df.columns]
            elif isinstance(tooltip, str) and tooltip in df.columns:
                pie_enc['tooltip'] = alt.Tooltip(tooltip)
        arc = base.mark_arc(innerRadius=0 if chart_type == 'pie' else 50).encode(**pie_enc)
        chart_obj = arc
    else:
        # Default to bar if unknown type
        chart_obj = base.mark_bar().encode(**encodings)

    # Faceting if requested
    if (column and column in df.columns) or (row and row in df.columns):
        facet = {}
        if column and column in df.columns:
            facet['column'] = alt.Column(column)
        if row and row in df.columns:
            facet['row'] = alt.Row(row)
        chart_obj = chart_obj.facet(**facet)

    return chart_obj

# Build a name->DataFrame map for tables
@st.cache_data(show_spinner=False)
def load_tables(report: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    tables = report.get("tables", [])
    mapping: Dict[str, pd.DataFrame] = {}
    for i, tbl in enumerate(tables):
        name = tbl.get("name") or f"Table {i+1}"
        mapping[name] = table_to_df(tbl)
    return mapping

# Display header info and issues
if not REPORT.get("valid", True):
    st.warning("Report is marked as invalid. See issues below.")

issues = REPORT.get("issues", [])
if issues:
    with st.expander("Issues", expanded=True):
        for issue in issues:
            sev = str(issue.get("severity", "info")).lower()
            fn = SEVERITY_TO_ST.get(sev, st.info)
            code = issue.get("code", "")
            msg = issue.get("message", "")
            fn(f"[{sev.upper()}] {code}: {msg}")

# Summary
st.subheader("Summary")
summ = REPORT.get("summary", [])
if isinstance(summ, list) and summ:
    for s in summ:
        st.markdown(f"- {s}")
else:
    st.info("No summary available.")

# Sidebar: Raw JSON echo and metadata
with st.sidebar:
    st.header("Report Metadata")
    st.caption("High-level info about the report")
    st.json({
        "valid": REPORT.get("valid"),
        "issues_count": len(REPORT.get("issues", [])),
        "tables_count": len(REPORT.get("tables", [])),
        "charts_count": len(REPORT.get("charts", [])),
        "intent": REPORT.get("echo", {}).get("intent"),
        "elapsed": REPORT.get("echo", {}).get("stats", {}).get("elapsed")
    })
    with st.expander("Raw report JSON", expanded=False):
        st.json(REPORT)

# Tables
st.subheader("Tables")
table_map = load_tables(REPORT)
if not table_map:
    st.info("No tables to display.")
else:
    for name, df in table_map.items():
        st.markdown(f"#### {name}")
        st.dataframe(df, use_container_width=True)

# Charts
st.subheader("Charts")
charts = REPORT.get("charts", [])
if not charts:
    st.info("No charts to display in this report.")
else:
    for idx, ch in enumerate(charts, start=1):
        df = chart_data_to_df(ch, table_map)
        chart_obj = render_chart(ch, df)
        chart_title = ch.get("title") or ch.get("name") or f"Chart {idx}"
        st.markdown(f"#### {chart_title}")
        if chart_obj is None:
            st.warning("Chart could not be rendered due to missing or invalid data/encodings.")
        else:
            st.altair_chart(chart_obj, use_container_width=True)

st.caption("Rendered with Streamlit, Pandas, and Altair.")
