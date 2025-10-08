import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime


def render_app():
    """
    Streamlit renderer for the provided JSON report.

    Usage:
        from streamlit_app import render_app
        render_app()
    """
    # The provided JSON report embedded for a self-contained app
    report = {
        "valid": True,
        "issues": [],
        "summary": [
            "Total sales show a fluctuating trend with no consistent improvement over the observed period.",
            "Sales peaked in November 2024 (194,247.50) and reached a low in September 2025 (18,826.01).",
            "Recent months (2025 Q2) saw a downward trend, with sales declining from 138,457.02 in June 2025 to 18,826.01 in September 2025."
        ],
        "tables": [
            {
                "name": "Table",
                "columns": ["month", "registered_users", "total_sales"],
                "rows": [
                    ["2024-01-01", "1559", 155716.77999999866],
                    ["2024-02-01", "755", 69937.42000000055],
                    ["2024-03-01", "384", 33747.91000000003],
                    ["2024-04-01", "1355", 115891.65999999913],
                    ["2024-05-01", "740", 82326.92000000003],
                    ["2024-06-01", "1036", 101096.36999999949],
                    ["2024-07-01", "1180", 113795.1999999991],
                    ["2024-08-01", "1320", 133218.4099999987],
                    ["2024-09-01", "477", 53061.82000000047],
                    ["2024-10-01", "1616", 126693.1599999974],
                    ["2024-11-01", "2506", 194247.4999999981],
                    ["2024-12-01", "1494", 127829.75999999963],
                    ["2025-01-01", "1416", 119626.18999999885],
                    ["2025-02-01", "2093", 181249.12999999718],
                    ["2025-03-01", "1946", 162391.27999999782],
                    ["2025-04-01", "1621", 122584.14999999863],
                    ["2025-05-01", "1096", 110036.75999999886],
                    ["2025-06-01", "1491", 138457.01999999848],
                    ["2025-07-01", "1036", 101228.30999999943],
                    ["2025-08-01", "762", 90910.37999999947],
                    ["2025-09-01", "194", 18826.00999999998]
                ]
            }
        ],
        "charts": [
            {
                "id": "sales_trend",
                "type": "line",
                "spec": {
                    "xKey": "month",
                    "yKey": "total_sales",
                    "series": [
                        {"name": "Total Sales", "yKey": "total_sales"}
                    ]
                }
            }
        ],
        "echo": {
            "intent": "trend",
            "used": {"tables": ["`Haleon_Rewards_User_Performance_110925_SKUs`"], "columns": ["Upload_Date", "comuserid", "Total Sales Amount"]},
            "stats": {"elapsed": 0.016164377},
            "sql_present": True
        }
    }

    # Helper: convert a table dict to a typed pandas DataFrame
    def _table_to_dataframe(table_dict: dict) -> pd.DataFrame:
        df = pd.DataFrame(table_dict.get("rows", []), columns=table_dict.get("columns", []))
        # Type conversions where possible
        if "month" in df.columns:
            df["month"] = pd.to_datetime(df["month"], errors="coerce")
        if "registered_users" in df.columns:
            df["registered_users"] = pd.to_numeric(df["registered_users"], errors="coerce")
        if "total_sales" in df.columns:
            df["total_sales"] = pd.to_numeric(df["total_sales"], errors="coerce")
        return df

    # Helper: infer Altair type from a pandas Series
    def _alt_type(series: pd.Series) -> str:
        if pd.api.types.is_datetime64_any_dtype(series):
            return "T"  # temporal
        if pd.api.types.is_numeric_dtype(series):
            return "Q"  # quantitative
        return "N"  # nominal

    # Title
    st.title("Sales Performance Report")

    # Summary
    summaries = report.get("summary", [])
    if summaries:
        st.subheader("Summary")
        st.markdown("\n".join([f"- {s}" for s in summaries]))

    # Tables
    st.subheader("Tables")
    tables = report.get("tables", [])
    dataframes = {}

    for idx, tbl in enumerate(tables):
        name = tbl.get("name") or f"Table {idx + 1}"
        df = _table_to_dataframe(tbl)
        dataframes[name] = df

        # Optional period caption if month exists
        if "month" in df.columns and not df["month"].isna().all():
            df_sorted = df.sort_values("month")
            start, end = df_sorted["month"].min(), df_sorted["month"].max()
            if pd.notna(start) and pd.notna(end):
                st.caption(f"Period: {start.strftime('%b %Y')} - {end.strftime('%b %Y')}")

        # Display the table with formatting if columns exist
        try:
            st.dataframe(
                df,
                hide_index=True,
                column_config={
                    "registered_users": st.column_config.NumberColumn("Registered Users", format=",d"),
                    "total_sales": st.column_config.NumberColumn("Total Sales", format=",.2f"),
                },
                use_container_width=True,
            )
        except Exception:
            # Fallback if Streamlit version doesn't support column_config
            st.dataframe(df, hide_index=True, use_container_width=True)

    # Charts
    charts = report.get("charts", [])
    if charts:
        st.subheader("Charts")

    # Assume charts relate to the first available table unless otherwise specified
    default_df = None
    if dataframes:
        # Prefer the first table for chart data
        first_key = list(dataframes.keys())[0]
        default_df = dataframes[first_key]

    for chart_def in charts:
        ctype = (chart_def.get("type") or "").lower()
        spec = chart_def.get("spec", {})
        x_key = spec.get("xKey")
        y_key = spec.get("yKey")

        # Pick dataframe to use
        df_for_chart = default_df
        if df_for_chart is None or x_key not in df_for_chart.columns or y_key not in df_for_chart.columns:
            # If we cannot find proper data, skip chart with a warning
            st.warning(f"Chart '{chart_def.get('id', 'chart')}' could not be rendered due to missing data columns.")
            continue

        # Ensure data is sorted by x if temporal
        if x_key in df_for_chart.columns and pd.api.types.is_datetime64_any_dtype(df_for_chart[x_key]):
            df_for_chart = df_for_chart.sort_values(x_key)

        x_type = _alt_type(df_for_chart[x_key])
        y_type = _alt_type(df_for_chart[y_key])

        # Build Altair chart based on type
        if ctype == "line":
            chart = (
                alt.Chart(df_for_chart)
                .mark_line(point=True)
                .encode(
                    x=alt.X(f"{x_key}:{x_type}", title=x_key.replace("_", " ").title()),
                    y=alt.Y(
                        f"{y_key}:{y_type}",
                        title=y_key.replace("_", " ").title(),
                        axis=alt.Axis(format=",.2f") if y_type == "Q" else alt.Undefined,
                    ),
                    tooltip=[
                        alt.Tooltip(f"{x_key}:{x_type}", title=x_key.replace("_", " ").title()),
                        alt.Tooltip(f"{y_key}:{y_type}", title=y_key.replace("_", " ").title(), format=",.2f" if y_type == "Q" else None),
                    ],
                )
                .properties(height=380)
            )
            st.altair_chart(chart, use_container_width=True)
        elif ctype == "bar":
            chart = (
                alt.Chart(df_for_chart)
                .mark_bar()
                .encode(
                    x=alt.X(f"{x_key}:{x_type}", title=x_key.replace("_", " ").title()),
                    y=alt.Y(
                        f"{y_key}:{y_type}",
                        title=y_key.replace("_", " ").title(),
                        axis=alt.Axis(format=",.2f") if y_type == "Q" else alt.Undefined,
                    ),
                    tooltip=[
                        alt.Tooltip(f"{x_key}:{x_type}", title=x_key.replace("_", " ").title()),
                        alt.Tooltip(f"{y_key}:{y_type}", title=y_key.replace("_", " ").title(), format=",.2f" if y_type == "Q" else None),
                    ],
                )
                .properties(height=380)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info(f"Chart type '{ctype}' not specifically handled; showing as line chart by default.")
            chart = (
                alt.Chart(df_for_chart)
                .mark_line(point=True)
                .encode(
                    x=alt.X(f"{x_key}:{x_type}", title=x_key.replace("_", " ").title()),
                    y=alt.Y(
                        f"{y_key}:{y_type}",
                        title=y_key.replace("_", " ").title(),
                        axis=alt.Axis(format=",.2f") if y_type == "Q" else alt.Undefined,
                    ),
                    tooltip=[
                        alt.Tooltip(f"{x_key}:{x_type}", title=x_key.replace("_", " ").title()),
                        alt.Tooltip(f"{y_key}:{y_type}", title=y_key.replace("_", " ").title(), format=",.2f" if y_type == "Q" else None),
                    ],
                )
                .properties(height=380)
            )
            st.altair_chart(chart, use_container_width=True)

    # Optional: Raw metadata
    echo = report.get("echo")
    if echo:
        with st.expander("View query metadata", expanded=False):
            st.json(echo)
