import json
from typing import List, Dict, Any

import streamlit as st
import pandas as pd
import altair as alt


# -------------------------------
# Embedded report JSON (source input)
# -------------------------------
report: Dict[str, Any] = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered purchasers decreased by 23.43% from Q1 (4,998) to Q2 (3,826) in 2025.",
        "Total sales dropped by 19.88% from Q1 (463,266.60) to Q2 (371,077.93) in 2025."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["period", "registered_purchasers", "total_sales"],
            "rows": [["2025 Q1", "4998", 463266.6000000094], ["2025 Q2", "3826", 371077.9300000016]]
        }
    ],
    "charts": [
        {
            "id": "main",
            "type": "groupedBar",
            "spec": {
                "xKey": "period",
                "yKey": "value",
                "series": [
                    {"name": "Registered Purchasers", "yKey": "registered_purchasers"},
                    {"name": "Total Sales", "yKey": "total_sales"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "comparison_totals",
        "used": {
            "tables": ["`Haleon_Rewards_User_Performance_110925_SKUs`", "`Haleon_Rewards_User_Performance_110925_user_list`"],
            "columns": ["Upload_Date", "Total Sales Amount", "comuserid", "user_id"]
        },
        "stats": {"elapsed": 0.039555222},
        "sql_present": True
    }
}


# -------------------------------
# Helpers
# -------------------------------

def _to_dataframe(table: Dict[str, Any]) -> pd.DataFrame:
    """Create a pandas DataFrame from a table spec and try to coerce numeric columns."""
    df = pd.DataFrame(table.get("rows", []), columns=table.get("columns", []))
    # Attempt numeric coercion for columns that look numeric
    for col in df.columns:
        # Try converting to numeric; if most values are numeric-like, keep conversion
        converted = pd.to_numeric(df[col], errors="coerce")
        # If conversion does not produce all NaNs and improves numeric representation, adopt
        num_non_nan = converted.notna().sum()
        if num_non_nan >= max(1, int(0.6 * len(converted))):
            df[col] = converted
    return df


def _find_table_for_chart(tables: List[pd.DataFrame], needed_cols: List[str]) -> pd.DataFrame:
    """Return the first table DataFrame that contains all needed columns."""
    for df in tables:
        if all(col in df.columns for col in needed_cols):
            return df
    # Fallback to the first table if not found
    return tables[0] if tables else pd.DataFrame()


def build_grouped_bar_chart(chart_cfg: Dict[str, Any], tables: List[pd.DataFrame]) -> alt.Chart:
    spec = chart_cfg.get("spec", {})
    x_key = spec.get("xKey")
    series = spec.get("series", [])

    # Determine needed columns
    needed_cols = [x_key] + [s.get("yKey") for s in series if s.get("yKey")]
    df = _find_table_for_chart(tables, needed_cols)
    if df.empty or not x_key or not series:
        return alt.Chart(pd.DataFrame({"message": ["No data to display."]})).mark_text().encode(text="message")

    # Build long-format DataFrame for Altair
    long_records = []
    for _, row in df.iterrows():
        x_val = row[x_key]
        for s in series:
            y_col = s.get("yKey")
            label = s.get("name", y_col)
            value = pd.to_numeric(row.get(y_col, None), errors="coerce")
            long_records.append({x_key: x_val, "series": label, "value": value})
    long_df = pd.DataFrame(long_records)

    # Create grouped bar chart using xOffset (Altair >= 4.2)
    chart = (
        alt.Chart(long_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_key}:N", title=x_key.replace("_", " ").title()),
            y=alt.Y("value:Q", title="Value"),
            color=alt.Color("series:N", title="Metric"),
            xOffset="series:N",
            tooltip=[
                alt.Tooltip(f"{x_key}:N", title=x_key.replace("_", " ").title()),
                alt.Tooltip("series:N", title="Metric"),
                alt.Tooltip("value:Q", title="Value", format=",.2f"),
            ],
        )
        .properties(height=360)
        .resolve_scale(y="shared")
    )
    return chart


def render_charts(charts: List[Dict[str, Any]], tables: List[pd.DataFrame]):
    for chart_cfg in charts:
        ctype = (chart_cfg.get("type") or "").lower()
        chart_obj = None
        title = chart_cfg.get("title") or chart_cfg.get("id") or "Chart"

        with st.container():
            st.markdown(f"#### {title}")
            if ctype == "groupedbar":
                chart_obj = build_grouped_bar_chart(chart_cfg, tables)
            else:
                # Fallback: try groupedBar logic for other unrecognized bar-like types
                chart_obj = build_grouped_bar_chart(chart_cfg, tables)

            st.altair_chart(chart_obj, use_container_width=True)


# -------------------------------
# Streamlit App
# -------------------------------

def main():
    st.set_page_config(page_title="AI Report Dashboard", page_icon="📊", layout="wide")

    st.title("AI Report Dashboard")
    st.caption("This dashboard was generated automatically from a structured report JSON.")

    # Summary
    st.markdown("### Summary")
    summaries = report.get("summary", [])
    if summaries:
        for s in summaries:
            st.markdown(f"- {s}")
    else:
        st.info("No summary available.")

    # Tables
    st.markdown("### Tables")
    raw_tables = report.get("tables", [])
    dataframes: List[pd.DataFrame] = []
    if raw_tables:
        for idx, tbl in enumerate(raw_tables):
            name = tbl.get("name") or f"Table {idx + 1}"
            df = _to_dataframe(tbl)
            dataframes.append(df)

            st.markdown(f"#### {name}")
            st.dataframe(df, use_container_width=True)
    else:
        st.info("No tables provided in report.")

    # Charts
    st.markdown("### Charts")
    charts_cfg = report.get("charts", [])
    if charts_cfg:
        render_charts(charts_cfg, dataframes)
    else:
        st.info("No charts provided in report.")

    # Optional: echo technical details
    with st.expander("Technical details (source and diagnostics)"):
        st.code(json.dumps(report.get("echo", {}), indent=2), language="json")
        st.caption("Echo shows the analytical intent, upstream sources, and timing metadata.")


if __name__ == "__main__":
    main()
