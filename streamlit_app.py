import json
from typing import Any, Dict, List, Optional, Tuple

import altair as alt
import pandas as pd
import streamlit as st

# ================================
# Embedded default report JSON
# ================================
DEFAULT_REPORT: Dict[str, Any] = {
    "valid": False,
    "issues": [
        {
            "code": "missing_column",
            "severity": "error",
            "message": "Cannot compare registered users and sales for 2025 Q1 vs Q2 because neither table contains a Date/DateTime column to determine quarters."
        }
    ],
    "summary": [
        "Comparison between 2025 Q1 and Q2 is not possible due to missing date or time columns in the dataset."
    ],
    "tables": [],
    "charts": [],
    "echo": {
        "intent": "comparison_totals",
        "used": {
            "tables": [
                "`Haleon_Rewards_User_Performance_110925_user_list`",
                "`Haleon_Rewards_User_Performance_110925_SKUs`"
            ],
            "columns": ["user_id", "Total Sales Amount"]
        },
        "stats": {"elapsed": 0.023126537},
        "sql_present": True
    }
}

# ================================
# Helpers
# ================================

def coerce_dataframe(data: Any) -> Optional[pd.DataFrame]:
    """Attempt to build a pandas DataFrame from a variety of possible shapes.
    Supports:
    - list[dict]
    - {"columns": [...], "rows": [[...], ...]}
    - dict of column -> list
    Returns None if not possible.
    """
    if data is None:
        return None
    try:
        # list of dicts
        if isinstance(data, list) and (len(data) == 0 or isinstance(data[0], dict)):
            return pd.DataFrame(data)
        # dict with columns/rows
        if isinstance(data, dict):
            if "columns" in data and "rows" in data:
                cols = data.get("columns") or []
                rows = data.get("rows") or []
                return pd.DataFrame(rows, columns=cols)
            # dict of arrays
            return pd.DataFrame(data)
    except Exception:
        return None
    return None


def infer_encodings(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Infer basic encodings for x, y, and color from a dataframe for simple charts.
    Returns (x, y, color)."""
    if df is None or df.empty:
        return None, None, None

    # Try to find numeric and categorical columns
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

    x = None
    y = None
    color = None

    if len(categorical_cols) > 0 and len(numeric_cols) > 0:
        x = categorical_cols[0]
        y = numeric_cols[0]
        color = None
    elif len(numeric_cols) >= 2:
        x = numeric_cols[0]
        y = numeric_cols[1]
    elif len(numeric_cols) == 1:
        y = numeric_cols[0]
        if len(df.columns) > 1:
            x = [c for c in df.columns if c != y][0]
        else:
            x = df.columns[0]
    else:
        # No numeric columns; just pick first two for a count plot
        if len(df.columns) >= 2:
            x, y = df.columns[0], df.columns[1]
        elif len(df.columns) == 1:
            x = df.columns[0]
    return x, y, color


def build_altair_chart(chart_obj: Dict[str, Any], tables_index: Dict[str, pd.DataFrame], idx: int) -> Optional[alt.Chart]:
    """Build an Altair chart from a generic chart specification.
    The function supports minimal schemas commonly used in structured reports.

    Recognized structures on chart_obj:
    - type: one of [bar, line, area, pie, scatter, histogram]
    - title: str
    - data: list[dict] or {columns, rows} or dict column->list
    - data_table_ref: name of a table present in tables_index to use as data
    - encoding: {x: str or {field, type}, y: ..., color: ..., size: ..., tooltip: list[str or {field, type}]}
    - transform: not executed (Altair transforms could be added if needed)
    """
    chart_type = (chart_obj or {}).get("type", "bar").lower()

    # Resolve data source
    df = None
    if chart_obj is None:
        return None
    if "data" in chart_obj:
        df = coerce_dataframe(chart_obj.get("data"))
    elif "data_table_ref" in chart_obj:
        ref = chart_obj.get("data_table_ref")
        df = tables_index.get(ref)

    if df is None or df.empty:
        return None

    enc = chart_obj.get("encoding", {})

    # Helper to normalize enc fields
    def enc_channel(key: str) -> Optional[alt.Encoding]:
        val = enc.get(key)
        if val is None:
            return None
        if isinstance(val, str):
            return alt.Color(val) if key == "color" else alt.X(val) if key == "x" else alt.Y(val) if key == "y" else alt.Tooltip(val)
        if isinstance(val, dict):
            # Expect {field, type}
            field = val.get("field")
            vtype = val.get("type")
            if key == "x":
                return alt.X(field, type=vtype)
            if key == "y":
                return alt.Y(field, type=vtype)
            if key == "color":
                return alt.Color(field, type=vtype)
            if key == "size":
                return alt.Size(field, type=vtype)
            if key == "tooltip":
                # Tooltip may be a single field dict
                return alt.Tooltip(field, type=vtype)
        if isinstance(val, list):
            # Tooltips likely list of str or dict
            tooltips = []
            for t in val:
                if isinstance(t, str):
                    tooltips.append(alt.Tooltip(t))
                elif isinstance(t, dict):
                    tooltips.append(alt.Tooltip(t.get("field"), type=t.get("type")))
            # Return as a list; caller handles assignment
            return tooltips  # type: ignore
        return None

    x_enc = enc_channel("x")
    y_enc = enc_channel("y")
    color_enc = enc_channel("color")
    size_enc = enc_channel("size")
    tooltip_enc = enc_channel("tooltip")

    # If encodings not supplied, infer
    if x_enc is None and y_enc is None:
        x_name, y_name, _ = infer_encodings(df)
        if x_name:
            x_enc = alt.X(x_name)
        if y_name:
            y_enc = alt.Y(y_name)

    chart = alt.Chart(df).properties(title=chart_obj.get("title", f"Chart {idx+1}"))

    if chart_type == "bar":
        mark = chart.mark_bar()
        encs = {}
        if x_enc is not None:
            encs["x"] = x_enc
        if y_enc is not None:
            encs["y"] = y_enc
        if color_enc is not None:
            encs["color"] = color_enc
        if tooltip_enc is not None:
            encs["tooltip"] = tooltip_enc
        return mark.encode(**encs)

    if chart_type == "line":
        mark = chart.mark_line(point=True)
        encs = {}
        if x_enc is not None:
            encs["x"] = x_enc
        if y_enc is not None:
            encs["y"] = y_enc
        if color_enc is not None:
            encs["color"] = color_enc
        if tooltip_enc is not None:
            encs["tooltip"] = tooltip_enc
        return mark.encode(**encs)

    if chart_type == "area":
        mark = chart.mark_area()
        encs = {}
        if x_enc is not None:
            encs["x"] = x_enc
        if y_enc is not None:
            encs["y"] = y_enc
        if color_enc is not None:
            encs["color"] = color_enc
        if tooltip_enc is not None:
            encs["tooltip"] = tooltip_enc
        return mark.encode(**encs)

    if chart_type == "scatter":
        mark = chart.mark_circle()
        encs = {}
        if x_enc is not None:
            encs["x"] = x_enc
        if y_enc is not None:
            encs["y"] = y_enc
        if color_enc is not None:
            encs["color"] = color_enc
        if size_enc is not None:
            encs["size"] = size_enc
        if tooltip_enc is not None:
            encs["tooltip"] = tooltip_enc
        return mark.encode(**encs)

    if chart_type == "histogram":
        # If x is numeric, bin it
        x_name, y_name, _ = infer_encodings(df)
        if x_name is None:
            return None
        mark = chart.mark_bar()
        return mark.encode(x=alt.X(f"{x_name}:Q", bin=True), y=alt.Y("count()"))

    if chart_type == "pie":
        # Expect a categorical field and a numeric value field
        x_name, y_name, _ = infer_encodings(df)
        category_field = x_name
        value_field = y_name
        if category_field is None and len(df.columns) > 0:
            category_field = df.columns[0]
        if value_field is None and len(df.columns) > 1:
            value_field = [c for c in df.columns if c != category_field][0]
        if category_field is None or value_field is None:
            return None
        total = alt.Chart(df).mark_arc().encode(
            theta=alt.Theta(field=value_field, type="quantitative"),
            color=alt.Color(field=category_field, type="nominal"),
            tooltip=[category_field, value_field],
        ).properties(title=chart_obj.get("title", f"Chart {idx+1}"))
        return total

    # Default fallback: try bar
    mark = chart.mark_bar()
    encs = {}
    if x_enc is not None:
        encs["x"] = x_enc
    if y_enc is not None:
        encs["y"] = y_enc
    if color_enc is not None:
        encs["color"] = color_enc
    if tooltip_enc is not None:
        encs["tooltip"] = tooltip_enc
    return mark.encode(**encs) if encs else None


# ================================
# Streamlit App
# ================================

def main():
    st.set_page_config(page_title="AI Report Viewer", layout="wide")
    st.title("AI Report Viewer")

    st.caption("This app renders summaries, tables, and charts from an AI-generated JSON report.")

    # Sidebar: allow uploading a different report JSON (optional convenience)
    with st.sidebar:
        st.header("Report Source")
        uploaded = st.file_uploader("Upload report JSON", type=["json"])
        if uploaded is not None:
            try:
                report = json.load(uploaded)
            except Exception as e:
                st.error(f"Failed to parse uploaded JSON: {e}")
                report = DEFAULT_REPORT
        else:
            report = DEFAULT_REPORT

        st.download_button(
            label="Download current report JSON",
            data=json.dumps(report, indent=2),
            file_name="report.json",
            mime="application/json",
            use_container_width=True,
        )

    # Validate expected structure
    if not isinstance(report, dict):
        st.error("Invalid report structure: expected a JSON object.")
        st.stop()

    # Status and issues
    valid = bool(report.get("valid", False))
    issues: List[Dict[str, Any]] = report.get("issues") or []
    if valid:
        st.success("Report marked as valid.")
    else:
        st.warning("Report marked as invalid or incomplete.")
    if issues:
        st.subheader("Issues")
        for i, issue in enumerate(issues):
            severity = (issue.get("severity") or "info").lower()
            msg = issue.get("message") or ""
            code = issue.get("code") or ""
            line = f"[{severity.upper()}] {code}: {msg}" if code else f"[{severity.upper()}] {msg}"
            if severity == "error":
                st.error(line)
            elif severity == "warning":
                st.warning(line)
            else:
                st.info(line)

    # Summary
    summary = report.get("summary") or []
    st.subheader("Summary")
    if isinstance(summary, list):
        if len(summary) == 0:
            st.info("No summary provided.")
        else:
            for s in summary:
                st.markdown(f"- {s}")
    elif isinstance(summary, str):
        st.markdown(summary)
    else:
        st.info("Summary not available in a recognizable format.")

    # Tables
    tables = report.get("tables") or []
    st.subheader("Tables")
    if not tables:
        st.info("No tables available in this report.")
    tables_index: Dict[str, pd.DataFrame] = {}
    for i, tbl in enumerate(tables):
        # Accept table as {name, data: list[dict] or {columns, rows}}
        name = tbl.get("name") or f"Table {i+1}"
        df = None
        # Common shapes: tbl may have a directly usable data field, or be the data itself
        if isinstance(tbl, dict) and "data" in tbl:
            df = coerce_dataframe(tbl.get("data"))
        else:
            df = coerce_dataframe(tbl)
        if df is None:
            st.warning(f"Table '{name}' is present but could not be parsed into a dataframe.")
            with st.expander(f"Raw table object: {name}"):
                st.json(tbl)
            continue
        st.markdown(f"**{name}**")
        st.dataframe(df, use_container_width=True)
        tables_index[name] = df

    # Charts
    charts = report.get("charts") or []
    st.subheader("Charts")
    if not charts:
        st.info("No charts available in this report.")
    else:
        for i, chart_obj in enumerate(charts):
            title = (chart_obj or {}).get("title") or f"Chart {i+1}"
            st.markdown(f"**{title}**")
            chart = build_altair_chart(chart_obj, tables_index, i)
            if chart is None:
                st.warning("Unable to render this chart. Showing raw specification instead.")
                with st.expander("Chart specification"):
                    st.json(chart_obj)
            else:
                st.altair_chart(chart, use_container_width=True)

    # Echo / provenance details
    echo = report.get("echo") or {}
    if echo:
        st.subheader("Provenance and Query Details")
        intent = echo.get("intent")
        if intent:
            st.write(f"Intent: {intent}")
        used = echo.get("used") or {}
        if used:
            tables_used = used.get("tables") or []
            cols_used = used.get("columns") or []
            if tables_used:
                st.write("Tables used:")
                for t in tables_used:
                    st.markdown(f"- {t}")
            if cols_used:
                st.write("Columns used:")
                for c in cols_used:
                    st.markdown(f"- {c}")
        stats = echo.get("stats") or {}
        if stats:
            st.write("Stats:")
            for k, v in stats.items():
                st.markdown(f"- {k}: {v}")
        if "sql_present" in echo:
            st.write(f"SQL present: {bool(echo.get('sql_present'))}")

    st.divider()
    st.caption("Rendered with Streamlit, pandas, and Altair.")


if __name__ == "__main__":
    main()
