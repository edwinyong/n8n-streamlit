import json
from typing import Any, Dict, List, Optional, Tuple

import altair as alt
import pandas as pd
import streamlit as st


# ------------------------------------------------------------
# Streamlit App: AI Report Viewer
# ------------------------------------------------------------
# This app renders a provided JSON report, displaying:
# - Summary (markdown)
# - Tables (as st.dataframe)
# - Charts (with Altair: pie, bar, line, area, scatter)
# The report used below is embedded from the provided JSON input.
# ------------------------------------------------------------

st.set_page_config(page_title="AI Report Viewer", layout="wide")
alt.data_transformers.disable_max_rows()

# Embedded default report (from the user-provided JSON)
DEFAULT_REPORT: Dict[str, Any] = {
    "valid": True,
    "issues": [],
    "summary": [
        "No data available for SKU performance analysis."
    ],
    "tables": [],
    "charts": [],
    "echo": {
        "intent": "single_number",
        "used": {"tables": [""], "columns": []},
        "stats": {"elapsed": 0.001811491},
        "sql_present": True,
    },
}


# ------------------------- Utilities -------------------------

def _to_dataframe(obj: Any) -> Optional[pd.DataFrame]:
    """Best-effort conversion of various table-like structures to a DataFrame.

    Supports:
    - list[dict]
    - dict with keys {"columns", "rows"}
    - dict with key "data" (list[dict] or list[list])
    - dict mapping column -> list
    - list[list] (requires separate columns key in same dict; handled by caller)
    """
    try:
        if obj is None:
            return None

        # If it's already a DataFrame
        if isinstance(obj, pd.DataFrame):
            return obj

        # list of dicts
        if isinstance(obj, list):
            if len(obj) == 0:
                return pd.DataFrame()
            if isinstance(obj[0], dict):
                return pd.DataFrame(obj)
            # list of lists without headers: create index-based columns
            if isinstance(obj[0], (list, tuple)):
                max_len = max(len(r) if hasattr(r, "__len__") else 0 for r in obj)
                cols = [f"col_{i}" for i in range(max_len)]
                return pd.DataFrame([list(r) for r in obj], columns=cols)

        # dict with columns & rows
        if isinstance(obj, dict):
            if "columns" in obj and "rows" in obj:
                cols = obj.get("columns") or []
                rows = obj.get("rows") or []
                # rows could be list[dict] or list[list]
                if rows and isinstance(rows[0], dict):
                    return pd.DataFrame(rows)[cols] if cols else pd.DataFrame(rows)
                return pd.DataFrame(rows, columns=cols if cols else None)

            # dict with data key
            if "data" in obj:
                data = obj.get("data")
                if isinstance(data, list):
                    if len(data) == 0:
                        return pd.DataFrame()
                    if isinstance(data[0], dict):
                        return pd.DataFrame(data)
                    if isinstance(data[0], (list, tuple)):
                        max_len = max(len(r) if hasattr(r, "__len__") else 0 for r in data)
                        cols = obj.get("columns") or [f"col_{i}" for i in range(max_len)]
                        return pd.DataFrame([list(r) for r in data], columns=cols)

            # dict mapping column -> list
            # Avoid treating general metadata dicts as tables by checking for list values
            if any(isinstance(v, list) for v in obj.values()):
                return pd.DataFrame(obj)

        # Fallback: try direct DataFrame construction
        return pd.DataFrame(obj)
    except Exception:
        return None


def _infer_fields_for_chart(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Infer sensible default fields for charts when not explicitly provided.

    Returns a dict with potential keys: category, value, x, y, color.
    """
    fields = {"category": None, "value": None, "x": None, "y": None, "color": None}
    if df is None or df.empty:
        return fields

    # Identify numeric vs non-numeric columns
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    non_numeric_cols = [c for c in df.columns if c not in numeric_cols]

    # Prefer the first non-numeric as category, first numeric as value
    fields["category"] = non_numeric_cols[0] if non_numeric_cols else (df.columns[0] if len(df.columns) > 0 else None)
    fields["value"] = numeric_cols[0] if numeric_cols else (df.columns[1] if len(df.columns) > 1 else None)

    # For x/y, prefer category on x and numeric on y
    fields["x"] = fields["category"]
    fields["y"] = fields["value"]

    # If we have another non-numeric, set as color
    if len(non_numeric_cols) > 1:
        fields["color"] = non_numeric_cols[1]

    return fields


def render_summary(summary: Any) -> None:
    st.header("Summary")
    if not summary:
        st.info("No summary provided in the report.")
        return

    # summary may be a list of markdown strings or a single string
    if isinstance(summary, list):
        for s in summary:
            if isinstance(s, str) and s.strip():
                st.markdown(s)
    elif isinstance(summary, str):
        st.markdown(summary)
    else:
        st.write(summary)


def render_tables(tables: Any) -> None:
    st.header("Tables")
    if not tables:
        st.info("No tables in the report.")
        return

    # tables may be a list of table objects or a single object
    if not isinstance(tables, list):
        tables = [tables]

    for idx, t in enumerate(tables, start=1):
        title = None
        df = None

        if isinstance(t, dict):
            title = t.get("title") or t.get("name") or f"Table {idx}"
            df = _to_dataframe(t.get("data") if "data" in t else t)
        else:
            title = f"Table {idx}"
            df = _to_dataframe(t)

        st.subheader(title)
        if df is None:
            st.warning("Unable to parse this table into a dataframe.")
        else:
            st.dataframe(df, use_container_width=True)


def _build_altair_chart(chart_spec: Dict[str, Any]) -> Optional[alt.Chart]:
    """Create an Altair chart from a generic chart spec using best-effort heuristics."""
    # Extract data
    data_obj = chart_spec.get("data", chart_spec.get("dataset"))
    df = _to_dataframe(data_obj)
    if df is None or df.empty:
        # If the spec references a named table present elsewhere, support minimal lookup
        source_table_name = chart_spec.get("table")
        if source_table_name and isinstance(APP_STATE.get("tables_map"), dict):
            ref = APP_STATE["tables_map"].get(source_table_name)
            if isinstance(ref, pd.DataFrame) and not ref.empty:
                df = ref
    if df is None or df.empty:
        return None

    # Determine chart type
    ctype = (chart_spec.get("type") or chart_spec.get("chart") or "bar").lower()

    # Determine encodings
    enc = chart_spec.get("encoding", {})
    inferred = _infer_fields_for_chart(df)

    # Explicit fields if provided in spec; otherwise inferred
    x = chart_spec.get("x") or enc.get("x") or inferred["x"]
    y = chart_spec.get("y") or enc.get("y") or inferred["y"]
    color = chart_spec.get("color") or enc.get("color") or inferred["color"]
    category = chart_spec.get("category") or enc.get("category") or inferred["category"]
    value = chart_spec.get("value") or enc.get("value") or inferred["value"]

    title = chart_spec.get("title")

    # Build chart based on type
    chart = None
    try:
        if ctype in ("pie", "donut", "doughnut"):
            # For pie, require category and value
            if not category or not value:
                return None
            chart = (
                alt.Chart(df, title=title)
                .mark_arc()
                .encode(
                    theta=alt.Theta(field=value, type="quantitative"),
                    color=alt.Color(field=category, type="nominal"),
                    tooltip=[category, value],
                )
            )
        elif ctype in ("bar", "column"):
            if not x or not y:
                return None
            chart = (
                alt.Chart(df, title=title)
                .mark_bar()
                .encode(
                    x=alt.X(x, sort=chart_spec.get("x_sort")),
                    y=alt.Y(y),
                    color=alt.Color(color) if color else alt.value("steelblue"),
                    tooltip=[x, y] if x != y else [x],
                )
            )
        elif ctype == "line":
            if not x or not y:
                return None
            chart = (
                alt.Chart(df, title=title)
                .mark_line(point=True)
                .encode(
                    x=alt.X(x, sort=chart_spec.get("x_sort")),
                    y=alt.Y(y),
                    color=alt.Color(color) if color else alt.value("#1f77b4"),
                    tooltip=[x, y] if x != y else [x],
                )
            )
        elif ctype == "area":
            if not x or not y:
                return None
            chart = (
                alt.Chart(df, title=title)
                .mark_area(opacity=0.7)
                .encode(
                    x=alt.X(x, sort=chart_spec.get("x_sort")),
                    y=alt.Y(y),
                    color=alt.Color(color) if color else alt.value("#1f77b4"),
                    tooltip=[x, y] if x != y else [x],
                )
            )
        elif ctype == "scatter":
            # Scatter needs two numeric axes; if missing, pick two numeric columns
            if not x or not y:
                num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                if len(num_cols) >= 2:
                    x = x or num_cols[0]
                    y = y or num_cols[1]
            if not x or not y:
                return None
            chart = (
                alt.Chart(df, title=title)
                .mark_circle(size=60)
                .encode(
                    x=x,
                    y=y,
                    color=alt.Color(color) if color else alt.value("#2ca02c"),
                    tooltip=[x, y] if x != y else [x],
                )
            )
        else:
            # Default to bar
            if not x or not y:
                if value and category:
                    x = category
                    y = value
                else:
                    # pick any two columns
                    if len(df.columns) >= 2:
                        x = x or df.columns[0]
                        y = y or df.columns[1]
            if not x or not y:
                return None
            chart = (
                alt.Chart(df, title=title)
                .mark_bar()
                .encode(
                    x=alt.X(x, sort=chart_spec.get("x_sort")),
                    y=alt.Y(y),
                    color=alt.Color(color) if color else alt.value("steelblue"),
                    tooltip=[x, y] if x != y else [x],
                )
            )
    except Exception:
        chart = None

    return chart


def render_charts(charts: Any) -> None:
    st.header("Charts")
    if not charts:
        st.info("No charts in the report.")
        return

    # charts may be a list of chart specs or a single spec
    if not isinstance(charts, list):
        charts = [charts]

    for idx, spec in enumerate(charts, start=1):
        title = None
        if isinstance(spec, dict):
            title = spec.get("title") or spec.get("name") or f"Chart {idx}"
        else:
            title = f"Chart {idx}"

        st.subheader(title)
        if not isinstance(spec, dict):
            st.warning("Unrecognized chart specification format.")
            continue

        chart = _build_altair_chart(spec)
        if chart is None:
            st.warning("Unable to render this chart with the provided data/spec.")
        else:
            st.altair_chart(chart.properties(width="container"), use_container_width=True)


# ------------------------- App State -------------------------
APP_STATE: Dict[str, Any] = {}


def build_tables_map(tables: Any) -> Dict[str, pd.DataFrame]:
    """Build a name->DataFrame map for tables to support chart references."""
    result: Dict[str, pd.DataFrame] = {}
    if not tables:
        return result

    if not isinstance(tables, list):
        tables = [tables]

    for idx, t in enumerate(tables, start=1):
        name = None
        df = None
        if isinstance(t, dict):
            name = t.get("name") or t.get("title") or f"table_{idx}"
            df = _to_dataframe(t.get("data") if "data" in t else t)
        else:
            name = f"table_{idx}"
            df = _to_dataframe(t)

        if isinstance(df, pd.DataFrame):
            result[name] = df
    return result


# ------------------------- Main UI -------------------------

def main() -> None:
    st.title("AI Report Viewer")
    st.caption("Render summaries, tables, and charts from a structured JSON report.")

    # Sidebar: allow optional upload or paste of a report JSON to override default
    st.sidebar.header("Report Source")
    src_choice = st.sidebar.radio("Select report source:", ["Embedded (default)", "Upload JSON", "Paste JSON"], index=0)
    report: Dict[str, Any] = DEFAULT_REPORT

    if src_choice == "Upload JSON":
        uploaded = st.sidebar.file_uploader("Upload report JSON", type=["json"]) 
        if uploaded is not None:
            try:
                report = json.load(uploaded)
            except Exception as e:
                st.sidebar.error(f"Failed to parse JSON file: {e}")
    elif src_choice == "Paste JSON":
        pasted = st.sidebar.text_area("Paste report JSON here", height=200)
        if pasted.strip():
            try:
                report = json.loads(pasted)
            except Exception as e:
                st.sidebar.error(f"Failed to parse pasted JSON: {e}")

    # Validate structure lightly
    if not isinstance(report, dict):
        st.error("Invalid report format. Expected a JSON object.")
        return

    # Store tables map for possible chart references
    tables_map = build_tables_map(report.get("tables"))
    APP_STATE["tables_map"] = tables_map

    # Render sections
    render_summary(report.get("summary"))
    render_tables(report.get("tables"))
    render_charts(report.get("charts"))

    # Optional: show issues and raw report
    issues = report.get("issues")
    if isinstance(issues, list) and len(issues) > 0:
        st.header("Issues")
        for issue in issues:
            st.warning(str(issue))

    with st.expander("Debug: Raw Report JSON"):
        st.json(report)


if __name__ == "__main__":
    main()
