import streamlit as st
import pandas as pd
import altair as alt
from typing import List, Dict, Any, Optional

# Embedded report data provided to the app
REPORT: Dict[str, Any] = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered users in 2025 Q2 (3,826) decreased by 23.43% compared to Q1 (4,998).",
        "Total sales in Q2 (371,077.93) dropped by 19.61% from Q1 (461,543.37).",
        "Total units sold in Q2 (15,482) declined by 21.01% from Q1 (19,603).",
        "Q2 2025 performance is lower than Q1 2025 across registrations, sales, and units sold."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["period", "registered_users", "total_sales", "total_units"],
            "rows": [["Q2", "3826", 371077.93, "15482"], ["Q1", "4998", 461543.3700000002, "19603"]]
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
            "tables": ["`Haleon_Rewards_User_Performance_110925_list`", "`Haleon_Rewards_User_Performance_110925_SKUs`"],
            "columns": ["\"user_id\"", "\"comuserid\"", "\"Upload_Date\"", "\"Total Sales Amount\"", "\"Total_Purchase_Units\""]
        },
        "stats": {"elapsed": 0.042964239},
        "sql_present": True
    }
}

# -----------------------------
# Utility functions
# -----------------------------

def to_dataframe(table_obj: Dict[str, Any]) -> pd.DataFrame:
    """Create a pandas DataFrame from a table object with 'columns' and 'rows'."""
    cols = table_obj.get("columns", [])
    rows = table_obj.get("rows", [])
    df = pd.DataFrame(rows, columns=cols)
    return df


def coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Attempt to convert columns to numeric where possible, in place."""
    for c in df.columns:
        # Try to convert entire column; non-convertible values remain as-is
        try:
            converted = pd.to_numeric(df[c], errors="ignore")
            df[c] = converted
        except Exception:
            pass
    return df


def get_all_dfs(report: Dict[str, Any]) -> List[pd.DataFrame]:
    dfs = []
    for t in report.get("tables", []):
        df = to_dataframe(t)
        df = coerce_numeric_columns(df)
        dfs.append(df)
    return dfs


def find_table_for_chart(report: Dict[str, Any], x_key: str, y_keys: List[str]) -> Optional[pd.DataFrame]:
    """Find the first table that contains x_key and all y_keys."""
    for t in report.get("tables", []):
        cols = t.get("columns", [])
        if x_key in cols and all(y in cols for y in y_keys):
            df = to_dataframe(t)
            df = coerce_numeric_columns(df)
            return df
    return None


def build_bar_chart(df: pd.DataFrame, spec: Dict[str, Any], chart_title: str = "") -> alt.Chart:
    x_key = spec.get("xKey")
    # Determine series to plot
    series_list = spec.get("series")
    if series_list and isinstance(series_list, list):
        y_keys = [s.get("yKey") for s in series_list if s.get("yKey")]
        name_map = {s.get("yKey"): s.get("name", s.get("yKey")) for s in series_list if s.get("yKey")}
        metric_order = [name_map[y] for y in y_keys]
    else:
        # Fallback to single yKey
        y_key = spec.get("yKey")
        y_keys = [y_key] if y_key else []
        name_map = {y_key: y_key}
        metric_order = [name_map[y_key]] if y_key else []

    if not x_key or not y_keys:
        raise ValueError("Bar chart spec requires xKey and at least one yKey/series")

    # Keep x order as it appears in the data
    x_order = df[x_key].astype(str).tolist()

    # Melt to long format for grouped bars
    use_cols = [x_key] + y_keys
    df_long = df[use_cols].copy()
    df_long = df_long.melt(id_vars=[x_key], value_vars=y_keys, var_name="metric_key", value_name="value")
    df_long["metric"] = df_long["metric_key"].map(name_map).fillna(df_long["metric_key"])

    # Build chart
    chart = (
        alt.Chart(df_long, title=chart_title)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_key}:N", sort=x_order, title=x_key),
            xOffset=alt.X("metric:N", sort=metric_order, title=None),
            y=alt.Y("value:Q", title="Value"),
            color=alt.Color("metric:N", sort=metric_order, title="Metric"),
            tooltip=[
                alt.Tooltip(f"{x_key}:N", title=x_key),
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip("value:Q", title="Value", format=",.2f"),
            ],
        )
        .properties(height=360)
    )
    return chart


# -----------------------------
# Streamlit App UI
# -----------------------------

st.set_page_config(page_title="AI Report Dashboard", layout="wide")
st.title("AI Report Dashboard")

# Summary
summary_items = REPORT.get("summary", [])
if summary_items:
    st.header("Summary")
    for item in summary_items:
        st.markdown(f"- {item}")

# Tables
tables = REPORT.get("tables", [])
if tables:
    st.header("Tables")
    for idx, t in enumerate(tables):
        name = t.get("name") or f"Table {idx + 1}"
        st.subheader(name)
        df = to_dataframe(t)
        df = coerce_numeric_columns(df)
        st.dataframe(df, use_container_width=True)

# Charts
charts = REPORT.get("charts", [])
if charts:
    st.header("Charts")

for ch in charts:
    ch_id = ch.get("id", "chart")
    ch_type = ch.get("type", "bar")
    spec = ch.get("spec", {})
    # Determine data source table for the chart
    x_key = spec.get("xKey")
    series_list = spec.get("series")
    if series_list and isinstance(series_list, list):
        y_keys = [s.get("yKey") for s in series_list if s.get("yKey")]
    else:
        y_keys = [spec.get("yKey")] if spec.get("yKey") else []

    df_for_chart = None
    if x_key and y_keys:
        df_for_chart = find_table_for_chart(REPORT, x_key, y_keys)

    # Fallback to first table if no perfect match
    if df_for_chart is None:
        dfs = get_all_dfs(REPORT)
        if dfs:
            df_for_chart = dfs[0]

    if df_for_chart is None:
        st.warning(f"No data available to render chart '{ch_id}'.")
        continue

    try:
        if ch_type == "bar":
            chart_obj = build_bar_chart(df_for_chart, spec, chart_title=f"{ch_id} - {ch_type.capitalize()} Chart")
            st.altair_chart(chart_obj, use_container_width=True)
        else:
            st.info(f"Chart type '{ch_type}' is not specifically implemented. Attempting bar chart rendering.")
            chart_obj = build_bar_chart(df_for_chart, spec, chart_title=f"{ch_id} - {ch_type.capitalize()} Chart")
            st.altair_chart(chart_obj, use_container_width=True)
    except Exception as e:
        st.error(f"Failed to render chart '{ch_id}': {e}")

# Optional: show basic metadata
with st.expander("Report Metadata"):
    st.write({
        "valid": REPORT.get("valid"),
        "issues": REPORT.get("issues"),
        "echo": REPORT.get("echo")
    })
