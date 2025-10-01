import json
from typing import Dict, Any, List

import streamlit as st
import pandas as pd
import altair as alt


REPORT_JSON = r'''{
  "valid": true,
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
    "sql_present": true
  }
}'''


def load_report() -> Dict[str, Any]:
    return json.loads(REPORT_JSON)


def table_to_dataframe(table_obj: Dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame(table_obj.get("rows", []), columns=table_obj.get("columns", []))
    # Best-effort numeric conversion
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="ignore")
    return df


def get_first_table_df(report: Dict[str, Any]) -> pd.DataFrame:
    tables = report.get("tables", [])
    if not tables:
        return pd.DataFrame()
    return table_to_dataframe(tables[0])


def currency_columns(df: pd.DataFrame) -> List[str]:
    cols = []
    for c in df.columns:
        lc = str(c).lower()
        if "amount" in lc or "revenue" in lc or "sales" in lc or "purchased" in lc:
            if pd.api.types.is_numeric_dtype(df[c]):
                cols.append(c)
    return cols


def integer_like_columns(df: pd.DataFrame) -> List[str]:
    cols = []
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            if (df[c].dropna() == df[c].dropna().astype(int)).all():
                cols.append(c)
    return cols


def render_tables(report: Dict[str, Any]):
    tables = report.get("tables", [])
    if not tables:
        st.info("No tables available in the report.")
        return

    for idx, tbl in enumerate(tables, start=1):
        name = tbl.get("name") or f"Table {idx}"
        st.subheader(f"Table: {name}")
        df = table_to_dataframe(tbl)

        # Column configuration for nicer display
        col_config = {}
        # Currency-style numbers
        for c in currency_columns(df):
            col_config[c] = st.column_config.NumberColumn(label=c, format="$%,.2f")
        # Integer-like numbers
        for c in integer_like_columns(df):
            if c not in col_config:
                col_config[c] = st.column_config.NumberColumn(label=c, format=",d")

        st.dataframe(df, use_container_width=True, column_config=col_config)


def build_pie_chart(df: pd.DataFrame, x_key: str, y_key: str, title: str = "") -> alt.Chart:
    # Compute percentages for tooltip
    if y_key in df.columns and pd.api.types.is_numeric_dtype(df[y_key]):
        total = df[y_key].sum() if df[y_key].sum() != 0 else 1.0
        df = df.copy()
        df["_pct"] = (df[y_key] / total) * 100.0
    else:
        df = df.copy()
        df["_pct"] = 0.0

    chart = (
        alt.Chart(df)
        .mark_arc(outerRadius=120)
        .encode(
            theta=alt.Theta(field=y_key, type="quantitative"),
            color=alt.Color(field=x_key, type="nominal", legend=alt.Legend(title=x_key)),
            tooltip=[
                alt.Tooltip(x_key, type="nominal"),
                alt.Tooltip(y_key, type="quantitative", title=title or y_key, format=",.2f"),
                alt.Tooltip("_pct", type="quantitative", title="Share (%)", format=".2f")
            ],
        )
        .properties(title=title or f"{y_key} by {x_key}")
    )
    return chart


def build_bar_chart(df: pd.DataFrame, x_key: str, y_key: str, title: str = "") -> alt.Chart:
    # Sort bars by value descending by default
    sort_order = alt.SortField(field=y_key, order="descending")

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(field=x_key, type="nominal", sort=sort_order, title=x_key),
            y=alt.Y(field=y_key, type="quantitative", title=title or y_key),
            tooltip=[
                alt.Tooltip(x_key, type="nominal"),
                alt.Tooltip(y_key, type="quantitative", format=",.0f"),
            ],
        )
        .properties(title=title or f"{y_key} by {x_key}")
    )
    return chart


def render_charts(report: Dict[str, Any]):
    charts = report.get("charts", [])
    if not charts:
        st.info("No charts available in the report.")
        return

    base_df = get_first_table_df(report)
    if base_df.empty:
        st.warning("Charts could not be rendered because there is no table data.")
        return

    # Ensure numeric fields are numeric for charting
    for col in base_df.columns:
        if base_df[col].dtype == object:
            # try numeric coercion
            coerced = pd.to_numeric(base_df[col], errors="ignore")
            base_df[col] = coerced

    for ch in charts:
        ch_type = ch.get("type")
        spec = ch.get("spec", {})
        x_key = spec.get("xKey")
        # Prefer spec.yKey, else fallback to first series yKey
        y_key = spec.get("yKey")
        series = spec.get("series") or []
        if not y_key and series and isinstance(series, list) and series[0].get("yKey"):
            y_key = series[0].get("yKey")

        title = ""
        if series and isinstance(series, list) and series[0].get("name"):
            title = series[0].get("name")

        if not x_key or not y_key:
            st.warning(f"Skipping chart (missing keys): {ch}")
            continue

        st.subheader(f"Chart: {ch.get('id', ch_type).title()}")
        if ch_type == "pie":
            chart = build_pie_chart(base_df, x_key=x_key, y_key=y_key, title=title)
        elif ch_type == "bar":
            chart = build_bar_chart(base_df, x_key=x_key, y_key=y_key, title=title)
        else:
            st.warning(f"Unsupported chart type '{ch_type}'.")
            continue

        st.altair_chart(chart, use_container_width=True)


def render_summary(report: Dict[str, Any]):
    summary = report.get("summary", [])
    if not summary:
        return
    st.subheader("Summary")
    for line in summary:
        st.markdown(f"- {line}")


def render_meta(report: Dict[str, Any]):
    echo = report.get("echo", {})
    if not echo:
        return
    with st.expander("Report metadata"):
        st.write("Intent:", echo.get("intent"))
        used = echo.get("used", {})
        if used:
            st.write("Source tables:", used.get("tables"))
            st.write("Columns used:", used.get("columns"))
        stats = echo.get("stats", {})
        if stats:
            st.write("Generation stats:", stats)
        sql_present = echo.get("sql_present")
        if sql_present is not None:
            st.write("SQL present:", sql_present)


def main():
    st.set_page_config(page_title="AI Report App", layout="wide")
    st.title("AI Report App")

    report = load_report()

    # High-level validity/issue status
    if not report.get("valid", True):
        st.error("Report marked as invalid.")
    issues = report.get("issues", [])
    if issues:
        with st.expander("Issues detected in report"):
            for iss in issues:
                st.write("-", iss)

    # Sections
    render_summary(report)
    st.divider()
    render_tables(report)
    st.divider()
    render_charts(report)
    st.divider()
    render_meta(report)


if __name__ == "__main__":
    main()
