import streamlit as st
import pandas as pd
import altair as alt
from typing import Dict, Any, List

# Disable Altair's default row limit to avoid issues with larger datasets
alt.data_transformers.disable_max_rows()

st.set_page_config(page_title="AI Report Dashboard", layout="wide")

# -----------------------------
# Embedded report JSON (as provided)
# -----------------------------
REPORT: Dict[str, Any]
REPORT = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered users in 2025 peak in January (2,100), drop in February (1,300), then stabilize between 1,100 and 1,500 for the rest of the year.",
        "Sales are highest in January (190,000.00), decrease in February (130,000.00), and remain between 100,000.00 and 140,000.00 monthly through December.",
        "No abnormal monthly spikes after January; performance is steady post-Q1."
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
        "used": {
            "tables": ["`Haleon_Rewards_User_Performance_110925_list`"],
            "columns": ["\"user_id\"", "\"Total Sales Amount\"", "\"Upload_Date\""]
        },
        "stats": {"elapsed": 0.04843408},
        "sql_present": True
    }
}

# -----------------------------
# Helper functions
# -----------------------------

def _convert_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Attempt sensible dtype conversions for common types (numeric, datetime)."""
    df = df.copy()
    for col in df.columns:
        lower = str(col).lower()
        # Convert date-like columns
        if any(key in lower for key in ["date", "time", "month", "day", "datetime", "upload_date"]):
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
            except Exception:
                pass
        # Convert numeric-like columns
        try:
            converted = pd.to_numeric(df[col], errors="ignore")
            df[col] = converted
        except Exception:
            pass
    return df


def create_altair_chart(df: pd.DataFrame, chart: Dict[str, Any]) -> alt.Chart:
    ctype = chart.get("type", "line").lower()
    spec = chart.get("spec", {})

    x_key = spec.get("xKey")
    y_key_root = spec.get("yKey")
    series = spec.get("series", [])

    # Determine y-keys to plot
    series_keys: List[str] = []
    if isinstance(series, list) and len(series) > 0:
        for s in series:
            if isinstance(s, dict) and s.get("yKey"):
                series_keys.append(s["yKey"])
    if not series_keys and y_key_root:
        series_keys = [y_key_root]

    if x_key is None or not series_keys:
        raise ValueError("Chart spec must include xKey and at least one yKey/series")

    # Sort data by x if possible
    sort_df = df.copy()
    if x_key in sort_df.columns:
        try:
            sort_df = sort_df.sort_values(by=x_key)
        except Exception:
            pass

    # Determine encoding types
    x_dtype = "quantitative"
    if pd.api.types.is_datetime64_any_dtype(sort_df[x_key]):
        x_dtype = "temporal"
    elif pd.api.types.is_numeric_dtype(sort_df[x_key]):
        x_dtype = "quantitative"
    else:
        x_dtype = "nominal"

    # Build tooltips
    tooltips = [
        alt.Tooltip(f"{x_key}:{'T' if x_dtype=='temporal' else ('Q' if x_dtype=='quantitative' else 'N')}", title=x_key)
    ]
    for yk in series_keys:
        if yk in sort_df.columns:
            # Infer quantitative for y
            tooltips.append(alt.Tooltip(f"{yk}:Q", title=yk))

    # Multi-series vs single-series handling
    if len(series_keys) > 1:
        base = alt.Chart(sort_df)
        folded = base.transform_fold(
            series_keys,
            as_=["Series", "Value"],
        )
        mark = None
        if ctype == "line":
            mark = folded.mark_line(point=True)
        elif ctype == "bar":
            mark = folded.mark_bar()
        elif ctype == "area":
            mark = folded.mark_area()
        elif ctype == "scatter":
            mark = folded.mark_point()
        else:
            # Default to line for unsupported types in multi-series context
            mark = folded.mark_line(point=True)

        chart_obj = mark.encode(
            x=alt.X(f"{x_key}:{'T' if x_dtype=='temporal' else ('Q' if x_dtype=='quantitative' else 'N')}", axis=alt.Axis(format="%Y-%m" if x_dtype == "temporal" else None, title=x_key)),
            y=alt.Y("Value:Q", title=", ".join(series_keys)),
            color=alt.Color("Series:N", legend=alt.Legend(title="Series")),
            tooltip=tooltips,
        ).properties(height=320)
        return chart_obj
    else:
        yk = series_keys[0]
        if ctype == "pie":
            # For pie charts, we expect category and value keys; fallback if not provided
            category_key = spec.get("categoryKey", x_key)
            value_key = spec.get("valueKey", yk)
            return alt.Chart(sort_df).mark_arc().encode(
                theta=alt.Theta(f"{value_key}:Q"),
                color=alt.Color(f"{category_key}:N", legend=alt.Legend(title=category_key)),
                tooltip=[alt.Tooltip(f"{category_key}:N", title=category_key), alt.Tooltip(f"{value_key}:Q", title=value_key)],
            ).properties(height=320)

        base = alt.Chart(sort_df)
        if ctype == "line":
            mark = base.mark_line(point=True)
        elif ctype == "bar":
            mark = base.mark_bar()
        elif ctype == "area":
            mark = base.mark_area()
        elif ctype == "scatter":
            mark = base.mark_point()
        else:
            mark = base.mark_line(point=True)

        chart_obj = mark.encode(
            x=alt.X(f"{x_key}:{'T' if x_dtype=='temporal' else ('Q' if x_dtype=='quantitative' else 'N')}", axis=alt.Axis(format="%Y-%m" if x_dtype == "temporal" else None, title=x_key)),
            y=alt.Y(f"{yk}:Q", title=yk),
            tooltip=tooltips,
        ).properties(height=320)
        return chart_obj


# -----------------------------
# App UI
# -----------------------------
st.title("AI Report Dashboard")

# Sidebar meta
with st.sidebar:
    st.header("Report Metadata")
    st.write(f"Valid: {REPORT.get('valid', False)}")
    issues = REPORT.get("issues", []) or []
    st.write(f"Issues: {len(issues)}")
    if issues:
        st.warning("\n".join(str(i) for i in issues))
    echo = REPORT.get("echo")
    if echo:
        st.markdown("---")
        st.subheader("Generator Echo")
        st.write({
            "intent": echo.get("intent"),
            "sql_present": echo.get("sql_present"),
            "elapsed": echo.get("stats", {}).get("elapsed"),
        })
        used = echo.get("used", {})
        if used:
            st.caption("Inputs used")
            st.write(used)

# Summary section
st.subheader("Summary")
summary_list: List[str] = REPORT.get("summary", []) or []
if summary_list:
    st.markdown("\n".join([f"- {item}" for item in summary_list]))
else:
    st.info("No summary available.")

# Tables section
st.subheader("Tables")
raw_tables = REPORT.get("tables", []) or []

# Keep parsed dataframes for charting
dataframes: Dict[str, pd.DataFrame] = {}

if not raw_tables:
    st.info("No tables available in the report.")
else:
    for idx, tbl in enumerate(raw_tables):
        name = tbl.get("name") or f"Table {idx+1}"
        cols = tbl.get("columns", [])
        rows = tbl.get("rows", [])
        df = pd.DataFrame(rows, columns=cols)
        df = _convert_dtypes(df)

        # Display
        st.markdown(f"**{name}**")
        st.dataframe(df, use_container_width=True)

        dataframes[name] = df

# Decide which dataframe to use for charts (use the first table by default)
main_df: pd.DataFrame = next(iter(dataframes.values()), pd.DataFrame())

# Charts section
st.subheader("Charts")
charts = REPORT.get("charts", []) or []
if not charts:
    st.info("No charts available in the report.")
else:
    for ch in charts:
        cid = ch.get("id", "chart")
        ctype = ch.get("type", "chart").capitalize()
        st.markdown(f"**{cid} ({ctype})**")
        try:
            if main_df.empty:
                st.warning("No data available to render this chart.")
            else:
                chart_obj = create_altair_chart(main_df, ch)
                st.altair_chart(chart_obj, use_container_width=True)
        except Exception as e:
            st.error(f"Failed to render chart '{cid}': {e}")

# Footer
st.markdown("---")
st.caption("App generated from provided JSON report. Libraries: Streamlit, Pandas, Altair.")
