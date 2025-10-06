import streamlit as st
import pandas as pd
import altair as alt
from typing import Any, Dict, List

# Embedded report JSON (self-contained app)
report: Dict[str, Any] = {
    "valid": False,
    "issues": [
        {
            "code": "missing_column",
            "severity": "error",
            "message": "Cannot compare 2025 Q1 vs Q2: no date or quarter information present in the dataset to determine quarterly registered users or sales."
        }
    ],
    "summary": [
        "Unable to compare registered users and sales between 2025 Q1 and Q2 due to missing date or quarter columns in the available data.",
        "Only overall totals for registered users (36,831) and total sales (1,843,315.89) are available."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["registered_users", "total_sales"],
            "rows": [["36831", 1843315.8899999924]]
        }
    ],
    "charts": [
        {
            "id": "main",
            "type": "kpi",
            "spec": {
                "xKey": "registered_users",
                "yKey": "total_sales",
                "series": [
                    {"name": "Total Sales", "yKey": "total_sales"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "comparison_totals",
        "used": {"tables": ["`Haleon_Rewards_User_Performance_110925_user_list`"], "columns": ["user_id", "Total Sales"]},
        "stats": {"elapsed": 0.02010398},
        "sql_present": True
    }
}

# Streamlit page setup
st.set_page_config(page_title="AI Report Dashboard", layout="wide")
st.title("AI Report Dashboard")

# Helper functions

def to_numeric_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        # Attempt numeric conversion where possible
        try:
            converted = pd.to_numeric(out[c], errors="ignore")
            out[c] = converted
        except Exception:
            pass
    return out


def human_int(value: Any) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{int(round(float(value))):,}"
    except Exception:
        return str(value)


def human_currency(value: Any) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"${float(value):,.2f}"
    except Exception:
        return str(value)


# Display validity/issues if present
if not report.get("valid", True):
    st.error("Report validation failed. See issues below.")
    issues = report.get("issues", [])
    if issues:
        with st.expander("Issues"):
            for i, issue in enumerate(issues, start=1):
                st.write(f"{i}. [{issue.get('severity','info').upper()}] {issue.get('message','')}")

# Summary section
st.header("Summary")
for item in report.get("summary", []):
    st.markdown(f"- {item}")

# Tables section
tables = report.get("tables", [])
if tables:
    st.header("Tables")
    dataframes: List[pd.DataFrame] = []
    for idx, t in enumerate(tables):
        name = t.get("name") or f"Table {idx+1}"
        cols = t.get("columns", [])
        rows = t.get("rows", [])
        df = pd.DataFrame(rows, columns=cols)
        df = to_numeric_df(df)
        dataframes.append(df)
        st.subheader(name)
        st.dataframe(df, use_container_width=True)
else:
    dataframes = []

# Charts section (Altair only)
charts = report.get("charts", [])
if charts:
    st.header("Charts")

    # Use the first available table as the data source for charts unless specified otherwise
    base_df = dataframes[0] if dataframes else pd.DataFrame()

    for c in charts:
        chart_id = c.get("id", "chart")
        chart_type = c.get("type", "").lower()
        spec = c.get("spec", {})

        st.subheader(f"Chart: {chart_id} ({chart_type})")

        if base_df.empty:
            st.info("No data available to render this chart.")
            continue

        # Ensure numeric where appropriate
        df_plot = base_df.copy()
        df_plot = to_numeric_df(df_plot)

        # Render based on chart type; handle 'kpi' as a point plot with labels
        if chart_type == "kpi":
            x_key = spec.get("xKey")
            y_key = spec.get("yKey")

            if x_key not in df_plot.columns or y_key not in df_plot.columns:
                st.info("Required keys for KPI chart not found in data.")
                continue

            # Create a friendly label to annotate the single point
            label_col = "__kpi_label__"
            df_plot[label_col] = df_plot.apply(
                lambda r: f"Users: {human_int(r.get(x_key))}  |  Sales: {human_currency(r.get(y_key))}", axis=1
            )

            # Build a scatter point with text annotation
            point = (
                alt.Chart(df_plot)
                .mark_point(size=200, color="#1f77b4")
                .encode(
                    x=alt.X(f"{x_key}:Q", axis=alt.Axis(title="Registered Users", format=",d")),
                    y=alt.Y(f"{y_key}:Q", axis=alt.Axis(title="Total Sales", format="$,.2f")),
                    tooltip=[
                        alt.Tooltip(f"{x_key}:Q", title="Registered Users", format=",d"),
                        alt.Tooltip(f"{y_key}:Q", title="Total Sales", format="$,.2f"),
                    ],
                )
            )

            text = (
                alt.Chart(df_plot)
                .mark_text(align="left", dx=8, dy=-8, fontSize=12)
                .encode(
                    x=alt.X(f"{x_key}:Q"),
                    y=alt.Y(f"{y_key}:Q"),
                    text=alt.Text(f"{label_col}:N"),
                )
            )

            kpi_chart = (point + text).properties(height=360)
            st.altair_chart(kpi_chart, use_container_width=True)
        elif chart_type in {"bar", "column"}:
            # Fallback generic bar if a field is supplied in spec
            y_key = spec.get("yKey") or spec.get("value")
            x_key = spec.get("xKey") or spec.get("category")
            if x_key and y_key and x_key in df_plot.columns and y_key in df_plot.columns:
                bar = (
                    alt.Chart(df_plot)
                    .mark_bar(color="#1f77b4")
                    .encode(
                        x=alt.X(f"{x_key}:N", title=x_key),
                        y=alt.Y(f"{y_key}:Q", title=y_key, axis=alt.Axis(format="$,.2f")),
                        tooltip=[x_key, alt.Tooltip(y_key, format="$,.2f")],
                    )
                    .properties(height=360)
                )
                st.altair_chart(bar, use_container_width=True)
            else:
                st.info("Insufficient information to render bar chart.")
        elif chart_type in {"pie"}:
            # Expect a 'category' and 'value' in spec
            category = spec.get("category")
            value = spec.get("value")
            if category and value and category in df_plot.columns and value in df_plot.columns:
                pie = (
                    alt.Chart(df_plot)
                    .mark_arc()
                    .encode(
                        theta=alt.Theta(f"{value}:Q"),
                        color=alt.Color(f"{category}:N"),
                        tooltip=[category, alt.Tooltip(value, format="$,.2f")],
                    )
                    .properties(height=360)
                )
                st.altair_chart(pie, use_container_width=True)
            else:
                st.info("Insufficient information to render pie chart.")
        elif chart_type in {"line", "area", "scatter"}:
            # Generic scatter as a fallback for these types
            x_key = spec.get("xKey")
            y_key = spec.get("yKey")
            if x_key and y_key and x_key in df_plot.columns and y_key in df_plot.columns:
                mark = {
                    "line": "line",
                    "area": "area",
                    "scatter": "point",
                }.get(chart_type, "point")
                chart = (
                    alt.Chart(df_plot)
                    .mark_point() if mark == "point" else
                    alt.Chart(df_plot).mark_line() if mark == "line" else
                    alt.Chart(df_plot).mark_area(opacity=0.3)
                ).encode(
                    x=alt.X(f"{x_key}:Q", title=x_key),
                    y=alt.Y(f"{y_key}:Q", title=y_key),
                    tooltip=[x_key, y_key],
                ).properties(height=360)
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("Insufficient information to render chart.")
        else:
            # Unknown chart type: try a sensible default using xKey/yKey if available
            x_key = spec.get("xKey")
            y_key = spec.get("yKey")
            if x_key and y_key and x_key in df_plot.columns and y_key in df_plot.columns:
                chart = (
                    alt.Chart(df_plot)
                    .mark_point(size=120, color="#1f77b4")
                    .encode(
                        x=alt.X(f"{x_key}:Q", title=x_key, axis=alt.Axis(format=",d")),
                        y=alt.Y(f"{y_key}:Q", title=y_key, axis=alt.Axis(format="$,.2f")),
                        tooltip=[
                            alt.Tooltip(f"{x_key}:Q", title=x_key, format=",d"),
                            alt.Tooltip(f"{y_key}:Q", title=y_key, format="$,.2f"),
                        ],
                    )
                    .properties(height=360)
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info(f"Unsupported chart type '{chart_type}' and insufficient spec to render.")
else:
    st.info("No charts available in the report.")

# Optional: show raw report for transparency/debugging
with st.expander("Show raw report JSON"):
    st.json(report)
