import streamlit as st
import pandas as pd
import altair as alt
import json
from typing import Dict, Any, List

# ---------------------------------------------
# AI Report App - Auto-generated Streamlit app
# ---------------------------------------------
# This app renders the provided JSON report:
#  - Displays summary in markdown
#  - Renders all tables with st.dataframe
#  - Renders all charts with Altair
#
# Libraries used: streamlit, pandas, altair
# ---------------------------------------------

st.set_page_config(page_title="AI Report Dashboard", page_icon="📊", layout="wide")

# Embed the provided JSON report directly in the app
def load_report() -> Dict[str, Any]:
    report = {
        "valid": True,
        "issues": [],
        "summary": [
            "No change in registered users or total sales between 2025 Q1 and 2025 Q2.",
            "Registered users: 36,831; Total sales: 1,843,315.89 in both quarters."
        ],
        "tables": [
            {
                "name": "Table",
                "columns": ["period", "registered_users", "total_sales"],
                "rows": [
                    ["2025 Q2", "36831", "1843315.8899999924"],
                    ["2025 Q1", "36831", "1843315.8899999924"]
                ]
            }
        ],
        "charts": [
            {
                "id": "main",
                "type": "kpi",
                "spec": {
                    "xKey": "period",
                    "yKey": "total_sales",
                    "series": [
                        {"name": "Total Sales", "yKey": "total_sales"}
                    ]
                }
            },
            {
                "id": "main_2",
                "type": "kpi",
                "spec": {
                    "xKey": "period",
                    "yKey": "registered_users",
                    "series": [
                        {"name": "Registered Users", "yKey": "registered_users"}
                    ]
                }
            }
        ],
        "echo": {
            "intent": "comparison_totals",
            "used": {
                "tables": ["Haleon_Rewards_User_Performance_110925_list"],
                "columns": ["user_id", "Total Sales"]
            },
            "stats": {"elapsed": 0.021348218},
            "sql_present": True
        }
    }
    return report


def build_dataframes(report: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    dfs: Dict[str, pd.DataFrame] = {}
    for tbl in report.get("tables", []):
        name = tbl.get("name", "Table")
        cols = tbl.get("columns", [])
        rows = tbl.get("rows", [])
        df = pd.DataFrame(rows, columns=cols)
        # Coerce numerics where appropriate
        for c in df.columns:
            # Try to convert to numeric when possible (without raising)
            if c.lower() in ["registered_users", "total_sales", "value", "amount", "count"]:
                df[c] = pd.to_numeric(df[c], errors='ignore')
        dfs[name] = df
    return dfs


def format_big_number(x: float) -> str:
    try:
        return f"{x:,.2f}"
    except Exception:
        return str(x)


def render_summary(summary_items: List[str]) -> None:
    st.subheader("Summary")
    if not summary_items:
        st.info("No summary provided.")
        return
    for item in summary_items:
        st.markdown(f"- {item}")


def chart_from_kpi(df: pd.DataFrame, x_key: str, y_key: str, title: str) -> alt.Chart:
    # Ensure dtype
    dff = df.copy()
    if y_key in dff.columns:
        dff[y_key] = pd.to_numeric(dff[y_key], errors='coerce')
    # Build a bar chart with labels for KPI-style summary per period
    base = alt.Chart(dff)
    bar = base.mark_bar(color="#4C78A8").encode(
        x=alt.X(f"{x_key}:N", title=x_key.replace("_", " ").title()),
        y=alt.Y(
            f"{y_key}:Q",
            title=y_key.replace("_", " ").title(),
            axis=alt.Axis(format=",")
        ),
        tooltip=[x_key, alt.Tooltip(y_key, format=",")]
    )
    text = base.mark_text(dy=-6, color="#333", fontWeight="bold").encode(
        x=alt.X(f"{x_key}:N"),
        y=alt.Y(f"{y_key}:Q"),
        text=alt.Text(f"{y_key}:Q", format=",")
    )
    chart = (bar + text).properties(title=title).configure_title(anchor='start')
    return chart


def render_charts(report: Dict[str, Any], dfs: Dict[str, pd.DataFrame]) -> None:
    st.subheader("Charts")
    charts = report.get("charts", [])
    if not charts:
        st.info("No charts available.")
        return

    # Use the first table as the default data source for charts unless specified
    default_df = next(iter(dfs.values())) if dfs else pd.DataFrame()

    for ch in charts:
        ch_type = ch.get("type", "bar")
        spec = ch.get("spec", {})
        x_key = spec.get("xKey")
        y_key = spec.get("yKey")
        series = spec.get("series", [])
        title = series[0].get("name") if series and isinstance(series, list) and isinstance(series[0], dict) else (y_key or "Chart")

        df = default_df.copy()
        if df.empty or not x_key or not y_key or x_key not in df.columns or y_key not in df.columns:
            st.warning(f"Skipping chart '{ch.get('id', '')}' due to missing data or keys.")
            continue

        if ch_type.lower() == "kpi":
            chart = chart_from_kpi(df, x_key, y_key, title)
        elif ch_type.lower() in ("bar", "column"):
            chart = alt.Chart(df).mark_bar().encode(
                x=alt.X(f"{x_key}:N", title=x_key),
                y=alt.Y(f"{y_key}:Q", title=y_key, axis=alt.Axis(format=",")),
                tooltip=[x_key, alt.Tooltip(y_key, format=",")]
            ).properties(title=title)
        elif ch_type.lower() == "line":
            chart = alt.Chart(df).mark_line(point=True).encode(
                x=alt.X(f"{x_key}:N", title=x_key),
                y=alt.Y(f"{y_key}:Q", title=y_key, axis=alt.Axis(format=",")),
                tooltip=[x_key, alt.Tooltip(y_key, format=",")]
            ).properties(title=title)
        elif ch_type.lower() == "pie":
            chart = alt.Chart(df).mark_arc().encode(
                theta=alt.Theta(f"{y_key}:Q", stack=True),
                color=alt.Color(f"{x_key}:N"),
                tooltip=[x_key, alt.Tooltip(y_key, format=",")]
            ).properties(title=title)
        else:
            # Fallback to bar
            chart = chart_from_kpi(df, x_key, y_key, title)

        st.altair_chart(chart, use_container_width=True)


def render_tables(dfs: Dict[str, pd.DataFrame]) -> None:
    st.subheader("Tables")
    if not dfs:
        st.info("No tables available.")
        return

    for name, df in dfs.items():
        st.markdown(f"**{name}**")
        # Try to improve dtypes where applicable
        display_df = df.copy()
        for c in display_df.columns:
            if display_df[c].dtype == object:
                try:
                    display_df[c] = pd.to_numeric(display_df[c])
                except Exception:
                    pass
        st.dataframe(display_df, use_container_width=True)


def main():
    st.title("AI Report Dashboard")

    report = load_report()

    # Header status
    if not report.get("valid", True):
        st.error("Report marked as invalid.")
    if report.get("issues"):
        with st.expander("Issues detected in report"):
            for issue in report["issues"]:
                st.write(f"- {issue}")

    # Summary
    render_summary(report.get("summary", []))

    # Build DataFrames
    dfs = build_dataframes(report)

    # Charts
    render_charts(report, dfs)

    # Tables
    render_tables(dfs)

    # Optional: Raw JSON for debugging/review
    with st.expander("View raw report JSON"):
        st.code(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
