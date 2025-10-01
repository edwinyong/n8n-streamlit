import streamlit as st
import pandas as pd
import altair as alt
from typing import List, Dict, Any

st.set_page_config(page_title="Sales Trend Report", layout="wide")

# Embedded report JSON (converted to Python dict)
report: Dict[str, Any] = {
    "valid": True,
    "issues": [],
    "summary": [
        "Monthly total sales amount is shown for the past 12 months.",
        "Sales peaked in November 2024 (RM194,247.50) and August 2025 saw the lowest sales (RM18,826.01).",
        "Recent months show significant fluctuation in sales amounts."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["bucket", "value"],
            "rows": [
                ["2024-10-01", 126693.1599999974],
                ["2024-11-01", 194247.4999999981],
                ["2024-12-01", 127829.75999999963],
                ["2025-01-01", 119626.18999999885],
                ["2025-02-01", 181249.12999999718],
                ["2025-03-01", 162391.27999999782],
                ["2025-04-01", 122584.14999999863],
                ["2025-05-01", 110036.75999999886],
                ["2025-06-01", 138457.01999999848],
                ["2025-07-01", 101228.30999999943],
                ["2025-08-01", 90910.37999999947],
                ["2025-09-01", 18826.00999999998]
            ]
        }
    ],
    "charts": [
        {
            "id": "main",
            "type": "line",
            "spec": {
                "xKey": "bucket",
                "yKey": "value",
                "series": [
                    {"name": "Total Sales Amount", "yKey": "value"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "trend",
        "used": {
            "tables": ["Haleon Rewards User Performance 110925 SKUs"],
            "columns": ["Upload_Date", "Total Sales Amount"]
        },
        "stats": {"elapsed": 0.00774957},
        "sql_present": True
    }
}

# Helper functions

def make_dataframe(table_obj: Dict[str, Any]) -> pd.DataFrame:
    cols = table_obj.get("columns", [])
    rows = table_obj.get("rows", [])
    df = pd.DataFrame(rows, columns=cols)
    return df


def maybe_parse_datetime(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col in df.columns:
        # Try parsing to datetime; keep original if mostly invalid
        parsed = pd.to_datetime(df[col], errors="coerce")
        non_null_ratio = parsed.notna().mean() if len(parsed) > 0 else 0
        if non_null_ratio > 0.7:
            df = df.copy()
            df[col] = parsed
    return df


def render_line_chart(df: pd.DataFrame, x_key: str, y_key: str, title: str = ""):
    df_local = df.copy()
    # Try to parse time on x-axis
    df_local = maybe_parse_datetime(df_local, x_key)
    # Sort by x if temporal
    if pd.api.types.is_datetime64_any_dtype(df_local[x_key]):
        df_local = df_local.sort_values(by=x_key)
        x_encoding = alt.X(f"{x_key}:T", title=x_key, axis=alt.Axis(format="%b %Y"))
    else:
        x_encoding = alt.X(f"{x_key}:O", title=x_key)

    chart = (
        alt.Chart(df_local)
        .mark_line(point=True)
        .encode(
            x=x_encoding,
            y=alt.Y(f"{y_key}:Q", title=y_key, axis=alt.Axis(format=",.2f")),
            tooltip=[
                alt.Tooltip(f"{x_key}", title=x_key),
                alt.Tooltip(f"{y_key}:Q", title=y_key, format=",.2f"),
            ],
            color=alt.value("#1f77b4"),
        )
    )

    if title:
        chart = chart.properties(title=title)

    st.altair_chart(chart.interactive(), use_container_width=True)


def render_chart(chart_obj: Dict[str, Any], tables: List[Dict[str, Any]]):
    ctype = chart_obj.get("type", "").lower()
    spec = chart_obj.get("spec", {})

    # Default to the first table if no explicit mapping is provided
    base_df = make_dataframe(tables[0]) if tables else pd.DataFrame()

    if base_df.empty:
        st.info("No data available for chart rendering.")
        return

    # Extract keys
    x_key = spec.get("xKey")
    y_key = spec.get("yKey")

    # Fallback for series list
    series = spec.get("series", [])
    if not y_key and series:
        # Use the first series yKey if present
        y_key = series[0].get("yKey")

    if not x_key or not y_key or x_key not in base_df.columns or y_key not in base_df.columns:
        st.warning("Unable to render chart: xKey/yKey not found in data.")
        return

    title = ""
    if series and isinstance(series, list) and "name" in series[0]:
        title = series[0]["name"]

    if ctype == "line":
        render_line_chart(base_df, x_key, y_key, title=title)
    elif ctype == "bar":
        df_local = maybe_parse_datetime(base_df.copy(), x_key)
        if pd.api.types.is_datetime64_any_dtype(df_local[x_key]):
            df_local = df_local.sort_values(by=x_key)
            x_enc = alt.X(f"{x_key}:T", axis=alt.Axis(format="%b %Y"))
        else:
            x_enc = alt.X(f"{x_key}:O")
        chart = (
            alt.Chart(df_local)
            .mark_bar()
            .encode(
                x=x_enc,
                y=alt.Y(f"{y_key}:Q", axis=alt.Axis(format=",.2f")),
                tooltip=[
                    alt.Tooltip(f"{x_key}", title=x_key),
                    alt.Tooltip(f"{y_key}:Q", title=y_key, format=",.2f"),
                ],
                color=alt.value("#1f77b4"),
            )
        )
        if title:
            chart = chart.properties(title=title)
        st.altair_chart(chart.interactive(), use_container_width=True)
    elif ctype == "pie":
        # Pie chart expects a category and a value; use x_key as category
        chart = (
            alt.Chart(base_df)
            .mark_arc()
            .encode(
                theta=alt.Theta(f"{y_key}:Q"),
                color=alt.Color(f"{x_key}:N"),
                tooltip=[
                    alt.Tooltip(f"{x_key}:N", title=x_key),
                    alt.Tooltip(f"{y_key}:Q", title=y_key, format=",.2f"),
                ],
            )
        )
        if title:
            chart = chart.properties(title=title)
        st.altair_chart(chart.interactive(), use_container_width=True)
    else:
        st.info(f"Chart type '{ctype}' not recognized. Supported types: line, bar, pie.")


# UI rendering
st.title("Sales Trend Report")

# Summary
st.header("Summary")
summary_items = report.get("summary", [])
if summary_items:
    for item in summary_items:
        st.markdown(f"- {item}")
else:
    st.write("No summary provided.")

# Tables
st.header("Tables")
if report.get("tables"):
    for idx, table_obj in enumerate(report["tables" ]):
        name = table_obj.get("name", f"Table {idx+1}")
        st.subheader(name)
        df = make_dataframe(table_obj)
        st.dataframe(df, use_container_width=True)
else:
    st.write("No tables available.")

# Charts
st.header("Charts")
if report.get("charts"):
    for chart_obj in report["charts"]:
        chart_id = chart_obj.get("id", "")
        if chart_id:
            st.subheader(f"Chart: {chart_id}")
        render_chart(chart_obj, report.get("tables", []))
else:
    st.write("No charts available.")

# Optional: show issues if any
if report.get("issues"):
    st.header("Issues")
    if len(report["issues"]) == 0:
        st.write("No issues detected.")
    else:
        for issue in report["issues"]:
            st.markdown(f"- {issue}")

# Footer
st.caption("App generated from provided JSON report. Uses Streamlit, Pandas, and Altair.")
