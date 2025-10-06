import json
from typing import Any, Dict, List, Optional

import altair as alt
import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# Default report data embedded from the provided JSON
# -----------------------------------------------------------------------------
default_report: Dict[str, Any] = {
    "valid": False,
    "issues": [
        {
            "code": "missing_column",
            "severity": "error",
            "message": "Safe fallback: users table has no registration time column to compute registered_users by quarter, so a period comparison cannot be safely produced",
        }
    ],
    "summary": [
        "Cannot compare registered users and sales between 2025 Q1 and Q2 due to missing registration time or sales period columns."
    ],
    "tables": [
        {"name": "Table", "columns": ["value"], "rows": [[0]]}
    ],
    "charts": [],
    "echo": {
        "intent": "single_number",
        "used": {"tables": [""], "columns": []},
        "stats": {"elapsed": 0.001173359},
        "sql_present": True,
    },
}

# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------

def sanitize_table_name(name: Optional[str], idx: int) -> str:
    if isinstance(name, str) and name.strip():
        return name.strip()
    return f"Table {idx+1}"


def dataframe_from_table_obj(table_obj: Dict[str, Any]) -> pd.DataFrame:
    cols = table_obj.get("columns", [])
    rows = table_obj.get("rows", [])
    try:
        df = pd.DataFrame(rows, columns=cols if cols else None)
    except Exception:
        # Fallback: attempt without enforcing columns
        df = pd.DataFrame(rows)
        if cols and len(cols) == df.shape[1]:
            df.columns = cols
    return df


def infer_vegalite_type(series: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(series):
        return "quantitative"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "temporal"
    return "nominal"


def build_altair_chart(chart_spec: Dict[str, Any], tables_map: Dict[str, pd.DataFrame]) -> Optional[alt.Chart]:
    ctype = (chart_spec.get("type") or chart_spec.get("chart") or "").lower()
    title = chart_spec.get("title")

    # Resolve data
    df: Optional[pd.DataFrame] = None
    data_spec = chart_spec.get("data")
    if isinstance(data_spec, dict):
        if "table" in data_spec and isinstance(data_spec["table"], str):
            df = tables_map.get(data_spec["table"])  # may be None
        elif {"columns", "rows"}.issubset(data_spec.keys()):
            try:
                df = pd.DataFrame(data_spec.get("rows", []), columns=data_spec.get("columns", None))
            except Exception:
                df = pd.DataFrame(data_spec.get("rows", []))
        elif "values" in data_spec and isinstance(data_spec["values"], list):
            try:
                df = pd.DataFrame(data_spec["values"]) if data_spec["values"] else pd.DataFrame()
            except Exception:
                df = pd.DataFrame()
    elif isinstance(data_spec, list) and all(isinstance(x, dict) for x in data_spec):
        df = pd.DataFrame(data_spec)

    # As an additional fallback, allow inline 'columns' + 'rows' at root
    if df is None and {"columns", "rows"}.issubset(chart_spec.keys()):
        try:
            df = pd.DataFrame(chart_spec.get("rows", []), columns=chart_spec.get("columns", None))
        except Exception:
            df = pd.DataFrame(chart_spec.get("rows", []))

    if df is None or df.empty:
        return None

    enc = chart_spec.get("encoding", {}) if isinstance(chart_spec.get("encoding"), dict) else {}

    # Helper to get field with fallback to first/second columns
    def pick_field(role_keys: List[str], fallback_index: int) -> str:
        for k in role_keys:
            v = enc.get(k)
            if isinstance(v, str) and v in df.columns:
                return v
        # Fallback to column by index if available
        if 0 <= fallback_index < df.shape[1]:
            return df.columns[fallback_index]
        # Last resort: first column
        return df.columns[0]

    # Build chart based on type
    chart: Optional[alt.Chart] = None

    if ctype == "pie":
        # Expect category and value fields
        category_field = pick_field(["category", "color", "x"], 0)
        value_field = pick_field(["value", "theta", "y"], 1 if df.shape[1] > 1 else 0)
        chart = (
            alt.Chart(df)
            .mark_arc()
            .encode(
                theta=alt.Theta(field=value_field, type=infer_vegalite_type(df[value_field])),
                color=alt.Color(field=category_field, type=infer_vegalite_type(df[category_field])),
                tooltip=[alt.Tooltip(c, type=infer_vegalite_type(df[c])) for c in df.columns],
            )
        )
    elif ctype == "bar":
        x_field = pick_field(["x"], 0)
        y_field = pick_field(["y"], 1 if df.shape[1] > 1 else 0)
        color_field = enc.get("color") if isinstance(enc.get("color"), str) and enc.get("color") in df.columns else None
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X(x_field, type=infer_vegalite_type(df[x_field])),
                y=alt.Y(y_field, type=infer_vegalite_type(df[y_field])),
                color=alt.Color(color_field, type=infer_vegalite_type(df[color_field])) if color_field else alt.value("#4C78A8"),
                tooltip=[alt.Tooltip(c, type=infer_vegalite_type(df[c])) for c in df.columns],
            )
        )
    elif ctype == "line":
        x_field = pick_field(["x"], 0)
        y_field = pick_field(["y"], 1 if df.shape[1] > 1 else 0)
        color_field = enc.get("color") if isinstance(enc.get("color"), str) and enc.get("color") in df.columns else None
        chart = (
            alt.Chart(df)
            .mark_line(point=True)
            .encode(
                x=alt.X(x_field, type=infer_vegalite_type(df[x_field])),
                y=alt.Y(y_field, type=infer_vegalite_type(df[y_field])),
                color=alt.Color(color_field, type=infer_vegalite_type(df[color_field])) if color_field else alt.value("#4C78A8"),
                tooltip=[alt.Tooltip(c, type=infer_vegalite_type(df[c])) for c in df.columns],
            )
        )
    elif ctype == "area":
        x_field = pick_field(["x"], 0)
        y_field = pick_field(["y"], 1 if df.shape[1] > 1 else 0)
        chart = (
            alt.Chart(df)
            .mark_area(opacity=0.6)
            .encode(
                x=alt.X(x_field, type=infer_vegalite_type(df[x_field])),
                y=alt.Y(y_field, type=infer_vegalite_type(df[y_field])),
                tooltip=[alt.Tooltip(c, type=infer_vegalite_type(df[c])) for c in df.columns],
            )
        )
    else:
        # Default visualization: scatter/point of first two columns if available
        x_field = df.columns[0]
        y_field = df.columns[1] if df.shape[1] > 1 else None
        if y_field is not None:
            chart = (
                alt.Chart(df)
                .mark_point()
                .encode(
                    x=alt.X(x_field, type=infer_vegalite_type(df[x_field])),
                    y=alt.Y(y_field, type=infer_vegalite_type(df[y_field])),
                    tooltip=[alt.Tooltip(c, type=infer_vegalite_type(df[c])) for c in df.columns],
                )
            )
        else:
            # If only one column, create a simple bar of counts/index vs value
            df_one = df.copy()
            df_one = df_one.reset_index().rename(columns={"index": "index", x_field: "value"})
            chart = (
                alt.Chart(df_one)
                .mark_bar()
                .encode(
                    x=alt.X("index", type="quantitative"),
                    y=alt.Y("value", type=infer_vegalite_type(df_one["value"])),
                    tooltip=["index", "value"],
                )
            )

    if chart is not None and title:
        chart = chart.properties(title=title)
    return chart


# -----------------------------------------------------------------------------
# Streamlit App
# -----------------------------------------------------------------------------
st.set_page_config(page_title="AI Report Viewer", layout="wide")

st.title("AI Report Viewer")
st.caption("This app renders summaries, tables, and charts from a JSON report.")

# Sidebar: allow replacing the embedded report JSON via upload
with st.sidebar:
    st.header("Report Source")
    uploaded = st.file_uploader("Upload a report JSON (optional)", type=["json"])
    use_uploaded = st.checkbox("Use uploaded JSON if provided", value=True)

# Load report
report: Dict[str, Any] = default_report
if uploaded is not None and use_uploaded:
    try:
        report = json.loads(uploaded.read().decode("utf-8"))
        st.sidebar.success("Loaded uploaded JSON report.")
    except Exception as e:
        st.sidebar.error(f"Failed to parse JSON: {e}")
        report = default_report

# Status banner
if report.get("valid") is True:
    st.success("Report is valid.")
else:
    st.error("Report is marked as invalid.")

# Issues panel (if any)
issues: List[Dict[str, Any]] = report.get("issues", []) if isinstance(report.get("issues"), list) else []
if issues:
    with st.expander(f"Issues ({len(issues)})", expanded=True):
        for i, issue in enumerate(issues, start=1):
            code = issue.get("code", "")
            severity = issue.get("severity", "")
            msg = issue.get("message", "")
            st.write(f"{i}. [{severity}] {code} - {msg}")

# Summary section
st.header("Summary")
summary_items = report.get("summary", [])
if isinstance(summary_items, list) and summary_items:
    for item in summary_items:
        st.markdown(f"- {str(item)}")
else:
    st.info("No summary available.")

# Tables section
st.header("Tables")
tables = report.get("tables", []) if isinstance(report.get("tables"), list) else []

# Build map of table name -> DataFrame
tables_map: Dict[str, pd.DataFrame] = {}
if tables:
    for idx, t in enumerate(tables):
        if not isinstance(t, dict):
            continue
        name = sanitize_table_name(t.get("name"), idx)
        df = dataframe_from_table_obj(t)
        tables_map[name] = df
        st.subheader(name)
        st.dataframe(df, use_container_width=True)
else:
    st.info("No tables available.")

# Charts section
st.header("Charts")
charts = report.get("charts", []) if isinstance(report.get("charts"), list) else []
if charts:
    for idx, ch in enumerate(charts):
        if not isinstance(ch, dict):
            continue
        title = ch.get("title") or f"Chart {idx+1}"
        chart = build_altair_chart(ch, tables_map)
        st.subheader(title)
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Chart has no data or could not be rendered.")
else:
    st.info("No charts available in this report.")

# Raw JSON for transparency
with st.expander("Raw Report JSON", expanded=False):
    st.json(report)

st.caption("Rendered with Streamlit, Altair, and pandas.")
