import streamlit as st
import pandas as pd
import altair as alt

# Embedded report JSON (from input)
report = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered purchasers decreased by 23.43% from Q1 (4,998) to Q2 (3,826) in 2025.",
        "Total sales dropped by 19.88% from Q1 (463,266.60) to Q2 (371,077.93) in 2025."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": [
                "period",
                "registered_purchasers",
                "total_sales"
            ],
            "rows": [
                [
                    "2025 Q1",
                    "4998",
                    463266.6000000094
                ],
                [
                    "2025 Q2",
                    "3826",
                    371077.9300000016
                ]
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
                    {
                        "name": "Registered Purchasers",
                        "yKey": "registered_purchasers"
                    },
                    {
                        "name": "Total Sales",
                        "yKey": "total_sales"
                    }
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
            "columns": [
                "Upload_Date",
                "Total Sales Amount",
                "comuserid",
                "user_id"
            ]
        },
        "stats": {
            "elapsed": 0.048701675
        },
        "sql_present": True
    }
}

st.set_page_config(page_title="AI Report App", layout="wide")
st.title("AI Report Viewer")

# ---------- Helpers ----------
def load_tables(rep: dict):
    tables = []
    for tbl in rep.get("tables", []):
        df = pd.DataFrame(tbl.get("rows", []), columns=tbl.get("columns", []))
        # Attempt to convert numeric-like columns
        for c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="ignore")
        tables.append((tbl.get("name", "Table"), df))
    return tables


def render_chart(chart_type: str, spec: dict, df: pd.DataFrame) -> alt.Chart:
    if chart_type == "groupedBar":
        xKey = spec.get("xKey")
        series = spec.get("series", [])
        if not xKey or not series:
            raise ValueError("Spec for groupedBar must include xKey and series")
        y_keys = [s["yKey"] for s in series if "yKey" in s]
        name_map = {s["yKey"]: s.get("name", s["yKey"]) for s in series if "yKey" in s}
        # Ensure numeric for value columns
        for y in y_keys:
            if y in df.columns:
                df[y] = pd.to_numeric(df[y], errors="coerce")
        # Melt to long format
        long_df = df[[xKey] + y_keys].melt(id_vars=[xKey], value_vars=y_keys, var_name="metric", value_name="value")
        long_df["metric"] = long_df["metric"].map(name_map).astype("category")
        chart = (
            alt.Chart(long_df)
            .mark_bar()
            .encode(
                x=alt.X(f"{xKey}:N", title=xKey),
                y=alt.Y("value:Q", title="Value"),
                color=alt.Color("metric:N", title="Series"),
                xOffset="metric:N",
                tooltip=[
                    alt.Tooltip(f"{xKey}:N", title=xKey),
                    alt.Tooltip("metric:N", title="Series"),
                    alt.Tooltip("value:Q", title="Value", format=",")
                ],
            )
            .properties(height=400)
        )
        return chart

    elif chart_type == "bar":
        xKey = spec.get("xKey")
        yKey = spec.get("yKey")
        if not xKey or not yKey:
            raise ValueError("Spec for bar must include xKey and yKey")
        df = df.copy()
        df[yKey] = pd.to_numeric(df[yKey], errors="coerce")
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X(f"{xKey}:N", title=xKey),
                y=alt.Y(f"{yKey}:Q", title=yKey),
                tooltip=[xKey, yKey],
            )
            .properties(height=400)
        )
        return chart

    elif chart_type == "pie":
        catKey = spec.get("categoryKey") or spec.get("xKey")
        valKey = spec.get("valueKey") or spec.get("yKey")
        if not catKey or not valKey:
            raise ValueError("Spec for pie must include categoryKey and valueKey (or xKey/yKey)")
        df = df.copy()
        df[valKey] = pd.to_numeric(df[valKey], errors="coerce")
        chart = (
            alt.Chart(df)
            .mark_arc()
            .encode(
                theta=alt.Theta(f"{valKey}:Q", stack=True),
                color=alt.Color(f"{catKey}:N", title="Category"),
                tooltip=[catKey, valKey],
            )
            .properties(height=400)
        )
        return chart

    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")

# ---------- UI Rendering ----------
# Summary
if report.get("summary"):
    st.subheader("Summary")
    for line in report["summary"]:
        st.markdown(f"- {line}")

# Tables
tables = load_tables(report)
if tables:
    st.subheader("Tables")
    for name, df in tables:
        st.markdown(f"**{name}**")
        st.dataframe(df, use_container_width=True)

# Charts
if report.get("charts"):
    st.subheader("Charts")
    # Default to first table for chart data unless otherwise specified in future specs
    base_df = tables[0][1] if tables else pd.DataFrame()
    for chart in report["charts"]:
        cid = chart.get("id", "chart")
        ctype = chart.get("type")
        spec = chart.get("spec", {})
        st.markdown(f"**Chart: {cid} ({ctype})**")
        try:
            chart_obj = render_chart(ctype, spec, base_df.copy())
            st.altair_chart(chart_obj, use_container_width=True)
        except Exception as e:
            st.error(f"Failed to render chart '{cid}': {e}")

# Metadata / Debug info
with st.expander("Report metadata and query info"):
    st.write("Intent:", report.get("echo", {}).get("intent"))
    used = report.get("echo", {}).get("used", {})
    if used:
        st.write("Used tables:")
        st.write(used.get("tables", []))
        st.write("Used columns:")
        st.write(used.get("columns", []))
    stats = report.get("echo", {}).get("stats", {})
    if stats:
        st.write("Stats:")
        st.json(stats)
    st.write("SQL present:", report.get("echo", {}).get("sql_present"))

st.caption("Generated by AI Report App Builder - renders summaries, tables, and Altair charts from a JSON report.")
