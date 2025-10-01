import streamlit as st
import pandas as pd
import altair as alt


def get_report_data():
    # Embedded report JSON provided by the user
    return {
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


def to_dataframe(table_obj: dict) -> pd.DataFrame:
    df = pd.DataFrame(table_obj.get("rows", []), columns=table_obj.get("columns", []))
    # Convert numeric-like columns to numeric types (except the Brand/categorical column)
    for col in df.columns:
        if col.lower() != "brand":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def render_summary(summary_list):
    st.subheader("Summary")
    if not summary_list:
        st.info("No summary provided.")
        return
    bullets = "\n".join([f"- {item}" for item in summary_list])
    st.markdown(bullets)


def render_tables(tables):
    if not tables:
        st.info("No tables to display.")
        return {}
    dataframes = {}
    for idx, tbl in enumerate(tables):
        name = tbl.get("name") or f"Table {idx+1}"
        st.subheader(f"Table: {name}")
        df = to_dataframe(tbl)
        dataframes[name] = df
        st.dataframe(df, use_container_width=True)
    return dataframes


def render_chart(chart_obj: dict, df_source: pd.DataFrame):
    chart_type = chart_obj.get("type")
    spec = chart_obj.get("spec", {})
    x_key = spec.get("xKey")
    y_key = spec.get("yKey")

    if df_source is None or df_source.empty:
        st.warning("No data available for chart rendering.")
        return

    if chart_type == "pie":
        if not x_key or not y_key:
            st.warning("Pie chart spec missing xKey or yKey.")
            return
        title = f"{y_key.replace('_', ' ').title()} by {x_key}"
        chart = (
            alt.Chart(df_source)
            .mark_arc(outerRadius=140)
            .encode(
                theta=alt.Theta(field=y_key, type="quantitative"),
                color=alt.Color(field=x_key, type="nominal", legend=alt.Legend(title=x_key)),
                tooltip=[
                    alt.Tooltip(field=x_key, type="nominal", title=x_key),
                    alt.Tooltip(field=y_key, type="quantitative", title=y_key.replace('_', ' ').title(), format=",.2f"),
                ],
            )
            .properties(title=title)
        )
        st.altair_chart(chart, use_container_width=True)

    elif chart_type == "bar":
        if not x_key or not y_key:
            st.warning("Bar chart spec missing xKey or yKey.")
            return
        title = f"{y_key.replace('_', ' ').title()} by {x_key}"
        chart = (
            alt.Chart(df_source)
            .mark_bar()
            .encode(
                x=alt.X(f"{x_key}:N", sort="-y", title=x_key),
                y=alt.Y(f"{y_key}:Q", title=y_key.replace('_', ' ').title()),
                tooltip=[
                    alt.Tooltip(field=x_key, type="nominal", title=x_key),
                    alt.Tooltip(field=y_key, type="quantitative", title=y_key.replace('_', ' ').title(), format=",.0f"),
                ],
            )
            .properties(title=title)
        )
        st.altair_chart(chart, use_container_width=True)

    else:
        st.info(f"Chart type '{chart_type}' is not supported in this app.")


def render_charts(charts, dataframes: dict):
    if not charts:
        st.info("No charts to display.")
        return

    # Default to the first available dataframe if multiple tables are present
    default_df = None
    if dataframes:
        # Pick the first dataframe deterministically
        first_key = list(dataframes.keys())[0]
        default_df = dataframes[first_key]

    st.subheader("Charts")
    for ch in charts:
        # Use default_df as the source since chart specs do not reference table names
        render_chart(ch, default_df)


def main():
    st.set_page_config(page_title="AI Report App", layout="wide")
    st.title("AI Report Dashboard")

    report = get_report_data()

    # Summary
    render_summary(report.get("summary", []))

    # Tables
    dataframes = render_tables(report.get("tables", []))

    # Charts
    render_charts(report.get("charts", []), dataframes)

    # Optional: show raw report JSON in an expander for transparency/debugging
    with st.expander("View raw report JSON"):
        st.json(report)


if __name__ == "__main__":
    main()
