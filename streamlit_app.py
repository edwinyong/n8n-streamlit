import json
from typing import Any, Dict, List

import altair as alt
import pandas as pd
import streamlit as st


def render_app() -> None:
    """Render the Streamlit application for the provided sales report JSON."""
    # Embedded report JSON (as provided)
    report_json = r'''{
"valid": true,
"issues": [],
"summary": [
  "Sensodyne led total sales in both 2025 Q1 (160,854.29) and Q2 (152,372.51), showing a slight decline of 5.27%.",
  "Most brands saw lower sales in Q2 vs Q1; Panadol dropped sharply (99.82% decline), while Parodontax slightly increased (+5.10%).",
  "Scotts, Polident, and Caltrate remain among the top-performing brands in both quarters, though all declined in Q2."
],
"tables": [
  {
    "name": "Table",
    "columns": [
      "period",
      "Brand",
      "total_sales"
    ],
    "rows": [
      [
        "2025 Q1",
        "Caltrate",
        56078.72000000009
      ],
      [
        "2025 Q1",
        "Centrum",
        29271.57000000004
      ],
      [
        "2025 Q1",
        "Eno",
        2801.000000000005
      ],
      [
        "2025 Q1",
        "Panadol",
        29712.080000000027
      ],
      [
        "2025 Q1",
        "Panaflex",
        7551.559999999975
      ],
      [
        "2025 Q1",
        "Parodontax",
        4412.130000000001
      ],
      [
        "2025 Q1",
        "Polident",
        81374.93000000063
      ],
      [
        "2025 Q1",
        "Scotts",
        91210.31999999912
      ],
      [
        "2025 Q1",
        "Sensodyne",
        160854.2899999991
      ],
      [
        "2025 Q2",
        "Caltrate",
        39618.420000000006
      ],
      [
        "2025 Q2",
        "Centrum",
        22508.870000000017
      ],
      [
        "2025 Q2",
        "Eno",
        1158.0699999999995
      ],
      [
        "2025 Q2",
        "Panadol",
        53.7
      ],
      [
        "2025 Q2",
        "Panaflex",
        6580.399999999977
      ],
      [
        "2025 Q2",
        "Parodontax",
        4637.609999999999
      ],
      [
        "2025 Q2",
        "Polident",
        70893.68000000072
      ],
      [
        "2025 Q2",
        "Scotts",
        73254.67000000027
      ],
      [
        "2025 Q2",
        "Sensodyne",
        152372.5099999975
      ]
    ]
  }
],
"charts": [
  {
    "id": "brand_performance_2025_q1_q2",
    "type": "groupedBar",
    "spec": {
      "xKey": "Brand",
      "yKey": "total_sales",
      "series": [
        {
          "name": "2025 Q1",
          "yKey": "2025 Q1"
        },
        {
          "name": "2025 Q2",
          "yKey": "2025 Q2"
        }
      ]
    }
  }
],
"echo": {
  "intent": "comparison_totals",
  "used": {
    "tables": [
      "`Haleon_Rewards_User_Performance_110925_SKUs`"
    ],
    "columns": [
      "Upload_Date",
      "Brand",
      "Total Sales Amount"
    ]
  },
  "stats": {
    "elapsed": 0.011678378
  },
  "sql_present": true
}
}'''

    # Parse report
    report: Dict[str, Any] = json.loads(report_json)

    st.title("Brand Sales Report: 2025 Q1 vs Q2")

    # Summaries
    summaries: List[str] = report.get("summary", []) or []
    if summaries:
        st.subheader("Summary")
        for s in summaries:
            st.markdown(f"- {s}")

    # Tables
    st.subheader("Tables")
    table_dfs: Dict[str, pd.DataFrame] = {}
    for tbl in report.get("tables", []):
        name = tbl.get("name", "Table")
        cols = tbl.get("columns", [])
        rows = tbl.get("rows", [])
        df = pd.DataFrame(rows, columns=cols)
        table_dfs[name] = df
        st.markdown(f"**{name}**")
        st.dataframe(df, use_container_width=True)

    # Charts
    def build_grouped_bar(df: pd.DataFrame, x_col: str, y_col: str, period_col: str, title: str = "") -> alt.Chart:
        # Pivot to wide to ensure a stable set of period columns
        pivot = (
            df.pivot_table(index=x_col, columns=period_col, values=y_col, aggfunc="sum")
            .reset_index()
        )
        # Melt back to long for grouped bars via xOffset
        value_columns = [c for c in pivot.columns if c != x_col]
        long_df = pivot.melt(id_vars=[x_col], value_vars=value_columns, var_name="Period", value_name="Sales")
        # Ensure numeric type for Sales
        long_df["Sales"] = pd.to_numeric(long_df["Sales"], errors="coerce")
        # Sort for better legend order (optional)
        long_df = long_df.sort_values([x_col, "Period"])  # noqa: F841

        chart = (
            alt.Chart(long_df)
            .mark_bar()
            .encode(
                x=alt.X(f"{x_col}:N", title=x_col),
                y=alt.Y("Sales:Q", title="Total Sales"),
                color=alt.Color("Period:N", title="Period"),
                xOffset="Period:N",
                tooltip=[
                    alt.Tooltip(f"{x_col}:N", title=x_col),
                    alt.Tooltip("Period:N", title="Period"),
                    alt.Tooltip("Sales:Q", title="Total Sales", format=",.2f"),
                ],
            )
            .properties(title=title)
        )
        return chart

    charts = report.get("charts", [])
    if charts:
        st.subheader("Charts")
        # Use the first table by default as the data source for charts
        source_df: pd.DataFrame = None
        if table_dfs:
            # Pick the first available table
            first_table_name = next(iter(table_dfs))
            source_df = table_dfs[first_table_name]
        else:
            source_df = pd.DataFrame()

        for chart_obj in charts:
            chart_type = chart_obj.get("type")
            spec = chart_obj.get("spec", {})
            if chart_type == "groupedBar":
                x_key = spec.get("xKey", "Brand")
                y_key = spec.get("yKey", "total_sales")
                title = chart_obj.get("id", "Grouped Bar Chart")
                if source_df is not None and not source_df.empty:
                    grouped = build_grouped_bar(
                        df=source_df,
                        x_col=x_key,
                        y_col=y_key,
                        period_col="period",
                        title=title,
                    )
                    st.altair_chart(grouped, use_container_width=True)
                else:
                    st.info("No data available to render the grouped bar chart.")
            else:
                st.info(f"Unsupported chart type: {chart_type}")

    # Footer / meta (optional)
    # st.caption("Report generated from provided JSON input.")


# Note: render_app() is intentionally not executed on import.
