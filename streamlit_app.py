import streamlit as st
import pandas as pd
import altair as alt

# Hardcoded report data (from provided JSON)
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

st.set_page_config(page_title="Brand Performance Report", layout="wide")
st.title("Brand Performance Report")

# Summary section
st.subheader("Summary")
if report.get("summary"):
    summary_md_lines = [f"- {item}" for item in report["summary"]]
    st.markdown("\n".join(summary_md_lines))
else:
    st.info("No summary available.")

# Utility: Convert DataFrame columns to numeric where possible (except brand-like columns)
def coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if col.lower() not in {"brand"}:
            out[col] = pd.to_numeric(out[col], errors="ignore")
    return out

# Render all tables
st.subheader("Tables")
all_tables = []
if report.get("tables"):
    for idx, tbl in enumerate(report["tables"]):
        name = tbl.get("name", f"Table {idx+1}")
        columns = tbl.get("columns", [])
        rows = tbl.get("rows", [])
        df = pd.DataFrame(rows, columns=columns)
        df = coerce_numeric(df)
        all_tables.append((name, df))
        st.markdown(f"**{name}**")
        st.dataframe(df, use_container_width=True)
else:
    st.info("No tables available.")

# Choose a primary DataFrame for charts (default to the first table if available)
primary_df = all_tables[0][1] if all_tables else pd.DataFrame()

# Helper: Ensure yKey is numeric for charting
def ensure_numeric(df: pd.DataFrame, key: str) -> pd.DataFrame:
    if key in df.columns:
        if not pd.api.types.is_numeric_dtype(df[key]):
            df = df.copy()
            df[key] = pd.to_numeric(df[key], errors="coerce")
    return df

# Render charts with Altair
st.subheader("Charts")
if report.get("charts") and not primary_df.empty:
    for ch in report["charts"]:
        ch_type = ch.get("type")
        spec = ch.get("spec", {})
        x_key = spec.get("xKey")
        y_key = spec.get("yKey")

        if not x_key or not y_key:
            continue

        df_plot = ensure_numeric(primary_df, y_key)

        if ch_type == "pie":
            # Pie chart using mark_arc
            chart = (
                alt.Chart(df_plot)
                .mark_arc(innerRadius=0)
                .encode(
                    theta=alt.Theta(field=y_key, type="quantitative"),
                    color=alt.Color(field=x_key, type="nominal", legend=alt.Legend(title=x_key)),
                    tooltip=[
                        alt.Tooltip(field=x_key, type="nominal", title=x_key),
                        alt.Tooltip(field=y_key, type="quantitative", title=y_key, format=",.2f"),
                    ],
                )
                .properties(title=f"{y_key} by {x_key}", height=420)
            )
            st.altair_chart(chart, use_container_width=True)

        elif ch_type == "bar":
            # Bar chart
            chart = (
                alt.Chart(df_plot)
                .mark_bar()
                .encode(
                    x=alt.X(field=x_key, type="nominal", sort='-y', title=x_key),
                    y=alt.Y(field=y_key, type="quantitative", title=y_key),
                    tooltip=[
                        alt.Tooltip(field=x_key, type="nominal", title=x_key),
                        alt.Tooltip(field=y_key, type="quantitative", title=y_key, format=","),
                    ],
                )
                .properties(title=f"{y_key} by {x_key}", height=420)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            # Unsupported type fallback (shouldn't happen given current spec)
            st.warning(f"Unsupported chart type: {ch_type}")
else:
    st.info("No charts available or no data to plot.")

# Footer / metadata
st.caption("Data source: Haleon Rewards (composition_share)")
