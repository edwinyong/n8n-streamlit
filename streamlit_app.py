import json
from typing import Dict, Any, List, Optional, Tuple

import streamlit as st
import pandas as pd
import altair as alt


# Embedded report JSON (exactly as provided)
REPORT_JSON_STR = """
{
  "valid": false,
  "issues": [
    {
      "code": "missing_column",
      "severity": "error",
      "message": "No typed time column in any table and no *_id join key across tables; cannot compare registered users and sales between 2025 Q1 and Q2."
    }
  ],
  "summary": [
    "Cannot compare registered users and sales between 2025 Q1 and Q2 due to missing time columns and join keys."
  ],
  "tables": [
    {
      "name": "Table",
      "columns": [
        "value"
      ],
      "rows": [
        [
          0
        ]
      ]
    }
  ],
  "charts": [],
  "echo": {
    "intent": "single_number",
    "used": {
      "tables": [
        ""
      ],
      "columns": []
    },
    "stats": {
      "elapsed": 0.001237
    },
    "sql_present": true
  }
}
"""


def parse_report(json_str: str) -> Dict[str, Any]:
    try:
        return json.loads(json_str)
    except Exception as e:
        st.error(f"Failed to parse embedded report JSON: {e}")
        return {}


def to_dataframe(table_obj: Dict[str, Any]) -> pd.DataFrame:
    cols = table_obj.get("columns", [])
    rows = table_obj.get("rows", [])
    try:
        df = pd.DataFrame(rows, columns=cols)
    except Exception:
        # Fallback: try to coerce rows to list of dicts
        if rows and isinstance(rows[0], dict):
            df = pd.DataFrame(rows)
        else:
            df = pd.DataFrame()
    return df


def infer_alt_type(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series) or pd.api.types.is_period_dtype(series) or pd.api.types.is_timedelta64_dtype(series):
        return "temporal"
    if pd.api.types.is_numeric_dtype(series):
        return "quantitative"
    return "nominal"


def pick_cat_num_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    cat_col = None
    num_col = None
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            cat_col = c
            break
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            num_col = c
            break
    return cat_col, num_col


def get_chart_dataframe(chart_obj: Dict[str, Any], tables_map: Dict[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
    # Priority: explicit data -> referenced table -> values
    data = chart_obj.get("data")
    if isinstance(data, dict):
        cols = data.get("columns")
        rows = data.get("rows")
        values = data.get("values")
        if cols is not None and rows is not None:
            try:
                return pd.DataFrame(rows, columns=cols)
            except Exception:
                pass
        if isinstance(values, list):
            try:
                return pd.DataFrame(values)
            except Exception:
                pass
        if isinstance(values, dict):
            try:
                return pd.DataFrame(list(values.items()), columns=["category", "value"])  # generic key/value
            except Exception:
                pass
    ref_table = chart_obj.get("table") or chart_obj.get("source")
    if isinstance(ref_table, str) and ref_table in tables_map:
        return tables_map[ref_table]
    # Direct values at root
    values = chart_obj.get("values")
    if isinstance(values, list):
        try:
            return pd.DataFrame(values)
        except Exception:
            return None
    if isinstance(values, dict):
        try:
            return pd.DataFrame(list(values.items()), columns=["category", "value"])  # generic key/value
        except Exception:
            return None
    return None


def build_altair_chart(chart_obj: Dict[str, Any], df: pd.DataFrame) -> Optional[alt.Chart]:
    if df is None or df.empty:
        return None

    ctype = (chart_obj.get("type") or chart_obj.get("kind") or chart_obj.get("chart")).lower() if chart_obj.get("type") or chart_obj.get("kind") or chart_obj.get("chart") else None

    # Determine encodings
    x_field = chart_obj.get("x")
    y_field = chart_obj.get("y")
    color_field = chart_obj.get("color") or chart_obj.get("series")
    size_field = chart_obj.get("size")
    theta_field = chart_obj.get("theta") or chart_obj.get("value")
    category_field = chart_obj.get("category") or chart_obj.get("label")

    # If x/y missing, attempt to infer
    if not x_field or (x_field not in df.columns and isinstance(x_field, str)):
        # choose first non-numeric for x; else first column
        x_field = None
        for c in df.columns:
            if not pd.api.types.is_numeric_dtype(df[c]):
                x_field = c
                break
        if x_field is None and len(df.columns) > 0:
            x_field = df.columns[0]
    if not y_field or (y_field not in df.columns and isinstance(y_field, str)):
        # choose first numeric for y; else second column if exists
        y_field = None
        for c in df.columns:
            if pd.api.types.is_numeric_dtype(df[c]):
                y_field = c
                break
        if y_field is None and len(df.columns) > 1:
            y_field = df.columns[1]

    # Chart dimensions
    width = chart_obj.get("width", 600)
    height = chart_obj.get("height", 400)
    title = chart_obj.get("title")

    # Build encodings with inferred types
    def enc_x():
        if x_field is None:
            return None
        return alt.X(x_field, type=infer_alt_type(df[x_field]))

    def enc_y():
        if y_field is None:
            return None
        return alt.Y(y_field, type=infer_alt_type(df[y_field]))

    def enc_color():
        if not color_field or color_field not in df.columns:
            return None
        return alt.Color(color_field, type=infer_alt_type(df[color_field]))

    def enc_size():
        if not size_field or size_field not in df.columns:
            return None
        return alt.Size(size_field, type=infer_alt_type(df[size_field]))

    if ctype == "pie":
        # Determine category and value columns
        if not category_field or category_field not in df.columns or not theta_field or theta_field not in df.columns:
            cat_guess, num_guess = pick_cat_num_columns(df)
            category_field = category_field if category_field in df.columns else cat_guess
            theta_field = theta_field if theta_field in df.columns else num_guess
        if not category_field or not theta_field:
            return None
        ch = (
            alt.Chart(df, title=title)
            .mark_arc()
            .encode(
                theta=alt.Theta(field=theta_field, type=infer_alt_type(df[theta_field])),
                color=alt.Color(field=category_field, type=infer_alt_type(df[category_field])),
                tooltip=[category_field, theta_field],
            )
            .properties(width=width, height=height)
        )
        return ch

    if ctype == "bar":
        ch = (
            alt.Chart(df, title=title)
            .mark_bar()
            .encode(
                x=enc_x(),
                y=enc_y(),
                color=enc_color(),
                tooltip=[c for c in [x_field, y_field, color_field] if c and c in df.columns],
            )
            .properties(width=width, height=height)
        )
        return ch

    if ctype == "line":
        ch = (
            alt.Chart(df, title=title)
            .mark_line(point=True)
            .encode(
                x=enc_x(),
                y=enc_y(),
                color=enc_color(),
                tooltip=[c for c in [x_field, y_field, color_field] if c and c in df.columns],
            )
            .properties(width=width, height=height)
        )
        return ch

    if ctype == "area":
        ch = (
            alt.Chart(df, title=title)
            .mark_area()
            .encode(
                x=enc_x(),
                y=enc_y(),
                color=enc_color(),
                tooltip=[c for c in [x_field, y_field, color_field] if c and c in df.columns],
            )
            .properties(width=width, height=height)
        )
        return ch

    if ctype == "scatter" or ctype == "point":
        ch = (
            alt.Chart(df, title=title)
            .mark_point()
            .encode(
                x=enc_x(),
                y=enc_y(),
                color=enc_color(),
                size=enc_size(),
                tooltip=[c for c in [x_field, y_field, color_field, size_field] if c and c in df.columns],
            )
            .properties(width=width, height=height)
        )
        return ch

    # Unknown chart type: attempt a sensible default (bar if we have numeric y)
    if y_field and pd.api.types.is_numeric_dtype(df[y_field]):
        ch = (
            alt.Chart(df, title=title or "Bar Chart")
            .mark_bar()
            .encode(
                x=enc_x(),
                y=enc_y(),
                color=enc_color(),
                tooltip=[c for c in [x_field, y_field, color_field] if c and c in df.columns],
            )
            .properties(width=width, height=height)
        )
        return ch

    return None


def main():
    st.set_page_config(page_title="AI Report App", layout="wide")
    st.title("AI Report Viewer")

    report = parse_report(REPORT_JSON_STR)

    # Sidebar: metadata
    with st.sidebar:
        st.header("Report Status")
        valid = report.get("valid", True)
        st.write("Valid:", valid)
        issues = report.get("issues", [])
        st.write("Issues:", len(issues))
        if not valid and issues:
            with st.expander("View Issues", expanded=True):
                for i, issue in enumerate(issues, start=1):
                    code = issue.get("code", "")
                    severity = issue.get("severity", "")
                    msg = issue.get("message", "")
                    st.markdown(f"- [{severity}] {code}: {msg}")

    # Summary
    st.subheader("Summary")
    summary = report.get("summary")
    if isinstance(summary, list) and summary:
        for line in summary:
            st.markdown(f"- {line}")
    elif isinstance(summary, str) and summary:
        st.markdown(summary)
    else:
        st.info("No summary provided.")

    # Tables
    st.subheader("Tables")
    tables = report.get("tables", [])
    tables_map: Dict[str, pd.DataFrame] = {}
    if tables:
        for t in tables:
            name = t.get("name") or "Table"
            df = to_dataframe(t)
            tables_map[name] = df
            st.markdown(f"### {name}")
            if df.empty:
                st.warning("Table is empty or could not be parsed.")
            st.dataframe(df, use_container_width=True)
    else:
        st.info("No tables provided.")

    # Charts
    st.subheader("Charts")
    charts = report.get("charts", [])
    if charts:
        for idx, ch_obj in enumerate(charts, start=1):
            title = ch_obj.get("title") or ch_obj.get("name") or f"Chart {idx}"
            st.markdown(f"### {title}")
            df_ch = get_chart_dataframe(ch_obj, tables_map)
            if df_ch is None or df_ch.empty:
                st.warning("Chart has no data to display.")
                continue
            try:
                ch = build_altair_chart(ch_obj, df_ch)
            except Exception as e:
                ch = None
                st.error(f"Failed to build chart: {e}")
            if ch is not None:
                st.altair_chart(ch, use_container_width=True)
            else:
                st.warning("Unsupported or malformed chart configuration.")
    else:
        st.info("No charts provided in this report.")

    # Debug info (optional)
    with st.expander("Raw Report JSON"):
        st.code(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
