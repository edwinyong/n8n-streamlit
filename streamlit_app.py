import json
from typing import Any, Dict, List, Optional

import altair as alt
import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# Embedded report JSON (provided by the user)
# ------------------------------------------------------------
REPORT_JSON = r'''{"valid":false,"issues":[{"code":"missing_column","severity":"error","message":"Safe fallback: users table lacks a registration timestamp for period bucketing, so a period-accurate users-vs-sales comparison for 2025 Q1 vs Q2 cannot be produced from the provided heads"}],"summary":["Cannot compare registered users and sales between 2025 Q1 and Q2 due to missing registration timestamp or sales period data."],"tables":[{"name":"Table","columns":["value"],"rows":[[0]]}],"charts":[],"echo":{"intent":"single_number","used":{"tables":[""],"columns":[]},"stats":{"elapsed":0.00126396},"sql_present":true}}'''

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def load_report_from_string(s: str) -> Dict[str, Any]:
    try:
        return json.loads(s)
    except Exception as e:
        st.error(f"Failed to parse JSON report: {e}")
        return {}


def df_from_columns_rows(obj: Dict[str, Any]) -> pd.DataFrame:
    columns = obj.get("columns") or []
    rows = obj.get("rows") or []
    try:
        if columns:
            return pd.DataFrame(rows, columns=columns)
        else:
            # Fallback if columns are missing
            return pd.DataFrame(rows)
    except Exception as e:
        st.warning(f"Could not build DataFrame from columns/rows: {e}")
        return pd.DataFrame()


def dataframe_from_unknown_data(data: Any) -> pd.DataFrame:
    # Try best-effort normalization to a DataFrame from potential chart data shapes
    if data is None:
        return pd.DataFrame()

    if isinstance(data, dict):
        # If columns/rows structure
        if "columns" in data and "rows" in data:
            return df_from_columns_rows(data)
        # If records array present
        if "records" in data and isinstance(data["records"], list):
            return pd.DataFrame(data["records"])
        # Dict of lists
        if all(isinstance(v, list) for v in data.values()):
            return pd.DataFrame(data)
        return pd.DataFrame([data])

    if isinstance(data, list):
        # List of dicts
        if len(data) > 0 and isinstance(data[0], dict):
            return pd.DataFrame(data)
        # List of lists
        return pd.DataFrame(data)

    # Fallback
    return pd.DataFrame([{"value": data}])


def guess_field(df: pd.DataFrame, prefer_numeric: bool = False) -> Optional[str]:
    if df is None or df.empty:
        return None
    cols = list(df.columns)
    if not cols:
        return None
    if prefer_numeric:
        for c in cols:
            if pd.api.types.is_numeric_dtype(df[c]):
                return c
    # fallback to first
    return cols[0]


def vega_type_for_series(s: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(s):
        return "T"
    if pd.api.types.is_numeric_dtype(s):
        return "Q"
    return "N"


def build_altair_chart(chart_obj: Dict[str, Any], df: pd.DataFrame) -> Optional[alt.Chart]:
    if df is None or df.empty:
        return None

    title = chart_obj.get("name") or chart_obj.get("title") or "Chart"
    chart_type = (chart_obj.get("type") or chart_obj.get("mark") or "").lower()
    encoding = chart_obj.get("encoding", {})

    # Extract fields from encoding or top-level fallbacks
    x_field = encoding.get("x") or chart_obj.get("x")
    y_field = encoding.get("y") or chart_obj.get("y")
    color_field = encoding.get("color") or chart_obj.get("color")
    theta_field = encoding.get("theta") or chart_obj.get("theta")
    size_field = encoding.get("size") or chart_obj.get("size")
    tooltip_field = encoding.get("tooltip") or chart_obj.get("tooltip")

    # Guess fields if missing
    if chart_type in ["bar", "bar_chart", "column"]:
        if x_field is None:
            x_field = guess_field(df, prefer_numeric=False)
        if y_field is None:
            # Prefer numeric for y
            y_field = guess_field(df, prefer_numeric=True)
            if y_field == x_field:
                # If only one column, fallback to count
                chart = alt.Chart(df, title=title).mark_bar().encode(
                    x=alt.X(f"{x_field}:{vega_type_for_series(df[x_field])}"),
                    y=alt.Y("count()")
                )
                if color_field and color_field in df.columns:
                    chart = chart.encode(color=alt.Color(f"{color_field}:{vega_type_for_series(df[color_field])}"))
                return chart
        x_enc = alt.X(f"{x_field}:{vega_type_for_series(df[x_field])}")
        y_enc = alt.Y(f"{y_field}:{vega_type_for_series(df[y_field])}")
        chart = alt.Chart(df, title=title).mark_bar().encode(x=x_enc, y=y_enc)
        if color_field and color_field in df.columns:
            chart = chart.encode(color=alt.Color(f"{color_field}:{vega_type_for_series(df[color_field])}"))
        if tooltip_field:
            if isinstance(tooltip_field, list):
                chart = chart.encode(tooltip=tooltip_field)
            elif isinstance(tooltip_field, str):
                chart = chart.encode(tooltip=[tooltip_field])
        return chart

    if chart_type in ["line", "line_chart"]:
        if x_field is None:
            x_field = guess_field(df, prefer_numeric=False)
        if y_field is None:
            y_field = guess_field(df, prefer_numeric=True)
        x_enc = alt.X(f"{x_field}:{vega_type_for_series(df[x_field])}")
        y_enc = alt.Y(f"{y_field}:{vega_type_for_series(df[y_field])}")
        chart = alt.Chart(df, title=title).mark_line(point=True).encode(x=x_enc, y=y_enc)
        if color_field and color_field in df.columns:
            chart = chart.encode(color=alt.Color(f"{color_field}:{vega_type_for_series(df[color_field])}"))
        if tooltip_field:
            if isinstance(tooltip_field, list):
                chart = chart.encode(tooltip=tooltip_field)
            elif isinstance(tooltip_field, str):
                chart = chart.encode(tooltip=[tooltip_field])
        return chart

    if chart_type in ["area"]:
        if x_field is None:
            x_field = guess_field(df, prefer_numeric=False)
        if y_field is None:
            y_field = guess_field(df, prefer_numeric=True)
        x_enc = alt.X(f"{x_field}:{vega_type_for_series(df[x_field])}")
        y_enc = alt.Y(f"{y_field}:{vega_type_for_series(df[y_field])}")
        chart = alt.Chart(df, title=title).mark_area().encode(x=x_enc, y=y_enc)
        if color_field and color_field in df.columns:
            chart = chart.encode(color=alt.Color(f"{color_field}:{vega_type_for_series(df[color_field])}"))
        return chart

    if chart_type in ["scatter", "point"]:
        if x_field is None:
            x_field = guess_field(df, prefer_numeric=True)
        if y_field is None:
            # Choose a different numeric column for y if possible
            numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            if len(numeric_cols) >= 2:
                y_field = numeric_cols[1] if numeric_cols[0] == x_field else numeric_cols[0]
            else:
                y_field = guess_field(df, prefer_numeric=True)
        chart = alt.Chart(df, title=title).mark_point().encode(
            x=alt.X(f"{x_field}:{vega_type_for_series(df[x_field])}"),
            y=alt.Y(f"{y_field}:{vega_type_for_series(df[y_field])}")
        )
        if color_field and color_field in df.columns:
            chart = chart.encode(color=alt.Color(f"{color_field}:{vega_type_for_series(df[color_field])}"))
        if size_field and size_field in df.columns:
            chart = chart.encode(size=alt.Size(f"{size_field}:{vega_type_for_series(df[size_field])}"))
        return chart

    if chart_type in ["pie", "donut", "arc"]:
        # Altair pie chart via mark_arc with theta and color
        if theta_field is None:
            # Prefer numeric for theta
            theta_field = guess_field(df, prefer_numeric=True)
        if color_field is None:
            # Category/color
            # Try a non-numeric column; fallback to first column
            cat_col = None
            for c in df.columns:
                if not pd.api.types.is_numeric_dtype(df[c]):
                    cat_col = c
                    break
            color_field = cat_col or guess_field(df, prefer_numeric=False)
        inner_radius = 0 if chart_type == "pie" else 50
        chart = alt.Chart(df, title=title).mark_arc(innerRadius=inner_radius).encode(
            theta=alt.Theta(f"{theta_field}:{vega_type_for_series(df[theta_field])}", stack=True),
            color=alt.Color(f"{color_field}:{vega_type_for_series(df[color_field])}")
        )
        return chart

    # Default fallback: bar count by first column
    first_col = guess_field(df, prefer_numeric=False)
    if first_col is None:
        return None
    return alt.Chart(df, title=title).mark_bar().encode(
        x=alt.X(f"{first_col}:{vega_type_for_series(df[first_col])}"),
        y=alt.Y("count()")
    )


# ------------------------------------------------------------
# Streamlit App UI
# ------------------------------------------------------------

def main():
    st.set_page_config(page_title="AI Report App", layout="wide")
    st.title("AI Report App")
    st.caption("Generated from a JSON report; tables rendered with st.dataframe and charts with Altair.")

    # Sidebar: allow optional JSON override via uploader or text input
    with st.sidebar:
        st.header("Report Source")
        mode = st.radio("Load report from:", ["Embedded JSON", "Upload JSON file", "Paste JSON"], index=0)
        uploaded_text = None
        if mode == "Upload JSON file":
            upl = st.file_uploader("Choose a JSON file", type=["json"])
            if upl is not None:
                uploaded_text = upl.read().decode("utf-8")
        elif mode == "Paste JSON":
            uploaded_text = st.text_area("Paste JSON here", height=200)

    report = load_report_from_string(uploaded_text if uploaded_text else REPORT_JSON)

    if not report:
        st.stop()

    # Validity and issues
    valid = report.get("valid", True)
    issues = report.get("issues", []) or []

    cols = st.columns(2)
    with cols[0]:
        st.subheader("Report Status")
        st.metric(label="Valid", value="Yes" if valid else "No")
    with cols[1]:
        st.subheader("Generation Stats")
        echo = report.get("echo", {})
        stats = echo.get("stats", {}) if isinstance(echo, dict) else {}
        elapsed = stats.get("elapsed")
        st.write({"intent": echo.get("intent"), "elapsed": elapsed, "sql_present": echo.get("sql_present")})

    if issues:
        st.subheader("Issues")
        for i, issue in enumerate(issues, start=1):
            code = issue.get("code", "")
            severity = issue.get("severity", "")
            message = issue.get("message", "")
            st.write(f"{i}. [{severity}] {code}: {message}")

    # Summary
    st.header("Summary")
    summary = report.get("summary", []) or []
    if isinstance(summary, list):
        for s in summary:
            st.markdown(f"- {s}")
    elif isinstance(summary, str):
        st.markdown(summary)
    else:
        st.info("No summary available.")

    # Tables
    st.header("Tables")
    tables = report.get("tables", []) or []
    if len(tables) == 0:
        st.info("No tables provided in the report.")
    else:
        for idx, tbl in enumerate(tables, start=1):
            name = tbl.get("name") or f"Table {idx}"
            df = df_from_columns_rows(tbl)
            st.subheader(name)
            st.dataframe(df, use_container_width=True)

    # Charts
    st.header("Charts")
    charts = report.get("charts", []) or []
    if len(charts) == 0:
        st.info("No charts provided in the report.")
    else:
        for idx, ch in enumerate(charts, start=1):
            st.subheader(ch.get("name") or ch.get("title") or f"Chart {idx}")
            # Normalize data for the chart
            data = ch.get("data")
            if data is None and ("columns" in ch or "rows" in ch):
                # Some charts might inline columns/rows
                data = {"columns": ch.get("columns", []), "rows": ch.get("rows", [])}
            df = dataframe_from_unknown_data(data)
            if df is None or df.empty:
                st.warning("Chart has no data to render.")
                continue
            try:
                chart = build_altair_chart(ch, df)
                if chart is None:
                    st.warning("Unsupported or empty chart; displaying data below.")
                    st.dataframe(df, use_container_width=True)
                else:
                    st.altair_chart(chart.interactive(), use_container_width=True)
            except Exception as e:
                st.error(f"Failed to render chart: {e}")
                st.dataframe(df, use_container_width=True)

    # Echo / Metadata
    st.header("Echo / Metadata")
    st.json(report.get("echo", {}))

    # Raw JSON
    with st.expander("Raw JSON Report"):
        try:
            st.code(json.dumps(report, indent=2), language="json")
        except Exception:
            st.code(str(report), language="json")


if __name__ == "__main__":
    main()
