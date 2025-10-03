import streamlit as st
import pandas as pd
import altair as alt
from typing import List, Dict, Any

# Embedded report data (from JSON input)
REPORT: Dict[str, Any] = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered users decreased from 4,998 in Q1 to 3,826 in Q2 2025 (-23.43%).",
        "Total sales dropped from 461,543.37 in Q1 to 371,077.93 in Q2 2025 (-19.63%).",
        "Both user registration and sales performance were lower in Q2 compared to Q1 2025."
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
        "used": {"tables": ["`Haleon_Rewards_User_Performance_110925_list`"], "columns": ['"user_id"', '"Total Sales Amount"', '"Upload_Date"']},
        "stats": {"elapsed": 0.04843408},
        "sql_present": True
    }
}


def coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Attempt to convert columns to numeric where possible."""
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="ignore")
    return df


def build_dataframe_from_table(table_obj: Dict[str, Any]) -> pd.DataFrame:
    cols = table_obj.get("columns", [])
    rows = table_obj.get("rows", [])
    df = pd.DataFrame(rows, columns=cols)
    df = coerce_numeric(df)
    return df


def grouped_bar_chart(df: pd.DataFrame, spec: Dict[str, Any], title: str = None) -> alt.Chart:
    x_key = spec.get("xKey")
    series = spec.get("series", [])

    # Build tidy (long) dataframe for Altair grouped bars
    value_keys = [s.get("yKey") for s in series if s.get("yKey")]
    name_map = {s.get("yKey"): (s.get("name") or s.get("yKey")) for s in series if s.get("yKey")}

    # Ensure numeric types for series columns
    for k in value_keys:
        if k in df.columns:
            df[k] = pd.to_numeric(df[k], errors="coerce")

    long_df = df.melt(id_vars=[x_key], value_vars=value_keys, var_name="metric_key", value_name="value")
    long_df["metric"] = long_df["metric_key"].map(name_map).fillna(long_df["metric_key"])  # display names

    # Sort categories in the original order they appear
    if x_key in df.columns:
        categories_order = list(df[x_key].astype(str).unique())
    else:
        categories_order = None

    chart = (
        alt.Chart(long_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_key}:N", sort=categories_order, title=x_key),
            xOffset=alt.XOffset("metric:N"),
            y=alt.Y("value:Q", title="Value"),
            color=alt.Color("metric:N", title="Series"),
            tooltip=[
                alt.Tooltip(f"{x_key}:N", title=x_key),
                alt.Tooltip("metric:N", title="Series"),
                alt.Tooltip("value:Q", title="Value", format=",.2f"),
            ],
        )
        .properties(title=title or "Grouped Bar")
    )

    return chart


def render_chart(chart_obj: Dict[str, Any], tables: List[Dict[str, Any]], df_cache: Dict[str, pd.DataFrame]) -> None:
    chart_id = chart_obj.get("id", "chart")
    chart_type = chart_obj.get("type", "").lower()
    spec = chart_obj.get("spec", {})

    # Heuristic: use the first table unless specified otherwise
    # Build DataFrame cache for table name lookup (if needed in the future)
    if not df_cache:
        for t in tables:
            name = t.get("name") or "Table"
            df_cache[name] = build_dataframe_from_table(t)

    # Default to first table
    first_table_name = tables[0].get("name") if tables else "Table"
    df = df_cache.get(first_table_name)

    st.markdown(f"#### Chart: {chart_id} ({chart_obj.get('type')})")

    if chart_type == "groupedbar":
        title = None
        try:
            # Create a readable title from series names if available
            series_names = [s.get("name") for s in spec.get("series", []) if s.get("name")]
            if series_names:
                title = " vs ".join(series_names)
        except Exception:
            title = None
        chart = grouped_bar_chart(df, spec, title=title)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info(f"Chart type '{chart_obj.get('type')}' is not explicitly supported. Attempting fallback rendering as grouped bar.")
        chart = grouped_bar_chart(df, spec)
        st.altair_chart(chart, use_container_width=True)


def main():
    st.set_page_config(page_title="AI Report Dashboard", page_icon="📊", layout="wide")
    st.title("AI Report Dashboard")

    # Summary
    summary_items = REPORT.get("summary", [])
    if summary_items:
        st.subheader("Summary")
        summary_md = "\n".join([f"- {line}" for line in summary_items])
        st.markdown(summary_md)

    # Tables
    tables = REPORT.get("tables", [])
    if tables:
        st.subheader("Tables")
        for idx, table_obj in enumerate(tables, start=1):
            name = table_obj.get("name") or f"Table {idx}"
            st.markdown(f"#### {name}")
            df = build_dataframe_from_table(table_obj)
            st.dataframe(df, use_container_width=True)

    # Charts
    charts = REPORT.get("charts", [])
    if charts:
        st.subheader("Charts")
        df_cache: Dict[str, pd.DataFrame] = {}
        for chart_obj in charts:
            render_chart(chart_obj, tables, df_cache)

    # Optional debug/metadata
    with st.expander("Report Metadata"):
        echo = REPORT.get("echo", {})
        st.write({
            "valid": REPORT.get("valid"),
            "issues": REPORT.get("issues"),
            "intent": echo.get("intent"),
            "used": echo.get("used"),
            "stats": echo.get("stats"),
            "sql_present": echo.get("sql_present"),
        })
        st.caption("This section shows diagnostic metadata included with the report input.")

    st.caption("Charts are rendered with Altair; tables are displayed with st.dataframe.")


if __name__ == "__main__":
    main()
