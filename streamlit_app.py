import streamlit as st
import pandas as pd
import altair as alt
import json

# -------------------------------
# Embedded report JSON
# -------------------------------
REPORT = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered users decreased from 4,998 in Q1 to 3,826 in Q2 2025 (-23.43%).",
        "Total sales dropped from 461,543.37 in Q1 to 371,077.93 in Q2 2025 (-19.63%).",
        "Total units purchased fell from 19,603 in Q1 to 15,482 in Q2 2025 (-21.02%).",
        "Both user registration and sales performance were lower in Q2 compared to Q1 2025."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["period", "registered_users", "total_sales", "total_units"],
            "rows": [["Q1", "4998", 461543.3700000002, "19603"], ["Q2", "3826", 371077.93, "15482"]]
        }
    ],
    "charts": [
        {
            "id": "main",
            "type": "groupedBar",
            "spec": {
                "xKey": "period",
                "yKey": "",
                "series": [
                    {"name": "Registered Users", "yKey": "registered_users"},
                    {"name": "Total Sales", "yKey": "total_sales"},
                    {"name": "Total Units", "yKey": "total_units"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "comparison_totals",
        "used": {
            "tables": ["`Haleon_Rewards_User_Performance_110925_list`", "`Haleon_Rewards_User_Performance_110925_SKUs`"],
            "columns": ["\"user_id\"", "\"Total Sales Amount\"", "\"Total_Purchase_Units\"", "\"Upload_Date\"", "\"comuserid\""]
        },
        "stats": {"elapsed": 0.04843408},
        "sql_present": True
    }
}

# -------------------------------
# Utility functions
# -------------------------------

def coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Attempt to convert columns that look numeric to numeric types."""
    for col in df.columns:
        # Don't convert the x-axis category if it's likely categorical like 'period'
        if df[col].dtype == object:
            converted = pd.to_numeric(df[col], errors="ignore")
            df[col] = converted
    return df


def dataframe_from_table(table_obj: dict) -> pd.DataFrame:
    df = pd.DataFrame(table_obj.get("rows", []), columns=table_obj.get("columns", []))
    df = coerce_numeric_columns(df)
    return df


def render_grouped_bar(df: pd.DataFrame, spec: dict, title: str = ""):
    x_key = spec.get("xKey")
    series = spec.get("series", [])
    if not x_key or not series:
        st.warning("Grouped bar spec is incomplete.")
        return

    # Ensure columns exist
    y_keys = [s.get("yKey") for s in series if s.get("yKey") in df.columns]
    if x_key not in df.columns or len(y_keys) == 0:
        st.warning("Chart columns not found in data table.")
        return

    # Prepare long format
    work_df = df[[x_key] + y_keys].copy()
    work_df = work_df.melt(id_vars=[x_key], value_vars=y_keys, var_name="metric_key", value_name="value")

    # Map metric display names
    name_map = {s.get("yKey"): s.get("name", s.get("yKey")) for s in series if s.get("yKey")}
    work_df["metric"] = work_df["metric_key"].map(name_map)

    # Ensure numeric values
    work_df["value"] = pd.to_numeric(work_df["value"], errors="coerce")

    # Build chart
    chart = (
        alt.Chart(work_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_key}:N", title=x_key),
            y=alt.Y("value:Q", title="Value", axis=alt.Axis(format=",.2f")),
            color=alt.Color("metric:N", title="Metric"),
            xOffset="metric:N",
            tooltip=[
                alt.Tooltip(f"{x_key}:N", title=x_key.title()),
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip("value:Q", title="Value", format=",.2f"),
            ],
        )
        .properties(title=title or "Grouped Bar", width=500, height=360)
        .configure_legend(orient="bottom")
    )

    st.altair_chart(chart, use_container_width=True)


def render_chart(chart_obj: dict, data_tables: list[pd.DataFrame]):
    ctype = (chart_obj or {}).get("type", "").lower()
    spec = (chart_obj or {}).get("spec", {})

    # Choose the first table by default if multiple are present
    df = data_tables[0] if data_tables else pd.DataFrame()

    if ctype == "groupedbar":
        title = chart_obj.get("id", "")
        render_grouped_bar(df, spec, title=title)
    elif ctype == "bar":
        # Basic bar support if spec contains xKey and yKey
        x_key = spec.get("xKey")
        y_key = spec.get("yKey")
        if x_key in df.columns and y_key in df.columns:
            chart = (
                alt.Chart(df)
                .mark_bar()
                .encode(
                    x=alt.X(f"{x_key}:N" if df[x_key].dtype == object else f"{x_key}:Q", title=x_key),
                    y=alt.Y(f"{y_key}:Q", title=y_key, axis=alt.Axis(format=",.2f")),
                    tooltip=[x_key, alt.Tooltip(y_key, format=",.2f")],
                )
                .properties(title=chart_obj.get("id", "Bar"), height=360)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("Bar chart spec keys not found in data table.")
    elif ctype == "pie":
        # Expect spec: categoryKey, valueKey
        category = spec.get("categoryKey")
        value = spec.get("valueKey")
        if category in df.columns and value in df.columns:
            base = alt.Chart(df).encode(theta=alt.Theta(f"{value}:Q"), color=alt.Color(f"{category}:N"))
            chart = base.mark_arc(outerRadius=120).properties(title=chart_obj.get("id", "Pie"), height=360)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("Pie chart spec keys not found in data table.")
    else:
        st.info(f"Unsupported or unspecified chart type: {chart_obj.get('type')}")


# -------------------------------
# Streamlit App
# -------------------------------

def main():
    st.set_page_config(page_title="AI Report App", layout="wide")
    st.title("AI Report App")

    # Display summary
    st.subheader("Summary")
    if REPORT.get("summary"):
        bullets = "\n".join([f"- {item}" for item in REPORT["summary"]])
        st.markdown(bullets)
    else:
        st.write("No summary available.")

    # Prepare tables
    st.subheader("Tables")
    dataframes = []
    if REPORT.get("tables"):
        for idx, tbl in enumerate(REPORT["tables"]):
            df = dataframe_from_table(tbl)
            dataframes.append(df)
            table_title = tbl.get("name") or f"Table {idx+1}"
            st.markdown(f"**{table_title}**")
            st.dataframe(df, use_container_width=True)
    else:
        st.write("No tables available.")

    # Charts
    st.subheader("Charts")
    if REPORT.get("charts"):
        for chart_obj in REPORT["charts"]:
            try:
                render_chart(chart_obj, dataframes)
            except Exception as e:
                st.error(f"Error rendering chart '{chart_obj.get('id','')}': {e}")
    else:
        st.write("No charts available.")

    # Optional: raw JSON in an expander for transparency
    with st.expander("View raw report JSON"):
        st.code(json.dumps(REPORT, indent=2), language="json")


if __name__ == "__main__":
    main()
