import streamlit as st
import pandas as pd
import altair as alt
import json

st.set_page_config(page_title="AI Report", layout="wide")

# Embedded report data (from the provided JSON)
report = {
    "valid": True,
    "issues": [],
    "summary": [
        "Histogram shows January with the highest registered users and sales in 2025.",
        "February has the lowest monthly performance.",
        "Rest of the months are relatively stable, with no extreme outliers after Q1."
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

# Title
st.title("AI Report Dashboard")

# Summary Section
st.header("Summary")
if report.get("summary"):
    for bullet in report["summary"]:
        st.markdown(f"- {bullet}")
else:
    st.info("No summary available.")

# Prepare and render tables
st.header("Tables")
tables = report.get("tables", [])
dfs = {}

if not tables:
    st.info("No tables available in the report.")

for tbl in tables:
    name = tbl.get("name") or "Table"
    columns = tbl.get("columns", [])
    rows = tbl.get("rows", [])

    # Build DataFrame
    df = pd.DataFrame(rows, columns=columns)

    # Normalize dtypes: convert numeric-looking columns (except 'month')
    for col in df.columns:
        if col != "month":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Ensure 'month' is string and create a datetime helper for sorting
    if "month" in df.columns:
        df["month"] = df["month"].astype(str)
        df["month_dt"] = pd.to_datetime(df["month"], format="%Y-%m", errors="coerce")

    dfs[name] = df

    st.subheader(f"Table: {name}")
    st.dataframe(df.drop(columns=["month_dt"], errors="ignore"))

# Charts Section
st.header("Charts")
charts = report.get("charts", [])

if not charts:
    st.info("No charts available in the report.")

# Use the first table as the base dataset for charts (common report pattern)
base_df = next(iter(dfs.values())) if dfs else pd.DataFrame()

# Compute month sort order if available
if not base_df.empty and "month" in base_df.columns:
    try:
        months_sorted = (
            base_df[["month", "month_dt"]]
            .drop_duplicates()
            .sort_values("month_dt")
            ["month"].tolist()
        )
    except Exception:
        months_sorted = base_df["month"].drop_duplicates().tolist()
else:
    months_sorted = []

# Render charts with Altair
for ch in charts:
    cid = ch.get("id", "")
    ctype = ch.get("type", "").lower()
    spec = ch.get("spec", {})
    x_key = spec.get("xKey")
    y_key = spec.get("yKey")

    if base_df.empty or x_key not in base_df.columns or y_key not in base_df.columns:
        st.warning(f"Chart '{cid}' skipped due to missing data or keys.")
        continue

    data = base_df.copy()
    # Ensure numeric y
    data[y_key] = pd.to_numeric(data[y_key], errors="coerce")

    # Define titles based on chart id for clarity
    if cid == "reg_hist":
        title = "Registered Users by Month (2025)"
        y_title = "Registered Users"
    elif cid == "sales_hist":
        title = "Total Sales by Month (2025)"
        y_title = "Total Sales"
    else:
        title = f"{y_key} by {x_key}"
        y_title = y_key.replace("_", " ").title()

    # For 'histogram' types, render as bar charts over discrete months
    if ctype in ("histogram", "bar"):
        chart = (
            alt.Chart(data, title=title)
            .mark_bar()
            .encode(
                x=alt.X(f"{x_key}:N", sort=months_sorted if months_sorted else None, title="Month" if x_key == "month" else x_key.title()),
                y=alt.Y(f"{y_key}:Q", title=y_title),
                tooltip=[
                    alt.Tooltip(f"{x_key}:N", title="Month" if x_key == "month" else x_key.title()),
                    alt.Tooltip(f"{y_key}:Q", title=y_title, format=",.2f"),
                ],
            )
            .properties(width="container", height=320)
        )
        st.altair_chart(chart, use_container_width=True)
    elif ctype == "pie":
        # General pie rendering support (not used in this report but supported)
        chart = (
            alt.Chart(data, title=title)
            .mark_arc(outerRadius=120)
            .encode(
                theta=alt.Theta(f"{y_key}:Q", stack=True),
                color=alt.Color(f"{x_key}:N", legend=alt.Legend(title=x_key.title())),
                tooltip=[x_key, y_key],
            )
            .properties(height=360)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info(f"Chart type '{ctype}' not directly supported; rendering as bar chart.")
        chart = (
            alt.Chart(data, title=title)
            .mark_bar()
            .encode(
                x=alt.X(f"{x_key}:N", sort=months_sorted if months_sorted else None, title=x_key.title()),
                y=alt.Y(f"{y_key}:Q", title=y_title),
                tooltip=[x_key, y_key],
            )
            .properties(width="container", height=320)
        )
        st.altair_chart(chart, use_container_width=True)

# Optional: Show raw JSON for debugging/transparency
with st.expander("Debug: Raw Report JSON"):
    st.code(json.dumps(report, indent=2), language="json")

st.caption("Generated by AI: Streamlit + Altair + pandas")
