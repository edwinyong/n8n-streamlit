#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import altair as alt

# Embedded report data
REPORT = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered users in 2025 show a peak in January (2,100), then a drop in February (1,300), with monthly registrations stabilizing between 1,100 and 1,500 for the rest of the year.",
        "Sales in 2025 are highest in January (190,000.00), then decrease in February (130,000.00), and remain between 100,000.00 and 140,000.00 monthly until December.",
        "No abnormal spikes detected after January; performance is relatively steady post-Q1."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["month", "registered_users", "total_sales"],
            "rows": [
                ["2025-01", "2100", 190000],
                ["2025-02", "1300", 130000],
                ["2025-03", "1598", 141543.37],
                ["2025-04", "1200", 120000],
                ["2025-05", "1250", 125000],
                ["2025-06", "1376", 126077.93],
                ["2025-07", "1320", 128000],
                ["2025-08", "1370", 128099.01],
                ["2025-09", "1321", 128000],
                ["2025-10", "1400", 134000],
                ["2025-11", "1400", 133120.55],
                ["2025-12", "1410", 134000]
            ]
        }
    ],
    "charts": [
        {
            "id": "main",
            "type": "line",
            "spec": {
                "xKey": "month",
                "yKey": "registered_users",
                "series": [
                    {"name": "Registered Users", "yKey": "registered_users"}
                ]
            }
        },
        {
            "id": "sales",
            "type": "line",
            "spec": {
                "xKey": "month",
                "yKey": "total_sales",
                "series": [
                    {"name": "Total Sales", "yKey": "total_sales"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "trend",
        "used": {"tables": ["`Haleon_Rewards_User_Performance_110925_list`"], "columns": ['"user_id"', '"Total Sales Amount"', '"Upload_Date"']},
        "stats": {"elapsed": 0.04843408},
        "sql_present": True
    }
}

st.set_page_config(page_title="AI Report Dashboard", page_icon="📊", layout="wide")
st.title("AI Report Dashboard")

# Helper functions

def to_dataframe(table_obj: dict) -> pd.DataFrame:
    df = pd.DataFrame(table_obj.get("rows", []), columns=table_obj.get("columns", []))
    # Try to convert numeric-looking columns
    for col in df.columns:
        if col.lower() != "month":
            df[col] = pd.to_numeric(df[col], errors="ignore")
    # Add a parsed date column for common time keys like 'month'
    if "month" in df.columns:
        parsed = pd.to_datetime(df["month"], errors="coerce")
        df["_month_dt"] = parsed
        # Sort by month when available
        df = df.sort_values(by=["_month_dt", "month"], ascending=[True, True])
    return df


def find_table_for_chart(x_key: str, y_keys: list, tables_map: dict) -> str:
    for tname, df in tables_map.items():
        if x_key in df.columns and all(y in df.columns for y in y_keys):
            return tname
        # Allow using parsed month for x if available
        if x_key == "month" and "_month_dt" in df.columns and all(y in df.columns for y in y_keys):
            return tname
    return ""


def prepare_x_axis(df: pd.DataFrame, x_key: str):
    # Determine field and type for Altair x-encoding
    if x_key == "month" and "_month_dt" in df.columns and df["_month_dt"].notna().any():
        return "_month_dt", "temporal"
    # Try generic parse
    parsed = pd.to_datetime(df[x_key], errors="coerce") if x_key in df.columns else None
    if parsed is not None and parsed.notna().sum() >= max(1, int(0.6 * len(df))):
        # Use a temp parsed column
        temp_col = f"_{x_key}_dt"
        if temp_col not in df.columns:
            df[temp_col] = parsed
        return temp_col, "temporal"
    # Fallback to ordinal for string keys
    return x_key, "ordinal"


def build_line_chart(df: pd.DataFrame, chart_id: str, spec: dict, title: str = None) -> alt.Chart:
    x_key = spec.get("xKey")
    series = spec.get("series", [])
    y_keys = [s.get("yKey") for s in series if s.get("yKey")]

    x_field, x_type = prepare_x_axis(df, x_key)

    # Ensure numeric y columns
    df = df.copy()
    for yk in y_keys:
        if yk in df.columns:
            df[yk] = pd.to_numeric(df[yk], errors="coerce")

    if len(series) <= 1:
        yk = y_keys[0]
        disp = series[0].get("name", yk)
        chart = (
            alt.Chart(df, title=title or disp)
            .mark_line(point=True)
            .encode(
                x=alt.X(f"{x_field}:{'T' if x_type=='temporal' else 'O'}", title=x_key),
                y=alt.Y(f"{yk}:Q", title=disp),
                tooltip=[
                    alt.Tooltip(f"{x_field}:{'yearmonth' if x_type=='temporal' else 'nominal'}", title=x_key),
                    alt.Tooltip(f"{yk}:Q", title=disp, format=",.2f" if df[yk].dtype.kind in "fc" else ",d"),
                ],
            )
        )
        return chart
    else:
        # Multiple series: melt to long format
        long_df = df.melt(id_vars=[x_field], value_vars=y_keys, var_name="SeriesKey", value_name="Value")
        # Map display names
        name_map = {s.get("yKey"): s.get("name", s.get("yKey")) for s in series}
        long_df["Series"] = long_df["SeriesKey"].map(name_map).fillna(long_df["SeriesKey"])\
            .astype(str)
        chart = (
            alt.Chart(long_df, title=title or chart_id)
            .mark_line(point=True)
            .encode(
                x=alt.X(f"{x_field}:{'T' if x_type=='temporal' else 'O'}", title=x_key),
                y=alt.Y("Value:Q", title="Value"),
                color=alt.Color("Series:N", title="Series"),
                tooltip=[
                    alt.Tooltip(f"{x_field}:{'yearmonth' if x_type=='temporal' else 'nominal'}", title=x_key),
                    alt.Tooltip("Series:N"),
                    alt.Tooltip("Value:Q", format=",.2f"),
                ],
            )
        )
        return chart


# Sidebar meta
with st.sidebar:
    st.header("Report Info")
    st.caption("Source: Embedded JSON")
    st.markdown(f"- Valid: {'✅' if REPORT.get('valid') else '❌'}")
    if REPORT.get("issues"):
        st.markdown("- Issues:")
        for iss in REPORT["issues"]:
            st.write(f"  • {iss}")
    with st.expander("Echo / Debug"):
        st.json(REPORT.get("echo", {}))

# Summary section
st.subheader("Summary")
if REPORT.get("summary"):
    st.markdown("\n".join([f"- {item}" for item in REPORT["summary"]]))
else:
    st.info("No summary available.")

# Tables section
st.subheader("Tables")

tables_map = {}
if REPORT.get("tables"):
    for t in REPORT["tables"]:
        tname = t.get("name") or "Table"
        df = to_dataframe(t)
        tables_map[tname] = df
        st.markdown(f"**{tname}**")
        # Display without helper columns
        disp_df = df.copy()
        if "_month_dt" in disp_df.columns:
            disp_df = disp_df.drop(columns=["_month_dt"])  # hide helper
        st.dataframe(disp_df, use_container_width=True)
else:
    st.warning("No tables found in the report.")

# Charts section
st.subheader("Charts")
if REPORT.get("charts"):
    for ch in REPORT["charts"]:
        ch_id = ch.get("id", "chart")
        ch_type = ch.get("type", "line")
        spec = ch.get("spec", {})
        x_key = spec.get("xKey")
        series_list = spec.get("series", [])
        y_keys = [s.get("yKey") for s in series_list if s.get("yKey")]

        # Find a suitable table for this chart
        tname = find_table_for_chart(x_key, y_keys, tables_map)
        if not tname:
            st.error(f"Could not find a table containing columns: x='{x_key}', y={y_keys}")
            continue
        df = tables_map[tname]

        # Build and render chart using Altair
        title = None
        if ch_type == "line":
            series_names = ", ".join([s.get("name", s.get("yKey")) for s in series_list])
            title = f"{series_names} over {x_key}"
            chart = build_line_chart(df, ch_id, spec, title=title)
            st.markdown(f"**{ch_id}** ({tname})")
            st.altair_chart(chart.properties(width="container").interactive(), use_container_width=True)
        else:
            st.warning(f"Unsupported chart type '{ch_type}'. Only 'line' is rendered in this report.")
else:
    st.info("No charts defined in the report.")

st.markdown("---")
st.caption("Built with Streamlit and Altair")
