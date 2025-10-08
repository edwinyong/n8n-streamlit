import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from typing import List, Dict, Any


REPORT_DATA: Dict[str, Any] = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered users decreased from 4,998 in 2025 Q1 to 3,826 in 2025 Q2, a drop of 23.45%.",
        "Total sales declined from 461,543.37 in Q1 to 371,077.93 in Q2, a decrease of 19.62%."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["period", "registered_users", "total_sales"],
            "rows": [
                ["2025 Q1", "4998", 461543.37000000733],
                ["2025 Q2", "3826", 371077.93000000285]
            ]
        }
    ],
    "charts": [
        {
            "id": "users_sales_comparison",
            "type": "groupedBar",
            "spec": {
                "xKey": "period",
                "yKey": "value",
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
            "tables": [
                "`Haleon_Rewards_User_Performance_110925_SKUs`",
                "`Haleon_Rewards_User_Performance_110925_user_list`"
            ],
            "columns": ["Upload_Date", "Total Sales Amount", "comuserid", "user_id"]
        },
        "stats": {"elapsed": 0.026647236},
        "sql_present": True
    }
}


def _to_dataframe(table_obj: Dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame(table_obj.get("rows", []), columns=table_obj.get("columns", []))
    # Best-effort dtype casting based on known column names
    if "registered_users" in df.columns:
        df["registered_users"] = pd.to_numeric(df["registered_users"], errors="coerce").astype("Int64")
    if "total_sales" in df.columns:
        df["total_sales"] = pd.to_numeric(df["total_sales"], errors="coerce")
    return df


def _grouped_bar_chart(df: pd.DataFrame, x_col: str, series: List[Dict[str, str]], chart_title: str = "") -> alt.Chart:
    # Prepare long-form data for Altair grouped bars
    value_cols = [s.get("yKey") for s in series]
    label_map = {s.get("yKey"): s.get("name", s.get("yKey")) for s in series}

    # Ensure numeric
    for col in value_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    long_df = df.melt(id_vars=[x_col], value_vars=value_cols, var_name="metric_key", value_name="value")
    long_df["metric"] = long_df["metric_key"].map(label_map)

    # Preserve input order for x-axis
    x_order = [x for x in df[x_col].astype(str).tolist()]

    chart = (
        alt.Chart(long_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_col}:N", sort=x_order, title=x_col),
            xOffset=alt.XOffset("metric:N"),
            y=alt.Y("value:Q", title="Value"),
            color=alt.Color("metric:N", title="Metric"),
            tooltip=[x_col + ":N", alt.Tooltip("metric:N", title="Metric"), alt.Tooltip("value:Q", title="Value", format=",")]
        )
        .properties(title=chart_title or "")
    )
    return chart


def render_app() -> None:
    st.set_page_config(page_title="Report Dashboard", layout="wide")

    report = REPORT_DATA

    st.title("Quarterly Performance Overview")

    # Summaries
    summaries = report.get("summary", [])
    if summaries:
        st.subheader("Summary")
        st.markdown("\n".join([f"- {s}" for s in summaries]))

    # Tables
    tables = report.get("tables", [])
    if tables:
        st.subheader("Tables")
        for idx, tbl in enumerate(tables, start=1):
            df = _to_dataframe(tbl)
            title = tbl.get("name") or f"Table {idx}"
            st.markdown(f"**{title}**")
            st.dataframe(df, use_container_width=True)

    # Charts
    charts = report.get("charts", [])
    if charts:
        st.subheader("Charts")
        for ch in charts:
            ch_type = (ch.get("type") or "").lower()
            ch_id = ch.get("id") or "chart"
            spec = ch.get("spec", {})
            if ch_type == "groupedbar":
                x_key = spec.get("xKey")
                series = spec.get("series", [])
                # Use the first table to source chart data (assumption based on provided JSON)
                if tables:
                    df = _to_dataframe(tables[0])
                    chart = _grouped_bar_chart(df, x_key, series, chart_title=ch_id)
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.info(f"No table data available for chart '{ch_id}'.")
            else:
                st.info(f"Unsupported chart type: {ch_type} (id: {ch_id})")

    # Optional: Context info from echo
    echo = report.get("echo")
    if echo:
        with st.expander("Details"):
            st.write(echo)


# This module exposes render_app() and does not execute on import.
