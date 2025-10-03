#!/usr/bin/env python3
# Streamlit app generated from provided JSON report

import streamlit as st
import pandas as pd
import altair as alt
from typing import Dict, Any, List

# Embedded report data (from user-provided JSON)
REPORT: Dict[str, Any] = {
    "valid": True,
    "issues": [],
    "summary": [
        "January 2025 shows the highest registered users and sales.",
        "February 2025 records the lowest monthly figures.",
        "Performance stabilizes from March onwards, with moderate monthly fluctuations."
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
                ["2025-12", "1410", 134000]
            ]
        }
    ],
    "charts": [
        {
            "id": "reg_hist",
            "type": "histogram",
            "spec": {
                "xKey": "month",
                "yKey": "registered_users",
                "series": [
                    {"name": "Registered Users", "yKey": "registered_users"}
                ]
            }
        },
        {
            "id": "sales_hist",
            "type": "histogram",
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
        "used": {
            "tables": ["`Haleon_Rewards_User_Performance_110925_list`"],
            "columns": ["\"user_id\"", "\"Total Sales Amount\"", "\"Upload_Date\""]
        },
        "stats": {"elapsed": 0.04843408},
        "sql_present": True
    }
}

# Configure Altair to avoid max rows warnings
alt.data_transformers.disable_max_rows()

st.set_page_config(page_title="Monthly User & Sales Report (2025)", layout="wide")
st.title("Monthly User & Sales Report (2025)")

# Utility helpers

def labelize(key: str) -> str:
    return key.replace("_", " ").title() if isinstance(key, str) else str(key)


def coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Attempt to convert columns to numeric where possible, keeping non-numeric as-is
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="ignore")
    return df


# Summary section
st.subheader("Summary")
if REPORT.get("summary"):
    for item in REPORT["summary"]:
        st.markdown(f"- {item}")
else:
    st.info("No summary available.")

st.markdown("---")

# Tables section
st.subheader("Tables")

dataframes_by_name: Dict[str, pd.DataFrame] = {}

for t in REPORT.get("tables", []):
    name = t.get("name", "Table")
    cols: List[str] = t.get("columns", [])
    rows: List[List[Any]] = t.get("rows", [])

    df = pd.DataFrame(rows, columns=cols)
    df = coerce_numeric_columns(df)

    dataframes_by_name[name] = df

    st.markdown(f"#### Table: {name}")
    st.dataframe(df, use_container_width=True)

if not dataframes_by_name:
    st.warning("No tables provided in the report.")

st.markdown("---")

# Charts section (Altair)
st.subheader("Charts")

# Use the first table as the default dataset for charts unless otherwise specified
first_df = None
if REPORT.get("tables"):
    first_table_name = REPORT["tables"][0].get("name", "Table")
    first_df = dataframes_by_name.get(first_table_name)

if not REPORT.get("charts"):
    st.info("No charts provided in the report.")
else:
    for chart in REPORT["charts"]:
        chart_id = chart.get("id", "chart")
        chart_type = chart.get("type", "bar").lower()
        spec = chart.get("spec", {})
        x_key = spec.get("xKey")
        y_key = spec.get("yKey")

        df_for_chart = first_df
        if df_for_chart is None or x_key not in df_for_chart.columns or y_key not in df_for_chart.columns:
            st.warning(f"Chart '{chart_id}' skipped due to missing data or keys.")
            continue

        # Preserve the input order for x-axis sorting (e.g., month order)
        x_order = df_for_chart[x_key].astype(str).tolist()

        # Axis formatting for y
        y_axis_format = None
        if isinstance(df_for_chart[y_key].dtype, pd.api.types.CategoricalDtype):
            y_axis_format = None
        else:
            # Heuristic: if column name suggests currency or contains 'sales', format as currency
            if "sale" in y_key.lower() or "amount" in y_key.lower() or "revenue" in y_key.lower():
                y_axis_format = "$,.0f"
            else:
                y_axis_format = ","

        chart_title = f"{labelize(y_key)} by {labelize(x_key)}"

        # Build Altair chart by type
        base = alt.Chart(df_for_chart, title=chart_title)

        if chart_type in ("histogram", "bar"):
            c = (
                base.mark_bar()
                .encode(
                    x=alt.X(f"{x_key}:N", sort=x_order, title=labelize(x_key)),
                    y=alt.Y(f"{y_key}:Q", title=labelize(y_key), axis=alt.Axis(format=y_axis_format)),
                    tooltip=[
                        alt.Tooltip(f"{x_key}:N", title=labelize(x_key)),
                        alt.Tooltip(f"{y_key}:Q", title=labelize(y_key), format=y_axis_format if y_axis_format else None),
                    ],
                )
            )
        elif chart_type == "line":
            c = (
                base.mark_line(point=True)
                .encode(
                    x=alt.X(f"{x_key}:N", sort=x_order, title=labelize(x_key)),
                    y=alt.Y(f"{y_key}:Q", title=labelize(y_key), axis=alt.Axis(format=y_axis_format)),
                    tooltip=[
                        alt.Tooltip(f"{x_key}:N", title=labelize(x_key)),
                        alt.Tooltip(f"{y_key}:Q", title=labelize(y_key), format=y_axis_format if y_axis_format else None),
                    ],
                )
            )
        elif chart_type == "area":
            c = (
                base.mark_area(opacity=0.6)
                .encode(
                    x=alt.X(f"{x_key}:N", sort=x_order, title=labelize(x_key)),
                    y=alt.Y(f"{y_key}:Q", title=labelize(y_key), axis=alt.Axis(format=y_axis_format)),
                    tooltip=[
                        alt.Tooltip(f"{x_key}:N", title=labelize(x_key)),
                        alt.Tooltip(f"{y_key}:Q", title=labelize(y_key), format=y_axis_format if y_axis_format else None),
                    ],
                )
            )
        elif chart_type == "scatter":
            c = (
                base.mark_point(filled=True, size=80)
                .encode(
                    x=alt.X(f"{x_key}:Q", title=labelize(x_key)),
                    y=alt.Y(f"{y_key}:Q", title=labelize(y_key), axis=alt.Axis(format=y_axis_format)),
                    tooltip=[
                        alt.Tooltip(f"{x_key}:Q", title=labelize(x_key)),
                        alt.Tooltip(f"{y_key}:Q", title=labelize(y_key), format=y_axis_format if y_axis_format else None),
                    ],
                )
            )
        elif chart_type == "pie":
            # For pie, treat y_key as value and x_key as category
            # Compute aggregated values by category
            pie_df = df_for_chart.groupby(x_key, as_index=False)[y_key].sum()
            c = (
                alt.Chart(pie_df, title=chart_title)
                .mark_arc()
                .encode(
                    theta=alt.Theta(f"{y_key}:Q", stack=True),
                    color=alt.Color(f"{x_key}:N", legend=alt.Legend(title=labelize(x_key))),
                    tooltip=[
                        alt.Tooltip(f"{x_key}:N", title=labelize(x_key)),
                        alt.Tooltip(f"{y_key}:Q", title=labelize(y_key), format=y_axis_format if y_axis_format else None),
                    ],
                )
            )
        else:
            # Fallback to bar
            c = (
                base.mark_bar()
                .encode(
                    x=alt.X(f"{x_key}:N", sort=x_order, title=labelize(x_key)),
                    y=alt.Y(f"{y_key}:Q", title=labelize(y_key), axis=alt.Axis(format=y_axis_format)),
                    tooltip=[
                        alt.Tooltip(f"{x_key}:N", title=labelize(x_key)),
                        alt.Tooltip(f"{y_key}:Q", title=labelize(y_key), format=y_axis_format if y_axis_format else None),
                    ],
                )
            )

        st.altair_chart(c.resolve_scale(y="independent"), use_container_width=True)

# Optional: Debug metadata
with st.expander("Debug Metadata", expanded=False):
    st.write("Validity:", REPORT.get("valid"))
    issues = REPORT.get("issues", [])
    if issues:
        st.error({"issues": issues})
    else:
        st.write("Issues: None")
    st.write("Intent:", REPORT.get("echo", {}).get("intent"))
    st.write("SQL present:", REPORT.get("echo", {}).get("sql_present"))
    st.write("Stats:")
    st.json(REPORT.get("echo", {}).get("stats", {}))
    st.write("Source usage:")
    st.json(REPORT.get("echo", {}).get("used", {}))

st.caption("Built with Streamlit, Altair, and Pandas")
