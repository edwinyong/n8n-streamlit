import streamlit as st
import pandas as pd
import altair as alt

# -----------------------------
# Embedded Report JSON
# -----------------------------
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


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        # Try to convert everything except likely categorical text columns
        if df[col].dtype == object and col.lower() not in {"brand"}:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def build_tables(report: dict) -> list[tuple[str, pd.DataFrame]]:
    tables_out = []
    for t in report.get("tables", []):
        name = t.get("name") or "Table"
        cols = t.get("columns", [])
        rows = t.get("rows", [])
        df = pd.DataFrame(rows, columns=cols)
        df = _coerce_numeric(df)
        tables_out.append((name, df))
    return tables_out


def pie_chart(df: pd.DataFrame, x_key: str, y_key: str, title: str | None = None) -> alt.Chart:
    chart = (
        alt.Chart(df)
        .mark_arc(outerRadius=150)
        .encode(
            theta=alt.Theta(field=y_key, type="quantitative"),
            color=alt.Color(field=x_key, type="nominal", legend=alt.Legend(title=x_key)),
            tooltip=[
                alt.Tooltip(field=x_key, type="nominal", title=x_key),
                alt.Tooltip(field=y_key, type="quantitative", title=y_key, format=",.2f"),
            ],
        )
    )
    if title:
        chart = chart.properties(title=title)
    return chart


def bar_chart(df: pd.DataFrame, x_key: str, y_key: str, title: str | None = None) -> alt.Chart:
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_key}:N", sort="-y", title=x_key),
            y=alt.Y(f"{y_key}:Q", title=y_key),
            color=alt.Color(f"{x_key}:N", legend=None),
            tooltip=[
                alt.Tooltip(field=x_key, type="nominal", title=x_key),
                alt.Tooltip(field=y_key, type="quantitative", title=y_key, format=",.2f"),
            ],
        )
    )
    if title:
        chart = chart.properties(title=title)
    return chart


def render_charts(report: dict, tables: list[tuple[str, pd.DataFrame]]):
    if not report.get("charts"):
        st.info("No charts available in the report.")
        return

    # Use the first table as the default data source for charts
    if not tables:
        st.warning("No table data available to render charts.")
        return
    _, df0 = tables[0]

    st.header("Charts")
    for ch in report.get("charts", []):
        ch_id = ch.get("id", "chart")
        ch_type = ch.get("type", "")
        spec = ch.get("spec", {})
        x_key = spec.get("xKey")
        # yKey may be directly in spec or nested inside first series
        y_key = spec.get("yKey")
        series = spec.get("series", [])
        series_name = None
        if not y_key and series:
            y_key = series[0].get("yKey")
        if series:
            series_name = series[0].get("name")

        if not x_key or not y_key:
            st.warning(f"Chart '{ch_id}' missing xKey or yKey; skipping.")
            continue

        title = None
        if series_name:
            title = f"{series_name} by {x_key}"
        else:
            title = f"{y_key} by {x_key}"

        # Ensure the required columns are present and numeric where needed
        if x_key not in df0.columns or y_key not in df0.columns:
            st.warning(f"Chart '{ch_id}': required columns not found in data; skipping.")
            continue

        # Build and render the Altair chart
        if ch_type.lower() == "pie":
            chart = pie_chart(df0, x_key, y_key, title=title)
        elif ch_type.lower() == "bar":
            chart = bar_chart(df0, x_key, y_key, title=title)
        else:
            st.warning(f"Chart '{ch_id}': unsupported chart type '{ch_type}'.")
            continue

        st.altair_chart(chart, use_container_width=True)


def main():
    st.set_page_config(page_title="AI Report App", layout="wide")
    st.title("AI Report Viewer")

    # Summary
    st.header("Summary")
    if REPORT.get("summary"):
        bullets = "\n".join([f"- {item}" for item in REPORT["summary"]])
        st.markdown(bullets)
    else:
        st.info("No summary provided.")

    # Tables
    st.header("Tables")
    tables = build_tables(REPORT)
    if not tables:
        st.info("No tables available in the report.")
    else:
        for name, df in tables:
            st.subheader(name)
            st.dataframe(df, use_container_width=True)

    # Charts
    render_charts(REPORT, tables)

    # Optional: Show raw JSON in an expander for transparency/debugging
    with st.expander("Show raw report JSON"):
        st.json(REPORT)


if __name__ == "__main__":
    main()
