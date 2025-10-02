import json
from typing import Dict, List, Optional

import streamlit as st
import pandas as pd
import altair as alt

# Disable row limit for Altair safety
alt.data_transformers.disable_max_rows()

# -----------------------------------------------------------------------------
# Embedded report JSON (provided by the user)
# -----------------------------------------------------------------------------
raw_report_json = r'''{"valid":true,"issues":[],"summary":["Registered users and total sales remained exactly the same in 2025 Q2 compared to 2025 Q1.","No improvement or decline in performance was observed between the two periods."],"tables":[{"name":"Table","columns":["period","registered_users","total_sales"],"rows":[["2025 Q2","36831","1843315.8899999924"],["2025 Q1","36831","1843315.8899999924"]]}],"charts":[{"id":"main","type":"kpi","spec":{"xKey":"period","yKey":"total_sales","series":[{"name":"Total Sales","yKey":"total_sales"}]}},{"id":"main_2","type":"kpi","spec":{"xKey":"period","yKey":"registered_users","series":[{"name":"Registered Users","yKey":"registered_users"}]}}],"echo":{"intent":"comparison_totals","used":{"tables":["Haleon_Rewards_User_Performance_110925_list"],"columns":["user_id","Total Sales"]},"stats":{"elapsed":0.022840919},"sql_present":true}}'''

report = json.loads(raw_report_json)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def to_dataframe(table_obj: Dict) -> pd.DataFrame:
    cols = table_obj.get("columns", [])
    rows = table_obj.get("rows", [])
    df = pd.DataFrame(rows, columns=cols)
    # Attempt to convert numeric-like columns to numeric, while leaving text intact
    for c in df.columns:
        # errors='ignore' will convert if possible; otherwise it leaves as original type
        df[c] = pd.to_numeric(df[c], errors='ignore')
    return df


def find_df_with_columns(dfs: Dict[str, pd.DataFrame], required_cols: List[str]) -> Optional[pd.DataFrame]:
    required = set([c for c in required_cols if c is not None])
    for name, df in dfs.items():
        if required.issubset(set(df.columns)):
            return df
    return None


def pretty_title(text: str) -> str:
    if not text:
        return ""
    return text.replace("_", " ").title()


def y_axis_format_for_field(field: str) -> str:
    # Apply compact number format for large numbers
    # Altair/Vega format tokens: ~s for SI-prefix
    # We'll default to ~s; adjust if needed per field name
    return "~s"


def kpi_as_bar_chart(df: pd.DataFrame, x_key: str, y_key: str, title: str) -> alt.Chart:
    y_fmt = y_axis_format_for_field(y_key)
    base = alt.Chart(df).encode(
        x=alt.X(f"{x_key}:N", title=pretty_title(x_key)),
        y=alt.Y(f"{y_key}:Q", title=pretty_title(y_key), axis=alt.Axis(format=y_fmt)),
        tooltip=[x_key, alt.Tooltip(y_key, format=y_fmt)],
    )

    bars = base.mark_bar(color="#4C78A8")
    text = base.mark_text(dy=-5, color="#333", fontSize=12).encode(
        text=alt.Text(f"{y_key}:Q", format=y_fmt)
    )

    chart = (bars + text).properties(title=title, width="container", height=320)
    return chart


def build_chart(chart_def: Dict, table_dfs: Dict[str, pd.DataFrame]) -> Optional[alt.Chart]:
    ctype = chart_def.get("type", "bar")
    spec = chart_def.get("spec", {})
    x_key = spec.get("xKey")
    y_key = spec.get("yKey")

    # Find a DataFrame that has the needed columns
    df = None
    if x_key and y_key:
        df = find_df_with_columns(table_dfs, [x_key, y_key])
    elif x_key and spec.get("series"):
        # Try to infer y from first series
        series = spec.get("series", [])
        if series and isinstance(series, list) and isinstance(series[0], dict):
            y_key = series[0].get("yKey")
            if y_key:
                df = find_df_with_columns(table_dfs, [x_key, y_key])
    else:
        # If missing keys, we cannot chart
        return None

    if df is None:
        return None

    title = pretty_title(chart_def.get("id") or ctype)

    # Map chart types to Altair
    if ctype == "kpi":
        # Render KPI as a bar chart comparing the KPI value(s) across the x dimension
        return kpi_as_bar_chart(df, x_key, y_key, title)

    y_fmt = y_axis_format_for_field(y_key)

    if ctype == "bar":
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X(f"{x_key}:N", title=pretty_title(x_key)),
                y=alt.Y(f"{y_key}:Q", title=pretty_title(y_key), axis=alt.Axis(format=y_fmt)),
                tooltip=[x_key, alt.Tooltip(y_key, format=y_fmt)],
            )
            .properties(title=title, width="container", height=320)
        )
        return chart

    if ctype == "line":
        chart = (
            alt.Chart(df)
            .mark_line(point=True)
            .encode(
                x=alt.X(f"{x_key}:N", title=pretty_title(x_key)),
                y=alt.Y(f"{y_key}:Q", title=pretty_title(y_key), axis=alt.Axis(format=y_fmt)),
                tooltip=[x_key, alt.Tooltip(y_key, format=y_fmt)],
            )
            .properties(title=title, width="container", height=320)
        )
        return chart

    if ctype == "area":
        chart = (
            alt.Chart(df)
            .mark_area()
            .encode(
                x=alt.X(f"{x_key}:N", title=pretty_title(x_key)),
                y=alt.Y(f"{y_key}:Q", title=pretty_title(y_key), axis=alt.Axis(format=y_fmt)),
                tooltip=[x_key, alt.Tooltip(y_key, format=y_fmt)],
            )
            .properties(title=title, width="container", height=320)
        )
        return chart

    if ctype == "scatter":
        chart = (
            alt.Chart(df)
            .mark_circle(size=80)
            .encode(
                x=alt.X(f"{x_key}:Q", title=pretty_title(x_key)),
                y=alt.Y(f"{y_key}:Q", title=pretty_title(y_key), axis=alt.Axis(format=y_fmt)),
                tooltip=[x_key, alt.Tooltip(y_key, format=y_fmt)],
                color=alt.value("#4C78A8"),
            )
            .properties(title=title, width="container", height=320)
        )
        return chart

    if ctype == "pie":
        # For pie: x_key is the category, y_key is the value
        chart = (
            alt.Chart(df)
            .mark_arc(innerRadius=0)
            .encode(
                theta=alt.Theta(f"{y_key}:Q", stack=True),
                color=alt.Color(f"{x_key}:N", legend=True, title=pretty_title(x_key)),
                tooltip=[x_key, alt.Tooltip(y_key, format=y_fmt)],
            )
            .properties(title=title, width=320, height=320)
        )
        return chart

    # Default fallback: bar
    return kpi_as_bar_chart(df, x_key, y_key, title)


# -----------------------------------------------------------------------------
# Streamlit App UI
# -----------------------------------------------------------------------------

st.set_page_config(page_title="AI Report Viewer", layout="wide")

st.title("AI Report Viewer")
intent = report.get("echo", {}).get("intent")
if intent:
    st.caption(f"Intent: {intent}")

# Validation and issues
if not report.get("valid", True):
    st.error("Report is marked invalid.")
issues = report.get("issues", [])
if issues:
    with st.expander("Issues detected in report"):
        for i, iss in enumerate(issues, 1):
            st.write(f"{i}. {iss}")

# Summary section
st.header("Summary")
summary_items = report.get("summary", [])
if summary_items:
    for s in summary_items:
        st.markdown(f"- {s}")
else:
    st.write("No summary provided.")

# Tables section
st.header("Tables")
table_defs = report.get("tables", [])
all_tables: Dict[str, pd.DataFrame] = {}

if not table_defs:
    st.write("No tables available in the report.")
else:
    for idx, t in enumerate(table_defs, start=1):
        name = t.get("name") or f"Table {idx}"
        df = to_dataframe(t)
        all_tables[name] = df
        st.subheader(name)
        st.dataframe(df, use_container_width=True)

# Charts section
st.header("Charts")
chart_defs = report.get("charts", [])

if not chart_defs:
    st.write("No charts available in the report.")
else:
    # Note to users on KPI representation
    if any(c.get("type") == "kpi" for c in chart_defs):
        st.caption("Note: KPI charts are visualized as Altair bar charts over the specified x-axis.")

    for ch in chart_defs:
        chart_obj = build_chart(ch, all_tables)
        chart_title = ch.get("id") or ch.get("type", "chart")
        if chart_obj is None:
            st.warning(f"Unable to render chart: {chart_title} (missing data columns)")
        else:
            st.altair_chart(chart_obj, use_container_width=True)

# Footer / metadata
with st.expander("Report metadata"):
    st.json({
        "intent": report.get("echo", {}).get("intent"),
        "used": report.get("echo", {}).get("used"),
        "stats": report.get("echo", {}).get("stats"),
        "sql_present": report.get("echo", {}).get("sql_present"),
    })
