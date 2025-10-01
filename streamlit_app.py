import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Brand Performance Report", layout="wide")

# -------
# Embedded report data (from provided JSON)
# -------
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

# -------
# Helpers
# -------

def coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    # Attempt to convert columns to numeric when possible
    for c in df.columns:
        if df[c].dtype == object:
            coerced = pd.to_numeric(df[c], errors='ignore')
            df[c] = coerced
    return df


def make_pie(df: pd.DataFrame, x_key: str, y_key: str, title: str = "") -> alt.Chart:
    # Pie (arc) chart using Altair
    tooltip = [
        alt.Tooltip(x_key, type='nominal', title=x_key),
        alt.Tooltip(y_key, type='quantitative', title=y_key, format=",")
    ]
    chart = (
        alt.Chart(df)
        .mark_arc()
        .encode(
            theta=alt.Theta(field=y_key, type='quantitative'),
            color=alt.Color(field=x_key, type='nominal', legend=alt.Legend(title=x_key)),
            tooltip=tooltip
        )
        .properties(title=title)
    )
    return chart


def make_bar(df: pd.DataFrame, x_key: str, y_key: str, title: str = "") -> alt.Chart:
    tooltip = [
        alt.Tooltip(x_key, type='nominal', title=x_key),
        alt.Tooltip(y_key, type='quantitative', title=y_key, format=",")
    ]
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(field=x_key, type='nominal', sort='-y', title=x_key),
            y=alt.Y(field=y_key, type='quantitative', title=y_key),
            color=alt.Color(field=x_key, type='nominal', legend=None),
            tooltip=tooltip
        )
        .properties(title=title)
    )
    return chart


# -------
# App UI
# -------
st.title("Brand Performance Report")
if report.get("echo", {}).get("used", {}).get("tables"):
    src_table_names = ", ".join(report["echo"]["used"]["tables"])
    st.caption(f"Source: {src_table_names}")

# Summary
st.subheader("Summary")
for item in report.get("summary", []):
    st.markdown(f"- {item}")

# Load tables into DataFrames
st.subheader("Tables")
dataframes = {}
for idx, tbl in enumerate(report.get("tables", [])):
    name = tbl.get("name", f"Table {idx+1}")
    columns = tbl.get("columns", [])
    rows = tbl.get("rows", [])
    df = pd.DataFrame(rows, columns=columns)
    df = coerce_numeric(df)
    dataframes[name] = df
    st.markdown(f"Table: {name}")
    st.dataframe(df, use_container_width=True)

# Use the first table as default data source for charts
default_df = None
if dataframes:
    # Get the first dataframe in insertion order
    first_key = list(dataframes.keys())[0]
    default_df = dataframes[first_key]

# Charts
st.subheader("Charts")
if not report.get("charts"):
    st.info("No charts available in the report.")
else:
    for chart_spec in report["charts"]:
        ctype = chart_spec.get("type")
        spec = chart_spec.get("spec", {})
        x_key = spec.get("xKey")
        y_key = spec.get("yKey")

        # Data selection: try to find a table containing the required columns; fallback to first
        df_for_chart = None
        for name, df in dataframes.items():
            if x_key in df.columns and y_key in df.columns:
                df_for_chart = df
                break
        if df_for_chart is None:
            df_for_chart = default_df

        if df_for_chart is None:
            st.warning("No data available for chart rendering.")
            continue

        if ctype == "pie":
            chart = make_pie(df_for_chart, x_key, y_key, title=f"Pie: {y_key} by {x_key}")
            st.altair_chart(chart, use_container_width=True)
        elif ctype == "bar":
            chart = make_bar(df_for_chart, x_key, y_key, title=f"Bar: {y_key} by {x_key}")
            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning(f"Unsupported chart type: {ctype}")

# Footer/meta
with st.expander("Report Metadata", expanded=False):
    st.write({k: v for k, v in report.items() if k not in ["tables", "charts", "summary"]})
