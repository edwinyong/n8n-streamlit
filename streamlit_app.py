import streamlit as st
import pandas as pd
import altair as alt

# ------------------------------
# Page Configuration
# ------------------------------
st.set_page_config(page_title="AI Report", layout="wide")

# ------------------------------
# Embedded Report Data (from JSON input)
# ------------------------------
report = {
    "valid": True,
    "issues": [],
    "summary": [
        "Sensodyne leads all brands in users (11,944), units sold (38,793), and sales amount (808,739.14).",
        "Scotts and Polident are strong performers in both units sold and sales amount, while Caltrate shows high purchase value but fewer units sold.",
        "Brands like Calsource, Eno, and Parodontax have much lower sales and user engagement."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": [
                "Brand",
                "total_users",
                "total_units_sold",
                "total_purchased_amount",
                "total_sales_amount",
                "total_receipts"
            ],
            "rows": [
                ["Sensodyne", "11944", "38793", 592439.1500000464, 808739.14000007, "20529"],
                ["Scotts", "5859", "19098", 382604.8000000136, 493057.3000000183, "11628"],
                ["Polident", "3476", "19056", 288272.4199999844, 392956.0600000011, "12206"],
                ["Caltrate", "2863", "5134", 348721.7800000042, 371326.40000000445, "4592"],
                ["Centrum", "1523", "2787", 178778.3299999982, 193685.1399999982, "2444"],
                ["Panaflex", "870", "4285", 24933.020000000426, 37043.94000000076, "2513"],
                ["Panadol", "316", "1951", 11055.489999999974, 29882.030000000028, "416"],
                ["Parodontax", "415", "796", 10693.959999999983, 15701.869999999963, "498"],
                ["Eno", "301", "2246", 6438.559999999968, 10154.350000000082, "1145"],
                ["Calsource", "8", "8", 325.9099999999999, 325.9099999999999, "8"]
            ]
        }
    ],
    "charts": [
        {
            "id": "main",
            "type": "pie",
            "spec": {
                "xKey": "Brand",
                "yKey": "total_sales_amount",
                "series": [
                    {"name": "Total Sales Amount", "yKey": "total_sales_amount"}
                ]
            }
        },
        {
            "id": "main_2",
            "type": "bar",
            "spec": {
                "xKey": "Brand",
                "yKey": "total_units_sold",
                "series": [
                    {"name": "Total Units Sold", "yKey": "total_units_sold"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "composition_share",
        "used": {
            "tables": ["Haleon_Rewards_User_Performance_110925_SKUs"],
            "columns": [
                "Brand",
                "comuserid",
                "Total_Purchase_Units",
                "Total_Purchased_Amount",
                "Total Sales Amount",
                "receiptid"
            ]
        },
        "stats": {"elapsed": 0.030871617},
        "sql_present": True
    }
}

# ------------------------------
# Helpers
# ------------------------------
def load_primary_dataframe(report_dict: dict) -> pd.DataFrame:
    """Convert the first table in the report to a typed pandas DataFrame."""
    if not report_dict.get("tables"):
        return pd.DataFrame()

    table = report_dict["tables"][0]
    df = pd.DataFrame(table["rows"], columns=table["columns"])

    # Convert numeric columns to appropriate dtypes
    numeric_cols = [
        "total_users",
        "total_units_sold",
        "total_purchased_amount",
        "total_sales_amount",
        "total_receipts",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Add derived metrics (optional, useful for tooltips)
    if "total_sales_amount" in df.columns and df["total_sales_amount"].sum() > 0:
        df["sales_share"] = df["total_sales_amount"] / df["total_sales_amount"].sum()
    else:
        df["sales_share"] = 0.0

    return df


def render_summary(summary_list):
    st.subheader("Summary")
    if not summary_list:
        st.info("No summary available.")
        return
    for item in summary_list:
        st.markdown(f"- {item}")


def render_tables(report_dict: dict, df: pd.DataFrame):
    st.subheader("Tables")
    if not report_dict.get("tables"):
        st.info("No tables available.")
        return

    for table in report_dict["tables"]:
        name = table.get("name", "Table")
        st.markdown(f"**{name}**")
        # Build DF again to preserve column order in display
        display_df = pd.DataFrame(table["rows"], columns=table["columns"])
        # Apply consistent typing as with primary df
        for col in [
            "total_users",
            "total_units_sold",
            "total_purchased_amount",
            "total_sales_amount",
            "total_receipts",
        ]:
            if col in display_df.columns:
                display_df[col] = pd.to_numeric(display_df[col], errors="coerce")

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Brand": st.column_config.TextColumn("Brand"),
                "total_users": st.column_config.NumberColumn("Total Users", format="%d"),
                "total_units_sold": st.column_config.NumberColumn("Total Units Sold", format="%d"),
                "total_purchased_amount": st.column_config.NumberColumn("Total Purchased Amount", format="%.2f"),
                "total_sales_amount": st.column_config.NumberColumn("Total Sales Amount", format="%.2f"),
                "total_receipts": st.column_config.NumberColumn("Total Receipts", format="%d"),
            },
        )


def render_charts(report_dict: dict, df: pd.DataFrame):
    st.subheader("Charts")
    if df.empty:
        st.info("No data available to render charts.")
        return

    if not report_dict.get("charts"):
        st.info("No charts present in the report.")
        return

    for chart in report_dict["charts"]:
        chart_type = chart.get("type")
        spec = chart.get("spec", {})
        x_key = spec.get("xKey")
        y_key = spec.get("yKey")

        if chart_type == "pie" and x_key in df.columns and y_key in df.columns:
            st.markdown("**Total Sales Amount by Brand (Pie Chart)**")
            pie = (
                alt.Chart(df)
                .mark_arc(outerRadius=130, innerRadius=40)
                .encode(
                    theta=alt.Theta(field=y_key, type="quantitative"),
                    color=alt.Color(field=x_key, type="nominal", legend=alt.Legend(title="Brand")),
                    tooltip=[
                        alt.Tooltip(x_key, title="Brand"),
                        alt.Tooltip(y_key, title="Total Sales Amount", format=",.2f"),
                        alt.Tooltip("sales_share", title="Sales Share", format=".1%"),
                    ],
                )
            )
            st.altair_chart(pie, use_container_width=True)

        elif chart_type == "bar" and x_key in df.columns and y_key in df.columns:
            st.markdown("**Total Units Sold by Brand (Bar Chart)**")
            bar = (
                alt.Chart(df)
                .mark_bar()
                .encode(
                    x=alt.X(f"{x_key}:N", sort="-y", title="Brand"),
                    y=alt.Y(f"{y_key}:Q", title="Total Units Sold"),
                    tooltip=[
                        alt.Tooltip(x_key, title="Brand"),
                        alt.Tooltip(y_key, title="Total Units Sold", format=",d"),
                    ],
                    color=alt.Color(f"{x_key}:N", legend=None),
                )
            )
            st.altair_chart(bar, use_container_width=True)
        else:
            st.warning(
                f"Chart with id '{chart.get('id', 'unknown')}' could not be rendered due to missing keys or unsupported type."
            )


# ------------------------------
# App Layout
# ------------------------------
st.title("AI Report")

# Summary
render_summary(report.get("summary", []))

# Data
df_primary = load_primary_dataframe(report)

# Tables
render_tables(report, df_primary)

# Charts
render_charts(report, df_primary)

# Optional: Raw data for reference
with st.expander("Show raw report JSON"):
    st.json(report)
