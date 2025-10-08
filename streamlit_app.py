import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from typing import List, Dict, Any

# Embedded report data
REPORT: Dict[str, Any] = {
    "valid": True,
    "issues": [],
    "summary": [
        "Weekly sales and units by brand show Sensodyne and Scotts consistently leading in both metrics.",
        "Sales and units fluctuate week by week, with notable peaks for Sensodyne (e.g., 23,462.60 sales and 1,244 units in 2024-11-03) and Scotts (13,750.67 sales and 459 units in 2025-02-23).",
        "Brands like Parodontax, Panadol, and Calsource have sporadic or low weekly performance."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": [
                "week_start",
                "Brand",
                "total_sales",
                "total_units"
            ],
            "rows": [
                ["2023-12-31", "Caltrate", 23176.70000000002, "259"],
                ["2023-12-31", "Centrum", 6240.799999999993, "100"],
                ["2023-12-31", "Eno", 50.980000000000004, "5"],
                ["2023-12-31", "Panaflex", 48.4, "9"],
                ["2023-12-31", "Polident", 4962.539999999996, "196"],
                ["2023-12-31", "Scotts", 12736.260000000022, "390"],
                ["2023-12-31", "Sensodyne", 32640.6399999999, "2156"],
                ["2024-01-07", "Caltrate", 9210.350000000008, "104"],
                ["2024-01-07", "Centrum", 3550.1000000000004, "62"],
                ["2024-01-07", "Eno", 263.41, "14"],
                ["2024-01-07", "Panaflex", 21.78, "4"],
                ["2024-01-07", "Parodontax", 260.3, "15"],
                ["2024-01-07", "Polident", 3105.7200000000007, "128"],
                ["2024-01-07", "Scotts", 5931.519999999991, "196"],
                ["2024-01-07", "Sensodyne", 12473.040000000003, "725"],
                ["2024-01-14", "Calsource", 40, "1"],
                ["2024-01-14", "Caltrate", 4345.41, "55"],
                ["2024-01-14", "Centrum", 2626.4000000000005, "35"],
                ["2024-01-14", "Eno", 137.4, "15"],
                ["2024-01-14", "Panaflex", 23.2, "4"],
                ["2024-01-14", "Parodontax", 438.89999999999986, "28"],
                ["2024-01-14", "Polident", 2594.540000000001, "136"],
                ["2024-01-14", "Scotts", 2451.65, "81"],
                ["2024-01-14", "Sensodyne", 3466.3200000000015, "194"],
                ["2024-01-21", "Caltrate", 6916.88, "86"],
                ["2024-01-21", "Centrum", 2708.4000000000005, "33"],
                ["2024-01-21", "Eno", 59.8, "20"],
                ["2024-01-21", "Panaflex", 64.9, "10"],
                ["2024-01-21", "Parodontax", 67.19999999999999, "4"],
                ["2024-01-21", "Polident", 2816.16, "136"],
                ["2024-01-21", "Scotts", 1998.2200000000007, "61"],
                ["2024-01-21", "Sensodyne", 3554.3700000000013, "194"],
                ["2024-01-28", "Caltrate", 4892.759999999999, "64"],
                ["2024-01-28", "Centrum", 2285.87, "27"],
                ["2024-01-28", "Eno", 37.25, "5"],
                ["2024-01-28", "Panaflex", 37.3, "5"],
                ["2024-01-28", "Parodontax", 12.9, "1"],
                ["2024-01-28", "Polident", 2253.7, "115"],
                ["2024-01-28", "Scotts", 1357.92, "44"],
                ["2024-01-28", "Sensodyne", 2457.800000000001, "126"]
            ]
        }
    ],
    "charts": [
        {
            "id": "weekly_sales_units_brand",
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
            "columns": ["Upload_Date", "Brand", "Total Sales Amount", "Total_Purchase_Units"]
        },
        "stats": {"elapsed": 0.012484838},
        "sql_present": True
    }
}


def _load_table_df(table_obj: Dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame(table_obj.get("rows", []), columns=table_obj.get("columns", []))
    # Coerce dtypes where appropriate
    if "week_start" in df.columns:
        df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
    # Attempt numeric conversion for known numeric columns
    for col in ["total_sales", "total_units"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _stacked_bar_from_long(df: pd.DataFrame, x_key: str, y_key: str, brand_col: str = "Brand", series_order: List[str] = None, title: str = None) -> alt.Chart:
    # Build color encoding with optional series order for consistent legend
    color_encoding = alt.Color(f"{brand_col}:N", title="Brand")
    if series_order:
        color_encoding = alt.Color(
            f"{brand_col}:N",
            title="Brand",
            scale=alt.Scale(domain=series_order)
        )

    # Tooltip fields
    tooltip_fields = [
        alt.Tooltip(f"{x_key}:T", title="Week"),
        alt.Tooltip(f"{brand_col}:N", title="Brand"),
        alt.Tooltip(f"sum({y_key}):Q", title="Total Sales", format=",.2f"),
    ]

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_key}:T", title="Week Start"),
            y=alt.Y(f"sum({y_key}):Q", title="Total Sales"),
            color=color_encoding,
            tooltip=tooltip_fields,
        )
        .properties(title=title or "Weekly Sales by Brand", height=420)
        .interactive()
    )
    return chart


def render_app():
    st.set_page_config(page_title="Weekly Brand Sales & Units", layout="wide")

    st.title("Weekly Sales and Units by Brand")
    st.caption("Auto-generated Streamlit app from JSON report")

    # Summary section
    summaries = REPORT.get("summary", [])
    if summaries:
        st.subheader("Summary")
        for s in summaries:
            st.markdown(f"- {s}")

    # Tables section
    tables = REPORT.get("tables", [])
    dfs: List[pd.DataFrame] = []
    if tables:
        st.subheader("Tables")
        for idx, tbl in enumerate(tables):
            df = _load_table_df(tbl)
            dfs.append(df)
            tbl_name = tbl.get("name", f"Table {idx+1}")
            st.markdown(f"**{tbl_name}**")
            st.dataframe(df, use_container_width=True)

    # Charts section
    charts = REPORT.get("charts", [])
    if charts:
        st.subheader("Charts")

        # Use the first table as the source for charts unless specified otherwise
        source_df = dfs[0] if dfs else None

        for ch in charts:
            ch_type = ch.get("type")
            ch_id = ch.get("id", "chart")
            spec = ch.get("spec", {})

            if ch_type == "stackedBar" and source_df is not None:
                x_key = spec.get("xKey", "week_start")
                y_key = spec.get("yKey", "total_sales")
                series = spec.get("series", [])
                series_order = [s.get("name") for s in series if s.get("name")] if series else None

                # Allow user to filter brands
                brand_list = sorted(source_df["Brand"].dropna().unique().tolist()) if "Brand" in source_df.columns else []
                default_brands = brand_list
                with st.container():
                    st.markdown("**Brand Filter**")
                    selected_brands = st.multiselect(
                        "Select brands to include",
                        options=brand_list,
                        default=default_brands,
                        key=f"brand_filter_{ch_id}"
                    )
                plot_df = source_df.copy()
                if selected_brands:
                    plot_df = plot_df[plot_df["Brand"].isin(selected_brands)]

                # Build and render chart
                title = "Weekly Total Sales by Brand (Stacked)"
                chart = _stacked_bar_from_long(
                    df=plot_df,
                    x_key=x_key,
                    y_key=y_key,
                    brand_col="Brand",
                    series_order=series_order,
                    title=title,
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                # For unsupported chart types or missing data, show a notice
                st.info(f"Chart '{ch.get('id', 'chart')}' of type '{ch_type}' is not supported or has no data.")

    # Footer
    st.markdown("—")
    st.caption("Report viewer generated by Streamlit and Altair")
