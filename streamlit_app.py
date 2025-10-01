import streamlit as st
import pandas as pd
import altair as alt

# Disable row limits for Altair data transformer to handle large dataframes
alt.data_transformers.disable_max_rows()

# Embedded report data
REPORT = {
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
                [
                    "Sensodyne",
                    "11944",
                    "38793",
                    592439.1500000464,
                    808739.14000007,
                    "20529"
                ],
                [
                    "Scotts",
                    "5859",
                    "19098",
                    382604.8000000136,
                    493057.3000000183,
                    "11628"
                ],
                [
                    "Polident",
                    "3476",
                    "19056",
                    288272.4199999844,
                    392956.0600000011,
                    "12206"
                ],
                [
                    "Caltrate",
                    "2863",
                    "5134",
                    348721.7800000042,
                    371326.40000000445,
                    "4592"
                ],
                [
                    "Centrum",
                    "1523",
                    "2787",
                    178778.3299999982,
                    193685.1399999982,
                    "2444"
                ],
                [
                    "Panaflex",
                    "870",
                    "4285",
                    24933.020000000426,
                    37043.94000000076,
                    "2513"
                ],
                [
                    "Panadol",
                    "316",
                    "1951",
                    11055.489999999974,
                    29882.030000000028,
                    "416"
                ],
                [
                    "Parodontax",
                    "415",
                    "796",
                    10693.959999999983,
                    15701.869999999963,
                    "498"
                ],
                [
                    "Eno",
                    "301",
                    "2246",
                    6438.559999999968,
                    10154.350000000082,
                    "1145"
                ],
                [
                    "Calsource",
                    "8",
                    "8",
                    325.9099999999999,
                    325.9099999999999,
                    "8"
                ]
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
                    {
                        "name": "Total Sales Amount",
                        "yKey": "total_sales_amount"
                    }
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
                    {
                        "name": "Total Units Sold",
                        "yKey": "total_units_sold"
                    }
                ]
            }
        }
    ],
    "echo": {
        "intent": "composition_share",
        "used": {
            "tables": [
                "Haleon_Rewards_User_Performance_110925_SKUs"
            ],
            "columns": [
                "Brand",
                "comuserid",
                "Total_Purchase_Units",
                "Total_Purchased_Amount",
                "Total Sales Amount",
                "receiptid"
            ]
        },
        "stats": {
            "elapsed": 0.030871617
        },
        "sql_present": True
    }
}


def build_dataframes(report_dict):
    """
    Convert tables in the report to pandas DataFrames and coerce numeric types where possible.
    Returns an ordered dict-like mapping of table name to DataFrame.
    """
    dfs = {}
    for tbl in report_dict.get("tables", []):
        name = tbl.get("name") or "Table"
        columns = tbl.get("columns", [])
        rows = tbl.get("rows", [])
        df = pd.DataFrame(rows, columns=columns)
        # Attempt to convert all columns to numeric when possible
        for c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="ignore")
        dfs[name] = df
    return dfs


def find_df_for_fields(dfs, fields):
    """Find the first dataframe that contains all specified field names."""
    if not fields:
        # If no fields were requested, return the first df (if any)
        for name, df in dfs.items():
            return name, df
        return None, None
    for name, df in dfs.items():
        if all(f in df.columns for f in fields):
            return name, df
    return None, None


def render_pie_chart(df, x_key, y_key, title=None):
    chart = (
        alt.Chart(df)
        .mark_arc(outerRadius=120, innerRadius=40)
        .encode(
            theta=alt.Theta(field=y_key, type="quantitative"),
            color=alt.Color(field=x_key, type="nominal", legend=alt.Legend(title=x_key)),
            tooltip=[
                alt.Tooltip(field=x_key, type="nominal", title=x_key),
                alt.Tooltip(field=y_key, type="quantitative", title=y_key, format=",")
            ],
        )
        .properties(title=title)
    )
    st.altair_chart(chart, use_container_width=True)


def render_bar_chart(df, x_key, y_key, series=None, title=None):
    # If multiple series are provided, fold them into long format
    if series and len(series) > 1:
        y_fields = [s.get("yKey") for s in series if s.get("yKey")]
        use_cols = [x_key] + y_fields
        melted = df[use_cols].melt(id_vars=[x_key], value_vars=y_fields, var_name="Series", value_name="Value")
        chart = (
            alt.Chart(melted)
            .mark_bar()
            .encode(
                x=alt.X(f"{x_key}:N", sort="-y", title=x_key),
                y=alt.Y("Value:Q", title="Value"),
                color=alt.Color("Series:N", title="Series"),
                tooltip=[
                    alt.Tooltip(field=x_key, type="nominal", title=x_key),
                    alt.Tooltip("Series:N", title="Series"),
                    alt.Tooltip("Value:Q", title="Value", format=",")
                ],
            )
            .properties(title=title)
        )
    else:
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X(f"{x_key}:N", sort="-y", title=x_key),
                y=alt.Y(f"{y_key}:Q", title=y_key),
                tooltip=[
                    alt.Tooltip(field=x_key, type="nominal", title=x_key),
                    alt.Tooltip(field=y_key, type="quantitative", title=y_key, format=",")
                ],
            )
            .properties(title=title)
        )
    st.altair_chart(chart, use_container_width=True)


def main():
    st.set_page_config(page_title="AI Report Dashboard", layout="wide")
    st.title("AI Report Dashboard")
    st.caption("This dashboard renders the provided JSON report with summary, tables, and charts.")

    # Summary
    summary_items = REPORT.get("summary") or []
    if summary_items:
        st.subheader("Summary")
        st.markdown("\n".join([f"- {item}" for item in summary_items]))

    # Tables
    dfs = build_dataframes(REPORT)
    if dfs:
        st.subheader("Tables")
        for name, df in dfs.items():
            st.markdown(f"### {name}")
            st.dataframe(df, use_container_width=True)

    # Charts
    charts = REPORT.get("charts") or []
    if charts:
        st.subheader("Charts")
        for chart_cfg in charts:
            chart_id = chart_cfg.get("id", "")
            ctype = chart_cfg.get("type")
            spec = chart_cfg.get("spec", {})
            x_key = spec.get("xKey")
            y_key = spec.get("yKey")
            series = spec.get("series", [])

            # Find a dataframe containing both keys
            df_name, df = find_df_for_fields(dfs, [x_key, y_key] if x_key and y_key else [])
            if df is None:
                st.warning(f"Chart '{chart_id}' skipped: could not find a table containing fields '{x_key}' and '{y_key}'.")
                continue

            if ctype == "pie":
                title = f"Pie: {y_key} by {x_key}"
                render_pie_chart(df, x_key, y_key, title=title)
            elif ctype == "bar":
                title = f"Bar: {y_key} by {x_key}"
                render_bar_chart(df, x_key, y_key, series=series, title=title)
            else:
                st.info(f"Unsupported chart type '{ctype}' for chart id '{chart_id}'. Displaying raw spec:")
                st.json(chart_cfg)

    with st.expander("Raw report JSON"):
        st.json(REPORT)


if __name__ == "__main__":
    main()
