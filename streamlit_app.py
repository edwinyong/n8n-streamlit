# Auto-generated Streamlit app to visualize a JSON report using tables and Altair charts
import streamlit as st
import pandas as pd
import altair as alt
import json
from typing import Dict, Any, List

st.set_page_config(page_title="AI Report Dashboard", layout="wide")

# Embedded report JSON (source provided by user)
REPORT: Dict[str, Any] = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered purchasers decreased by 23.43% from Q1 (4,998) to Q2 (3,826) in 2025.",
        "Total sales declined by 19.88% from Q1 (463,266.60) to Q2 (371,077.93) in 2025."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["period", "registered_purchasers", "total_sales"],
            "rows": [
                ["2025 Q1", "4998", 463266.6000000094],
                ["2025 Q2", "3826", 371077.9300000016]
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
                    {"name": "Registered Purchasers", "yKey": "registered_purchasers"},
                    {"name": "Total Sales", "yKey": "total_sales"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "comparison_totals",
        "used": {
            "tables": [
                "`Haleon_Rewards_User_Performance_110925_SKUs`",
                "`Haleon_Rewards_User_Performance_110925_user_list`"
            ],
            "columns": ["Upload_Date", "Total Sales Amount", "comuserid", "user_id"]
        },
        "stats": {"elapsed": 0.048144224},
        "sql_present": True
    }
}


def to_dataframe(table_spec: Dict[str, Any]) -> pd.DataFrame:
    """Convert a table spec with columns/rows to a pandas DataFrame."""
    df = pd.DataFrame(table_spec.get("rows", []), columns=table_spec.get("columns", []))
    return df


def smart_numeric_cast(df: pd.DataFrame) -> pd.DataFrame:
    """Attempt to cast object columns to numeric when appropriate, preserving non-numeric columns."""
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            series_str = out[col].astype(str).str.replace(",", "", regex=False)
            converted = pd.to_numeric(series_str, errors="coerce")
            # If majority of values convert to numeric, use the converted series
            non_na = converted.notna().sum()
            if len(out[col]) > 0 and non_na / len(out[col]) >= 0.8:
                out[col] = converted
    return out


def find_chart_dataframe(x_key: str, y_keys: List[str], tables: List[Dict[str, Any]]) -> pd.DataFrame:
    """Find the first table that contains required columns for a chart."""
    for t in tables:
        cols = t.get("columns", [])
        if x_key in cols and all(y in cols for y in y_keys):
            df = to_dataframe(t)
            return smart_numeric_cast(df)
    # fallback: return first table as DataFrame if nothing matches
    if tables:
        return smart_numeric_cast(to_dataframe(tables[0]))
    return pd.DataFrame()


def render_grouped_bar(chart_spec: Dict[str, Any], tables: List[Dict[str, Any]]):
    meta = chart_spec.get("spec", {})
    x_key = meta.get("xKey", "x")
    value_key = meta.get("yKey", "value")
    series_meta = meta.get("series", [])

    # yKeys from series
    y_keys = [s.get("yKey") for s in series_meta if s.get("yKey")]
    name_map = {s.get("yKey"): s.get("name", s.get("yKey")) for s in series_meta if s.get("yKey")}

    df = find_chart_dataframe(x_key, y_keys, tables)
    if df.empty:
        st.info("No data available for grouped bar chart.")
        return

    # Prepare long format
    needed_cols = [x_key] + y_keys
    long_df = pd.melt(df[needed_cols].copy(), id_vars=[x_key], value_vars=y_keys,
                      var_name="series_key", value_name=value_key)
    # Map to friendly series names
    long_df["series"] = long_df["series_key"].map(name_map).fillna(long_df["series_key"])  # type: ignore

    # Ensure value is numeric
    long_df[value_key] = pd.to_numeric(long_df[value_key], errors="coerce")

    # Build chart. Prefer xOffset if available (Altair 5), else facet fallback.
    major_version = 0
    try:
        major_version = int(str(alt.__version__).split(".")[0])
    except Exception:
        major_version = 0

    base = alt.Chart(long_df).encode(
        tooltip=[
            alt.Tooltip(f"{x_key}:N", title=x_key.replace("_", " ").title()),
            alt.Tooltip("series:N", title="Series"),
            alt.Tooltip(f"{value_key}:Q", title="Value", format=",.2f")
        ]
    )

    if major_version >= 5:
        chart = base.mark_bar().encode(
            x=alt.X(f"{x_key}:N", title=x_key.replace("_", " ").title()),
            y=alt.Y(f"{value_key}:Q", title="Value"),
            color=alt.Color("series:N", title="Series"),
            xOffset=alt.XOffset("series:N")
        ).properties(height=400)
    else:
        # Facet by x_key as a fallback for older Altair versions
        chart = base.mark_bar().encode(
            x=alt.X("series:N", title="Series"),
            y=alt.Y(f"{value_key}:Q", title="Value"),
            color=alt.Color("series:N", title="Series"),
            column=alt.Column(f"{x_key}:N", title=x_key.replace("_", " ").title())
        ).properties(height=300)

    st.altair_chart(chart, use_container_width=True)


def render_chart(chart: Dict[str, Any], tables: List[Dict[str, Any]]):
    ctype = chart.get("type", "").lower()
    chart_id = chart.get("id", "chart")

    st.subheader(f"Chart: {chart_id} ({chart.get('type')})")

    if ctype in ("groupedbar", "grouped_bar", "bar_grouped"):
        render_grouped_bar(chart, tables)
    elif ctype == "bar":
        # Simple bar chart assume first yKey in spec['series'] or a single yKey
        spec = chart.get("spec", {})
        x_key = spec.get("xKey")
        series_meta = spec.get("series", [])
        if series_meta:
            y_key = series_meta[0].get("yKey")
        else:
            y_key = spec.get("yKey")
        df = find_chart_dataframe(x_key, [y_key] if y_key else [], tables)
        if df.empty or not x_key or not y_key:
            st.info("No data available for bar chart.")
            return
        df = smart_numeric_cast(df)
        chart_obj = alt.Chart(df).mark_bar().encode(
            x=alt.X(f"{x_key}:N", title=x_key.replace("_", " ").title()),
            y=alt.Y(f"{y_key}:Q", title=y_key.replace("_", " ").title()),
            tooltip=[x_key, y_key]
        ).properties(height=400)
        st.altair_chart(chart_obj, use_container_width=True)
    elif ctype == "pie":
        # Pie chart expects category and value; try to infer from spec
        spec = chart.get("spec", {})
        category = spec.get("category") or spec.get("xKey")
        value = spec.get("value") or spec.get("yKey") or "value"
        df = find_chart_dataframe(category or "", [value] if value else [], tables)
        if df.empty or not category or not value:
            st.info("No data available for pie chart.")
            return
        df = smart_numeric_cast(df)
        pie = alt.Chart(df).mark_arc().encode(
            theta=alt.Theta(f"{value}:Q", title=value.replace("_", " ").title()),
            color=alt.Color(f"{category}:N", title=category.replace("_", " ").title()),
            tooltip=[category, value]
        ).properties(height=400)
        st.altair_chart(pie, use_container_width=True)
    elif ctype == "line":
        spec = chart.get("spec", {})
        x_key = spec.get("xKey")
        series_meta = spec.get("series", [])
        if series_meta:
            y_key = series_meta[0].get("yKey")
        else:
            y_key = spec.get("yKey")
        df = find_chart_dataframe(x_key, [y_key] if y_key else [], REPORT.get("tables", []))
        if df.empty or not x_key or not y_key:
            st.info("No data available for line chart.")
            return
        df = smart_numeric_cast(df)
        chart_obj = alt.Chart(df).mark_line(point=True).encode(
            x=alt.X(f"{x_key}:N", title=x_key.replace("_", " ").title()),
            y=alt.Y(f"{y_key}:Q", title=y_key.replace("_", " ").title()),
            tooltip=[x_key, y_key]
        ).properties(height=400)
        st.altair_chart(chart_obj, use_container_width=True)
    else:
        st.info(f"Chart type '{chart.get('type')}' is not recognized. Skipping.")


# Sidebar metadata
with st.sidebar:
    st.header("Report Info")
    st.markdown("- Valid: {}".format("Yes" if REPORT.get("valid") else "No"))
    issues = REPORT.get("issues", [])
    st.markdown(f"- Issues: {len(issues)}")
    if REPORT.get("echo", {}).get("intent"):
        st.markdown(f"- Intent: {REPORT['echo']['intent']}")
    if REPORT.get("echo", {}).get("stats", {}).get("elapsed") is not None:
        st.markdown(f"- Query time: {REPORT['echo']['stats']['elapsed']:.3f}s")

st.title("AI Report Dashboard")

# Summary section
st.subheader("Summary")
summary_items = REPORT.get("summary", [])
if summary_items:
    for item in summary_items:
        st.markdown(f"- {item}")
else:
    st.info("No summary available.")

# Tables section
st.subheader("Tables")
report_tables = REPORT.get("tables", [])
if not report_tables:
    st.info("No tables available.")
else:
    for idx, table in enumerate(report_tables, start=1):
        name = table.get("name") or f"Table {idx}"
        st.markdown(f"### {name}")
        df_table = to_dataframe(table)
        st.dataframe(df_table, use_container_width=True)

# Charts section
st.subheader("Charts")
report_charts = REPORT.get("charts", [])
if not report_charts:
    st.info("No charts available.")
else:
    for chart in report_charts:
        render_chart(chart, report_tables)

# Technical details
with st.expander("Technical details and provenance"):
    st.markdown("#### Data sources used")
    used = REPORT.get("echo", {}).get("used", {})
    st.write({
        "tables": used.get("tables", []),
        "columns": used.get("columns", [])
    })

    st.markdown("#### Raw report JSON")
    st.code(json.dumps(REPORT, indent=2), language="json")

st.caption("App generated to visualize the provided JSON report with Streamlit, pandas, and Altair.")
