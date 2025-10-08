import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

# Embedded report data (as provided)
REPORT = {
    "valid": True,
    "issues": [],
    "summary": [
        "Weekly KPIs per brand include purchases (distinct receipts), buyers (unique users), total sales, and total units.",
        "Sensodyne and Scotts consistently lead in weekly sales and user engagement across most weeks.",
        "Some brands (e.g., Parodontax, Panadol, Calsource) have sporadic activity, with weeks of zero or minimal performance.",
        "Redemption data is not present in the provided dataset; only purchase, buyer, sales, and unit metrics are available."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["week_start", "Brand", "purchases", "buyers", "total_sales", "total_units"],
            "rows": [
                ["2023-12-31", "Caltrate", "238", "224", 23176.70000000002, "259"],
                ["2023-12-31", "Centrum", "84", "75", 6240.799999999993, "100"],
                ["2023-12-31", "Eno", "4", "4", 50.980000000000004, "5"],
                ["2023-12-31", "Panaflex", "4", "3", 48.4, "9"],
                ["2023-12-31", "Polident", "107", "100", 4962.539999999996, "196"],
                ["2023-12-31", "Scotts", "202", "189", 12736.260000000022, "390"],
                ["2023-12-31", "Sensodyne", "504", "470", 32640.6399999999, "2156"],
                ["2024-01-07", "Caltrate", "99", "92", 9210.350000000008, "104"],
                ["2024-01-07", "Centrum", "45", "45", 3550.1000000000004, "62"],
                ["2024-01-07", "Eno", "7", "7", 263.41, "14"],
                ["2024-01-07", "Panaflex", "3", "3", 21.78, "4"],
                ["2024-01-07", "Parodontax", "10", "10", 260.3, "15"],
                ["2024-01-07", "Polident", "64", "58", 3105.7200000000007, "128"],
                ["2024-01-07", "Scotts", "101", "96", 5931.519999999991, "196"],
                ["2024-01-07", "Sensodyne", "203", "185", 12473.040000000003, "725"],
                ["2024-01-14", "Calsource", "1", "1", 40, "1"],
                ["2024-01-14", "Caltrate", "54", "48", 4345.41, "55"],
                ["2024-01-14", "Centrum", "35", "27", 2626.4000000000005, "35"],
                ["2024-01-14", "Eno", "10", "10", 137.4, "15"],
                ["2024-01-14", "Panaflex", "2", "2", 23.2, "4"],
                ["2024-01-14", "Parodontax", "15", "13", 438.89999999999986, "28"],
                ["2024-01-14", "Polident", "63", "62", 2594.540000000001, "136"],
                ["2024-01-14", "Scotts", "39", "36", 2451.65, "81"],
                ["2024-01-14", "Sensodyne", "79", "72", 3466.3200000000015, "194"],
                ["2024-01-21", "Caltrate", "80", "66", 6916.88, "86"],
                ["2024-01-21", "Centrum", "30", "25", 2708.4000000000005, "33"],
                ["2024-01-21", "Eno", "4", "4", 59.8, "20"],
                ["2024-01-21", "Panaflex", "3", "3", 64.9, "10"],
                ["2024-01-21", "Parodontax", "4", "4", 67.19999999999999, "4"],
                ["2024-01-21", "Polident", "62", "56", 2816.16, "136"],
                ["2024-01-21", "Scotts", "34", "32", 1998.2200000000007, "61"],
                ["2024-01-21", "Sensodyne", "66", "63", 3554.3700000000013, "194"],
                ["2024-01-28", "Caltrate", "60", "56", 4892.759999999999, "64"],
                ["2024-01-28", "Centrum", "27", "21", 2285.87, "27"],
                ["2024-01-28", "Eno", "4", "4", 37.25, "5"],
                ["2024-01-28", "Panaflex", "2", "2", 37.3, "5"],
                ["2024-01-28", "Parodontax", "1", "1", 12.9, "1"],
                ["2024-01-28", "Polident", "47", "43", 2253.7, "115"],
                ["2024-01-28", "Scotts", "27", "23", 1357.92, "44"],
                ["2024-01-28", "Sensodyne", "47", "45", 2457.800000000001, "126"]
            ]
        }
    ],
    "charts": [
        {
            "id": "weekly_brand_kpis",
            "type": "stackedBar",
            "spec": {
                "xKey": "week_start",
                "yKey": "total_sales",
                "series": [
                    {"name": "Caltrate", "yKey": "Caltrate"},
                    {"name": "Centrum", "yKey": "Centrum"},
                    {"name": "Eno", "yKey": "Eno"},
                    {"name": "Panaflex", "yKey": "Panaflex"},
                    {"name": "Parodontax", "yKey": "Parodontax"},
                    {"name": "Polident", "yKey": "Polident"},
                    {"name": "Scotts", "yKey": "Scotts"},
                    {"name": "Sensodyne", "yKey": "Sensodyne"},
                    {"name": "Calsource", "yKey": "Calsource"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "trend",
        "used": {
            "tables": ["`Haleon_Rewards_User_Performance_110925_SKUs`"],
            "columns": ["Upload_Date", "Brand", "receiptid", "comuserid", "Total Sales Amount", "Total_Purchase_Units"]
        },
        "stats": {"elapsed": 0.030837454},
        "sql_present": True
    }
}


def _prepare_dataframe(report_table: dict) -> pd.DataFrame:
    """Create and clean a pandas DataFrame from the embedded report table."""
    df = pd.DataFrame(report_table.get("rows", []), columns=report_table.get("columns", []))

    # Coerce data types
    if "week_start" in df.columns:
        df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
    for col in ["purchases", "buyers", "total_sales", "total_units"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Sort by week then brand
    sort_cols = [c for c in ["week_start", "Brand"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols).reset_index(drop=True)
    return df


def _stacked_sales_chart(df: pd.DataFrame, series_order=None) -> alt.Chart:
    """Build an Altair stacked bar chart of total sales by week and brand."""
    series_order = series_order or []
    color_scale = alt.Scale(domain=series_order) if series_order else alt.Undefined
    color_sort = series_order if series_order else alt.Undefined

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("week_start:T", title="Week Start", sort="ascending"),
            y=alt.Y("sum(total_sales):Q", title="Total Sales"),
            color=alt.Color("Brand:N", title="Brand", scale=color_scale, sort=color_sort),
            tooltip=[
                alt.Tooltip("yearmonthdate(week_start):T", title="Week"),
                alt.Tooltip("Brand:N", title="Brand"),
                alt.Tooltip("sum(total_sales):Q", title="Total Sales", format=",.2f"),
                alt.Tooltip("sum(purchases):Q", title="Purchases", format=","),
                alt.Tooltip("sum(buyers):Q", title="Buyers", format=","),
                alt.Tooltip("sum(total_units):Q", title="Units", format=",")
            ],
            order=alt.Order("Brand", sort="ascending"),
        )
        .properties(height=420)
    )
    return chart


def render_app():
    """Render the Streamlit application for the provided report."""
    st.set_page_config(page_title="Weekly Brand KPIs Dashboard", layout="wide")

    st.title("Weekly Brand KPIs Dashboard")

    # Summaries
    summaries = REPORT.get("summary", [])
    if summaries:
        st.subheader("Summary")
        st.markdown("\n".join([f"- {s}" for s in summaries]))

    # Load table into DataFrame
    tables = REPORT.get("tables", [])
    if tables:
        base_table = tables[0]
        df = _prepare_dataframe(base_table)

        # Optional filters for exploration
        with st.expander("Filters", expanded=False):
            available_brands = sorted(df["Brand"].dropna().unique().tolist()) if "Brand" in df.columns else []
            selected_brands = st.multiselect("Brands", options=available_brands, default=available_brands)
            min_date = pd.to_datetime(df["week_start"].min()) if "week_start" in df.columns else None
            max_date = pd.to_datetime(df["week_start"].max()) if "week_start" in df.columns else None
            date_range = st.date_input(
                "Week start range",
                value=(min_date.date() if min_date is not None else None, max_date.date() if max_date is not None else None),
                help="Limit the weeks shown in the table and charts"
            )

        # Apply filters
        filtered_df = df.copy()
        if selected_brands:
            filtered_df = filtered_df[filtered_df["Brand"].isin(selected_brands)]
        if "week_start" in filtered_df.columns and isinstance(date_range, (list, tuple)) and len(date_range) == 2 and all(date_range):
            start_dt = pd.to_datetime(date_range[0])
            end_dt = pd.to_datetime(date_range[1])
            filtered_df = filtered_df[(filtered_df["week_start"] >= start_dt) & (filtered_df["week_start"] <= end_dt)]

        # KPI totals
        kpi_cols = st.columns(4)
        kpi_totals = {
            "Total Purchases": int(filtered_df["purchases"].sum()) if "purchases" in filtered_df.columns else 0,
            "Total Buyers": int(filtered_df["buyers"].sum()) if "buyers" in filtered_df.columns else 0,
            "Total Sales": filtered_df["total_sales"].sum() if "total_sales" in filtered_df.columns else 0.0,
            "Total Units": int(filtered_df["total_units"].sum()) if "total_units" in filtered_df.columns else 0,
        }
        kpi_cols[0].metric("Total Purchases", f"{kpi_totals['Total Purchases']:,}")
        kpi_cols[1].metric("Total Buyers", f"{kpi_totals['Total Buyers']:,}")
        kpi_cols[2].metric("Total Sales", f"${kpi_totals['Total Sales']:,.2f}")
        kpi_cols[3].metric("Total Units", f"{kpi_totals['Total Units']:,}")

        # Data table display
        st.subheader("Weekly KPIs per Brand (Table)")
        st.dataframe(filtered_df, use_container_width=True)

        # Chart(s)
        st.subheader("Weekly Total Sales by Brand (Stacked Bar)")
        chart_spec = next((c for c in REPORT.get("charts", []) if c.get("id") == "weekly_brand_kpis"), None)
        series_order = [s.get("name") for s in chart_spec.get("spec", {}).get("series", [])] if chart_spec else []

        sales_chart = _stacked_sales_chart(filtered_df, series_order=series_order)
        st.altair_chart(sales_chart, use_container_width=True)

    # Metadata (optional)
    with st.expander("Report Metadata", expanded=False):
        st.write("Intent:", REPORT.get("echo", {}).get("intent"))
        st.write("Data Source Tables:", REPORT.get("echo", {}).get("used", {}).get("tables", []))
        st.write("Columns Used:", REPORT.get("echo", {}).get("used", {}).get("columns", []))
        st.write("SQL Present:", REPORT.get("echo", {}).get("sql_present"))

# The render_app() function is intentionally not executed on import.
