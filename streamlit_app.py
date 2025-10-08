import streamlit as st
import pandas as pd
import altair as alt
import json
from datetime import datetime


def render_app():
    st.set_page_config(page_title="Weekly Brand Sales & Units Dashboard", layout="wide")

    # Raw report JSON embedded for a self-contained app
    report_json = r'''{"valid":true,"issues":[],"summary":["Sensodyne and Scotts consistently lead in weekly sales and units across the observed period.","Sales and unit volumes show significant week-to-week fluctuations, with notable peaks for Sensodyne (e.g., over 23,000 in sales and 1,200+ units in some weeks).","Brands like Parodontax, Panadol, and Calsource show sporadic or minimal weekly activity.","No consistent upward or downward trend is observed for most brands; performance varies by week and brand."],"tables":[{"name":"Weekly Brand Sales & Units","columns":["week_start","Brand","total_sales","total_units"],"rows":[["2023-12-31","Caltrate",23176.70000000002,"259"],["2023-12-31","Centrum",6240.799999999993,"100"],["2023-12-31","Eno",50.980000000000004,"5"],["2023-12-31","Panaflex",48.4,"9"],["2023-12-31","Polident",4962.539999999996,"196"],["2023-12-31","Scotts",12736.260000000022,"390"],["2023-12-31","Sensodyne",32640.6399999999,"2156"],["2024-01-07","Caltrate",9210.350000000008,"104"],["2024-01-07","Centrum",3550.1000000000004,"62"],["2024-01-07","Eno",263.41,"14"],["2024-01-07","Panaflex",21.78,"4"],["2024-01-07","Parodontax",260.3,"15"],["2024-01-07","Polident",3105.7200000000007,"128"],["2024-01-07","Scotts",5931.519999999991,"196"],["2024-01-07","Sensodyne",12473.040000000003,"725"],["2024-01-14","Calsource",40,"1"],["2024-01-14","Caltrate",4345.41,"55"],["2024-01-14","Centrum",2626.4000000000005,"35"],["2024-01-14","Eno",137.4,"15"],["2024-01-14","Panaflex",23.2,"4"],["2024-01-14","Parodontax",438.89999999999986,"28"],["2024-01-14","Polident",2594.540000000001,"136"],["2024-01-14","Scotts",2451.65,"81"],["2024-01-14","Sensodyne",3466.3200000000015,"194"],["2024-01-21","Caltrate",6916.88,"86"],["2024-01-21","Centrum",2708.4000000000005,"33"],["2024-01-21","Eno",59.8,"20"],["2024-01-21","Panaflex",64.9,"10"],["2024-01-21","Parodontax",67.19999999999999,"4"],["2024-01-21","Polident",2816.16,"136"],["2024-01-21","Scotts",1998.2200000000007,"61"],["2024-01-21","Sensodyne",3554.3700000000013,"194"],["2024-01-28","Caltrate",4892.759999999999,"64"],["2024-01-28","Centrum",2285.87,"27"],["2024-01-28","Eno",37.25,"5"],["2024-01-28","Panaflex",37.3,"5"],["2024-01-28","Parodontax",12.9,"1"],["2024-01-28","Polident",2253.7,"115"],["2024-01-28","Scotts",1357.92,"44"],["2024-01-28","Sensodyne",2457.800000000001,"126"]]}],"charts":[{"id":"weekly_sales_by_brand","type":"stackedBar","spec":{"xKey":"week_start","yKey":"total_sales","series":[{"name":"Caltrate","yKey":"Caltrate"},{"name":"Centrum","yKey":"Centrum"},{"name":"Eno","yKey":"Eno"},{"name":"Panaflex","yKey":"Panaflex"},{"name":"Parodontax","yKey":"Parodontax"},{"name":"Polident","yKey":"Polident"},{"name":"Scotts","yKey":"Scotts"},{"name":"Sensodyne","yKey":"Sensodyne"},{"name":"Calsource","yKey":"Calsource"}]}},{"id":"weekly_units_by_brand","type":"stackedBar","spec":{"xKey":"week_start","yKey":"total_units","series":[{"name":"Caltrate","yKey":"Caltrate"},{"name":"Centrum","yKey":"Centrum"},{"name":"Eno","yKey":"Eno"},{"name":"Panaflex","yKey":"Panaflex"},{"name":"Parodontax","yKey":"Parodontax"},{"name":"Polident","yKey":"Polident"},{"name":"Scotts","yKey":"Scotts"},{"name":"Sensodyne","yKey":"Sensodyne"},{"name":"Calsource","yKey":"Calsource"}]}}],"echo":{"intent":"trend","used":{"tables":["`Haleon_Rewards_User_Performance_110925_SKUs`"],"columns":["Upload_Date","Brand","Total Sales Amount","Total_Purchase_Units"]},"stats":{"elapsed":0.028928044},"sql_present":true}}'''

    report = json.loads(report_json)

    st.title("Weekly Brand Performance")

    # Display summaries
    summaries = report.get("summary", [])
    if summaries:
        st.subheader("Summary")
        for item in summaries:
            st.markdown(f"- {item}")

    # Helper to build stacked bar charts using Altair
    def stacked_bar_chart(df: pd.DataFrame, y_col: str, title: str, brand_order=None) -> alt.Chart:
        tooltip_title = "Sales" if y_col == "total_sales" else "Units"
        y_title = "Sales Amount" if y_col == "total_sales" else "Units"
        number_format = ",.2f" if y_col == "total_sales" else ",d"
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X("week_start:T", title="Week Start"),
                y=alt.Y(f"sum({y_col}):Q", title=y_title),
                color=alt.Color("Brand:N", sort=brand_order, legend=alt.Legend(title="Brand")),
                order=alt.Order("Brand:N", sort=brand_order if brand_order else None),
                tooltip=[
                    alt.Tooltip("week_start:T", title="Week"),
                    alt.Tooltip("Brand:N", title="Brand"),
                    alt.Tooltip(f"sum({y_col}):Q", title=tooltip_title, format=number_format),
                ],
            )
            .properties(title=title, height=400)
            .interactive()
        )
        return chart

    # Display tables and collect main dataframe for charts
    st.subheader("Tables")
    df_main = None
    tables = report.get("tables", [])
    for idx, tbl in enumerate(tables, start=1):
        name = tbl.get("name", f"Table {idx}")
        st.markdown(f"#### {name}")
        df = pd.DataFrame(tbl.get("rows", []), columns=tbl.get("columns", []))

        # Type conversions
        if "week_start" in df.columns:
            df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
        for col in ["total_sales", "total_units"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        st.dataframe(df, use_container_width=True)

        if name == "Weekly Brand Sales & Units":
            df_main = df.copy()

    # If specific named table not found, fall back to first table
    if df_main is None and len(tables) > 0:
        df_main = pd.DataFrame(tables[0].get("rows", []), columns=tables[0].get("columns", []))
        if "week_start" in df_main.columns:
            df_main["week_start"] = pd.to_datetime(df_main["week_start"], errors="coerce")
        for col in ["total_sales", "total_units"]:
            if col in df_main.columns:
                df_main[col] = pd.to_numeric(df_main[col], errors="coerce")

    # Charts
    if df_main is not None and {"week_start", "Brand"}.issubset(set(df_main.columns)):
        st.subheader("Charts")
        # Determine brand order from chart spec if present
        brand_order = None
        sales_spec = next((c for c in report.get("charts", []) if c.get("id") == "weekly_sales_by_brand"), None)
        if sales_spec and "spec" in sales_spec and "series" in sales_spec["spec"]:
            brand_order = [s.get("name") for s in sales_spec["spec"]["series"] if s.get("name")]

        # Ensure consistent ordering and sorting by week
        if brand_order:
            df_main["Brand"] = pd.Categorical(df_main["Brand"], categories=brand_order, ordered=True)
        df_main = df_main.sort_values(["week_start", "Brand"])  # type: ignore[arg-type]

        cols = st.columns(2)
        with cols[0]:
            if "total_sales" in df_main.columns:
                sales_chart = stacked_bar_chart(df_main, "total_sales", "Weekly Sales by Brand", brand_order)
                st.altair_chart(sales_chart, use_container_width=True)
        with cols[1]:
            if "total_units" in df_main.columns:
                units_chart = stacked_bar_chart(df_main, "total_units", "Weekly Units by Brand", brand_order)
                st.altair_chart(units_chart, use_container_width=True)

    else:
        st.info("No compatible data found to render charts.")
