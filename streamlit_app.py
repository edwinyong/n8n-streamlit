import streamlit as st
import pandas as pd
import altair as alt
from typing import Dict, Any, List

# Embedded report JSON provided by the user
REPORT: Dict[str, Any] = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered users decreased from 4,998 in Q1 to 3,826 in Q2 2025 (-23.43%).",
        "Total sales dropped from 461,543.37 in Q1 to 371,077.93 in Q2 2025 (-19.61%).",
        "Total units sold declined from 19,603 in Q1 to 15,482 in Q2 2025 (-21.01%).",
        "Performance in Q2 2025 is lower than in Q1 2025 across all key metrics."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": [
                "period",
                "registered_users",
                "total_sales",
                "total_units"
            ],
            "rows": [
                ["Q2", "3826", 371077.93, "15482"],
                ["Q1", "4998", 461543.3700000002, "19603"]
            ]
        }
    ],
    "charts": [
        {
            "id": "main",
            "type": "bar",
            "spec": {
                "xKey": "period",
                "yKey": "total_sales",
                "series": [
                    {"name": "Registered Users", "yKey": "registered_users"},
                    {"name": "Total Sales", "yKey": "total_sales"},
                    {"name": "Total Units", "yKey": "total_units"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "comparison_totals",
        "used": {
            "tables": [
                "`Haleon_Rewards_User_Performance_110925_list`",
                "`Haleon_Rewards_User_Performance_110925_SKUs`"
            ],
            "columns": [
                "\"user_id\"",
                "\"comuserid\"",
                "\"Upload_Date\"",
                "\"Total Sales Amount\"",
                "\"Total_Purchase_Units\""
            ]
        },
        "stats": {"elapsed": 0.081987},
        "sql_present": True
    }
}


def dataframe_from_table(table_obj: Dict[str, Any]) -> pd.DataFrame:
    columns: List[str] = table_obj.get("columns", [])
    rows: List[List[Any]] = table_obj.get("rows", [])
    df = pd.DataFrame(rows, columns=columns)
    return df


def coerce_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def build_bar_chart(df: pd.DataFrame, chart_obj: Dict[str, Any]) -> alt.Chart | None:
    spec = chart_obj.get("spec", {})
    x_key = spec.get("xKey")
    series = spec.get("series", [])

    if not x_key or not series:
        return None

    value_cols = [s.get("yKey") for s in series if s.get("yKey")]
    # Ensure numeric types for value columns
    df_num = df.copy()
    df_num = coerce_numeric(df_num, value_cols)

    # Melt to long format for multi-series plotting
    long_df = df_num.melt(
        id_vars=[x_key],
        value_vars=value_cols,
        var_name="metric_key",
        value_name="value"
    )

    # Map metric keys to display names
    name_map = {s["yKey"]: s.get("name", s["yKey"]) for s in series if s.get("yKey")}
    long_df["metric"] = long_df["metric_key"].map(name_map).fillna(long_df["metric_key"])

    chart_title = chart_obj.get("id", "") or "Bar Chart"

    chart = (
        alt.Chart(long_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_key}:N", title=x_key),
            y=alt.Y("value:Q", title="Value"),
            color=alt.Color("metric:N", title="Metric"),
            tooltip=[
                alt.Tooltip(f"{x_key}:N", title=x_key),
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip("value:Q", title="Value", format=",")
            ],
        )
        .properties(title=chart_title)
    )

    return chart


def build_pie_chart(df: pd.DataFrame, chart_obj: Dict[str, Any]) -> alt.Chart | None:
    # Generic pie chart builder (not used by current input, included for completeness)
    spec = chart_obj.get("spec", {})
    category_key = spec.get("categoryKey") or spec.get("xKey") or spec.get("labelKey")
    value_key = spec.get("valueKey") or spec.get("yKey")

    if not category_key or not value_key:
        return None

    df_num = df.copy()
    df_num[value_key] = pd.to_numeric(df_num[value_key], errors="coerce")

    chart_title = chart_obj.get("id", "") or "Pie Chart"

    chart = (
        alt.Chart(df_num)
        .mark_arc()
        .encode(
            theta=alt.Theta(f"{value_key}:Q", title=value_key),
            color=alt.Color(f"{category_key}:N", title=category_key),
            tooltip=[
                alt.Tooltip(f"{category_key}:N", title=category_key),
                alt.Tooltip(f"{value_key}:Q", title=value_key, format=",")
            ],
        )
        .properties(title=chart_title)
    )

    return chart


def render_chart(chart_obj: Dict[str, Any], dataframes_by_name: Dict[str, pd.DataFrame]) -> None:
    if len(dataframes_by_name) == 0:
        st.info("No data available for charts.")
        return

    # Use the first available table as the data source for charts
    first_name, df = next(iter(dataframes_by_name.items()))

    ctype = chart_obj.get("type")
    chart = None

    if ctype == "bar":
        chart = build_bar_chart(df, chart_obj)
    elif ctype == "pie":
        chart = build_pie_chart(df, chart_obj)

    if chart is None:
        st.warning(f"Unsupported or invalid chart spec for chart id '{chart_obj.get('id', '')}'.")
    else:
        st.altair_chart(chart, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="AI Report", layout="wide")
    st.title("AI Report")

    # Summary
    summary_list = REPORT.get("summary", [])
    if summary_list:
        st.subheader("Summary")
        st.markdown("\n".join([f"- {item}" for item in summary_list]))
    else:
        st.info("No summary available.")

    # Tables
    tables = REPORT.get("tables", [])
    dataframes_by_name: Dict[str, pd.DataFrame] = {}

    if tables:
        st.subheader("Tables")
        for t in tables:
            df = dataframe_from_table(t)
            name = t.get("name") or "Table"
            dataframes_by_name[name] = df
            st.markdown(f"**{name}**")
            st.dataframe(df, use_container_width=True)
    else:
        st.info("No tables available.")

    # Charts
    charts = REPORT.get("charts", [])
    if charts:
        st.subheader("Charts")
        for chart in charts:
            render_chart(chart, dataframes_by_name)
    else:
        st.info("No charts available.")

    # Technical metadata (optional)
    echo = REPORT.get("echo")
    if echo:
        with st.expander("Technical details"):
            st.write(echo)


if __name__ == "__main__":
    main()
