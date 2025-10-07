import streamlit as st
import pandas as pd
import altair as alt
import json
from typing import Dict, Any, List

st.set_page_config(page_title="AI Report App", layout="wide")

# Embedded report JSON (provided by the user)
REPORT: Dict[str, Any] = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered purchasers dropped by 23.43% from Q1 (4,998) to Q2 (3,826) in 2025.",
        "Total sales decreased by 19.88% from Q1 (463,266.60) to Q2 (371,077.93) in 2025."
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
            "columns": ["Upload_Date", "`Total Sales Amount`", "comuserid", "user_id"]
        },
        "stats": {"elapsed": 0.045323458},
        "sql_present": True
    }
}

alt.data_transformers.disable_max_rows()

# Utility functions

def _auto_coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        # Try converting to numeric when all values are convertible
        converted = pd.to_numeric(out[col], errors='coerce')
        if converted.notna().sum() == len(out[col]):
            out[col] = converted
    return out


def _build_grouped_bar(df: pd.DataFrame, chart: Dict[str, Any]) -> alt.Chart:
    spec = chart.get("spec", {})
    x_key = spec.get("xKey")
    value_key = spec.get("yKey", "value")
    series = spec.get("series", [])

    if not x_key or not series:
        raise ValueError("Invalid groupedBar spec: missing xKey or series")

    # Prepare long-form data
    long_frames: List[pd.DataFrame] = []
    order = []
    for s in series:
        name = s.get("name") or s.get("yKey")
        y_col = s.get("yKey")
        order.append(name)
        if y_col not in df.columns:
            continue
        tmp = df[[x_key, y_col]].copy()
        # Ensure numeric values for y
        tmp[value_key] = pd.to_numeric(tmp[y_col], errors='coerce')
        tmp = tmp[[x_key, value_key]]
        tmp["metric"] = name
        long_frames.append(tmp)

    if not long_frames:
        raise ValueError("No valid series columns found for groupedBar chart.")

    long_df = pd.concat(long_frames, ignore_index=True)

    # Build grouped bar using xOffset for grouping by metric
    chart_alt = (
        alt.Chart(long_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_key}:N", title=x_key, sort=sorted(long_df[x_key].unique())),
            xOffset=alt.XOffset("metric:N", sort=order),
            y=alt.Y(f"{value_key}:Q", title="Value", stack=None),
            color=alt.Color("metric:N", title="Series", sort=order),
            tooltip=[
                alt.Tooltip(f"{x_key}:N", title=x_key),
                alt.Tooltip("metric:N", title="Series"),
                alt.Tooltip(f"{value_key}:Q", title="Value", format=",.2f"),
            ],
        )
        .properties(height=380)
    )
    return chart_alt


# App UI
st.title("AI-Generated Report")

# Summary
st.header("Summary")
if REPORT.get("summary"):
    for item in REPORT["summary"]:
        st.markdown(f"- {item}")
else:
    st.info("No summary available.")

# Tables
st.header("Tables")
table_dfs: Dict[str, pd.DataFrame] = {}
if REPORT.get("tables"):
    for idx, tbl in enumerate(REPORT["tables"], start=1):
        name = tbl.get("name") or f"Table {idx}"
        columns = tbl.get("columns", [])
        rows = tbl.get("rows", [])
        df = pd.DataFrame(rows, columns=columns)
        df = _auto_coerce_numeric(df)
        table_dfs[name] = df

        # Prepare a display copy with nicer float formatting
        disp_df = df.copy()
        float_cols = [c for c in disp_df.columns if pd.api.types.is_float_dtype(disp_df[c])]
        if float_cols:
            disp_df[float_cols] = disp_df[float_cols].round(2)

        st.subheader(name)
        st.dataframe(disp_df, use_container_width=True)
else:
    st.info("No tables available.")

# Charts
st.header("Charts")
if REPORT.get("charts"):
    # Choose primary data source: the first table if available
    if table_dfs:
        # Use the first table as the primary data source for charts
        primary_df = next(iter(table_dfs.values()))
    else:
        primary_df = pd.DataFrame()

    for chart in REPORT["charts"]:
        chart_id = chart.get("id", "chart")
        chart_type = (chart.get("type") or "").lower()
        st.subheader(f"Chart: {chart_id}")

        try:
            if chart_type in ("groupedbar", "grouped_bar", "groupbar"):
                ch = _build_grouped_bar(primary_df, chart)
            else:
                st.warning(f"Unsupported chart type '{chart.get('type')}'. Rendering as grouped bar if possible.")
                ch = _build_grouped_bar(primary_df, chart)

            st.altair_chart(ch, use_container_width=True)
        except Exception as e:
            st.error(f"Failed to render chart '{chart_id}': {e}")
else:
    st.info("No charts available.")

# Optional: Raw JSON in an expander for transparency
with st.expander("View raw JSON report"):
    st.code(json.dumps(REPORT, indent=2), language="json")
