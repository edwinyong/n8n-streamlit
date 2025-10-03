import streamlit as st
import pandas as pd
import altair as alt

# ==============================
# Embedded report data (from JSON)
# ==============================
REPORT = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered users decreased from 4,998 in Q1 to 3,826 in Q2 2025 (-23.43%).",
        "Total sales dropped from 461,543.37 in Q1 to 371,077.93 in Q2 2025 (-19.61%).",
        "Total units sold declined from 19,603 in Q1 to 15,482 in Q2 2025 (-21.01%).",
        "Performance in Q2 2025 is lower than in Q1 2025 across all metrics."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["period", "registered_users", "total_sales", "total_units"],
            "rows": [
                ["Q2", "3826", 371077.93, "15482"],
                ["Q1", "4998", 461543.3700000002, "19603"]
            ]
        }
    ],
    "charts": [
        {
            "id": "main",
            "type": "bar",
            "spec": {
                "xKey": "period",
                "yKey": "total_sales",
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
            "columns": ["\"user_id\"", "\"comuserid\"", "\"Upload_Date\"", "\"Total Sales Amount\"", "\"Total_Purchase_Units\""]
        },
        "stats": {"elapsed": 0.081987},
        "sql_present": True
    }
}

# ==============================
# Helper functions
# ==============================

def load_tables(report):
    """Convert REPORT["tables"] into a dict of DataFrames keyed by table name."""
    table_dfs = {}
    for t in report.get("tables", []):
        name = t.get("name") or "Table"
        columns = t.get("columns", [])
        rows = t.get("rows", [])
        df = pd.DataFrame(rows, columns=columns)
        table_dfs[name] = df
    return table_dfs


def coerce_numeric(df: pd.DataFrame, cols):
    """Attempt to coerce specific columns to numeric, ignoring errors."""
    df2 = df.copy()
    for c in cols:
        if c in df2.columns:
            df2[c] = pd.to_numeric(df2[c], errors="coerce")
    return df2


def find_table_with_columns(tables: dict, required_cols: set):
    """Find first DataFrame that contains all required columns."""
    for name, df in tables.items():
        if required_cols.issubset(set(df.columns)):
            return name, df
    return None, None


def render_bar_chart(chart_obj: dict, tables: dict):
    spec = chart_obj.get("spec", {})
    x_key = spec.get("xKey")
    series = spec.get("series")

    # If series not provided, fall back to single yKey
    if not series:
        y_key = spec.get("yKey")
        if not (x_key and y_key):
            st.warning(f"Chart '{chart_obj.get('id','')}' missing xKey or yKey.")
            return
        required = {x_key, y_key}
        table_name, df_src = find_table_with_columns(tables, required)
        if df_src is None:
            st.warning(f"No table found containing columns: {', '.join(required)}")
            return
        df = coerce_numeric(df_src, [y_key])
        title = chart_obj.get("id", "Bar Chart")
        ch = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X(f"{x_key}:N", title=x_key.replace("_", " ").title()),
                y=alt.Y(f"{y_key}:Q", title=y_key.replace("_", " ").title()),
                tooltip=[x_key, y_key]
            )
            .properties(title=title)
        )
        st.altair_chart(ch, use_container_width=True)
        return

    # Multi-series grouped bar
    y_keys = [s.get("yKey") for s in series if s.get("yKey")]
    # Build mapping yKey -> display name
    name_map = {s.get("yKey"): (s.get("name") or s.get("yKey")) for s in series if s.get("yKey")}

    required = {x_key, *y_keys}
    table_name, df_src = find_table_with_columns(tables, set(required))
    if df_src is None:
        st.warning(f"No table found containing columns: {', '.join(required)}")
        return

    df_num = coerce_numeric(df_src, y_keys)

    # Melt to long format
    melted = df_num.melt(id_vars=[x_key], value_vars=y_keys, var_name="__metric_key__", value_name="Value")
    melted["Metric"] = melted["__metric_key__"].map(name_map).fillna(melted["__metric_key__"])

    # Create grouped bar using xOffset for Altair v5
    title = chart_obj.get("id", "Bar Chart")
    ch = (
        alt.Chart(melted)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_key}:N", title=x_key.replace("_", " ").title()),
            y=alt.Y("Value:Q", title="Value"),
            color=alt.Color("Metric:N", title="Metric"),
            xOffset="Metric:N",
            tooltip=[x_key, "Metric", alt.Tooltip("Value:Q", format=",.2f")]
        )
        .properties(title=title)
    )
    st.altair_chart(ch, use_container_width=True)


def render_pie_chart(chart_obj: dict, tables: dict):
    # Generic pie support if needed by other reports
    spec = chart_obj.get("spec", {})
    category_key = spec.get("categoryKey") or spec.get("xKey")
    value_key = spec.get("valueKey") or spec.get("yKey")
    if not (category_key and value_key):
        st.warning(f"Pie chart '{chart_obj.get('id','')}' missing categoryKey/valueKey.")
        return

    required = {category_key, value_key}
    table_name, df_src = find_table_with_columns(tables, required)
    if df_src is None:
        st.warning(f"No table found containing columns: {', '.join(required)}")
        return

    df = coerce_numeric(df_src, [value_key])
    title = chart_obj.get("id", "Pie Chart")

    ch = (
        alt.Chart(df)
        .mark_arc(innerRadius=50)
        .encode(
            theta=alt.Theta(f"{value_key}:Q", stack=True),
            color=alt.Color(f"{category_key}:N", title=category_key.replace("_", " ").title()),
            tooltip=[category_key, alt.Tooltip(f"{value_key}:Q", format=",.2f")]
        )
        .properties(title=title)
    )
    st.altair_chart(ch, use_container_width=True)


def render_chart(chart_obj: dict, tables: dict):
    ctype = (chart_obj.get("type") or "").lower()
    if ctype == "bar":
        render_bar_chart(chart_obj, tables)
    elif ctype == "pie":
        render_pie_chart(chart_obj, tables)
    else:
        st.info(f"Unsupported chart type: {ctype}. Rendering skipped.")


# ==============================
# Streamlit App
# ==============================

def main():
    st.set_page_config(page_title="AI Report Dashboard", layout="wide")
    st.title("AI Report Dashboard")
    st.caption("This app renders the provided JSON report: summary, tables, and charts.")

    # Summary
    summary = REPORT.get("summary", [])
    if summary:
        st.subheader("Summary")
        for item in summary:
            st.markdown(f"- {item}")
    else:
        st.info("No summary available.")

    # Tables
    st.subheader("Data Tables")
    tables = load_tables(REPORT)
    if tables:
        for name, df in tables.items():
            st.markdown(f"**{name}**")
            # Attempt light type coercion for better display (without mutating original structure significantly)
            df_display = df.copy()
            for c in df_display.columns:
                df_display[c] = pd.to_numeric(df_display[c], errors="ignore")
            st.dataframe(df_display, use_container_width=True)
    else:
        st.info("No tables found in the report.")

    # Charts
    st.subheader("Charts")
    charts = REPORT.get("charts", [])
    if charts:
        for chart in charts:
            render_chart(chart, tables)
    else:
        st.info("No charts found in the report.")

    # Optional debug metadata
    with st.expander("Technical Details (from report metadata)"):
        st.write("Intent:", REPORT.get("echo", {}).get("intent"))
        st.write("SQL Present:", REPORT.get("echo", {}).get("sql_present"))
        st.write("Elapsed (s):", REPORT.get("echo", {}).get("stats", {}).get("elapsed"))
        st.write("Sources used:")
        st.json(REPORT.get("echo", {}).get("used", {}))


if __name__ == "__main__":
    main()
