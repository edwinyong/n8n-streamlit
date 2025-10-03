import streamlit as st
import pandas as pd
import altair as alt
from typing import List, Dict, Any

# Embedded report data (from JSON input)
REPORT: Dict[str, Any] = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered users in 2025 Q2 decreased to 3,826 from 4,998 in Q1 (-23.43%).",
        "Total sales in 2025 Q2 dropped to 371,077.93 from 461,543.37 in Q1 (-19.63%).",
        "Both registered user count and sales performance were lower in Q2 compared to Q1 2025."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["period", "registered_users", "total_sales"],
            "rows": [["Q1", "4998", 461543.3700000002], ["Q2", "3826", 371077.93]]
        }
    ],
    "charts": [
        {
            "id": "main",
            "type": "groupedBar",
            "spec": {
                "xKey": "period",
                "yKey": "",
                "series": [
                    {"name": "Registered Users", "yKey": "registered_users"},
                    {"name": "Total Sales", "yKey": "total_sales"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "comparison_totals",
        "used": {
            "tables": ["`Haleon_Rewards_User_Performance_110925_list`"],
            "columns": ['"user_id"', '"Total Sales Amount"', '"Upload_Date"']
        },
        "stats": {"elapsed": 0.04843408},
        "sql_present": True
    }
}

# Streamlit page config
st.set_page_config(page_title="AI Report Dashboard", layout="wide")
alt.data_transformers.disable_max_rows()

st.title("AI Report Dashboard")

# Summary section
st.subheader("Summary")
if REPORT.get("summary"):
    summary_md = "\n".join([f"- {line}" for line in REPORT["summary"]])
    st.markdown(summary_md)
else:
    st.info("No summary provided.")

# Helper: build DataFrame from table descriptor
def table_to_df(table: Dict[str, Any]) -> pd.DataFrame:
    cols = table.get("columns", [])
    rows = table.get("rows", [])
    df = pd.DataFrame(rows, columns=cols)
    return df

# Helper: safely coerce selected columns to numeric
def coerce_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# Tables section
st.subheader("Tables")
all_tables = REPORT.get("tables", [])

tables_dataframes: List[pd.DataFrame] = []
if all_tables:
    for idx, table in enumerate(all_tables, start=1):
        name = table.get("name") or f"Table {idx}"
        df = table_to_df(table)
        tables_dataframes.append(df)
        st.markdown(f"**{name}**")
        st.dataframe(df, use_container_width=True)
else:
    st.info("No tables available in report.")

# Choose a default DataFrame for charts (first table if exists)
default_df = tables_dataframes[0] if tables_dataframes else pd.DataFrame()

# Chart builders

def build_grouped_bar_chart(df: pd.DataFrame, spec: Dict[str, Any]) -> alt.Chart:
    x_key = spec.get("xKey")
    series = spec.get("series", [])
    if df.empty or not x_key or not series:
        return alt.Chart(pd.DataFrame({"message": ["No data"]})).mark_text().encode(text="message")

    # Ensure numeric columns for all yKeys
    y_keys = [s.get("yKey") for s in series if s.get("yKey")]
    df_num = coerce_numeric(df, y_keys)

    # Melt to long format for grouped bars
    df_long = df_num.melt(id_vars=[x_key], value_vars=y_keys, var_name="Metric", value_name="Value")

    # Map internal yKey to friendly series names
    name_map = {s["yKey"]: s.get("name", s["yKey"]) for s in series if s.get("yKey")}
    df_long["Series"] = df_long["Metric"].map(name_map).fillna(df_long["Metric"])

    chart = (
        alt.Chart(df_long)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_key}:N", title=x_key),
            y=alt.Y("Value:Q", title="Value"),
            color=alt.Color("Series:N", title="Metric"),
            xOffset="Series:N",
            tooltip=[x_key + ":N", "Series:N", alt.Tooltip("Value:Q", format=",")],
        )
    )
    return chart


def build_bar_chart(df: pd.DataFrame, spec: Dict[str, Any]) -> alt.Chart:
    # Fallback generic single-series bar chart
    x_key = spec.get("xKey")
    y_key = spec.get("yKey")
    if df.empty or not x_key or not y_key:
        return alt.Chart(pd.DataFrame({"message": ["No data"]})).mark_text().encode(text="message")
    df_num = coerce_numeric(df, [y_key])
    chart = (
        alt.Chart(df_num)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_key}:N", title=x_key),
            y=alt.Y(f"{y_key}:Q", title=y_key),
            tooltip=[x_key + ":N", alt.Tooltip(f"{y_key}:Q", format=",")],
        )
    )
    return chart


def build_pie_chart(df: pd.DataFrame, spec: Dict[str, Any]) -> alt.Chart:
    # Optional support if present in other reports
    category = spec.get("category") or spec.get("xKey")
    value = spec.get("value") or spec.get("yKey")
    if df.empty or not category or not value:
        return alt.Chart(pd.DataFrame({"message": ["No data"]})).mark_text().encode(text="message")
    df_num = coerce_numeric(df, [value])
    chart = (
        alt.Chart(df_num)
        .mark_arc(outerRadius=100)
        .encode(
            theta=alt.Theta(f"{value}:Q", stack=True),
            color=alt.Color(f"{category}:N", legend=True, title=category),
            tooltip=[f"{category}:N", alt.Tooltip(f"{value}:Q", format=",")],
        )
    )
    return chart


# Charts section
st.subheader("Charts")
charts = REPORT.get("charts", [])
if charts and not default_df.empty:
    for chart_obj in charts:
        cid = chart_obj.get("id", "chart")
        ctype = (chart_obj.get("type") or "").lower()
        spec = chart_obj.get("spec", {})

        st.markdown(f"**Chart: {cid} ({ctype})**")

        if ctype in ("groupedbar", "grouped_bar"):
            chart = build_grouped_bar_chart(default_df, spec)
        elif ctype == "bar":
            chart = build_bar_chart(default_df, spec)
        elif ctype == "pie":
            chart = build_pie_chart(default_df, spec)
        else:
            # Unknown type: try a safe fallback
            chart = build_grouped_bar_chart(default_df, spec) if spec.get("series") else build_bar_chart(default_df, spec)

        st.altair_chart(chart.properties(width="container", height=360), use_container_width=True)
else:
    st.info("No charts available or no data to visualize.")

# Optional: show raw report metadata for transparency/debugging
with st.expander("Report metadata (raw)"):
    st.json(REPORT)
