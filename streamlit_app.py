import streamlit as st
import pandas as pd
import altair as alt
from typing import Dict, Any, List

# Page configuration
st.set_page_config(page_title="AI Report Dashboard", layout="wide")

# Embedded report JSON (as provided)
report_json: Dict[str, Any] = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered users decreased from 4,998 in Q1 2025 to 3,826 in Q2 2025, a drop of 23.45%.",
        "Total sales declined from 461,543.37 in Q1 2025 to 371,077.93 in Q2 2025, a decrease of 19.62%.",
        "Both user registrations and sales show a downward trend from Q1 to Q2 2025."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["period", "registered_users", "total_sales"],
            "rows": [["2025 Q1", "4998", 461543.37000000733], ["2025 Q2", "3826", 371077.93000000285]]
        }
    ],
    "charts": [
        {
            "id": "comparison1",
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
            "tables": ["`Haleon_Rewards_User_Performance_110925_user_list`", "`Haleon_Rewards_User_Performance_110925_SKUs`"],
            "columns": ["user_id", "comuserid", "Upload_Date", "Total Sales Amount"]
        },
        "stats": {"elapsed": 0.033395779},
        "sql_present": True
    }
}


def maybe_convert_numeric_series(series: pd.Series) -> pd.Series:
    """Attempt to convert an object series to numeric. Retain original if not mostly numeric."""
    if not pd.api.types.is_object_dtype(series):
        return series
    s = series.astype(str).str.replace(",", "", regex=False).str.strip()
    conv = pd.to_numeric(s, errors="coerce")
    # Convert if at least half the values are numeric
    if conv.notna().sum() >= max(1, len(series)) * 0.5:
        # If all non-null values are integer-like, cast to Int64
        nonnull = conv.dropna()
        if len(nonnull) and ((nonnull % 1) == 0).all():
            try:
                return conv.astype("Int64")
            except Exception:
                return conv
        return conv.astype(float)
    return series


def build_dataframe(table_obj: Dict[str, Any]) -> pd.DataFrame:
    cols: List[str] = table_obj.get("columns", [])
    rows: List[List[Any]] = table_obj.get("rows", [])
    df = pd.DataFrame(rows, columns=cols)
    # Try numeric conversion column-wise
    for c in df.columns:
        df[c] = maybe_convert_numeric_series(df[c])
    return df


def render_grouped_bar(df: pd.DataFrame, spec: Dict[str, Any], title: str = None):
    x_key = spec.get("xKey")
    y_key = spec.get("yKey", "value")
    series_list = spec.get("series", [])

    if not x_key or not series_list:
        st.warning("Grouped bar spec is missing xKey or series definition.")
        return

    # Prepare long-form data
    y_keys = [s.get("yKey") for s in series_list if s.get("yKey") in df.columns]
    if not y_keys:
        st.warning("No matching series yKeys found in the table for the chart.")
        return

    name_map = {s.get("yKey"): s.get("name", s.get("yKey")) for s in series_list}

    # Ensure x_key exists
    if x_key not in df.columns:
        st.warning(f"xKey '{x_key}' not found in the data table.")
        return

    long_df = df.melt(id_vars=[x_key], value_vars=y_keys, var_name="series_key", value_name=y_key)
    long_df["series_name"] = long_df["series_key"].map(name_map).fillna(long_df["series_key"])  # display names

    # Ensure y is numeric
    long_df[y_key] = pd.to_numeric(long_df[y_key], errors="coerce")

    # Build Altair grouped bar with offset
    chart = (
        alt.Chart(long_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_key}:N", title=x_key.replace("_", " ").title()),
            y=alt.Y(f"{y_key}:Q", title="Value"),
            color=alt.Color("series_name:N", title="Series"),
            xOffset=alt.X("series_name:N"),
            tooltip=[
                alt.Tooltip(f"{x_key}:N", title=x_key.replace("_", " ").title()),
                alt.Tooltip("series_name:N", title="Series"),
                alt.Tooltip(f"{y_key}:Q", title="Value", format=",.2f"),
            ],
        )
        .properties(title=title or "")
        .resolve_scale(y="shared")
    )

    st.altair_chart(chart, use_container_width=True)


def render_chart(chart_obj: Dict[str, Any], tables: List[Dict[str, Any]], dfs: Dict[str, pd.DataFrame]):
    chart_id = chart_obj.get("id", "chart")
    chart_type = chart_obj.get("type", "")
    spec = chart_obj.get("spec", {})

    # Choose a data source: if only one table, use it; else try to match by heuristic
    df = None
    if len(dfs) == 1:
        df = list(dfs.values())[0]
    else:
        # Heuristic: prefer a table that contains all needed columns
        required_cols = set()
        xk = spec.get("xKey")
        if xk:
            required_cols.add(xk)
        for s in spec.get("series", []):
            if s.get("yKey"):
                required_cols.add(s["yKey"])
        for name, cand in dfs.items():
            if required_cols.issubset(set(cand.columns)):
                df = cand
                break
        if df is None and len(dfs):
            df = list(dfs.values())[0]

    st.subheader(f"Chart: {chart_type} ({chart_id})")

    if chart_type.lower() in ["groupedbar", "grouped_bar", "groupbar", "bar_grouped"]:
        render_grouped_bar(df, spec, title=None)
    elif chart_type.lower() in ["bar"]:
        # Simple bar using first series
        x_key = spec.get("xKey")
        series_list = spec.get("series", [])
        if not series_list or not x_key:
            st.info("Bar chart spec incomplete.")
            return
        y_key = series_list[0].get("yKey")
        label = series_list[0].get("name", y_key)
        if y_key not in df.columns or x_key not in df.columns:
            st.warning("Bar chart keys not found in data.")
            return
        bar = alt.Chart(df).mark_bar().encode(
            x=alt.X(f"{x_key}:N", title=x_key.replace("_", " ").title()),
            y=alt.Y(f"{y_key}:Q", title=label),
            tooltip=[x_key, alt.Tooltip(f"{y_key}:Q", title=label, format=",.2f")],
            color=alt.value("#4C78A8"),
        )
        st.altair_chart(bar, use_container_width=True)
    elif chart_type.lower() in ["pie"]:
        # Pie expects one series
        series_list = spec.get("series", [])
        label_key = spec.get("xKey") or spec.get("labelKey")
        value_key = series_list[0].get("yKey") if series_list else spec.get("yKey")
        if not label_key or not value_key or label_key not in df.columns or value_key not in df.columns:
            st.info("Pie chart spec incomplete.")
            return
        pie = alt.Chart(df).mark_arc().encode(
            theta=alt.Theta(f"{value_key}:Q"),
            color=alt.Color(f"{label_key}:N", title=label_key.replace("_", " ").title()),
            tooltip=[label_key, alt.Tooltip(f"{value_key}:Q", format=",.2f")],
        )
        st.altair_chart(pie, use_container_width=True)
    elif chart_type.lower() in ["line"]:
        x_key = spec.get("xKey")
        series_list = spec.get("series", [])
        if not x_key or not series_list:
            st.info("Line chart spec incomplete.")
            return
        # Long-form for multi-series line
        y_keys = [s.get("yKey") for s in series_list if s.get("yKey") in df.columns]
        if not y_keys:
            st.info("Line chart series not found in data.")
            return
        name_map = {s.get("yKey"): s.get("name", s.get("yKey")) for s in series_list}
        long_df = df.melt(id_vars=[x_key], value_vars=y_keys, var_name="series_key", value_name="value")
        long_df["series_name"] = long_df["series_key"].map(name_map)
        line = alt.Chart(long_df).mark_line(point=True).encode(
            x=alt.X(f"{x_key}:N", title=x_key.replace("_", " ").title()),
            y=alt.Y("value:Q", title="Value"),
            color=alt.Color("series_name:N", title="Series"),
            tooltip=[x_key, "series_name", alt.Tooltip("value:Q", format=",.2f")],
        )
        st.altair_chart(line, use_container_width=True)
    else:
        st.info(f"Chart type '{chart_type}' not specifically supported. Displaying grouped bar if possible.")
        render_grouped_bar(df, spec, title=None)


def main():
    st.title("AI Report Dashboard")

    # Validation and issues
    valid = report_json.get("valid", True)
    issues = report_json.get("issues", [])
    if not valid:
        st.error("Report marked as invalid.")
    if issues:
        with st.expander("Issues detected in report", expanded=False):
            for i, issue in enumerate(issues, start=1):
                st.write(f"{i}. {issue}")

    # Summary
    st.subheader("Summary")
    summary_lines = report_json.get("summary", [])
    if summary_lines:
        for line in summary_lines:
            st.markdown(f"- {line}")
    else:
        st.write("No summary available.")

    # Tables
    st.subheader("Tables")
    tables = report_json.get("tables", [])
    dfs: Dict[str, pd.DataFrame] = {}
    if tables:
        for idx, tbl in enumerate(tables):
            name = tbl.get("name") or f"Table {idx+1}"
            df = build_dataframe(tbl)
            dfs[name] = df
            st.markdown(f"**{name}**")
            st.dataframe(df, use_container_width=True)
    else:
        st.write("No tables found.")

    # Charts
    st.subheader("Charts")
    charts = report_json.get("charts", [])
    if charts:
        for chart in charts:
            render_chart(chart, tables, dfs)
            st.caption("Note: Mixed units in grouped bars may make comparisons by absolute height misleading.")
    else:
        st.write("No charts found.")

    # Optional technical details
    with st.expander("Technical details", expanded=False):
        st.json({
            "echo": report_json.get("echo", {}),
        })


if __name__ == "__main__":
    main()
