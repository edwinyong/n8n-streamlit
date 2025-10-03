import streamlit as st
import pandas as pd
import altair as alt

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="AI Report App", layout="wide")
alt.data_transformers.disable_max_rows()

# -----------------------------
# Embedded report JSON (as Python dict)
# -----------------------------
report = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered users in 2025 Q2 decreased to 3,826 from 4,998 in Q1 (-23.43%).",
        "Total sales in 2025 Q2 dropped to 371,077.93 from 461,543.37 in Q1 (-19.63%).",
        "Both registered user count and sales performance were lower in Q2 compared to Q1 2025."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["period", "registered_users", "total_sales"],
            "rows": [["Q1", "4998", 461543.3700000002], ["Q2", "3826", 371077.93]]
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
                    {"name": "Total Sales", "yKey": "total_sales"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "comparison_totals",
        "used": {
            "tables": ["`Haleon_Rewards_User_Performance_110925_list`"],
            "columns": ['"user_id"', '"Total Sales Amount"', '"Upload_Date"']
        },
        "stats": {"elapsed": 0.04843408},
        "sql_present": True
    }
}

# -----------------------------
# Helper functions
# -----------------------------

def to_dataframe(table_obj: dict) -> pd.DataFrame:
    """Convert a table object from the report to a pandas DataFrame with best-effort numeric coercion."""
    df = pd.DataFrame(table_obj.get("rows", []), columns=table_obj.get("columns", []))
    # Best-effort numeric conversion for each column
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="ignore")
    return df


def render_grouped_bar(spec: dict, df: pd.DataFrame) -> alt.Chart:
    """Render a grouped bar chart using Altair from the provided spec and dataframe.

    Expects spec with keys: xKey, series (list of {name, yKey}).
    """
    x_key = spec.get("xKey")
    if not x_key:
        # Fallback to first column if not specified
        x_key = df.columns[0]

    series_list = spec.get("series", [])
    value_vars = [s.get("yKey") for s in series_list if s.get("yKey")]

    # Validate presence of columns
    missing = [c for c in value_vars + [x_key] if c not in df.columns]
    if missing:
        st.warning(f"Cannot render grouped bar: missing columns {missing}")
        return None

    # Coerce value_vars to numeric where possible
    df2 = df.copy()
    for c in value_vars:
        df2[c] = pd.to_numeric(df2[c], errors="coerce")

    # Melt to long format for grouped bar
    long_df = df2.melt(id_vars=[x_key], value_vars=value_vars, var_name="series_key", value_name="value")

    # Map yKey to display name
    name_map = {s.get("yKey"): s.get("name", s.get("yKey")) for s in series_list}
    long_df["series_name"] = long_df["series_key"].map(name_map).fillna(long_df["series_key"]) 

    # Build chart
    chart = (
        alt.Chart(long_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_key}:N", title=x_key),
            xOffset=alt.XOffset("series_name:N"),
            y=alt.Y("value:Q", title="Value"),
            color=alt.Color("series_name:N", title="Series"),
            tooltip=[
                alt.Tooltip(f"{x_key}:N", title=x_key),
                alt.Tooltip("series_name:N", title="Series"),
                alt.Tooltip("value:Q", title="Value", format=",.2f"),
            ],
        )
        .properties(height=380)
        .interactive()
    )
    return chart


def render_chart(chart_obj: dict, tables_map: dict):
    """Dispatch rendering based on chart type. Uses the first table if none specified."""
    ctype = (chart_obj or {}).get("type", "").lower()
    spec = (chart_obj or {}).get("spec", {})

    # Choose a data source: use the first table by default
    df = None
    if tables_map:
        # Grab the first DataFrame in the map
        df = next(iter(tables_map.values()))

    if df is None or df.empty:
        st.info("No data available to render charts.")
        return

    if ctype in ("groupedbar", "grouped_bar", "group-bar"):
        chart = render_grouped_bar(spec, df)
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        return

    # Basic bar chart (single series) fallback if type is 'bar' and spec.yKey provided
    if ctype == "bar":
        x_key = spec.get("xKey") or df.columns[0]
        y_key = spec.get("yKey")
        if y_key and y_key in df.columns:
            c = (
                alt.Chart(df)
                .mark_bar()
                .encode(
                    x=alt.X(f"{x_key}:N", title=x_key),
                    y=alt.Y(f"{y_key}:Q", title=y_key),
                    tooltip=[x_key, alt.Tooltip(f"{y_key}:Q", format=",.2f")],
                    color=alt.value("#1f77b4"),
                )
                .properties(height=380)
                .interactive()
            )
            st.altair_chart(c, use_container_width=True)
            return

    # Basic line chart
    if ctype == "line":
        x_key = spec.get("xKey") or df.columns[0]
        y_key = spec.get("yKey")
        if y_key and y_key in df.columns:
            c = (
                alt.Chart(df)
                .mark_line(point=True)
                .encode(
                    x=alt.X(f"{x_key}:N", title=x_key),
                    y=alt.Y(f"{y_key}:Q", title=y_key),
                    color=alt.value("#ff7f0e"),
                    tooltip=[x_key, alt.Tooltip(f"{y_key}:Q", format=",.2f")],
                )
                .properties(height=380)
                .interactive()
            )
            st.altair_chart(c, use_container_width=True)
            return

    # Basic pie chart (requires spec with categoryKey and valueKey); included for completeness
    if ctype == "pie":
        category_key = spec.get("categoryKey") or df.columns[0]
        value_key = spec.get("valueKey") or df.columns[1] if len(df.columns) > 1 else None
        if value_key and value_key in df.columns:
            c = (
                alt.Chart(df)
                .mark_arc()
                .encode(
                    theta=alt.Theta(f"{value_key}:Q", stack=True),
                    color=alt.Color(f"{category_key}:N", legend=True),
                    tooltip=[category_key, alt.Tooltip(f"{value_key}:Q", format=",.2f")],
                )
                .properties(height=380)
            )
            st.altair_chart(c, use_container_width=True)
            return

    # If we reach here, type is not supported
    st.warning(f"Unsupported chart type: {chart_obj.get('type')}. Displaying raw spec below.")
    with st.expander("Raw chart spec"):
        st.json(chart_obj)


# -----------------------------
# App layout
# -----------------------------
st.title("AI Report Dashboard")
st.caption("Auto-generated Streamlit app rendering summary, tables, and charts from a JSON report.")

# Summary section
st.header("Summary")
summary_items = report.get("summary", [])
if summary_items:
    for s in summary_items:
        st.markdown(f"- {s}")
else:
    st.info("No summary available.")

# Tables section
st.header("Tables")
tables = report.get("tables", [])
tables_map = {}
if tables:
    for idx, t in enumerate(tables, start=1):
        name = t.get("name") or f"Table {idx}"
        df = to_dataframe(t)
        tables_map[name] = df
        st.subheader(name)
        st.dataframe(df, use_container_width=True)
else:
    st.info("No tables available.")

# Charts section
st.header("Charts")
charts = report.get("charts", [])
if charts:
    for ch in charts:
        chart_title = ch.get("id") or ch.get("type", "Chart")
        st.subheader(str(chart_title).title())
        render_chart(ch, tables_map)
else:
    st.info("No charts available.")

# Technical details
with st.expander("Technical details (echo)"):
    st.json(report.get("echo", {}))

# Footer spacing
st.write("")
st.write("")
st.caption("Generated by AI from a provided JSON report.")
