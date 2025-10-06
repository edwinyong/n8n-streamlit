import streamlit as st
import pandas as pd
import altair as alt

# -----------------------------
# Embedded report JSON (as Python dict)
# -----------------------------
REPORT = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered users decreased from 4,998 in 2025 Q1 to 3,826 in 2025 Q2, a drop of 1,172 users (-23.45%).",
        "Total sales fell from 461,543.37 in 2025 Q1 to 371,077.93 in 2025 Q2, a decrease of 90,465.44 (-19.61%).",
        "Both registered users and sales were higher in 2025 Q1 compared to Q2."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["period", "registered_users", "total_sales"],
            "rows": [
                ["2025 Q1", "4998", 461543.37000000733],
                ["2025 Q2", "3826", 371077.93000000285]
            ]
        }
    ],
    "charts": [
        {
            "id": "main",
            "type": "groupedBar",
            "spec": {
                "xKey": "period",
                "yKey": "value",
                "series": [
                    {"name": "Registered Users", "yKey": "registered_users"},
                    {"name": "Total Sales", "yKey": "total_sales"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "comparison_totals",
        "used": {
            "tables": [
                "`Haleon_Rewards_User_Performance_110925_user_list`",
                "`Haleon_Rewards_User_Performance_110925_SKUs`"
            ],
            "columns": ["user_id", "Upload_Date", "Total Sales Amount", "comuserid"]
        },
        "stats": {"elapsed": 0.070259202},
        "sql_present": True
    }
}

# -----------------------------
# Streamlit App
# -----------------------------
st.set_page_config(page_title="User & Sales Report (2025 Q1 vs Q2)", layout="wide")
alt.data_transformers.disable_max_rows()

st.title("User & Sales Report")
st.caption("A Streamlit app rendering summaries, tables, and Altair charts from a JSON report.")

# -----------------------------
# Helper functions
# -----------------------------

def to_dataframe(table_dict: dict) -> pd.DataFrame:
    df = pd.DataFrame(table_dict.get("rows", []), columns=table_dict.get("columns", []))
    # Attempt safe numeric conversion for columns that are fully numeric
    for col in df.columns:
        # Remove common thousands separators before attempting conversion
        series_str = df[col].astype(str).str.replace(",", "", regex=False)
        converted = pd.to_numeric(series_str, errors="coerce")
        # Convert only if all non-null and original length match (i.e., fully numeric or NA)
        if converted.notna().sum() == len(df):
            df[col] = converted
    return df


def render_grouped_bar(df: pd.DataFrame, x_key: str, series: list, title: str = None):
    # Build a long-form dataframe: [x_key, metric, value]
    long_parts = []
    for s in series:
        metric_name = s.get("name") or s.get("yKey")
        y_key = s.get("yKey")
        if y_key not in df.columns:
            continue
        part = pd.DataFrame({
            x_key: df[x_key],
            "metric": metric_name,
            "value": pd.to_numeric(df[y_key], errors="coerce")
        })
        long_parts.append(part)
    if not long_parts:
        st.warning("No valid series found to render grouped bar chart.")
        return
    long_df = pd.concat(long_parts, ignore_index=True)

    # Determine a reasonable width based on number of categories
    categories = long_df[x_key].unique().tolist()
    width = max(300, 80 * len(categories))

    chart = (
        alt.Chart(long_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_key}:N", title=x_key),
            y=alt.Y("value:Q", title="Value"),
            color=alt.Color("metric:N", title="Metric"),
            xOffset=alt.XOffset("metric:N"),
            tooltip=[alt.Tooltip(f"{x_key}:N", title=x_key), alt.Tooltip("metric:N"), alt.Tooltip("value:Q")],
        )
        .properties(width=width, height=400, title=title)
    )
    st.altair_chart(chart, use_container_width=True)


def render_bar(df: pd.DataFrame, x_key: str, y_key: str, title: str = None, color_key: str = None):
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_key}:N", title=x_key),
            y=alt.Y(f"{y_key}:Q", title=y_key),
            color=(alt.Color(f"{color_key}:N") if color_key else alt.value("steelblue")),
            tooltip=[alt.Tooltip(f"{x_key}:N", title=x_key), alt.Tooltip(f"{y_key}:Q", title=y_key)],
        )
        .properties(height=400, title=title)
    )
    st.altair_chart(chart, use_container_width=True)


def render_pie(df: pd.DataFrame, category_key: str, value_key: str, title: str = None):
    chart = (
        alt.Chart(df)
        .mark_arc(innerRadius=40)
        .encode(
            theta=alt.Theta(f"{value_key}:Q", title=value_key),
            color=alt.Color(f"{category_key}:N", title=category_key),
            tooltip=[alt.Tooltip(f"{category_key}:N", title=category_key), alt.Tooltip(f"{value_key}:Q", title=value_key)],
        )
        .properties(height=400, title=title)
    )
    st.altair_chart(chart, use_container_width=True)


# -----------------------------
# Render Summary
# -----------------------------
st.subheader("Summary")
if REPORT.get("summary"):
    for item in REPORT["summary"]:
        st.markdown(f"- {item}")
else:
    st.info("No summary available.")

# -----------------------------
# Render Tables
# -----------------------------
st.subheader("Tables")
base_df = None
if REPORT.get("tables"):
    for idx, tbl in enumerate(REPORT["tables"], start=1):
        df = to_dataframe(tbl)
        if base_df is None:
            base_df = df.copy()
        table_name = tbl.get("name") or f"Table {idx}"
        st.markdown(f"**{table_name}**")
        st.dataframe(df, use_container_width=True)
else:
    st.info("No tables provided in the report.")

# -----------------------------
# Render Charts (Altair)
# -----------------------------
st.subheader("Charts")
if REPORT.get("charts"):
    if base_df is None and REPORT.get("tables"):
        # Fallback: build from first table
        base_df = to_dataframe(REPORT["tables"][0])

    for ch in REPORT["charts"]:
        ch_type = (ch.get("type") or "").lower()
        ch_id = ch.get("id") or "chart"
        spec = ch.get("spec", {})

        with st.container():
            st.markdown(f"**Chart: {ch_id}**")
            if ch_type == "groupedbar":
                x_key = spec.get("xKey")
                series = spec.get("series", [])
                if base_df is None:
                    st.warning("No base data available for grouped bar chart.")
                elif not x_key or not series:
                    st.warning("Grouped bar chart spec missing xKey or series.")
                else:
                    # Ensure x_key exists and numeric columns are numeric
                    df_chart = base_df.copy()
                    if x_key not in df_chart.columns:
                        st.warning(f"xKey '{x_key}' not found in data.")
                    else:
                        render_grouped_bar(df_chart, x_key=x_key, series=series, title=None)

            elif ch_type == "bar":
                x_key = spec.get("xKey")
                y_key = spec.get("yKey")
                color_key = spec.get("colorKey")
                if base_df is None:
                    st.warning("No base data available for bar chart.")
                elif not x_key or not y_key:
                    st.warning("Bar chart spec missing xKey or yKey.")
                else:
                    df_chart = base_df.copy()
                    render_bar(df_chart, x_key=x_key, y_key=y_key, title=None, color_key=color_key)

            elif ch_type == "pie":
                cat_key = spec.get("categoryKey") or spec.get("xKey")
                val_key = spec.get("valueKey") or spec.get("yKey")
                if base_df is None:
                    st.warning("No base data available for pie chart.")
                elif not cat_key or not val_key:
                    st.warning("Pie chart spec missing categoryKey/xKey or valueKey/yKey.")
                else:
                    df_chart = base_df.copy()
                    render_pie(df_chart, category_key=cat_key, value_key=val_key, title=None)

            else:
                st.info(f"Chart type '{ch.get('type')}' not recognized. Supported: groupedBar, bar, pie.")
else:
    st.info("No charts provided in the report.")

# -----------------------------
# Optional: Show data provenance / echo
# -----------------------------
with st.expander("Report Metadata / Provenance", expanded=False):
    st.write({k: v for k, v in REPORT.items() if k in ["valid", "issues"]})
    echo = REPORT.get("echo") or {}
    if echo:
        st.write(echo)

st.caption("Built with Streamlit, Pandas, and Altair.")
