import streamlit as st
import pandas as pd
import altair as alt
from typing import List, Dict, Any

# Embedded report JSON
REPORT: Dict[str, Any] = {
    "valid": True,
    "issues": [],
    "summary": [
        "Stacked bar chart shows monthly registered users and sales for 2025 side by side for each month.",
        "January has the highest values for both metrics; February is the lowest.",
        "From March onwards, both metrics stabilize with moderate monthly variations.",
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["month", "registered_users", "total_sales"],
            "rows": [
                ["2025-01", "2100", 190000],
                ["2025-02", "1300", 130000],
                ["2025-03", "1598", 141543.37],
                ["2025-04", "1200", 120000],
                ["2025-05", "1250", 125000],
                ["2025-06", "1376", 126077.93],
                ["2025-07", "1320", 128000],
                ["2025-08", "1370", 128099.01],
                ["2025-09", "1321", 128000],
                ["2025-10", "1400", 134000],
                ["2025-11", "1400", 133120.55],
                ["2025-12", "1410", 134000],
            ],
        }
    ],
    "charts": [
        {
            "id": "stacked_bar",
            "type": "stackedBar",
            "spec": {
                "xKey": "month",
                "yKey": "value",
                "series": [
                    {"name": "Registered Users", "yKey": "registered_users"},
                    {"name": "Total Sales", "yKey": "total_sales"},
                ],
            },
        }
    ],
    "echo": {
        "intent": "trend",
        "used": {
            "tables": ["`Haleon_Rewards_User_Performance_110925_list`"],
            "columns": ['"user_id"', '"Total Sales Amount"', '"Upload_Date"'],
        },
        "stats": {"elapsed": 0.04843408},
        "sql_present": True,
    },
}


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Attempt to convert object columns to numeric where possible."""
    for col in df.columns:
        if df[col].dtype == 'object':
            coerced = pd.to_numeric(df[col], errors='ignore')
            df[col] = coerced
    return df


def _parse_month_column(df: pd.DataFrame, month_col: str = "month") -> pd.DataFrame:
    if month_col in df.columns:
        try:
            # Parse YYYY-MM to datetime by appending day
            df[month_col] = pd.to_datetime(df[month_col].astype(str), format="%Y-%m", errors="coerce")
        except Exception:
            # Fallback generic parse
            df[month_col] = pd.to_datetime(df[month_col].astype(str), errors="coerce")
        # Also keep a label column for tooltips/axes formatting
        df[month_col + "_label"] = df[month_col].dt.strftime("%b %Y")
    return df


def render_table(table: Dict[str, Any]) -> pd.DataFrame:
    name = table.get("name", "Table")
    columns = table.get("columns", [])
    rows = table.get("rows", [])

    df = pd.DataFrame(rows, columns=columns)
    df = _coerce_numeric(df.copy())
    df = _parse_month_column(df, month_col="month")

    st.subheader(f"Table: {name}")
    st.dataframe(df, use_container_width=True)
    return df


def stacked_or_grouped_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    series: List[Dict[str, str]],
    title: str = ""
):
    # Prepare long-form data
    value_cols = [s["yKey"] for s in series]

    # Build a mapping for pretty names
    name_map = {s["yKey"]: s.get("name", s["yKey"]) for s in series}

    # Ensure numeric
    for c in value_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    long_df = df.melt(id_vars=[x_col, x_col + "_label"], value_vars=value_cols, var_name="metric", value_name="value")
    long_df["Metric"] = long_df["metric"].map(name_map)

    # Controls
    st.write("")
    mode = st.radio("Bar display", ["Grouped", "Stacked"], horizontal=True, index=0, key=f"bar_mode_{title}")

    base = (
        alt.Chart(long_df)
        .encode(
            x=alt.X(f"{x_col}:T", title="Month", axis=alt.Axis(format="%b %Y")),
            color=alt.Color("Metric:N", title="Metric", scale=alt.Scale(scheme="tableau10")),
            tooltip=[
                alt.Tooltip(f"{x_col}_label:N", title="Month"),
                alt.Tooltip("Metric:N"),
                alt.Tooltip("value:Q", title="Value", format=",")
            ],
        )
    )

    if mode == "Grouped":
        chart = base.mark_bar().encode(
            y=alt.Y("value:Q", title="Value"),
            xOffset=alt.XOffset("Metric:N"),
        )
    else:
        chart = base.mark_bar().encode(
            y=alt.Y("value:Q", title="Value", stack="zero"),
        )

    if title:
        chart = chart.properties(title=title)

    st.altair_chart(chart.properties(width="container", height=420), use_container_width=True)


def main():
    st.set_page_config(page_title="AI Report App", layout="wide")
    st.title("AI Report")

    # Status/Issues
    if REPORT.get("valid", False):
        st.success("Report validated successfully.")
    else:
        st.warning("Report indicated as invalid.")

    issues = REPORT.get("issues", [])
    if issues:
        with st.expander("Issues detected in report"):
            for i, issue in enumerate(issues, start=1):
                st.write(f"{i}. {issue}")

    # Summary
    st.header("Summary")
    summary_items = REPORT.get("summary", [])
    if summary_items:
        st.markdown("\n".join([f"- {s}" for s in summary_items]))
    else:
        st.write("No summary available.")

    # Tables
    st.header("Tables")
    tables = REPORT.get("tables", [])
    dataframes: List[pd.DataFrame] = []
    for t in tables:
        df = render_table(t)
        dataframes.append(df)

    # Charts
    st.header("Charts")
    charts = REPORT.get("charts", [])

    # For this report, we assume charts use the first/only table's data
    base_df = dataframes[0] if dataframes else None

    if not charts:
        st.info("No charts provided in the report.")
    else:
        for ch in charts:
            ch_type = ch.get("type")
            ch_id = ch.get("id", "chart")
            spec = ch.get("spec", {})

            if ch_type == "stackedBar":
                if base_df is None:
                    st.warning("No data available to plot.")
                    continue
                x_key = spec.get("xKey", "month")
                series = spec.get("series", [])
                stacked_or_grouped_bar_chart(
                    base_df.copy(),
                    x_col=x_key,
                    series=series,
                    title="Monthly Registered Users and Total Sales (2025)",
                )
            else:
                st.warning(f"Unsupported chart type: {ch_type}")

    # Metadata/Echo
    with st.expander("Report Metadata"):
        echo = REPORT.get("echo", {})
        st.json(echo)


if __name__ == "__main__":
    main()
