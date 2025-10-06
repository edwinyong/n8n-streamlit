import streamlit as st
import pandas as pd
import altair as alt
import json

# ------------------------------------------------------------
# Embedded report JSON (as provided)
# ------------------------------------------------------------
REPORT = {
    "valid": False,
    "issues": [
        {
            "code": "missing_column",
            "severity": "error",
            "message": "Cannot compare registered users and sales for 2025 Q1 vs Q2 because neither table contains a Date/DateTime column to determine quarters."
        }
    ],
    "summary": [
        "Comparison between 2025 Q1 and Q2 is not possible due to missing date or time columns in the dataset."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["period", "registered_users", "total_sales"],
            "rows": [["NO_TYPED_TIME_TOTALS", "36831", 2352872.13999997]]
        }
    ],
    "charts": [
        {
            "id": "main",
            "type": "kpi",
            "spec": {
                "xKey": "period",
                "yKey": "total_sales",
                "series": [
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
            "columns": ["user_id", "Total Sales Amount"]
        },
        "stats": {"elapsed": 0.021262097},
        "sql_present": True
    }
}

# ------------------------------------------------------------
# Streamlit App
# ------------------------------------------------------------
st.set_page_config(page_title="AI Report Viewer", page_icon="📊", layout="wide")
st.title("AI Report Viewer")

# Helper: convert potential numeric object columns to numeric where possible
def coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = pd.to_numeric(df[col], errors="ignore")
    return df

# Helper: build Altair chart from chart definition
def build_chart(chart_def: dict, df: pd.DataFrame) -> alt.Chart:
    ctype = (chart_def or {}).get("type", "").lower()
    spec = (chart_def or {}).get("spec", {})

    # Default keys
    x_key = spec.get("xKey")
    y_key = spec.get("yKey")

    # Handle empty or invalid df/keys safely
    if df is None or df.empty:
        # Return an empty text chart stating no data
        return alt.Chart(pd.DataFrame({"msg": ["No data available for chart"]})).mark_text(align="left").encode(text="msg")

    if ctype in {"bar", "column"} and x_key and y_key and x_key in df.columns and y_key in df.columns:
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X(f"{x_key}:N", title=x_key),
                y=alt.Y(f"{y_key}:Q", title=y_key, axis=alt.Axis(format="$,.2f")),
                tooltip=[x_key, alt.Tooltip(y_key, format=",.2f")]
            )
        )
        text = (
            chart.mark_text(dy=-5, color="#333")
            .encode(text=alt.Text(f"{y_key}:Q", format="$,.2f"))
        )
        return (chart + text).properties(height=320)

    if ctype in {"line"} and x_key and y_key and x_key in df.columns and y_key in df.columns:
        return (
            alt.Chart(df)
            .mark_line(point=True)
            .encode(
                x=alt.X(f"{x_key}", title=x_key),
                y=alt.Y(f"{y_key}:Q", title=y_key, axis=alt.Axis(format="$,.2f")),
                tooltip=[x_key, alt.Tooltip(y_key, format=",.2f")]
            )
            .properties(height=320)
        )

    if ctype in {"pie"} and x_key and y_key and x_key in df.columns and y_key in df.columns:
        # Pie using theta for quantitative and color for category
        return (
            alt.Chart(df)
            .mark_arc(innerRadius=40, outerRadius=120)
            .encode(
                theta=alt.Theta(f"{y_key}:Q"),
                color=alt.Color(f"{x_key}:N"),
                tooltip=[x_key, alt.Tooltip(y_key, format=",.2f")]
            )
            .properties(height=360)
        )

    if ctype in {"kpi"}:
        # Represent KPI as a single-bar chart (or multiple if multiple rows) with labels
        # Fallback defaults if keys are missing
        # Prefer provided yKey; if missing, try first numeric column
        local_y_key = y_key
        if not local_y_key or local_y_key not in df.columns:
            # Find first numeric column
            num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            local_y_key = num_cols[0] if num_cols else None
        # Prefer provided xKey; if missing, create an index-based label
        local_x_key = x_key if (x_key in df.columns if x_key else False) else None
        working_df = df.copy()
        if local_x_key is None:
            working_df = working_df.reset_index().rename(columns={"index": "label"})
            local_x_key = "label"
        if local_y_key is None:
            return alt.Chart(pd.DataFrame({"msg": ["No numeric measure to plot for KPI chart"]})).mark_text(align="left").encode(text="msg")

        # Ensure proper types
        # Coerce x to string for nominal display
        working_df[local_x_key] = working_df[local_x_key].astype(str)

        base = alt.Chart(working_df)
        bars = base.mark_bar(size=60).encode(
            x=alt.X(f"{local_x_key}:N", title=local_x_key),
            y=alt.Y(f"{local_y_key}:Q", title=local_y_key, axis=alt.Axis(format="$,.2f")),
            tooltip=[local_x_key, alt.Tooltip(local_y_key, format=",.2f")]
        )
        labels = base.mark_text(dy=-5, color="#333").encode(
            x=alt.X(f"{local_x_key}:N"),
            y=alt.Y(f"{local_y_key}:Q"),
            text=alt.Text(f"{local_y_key}:Q", format="$,.2f")
        )
        return (bars + labels).properties(height=300)

    # Fallback: show a text note if chart type or keys are not supported
    message = f"Unsupported or improperly specified chart (type={ctype}, xKey={x_key}, yKey={y_key})."
    return alt.Chart(pd.DataFrame({"msg": [message]})).mark_text(align="left").encode(text="msg")

# ------------------------ UI Sections ------------------------
# Summary
if REPORT.get("summary"):
    st.subheader("Summary")
    for s in REPORT["summary"]:
        st.markdown(f"- {s}")

# Issues (if any)
issues = REPORT.get("issues", [])
if issues:
    st.subheader("Issues Detected")
    for issue in issues:
        sev = (issue.get("severity") or "").lower()
        msg = issue.get("message", "")
        code = issue.get("code", "")
        line = f"[{code}] {msg}" if code else msg
        if sev == "error":
            st.error(line)
        elif sev == "warning":
            st.warning(line)
        else:
            st.info(line)

# Tables
tables = REPORT.get("tables", [])
name_to_df = {}
if tables:
    st.subheader("Tables")
    for t in tables:
        t_name = t.get("name", "Table")
        cols = t.get("columns", [])
        rows = t.get("rows", [])
        try:
            df = pd.DataFrame(rows, columns=cols)
        except Exception:
            # Fallback if columns don't match rows
            df = pd.DataFrame(rows)
        df = coerce_numeric(df)
        name_to_df[t_name] = df
        with st.container():
            st.markdown(f"**{t_name}**")
            st.dataframe(df, use_container_width=True)

# Charts
charts = REPORT.get("charts", [])
if charts:
    st.subheader("Charts")
    # Choose a default data source: first table if not specified
    default_df = None
    if name_to_df:
        # Pick the first table inserted
        default_df = next(iter(name_to_df.values()))

    for ch in charts:
        chart_id = ch.get("id", "chart")
        st.markdown(f"**Chart: {chart_id}**")
        chart_obj = build_chart(ch, default_df)
        st.altair_chart(chart_obj, use_container_width=True)

# Technical details (optional)
with st.expander("Report JSON (technical details)"):
    st.code(json.dumps(REPORT, indent=2))

st.caption("Rendered with Streamlit, Pandas, and Altair.")
