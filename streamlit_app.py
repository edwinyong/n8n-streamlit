import json
from typing import Dict, List
import pandas as pd
import altair as alt
import streamlit as st

# -------------------------
# Page configuration
# -------------------------
st.set_page_config(page_title="AI Report Dashboard", page_icon="📈", layout="wide")

# -------------------------
# Embedded JSON report (as provided)
# -------------------------
REPORT_JSON = r'''{"valid":true,"issues":[],"summary":["Registered users and sales peaked in February 2025, with 2,093 users and 181,249.13 in sales.","There is a downward trend in both registered users and sales from March to September 2025.","September 2025 recorded the lowest figures: 194 registered users and 18,826.01 in sales."],"tables":[{"name":"Table","columns":["month","registered_users","total_sales"],"rows":[["2025-01-01","1416",119626.18999999885],["2025-02-01","2093",181249.12999999718],["2025-03-01","1946",162391.27999999782],["2025-04-01","1621",122584.14999999863],["2025-05-01","1096",110036.75999999886],["2025-06-01","1491",138457.01999999848],["2025-07-01","1036",101228.30999999943],["2025-08-01","762",90910.37999999947],["2025-09-01","194",18826.00999999998]]}],"charts":[{"id":"users_trend","type":"line","spec":{"xKey":"month","yKey":"registered_users","series":[{"name":"Registered Users","yKey":"registered_users"}]}},{"id":"sales_trend","type":"line","spec":{"xKey":"month","yKey":"total_sales","series":[{"name":"Total Sales","yKey":"total_sales"}]}}],"echo":{"intent":"trend","used":{"tables":["`Haleon_Rewards_User_Performance_110925_SKUs`"],"columns":["Upload_Date","comuserid","Total Sales Amount"]},"stats":{"elapsed":0.032927939},"sql_present":true}}'''

# -------------------------
# Helper functions
# -------------------------

def load_report(raw: str) -> Dict:
    return json.loads(raw)


def tables_to_dataframes(report: Dict) -> Dict[str, pd.DataFrame]:
    dfs: Dict[str, pd.DataFrame] = {}
    for t in report.get("tables", []):
        name = t.get("name") or "Table"
        cols: List[str] = t.get("columns", [])
        rows: List[List] = t.get("rows", [])
        df = pd.DataFrame(rows, columns=cols)

        # Attempt sensible type conversions
        for c in df.columns:
            if c.lower() in {"date", "month", "day", "timestamp"}:
                df[c] = pd.to_datetime(df[c], errors="coerce")
        # Convert numeric-like columns
        for c in df.columns:
            if df[c].dtype == object and c.lower() not in {"date", "month", "day", "timestamp"}:
                converted = pd.to_numeric(df[c], errors="ignore")
                df[c] = converted
        # Specific coercions based on known schema
        if "registered_users" in df.columns:
            df["registered_users"] = pd.to_numeric(df["registered_users"], errors="coerce")
        if "total_sales" in df.columns:
            df["total_sales"] = pd.to_numeric(df["total_sales"], errors="coerce")
        # Sort by time if month/date column exists
        time_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
        if time_cols:
            df = df.sort_values(time_cols[0])

        dfs[name] = df.reset_index(drop=True)
    return dfs


def build_altair_chart(df: pd.DataFrame, chart_def: Dict) -> alt.Chart:
    ctype = (chart_def.get("type") or "").lower()
    spec = chart_def.get("spec", {})

    # Identify keys
    x_key = spec.get("xKey")
    y_key = spec.get("yKey")
    series = spec.get("series") or []

    # If multiple series, gather yKeys and reshape to long format
    y_keys = []
    series_name_map = {}
    if series:
        for s in series:
            yk = s.get("yKey") or y_key
            nm = s.get("name") or yk
            if yk and yk not in y_keys:
                y_keys.append(yk)
            series_name_map[yk] = nm
    elif y_key:
        y_keys = [y_key]

    base = df

    # Construct tooltip fields
    tooltip_fields = []
    if x_key and x_key in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[x_key]):
            tooltip_fields.append(alt.Tooltip(f"{x_key}:T", title=x_key))
        else:
            tooltip_fields.append(alt.Tooltip(f"{x_key}:N", title=x_key))

    # Title inference
    inferred_title = chart_def.get("id") or (ctype.capitalize() + " Chart")

    if ctype == "line":
        if len(y_keys) > 1:
            # Melt to long format for multi-series line
            mdf = base.melt(id_vars=[x_key] if x_key else None, value_vars=y_keys, var_name="metric", value_name="value")
            mdf["metric_label"] = mdf["metric"].map(lambda k: series_name_map.get(k, k))
            tooltip = tooltip_fields + [alt.Tooltip("metric_label:N", title="Series"), alt.Tooltip("value:Q", title="Value")]
            chart = (
                alt.Chart(mdf, title=inferred_title)
                .mark_line(point=True)
                .encode(
                    x=alt.X(f"{x_key}:T" if pd.api.types.is_datetime64_any_dtype(base[x_key]) else f"{x_key}:N",
                            axis=alt.Axis(title=x_key, format="%b %Y" if pd.api.types.is_datetime64_any_dtype(base[x_key]) else None)),
                    y=alt.Y("value:Q", axis=alt.Axis(title="Value")),
                    color=alt.Color("metric_label:N", title="Series"),
                    tooltip=tooltip,
                )
            )
        else:
            yk = y_keys[0] if y_keys else None
            if yk is None or yk not in base.columns:
                return alt.Chart(base).mark_text(text="Invalid chart spec: missing yKey")
            tooltip = tooltip_fields + [alt.Tooltip(f"{yk}:Q", title=series_name_map.get(yk, yk))]
            chart = (
                alt.Chart(base, title=inferred_title)
                .mark_line(point=True)
                .encode(
                    x=alt.X(f"{x_key}:T" if x_key and pd.api.types.is_datetime64_any_dtype(base[x_key]) else (f"{x_key}:N" if x_key else None),
                            axis=alt.Axis(title=x_key, format="%b %Y" if x_key and pd.api.types.is_datetime64_any_dtype(base[x_key]) else None)),
                    y=alt.Y(f"{yk}:Q", axis=alt.Axis(title=series_name_map.get(yk, yk))),
                    tooltip=tooltip,
                )
            )
        return chart

    if ctype == "bar":
        yk = y_keys[0] if y_keys else None
        if not x_key or not yk:
            return alt.Chart(base).mark_text(text="Invalid bar spec: missing xKey/yKey")
        tooltip = tooltip_fields + [alt.Tooltip(f"{yk}:Q", title=series_name_map.get(yk, yk))]
        chart = (
            alt.Chart(base, title=inferred_title)
            .mark_bar()
            .encode(
                x=alt.X(f"{x_key}:T" if pd.api.types.is_datetime64_any_dtype(base[x_key]) else f"{x_key}:N",
                        axis=alt.Axis(title=x_key, format="%b %Y" if pd.api.types.is_datetime64_any_dtype(base[x_key]) else None)),
                y=alt.Y(f"{yk}:Q", axis=alt.Axis(title=series_name_map.get(yk, yk))),
                tooltip=tooltip,
            )
        )
        return chart

    if ctype == "pie":
        # Expect keys: categoryKey, valueKey
        cat = spec.get("categoryKey") or x_key
        val = spec.get("valueKey") or y_key
        if not cat or not val or cat not in base.columns or val not in base.columns:
            return alt.Chart(base).mark_text(text="Invalid pie spec: missing category/value key")
        chart = (
            alt.Chart(base, title=inferred_title)
            .mark_arc(innerRadius=50)
            .encode(
                theta=alt.Theta(f"{val}:Q", title=val),
                color=alt.Color(f"{cat}:N", title=cat),
                tooltip=[alt.Tooltip(f"{cat}:N", title=cat), alt.Tooltip(f"{val}:Q", title=val)],
            )
        )
        return chart

    # Fallback: show a message if chart type isn't supported
    return alt.Chart(base).mark_text(text=f"Unsupported chart type: {ctype}")


# -------------------------
# App rendering
# -------------------------
report = load_report(REPORT_JSON)

st.title("AI Report Dashboard")

# Summary
summary_items = report.get("summary", [])
if summary_items:
    st.subheader("Summary")
    for item in summary_items:
        st.markdown(f"- {item}")
else:
    st.info("No summary available.")

# Tables
st.subheader("Tables")
dfs = tables_to_dataframes(report)
if not dfs:
    st.warning("No tables found in the report.")
else:
    for tname, df in dfs.items():
        st.markdown(f"#### {tname}")
        st.dataframe(df, use_container_width=True)

# Charts
st.subheader("Charts")
charts = report.get("charts", [])
if not charts:
    st.warning("No charts found in the report.")
else:
    # Use the first table as the data source for charts by default
    first_df = next(iter(dfs.values())) if dfs else pd.DataFrame()

    # Display charts one per row
    for ch in charts:
        chart_obj = build_altair_chart(first_df, ch)
        st.altair_chart(chart_obj, use_container_width=True)

# Optional: Metadata
with st.expander("Report Metadata"):
    st.json({k: v for k, v in report.items() if k not in {"tables", "charts", "summary"}})

st.caption("Built with Streamlit + Altair. All visualizations are rendered from the embedded JSON report.")
