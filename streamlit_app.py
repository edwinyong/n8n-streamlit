import streamlit as st
import pandas as pd
import altair as alt
import json
from typing import List, Dict, Any

# -------------------------------
# Embedded report JSON
# -------------------------------
json_report = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered users and total sales in 2025 Q2 are exactly the same as in 2025 Q1.",
        "No improvement or decline observed between Q1 and Q2 2025."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["period", "registered_users", "total_sales"],
            "rows": [
                ["2025 Q2", "36831", "1843315.8899999924"],
                ["2025 Q1", "36831", "1843315.8899999924"]
            ]
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
        },
        {
            "id": "main_2",
            "type": "kpi",
            "spec": {
                "xKey": "period",
                "yKey": "registered_users",
                "series": [
                    {"name": "Registered Users", "yKey": "registered_users"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "comparison_totals",
        "used": {"tables": ["Haleon_Rewards_User_Performance_110925_list"], "columns": ["user_id", "Total Sales"]},
        "stats": {"elapsed": 0},
        "sql_present": True
    }
}

# -------------------------------
# Streamlit App
# -------------------------------

def _coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        # Try numeric conversion; leave as-is if fails
        converted = pd.to_numeric(df[col], errors="ignore")
        df[col] = converted
    return df


def _format_for_dtype(series: pd.Series) -> str:
    # Choose a number format based on dtype
    if pd.api.types.is_integer_dtype(series):
        return ",d"
    if pd.api.types.is_float_dtype(series):
        return ",.2f"
    return ""


def _find_chart_dataframe(x_key: str, y_keys: List[str], tables: List[Dict[str, Any]]):
    # Find first table that contains x_key and all y_keys
    for t in tables:
        df = t["df"]
        cols = set(df.columns)
        if x_key in cols and all(y in cols for y in y_keys):
            return t
    return None


def _build_chart(chart_def: Dict[str, Any], tables: List[Dict[str, Any]]):
    ctype = (chart_def.get("type") or "").lower()
    spec = chart_def.get("spec", {})
    x_key = spec.get("xKey")

    # Gather series and y-keys
    series_list = spec.get("series", []) or []
    y_key_from_root = spec.get("yKey")
    y_keys = [s.get("yKey") for s in series_list if s.get("yKey")]
    if not y_keys and y_key_from_root:
        y_keys = [y_key_from_root]
        # fallback name
        series_list = [{"name": y_key_from_root, "yKey": y_key_from_root}]

    if not x_key or not y_keys:
        st.warning(f"Chart {chart_def.get('id', '')}: Missing xKey or yKey in spec.")
        return

    tmatch = _find_chart_dataframe(x_key, y_keys, tables)
    if tmatch is None:
        st.warning(f"Chart {chart_def.get('id', '')}: No table found containing required keys: {x_key}, {', '.join(y_keys)}")
        return

    df = tmatch["df"].copy()

    # Altair settings
    alt.data_transformers.disable_max_rows()

    # Single-series vs multi-series
    if len(y_keys) == 1:
        y_key = y_keys[0]
        title = series_list[0].get("name") or y_key
        # Keep order as in table (no sorting) to respect report ordering
        plot_df = df[[x_key, y_key]].copy()
        numfmt = _format_for_dtype(plot_df[y_key])

        # Choose a sensible default for KPI: bar with value labels
        base = alt.Chart(plot_df)
        bar = base.mark_bar(size=50, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=alt.X(f"{x_key}:N", sort=None, title=x_key),
            y=alt.Y(f"{y_key}:Q", title=title),
            tooltip=[alt.Tooltip(f"{x_key}:N", title=x_key), alt.Tooltip(f"{y_key}:Q", title=title, format=numfmt or None)],
            color=alt.value("#4C78A8")
        )
        # Text labels on top of bars
        text = base.mark_text(align="center", baseline="bottom", dy=-2, color="#333").encode(
            x=alt.X(f"{x_key}:N", sort=None),
            y=alt.Y(f"{y_key}:Q"),
            text=alt.Text(f"{y_key}:Q", format=numfmt or None)
        )
        chart = (bar + text).properties(height=320, width="container", title=title)
        st.altair_chart(chart, use_container_width=True)
    else:
        # Multi-series: reshape to long format
        plot_df = df[[x_key] + y_keys].melt(id_vars=[x_key], var_name="Series", value_name="Value")
        numfmt = _format_for_dtype(plot_df["Value"]) if not plot_df.empty else ",.2f"
        base = alt.Chart(plot_df)
        bar = base.mark_bar().encode(
            x=alt.X(f"{x_key}:N", sort=None, title=x_key),
            y=alt.Y("Value:Q", title="Value"),
            color=alt.Color("Series:N", title="Series"),
            tooltip=[alt.Tooltip(f"{x_key}:N", title=x_key), alt.Tooltip("Series:N", title="Series"), alt.Tooltip("Value:Q", title="Value", format=numfmt or None)]
        )
        text = base.mark_text(align="center", baseline="bottom", dy=-2, color="#333").encode(
            x=alt.X(f"{x_key}:N", sort=None),
            y=alt.Y("Value:Q"),
            detail="Series:N",
            text=alt.Text("Value:Q", format=numfmt or None)
        )
        title = chart_def.get("id") or "Chart"
        chart = (bar + text).properties(height=360, width="container", title=title)
        st.altair_chart(chart, use_container_width=True)


def main():
    st.set_page_config(page_title="AI Report Dashboard", page_icon="📊", layout="wide")

    st.title("AI Report Dashboard")

    # Optional: allow user to upload/override the embedded JSON
    with st.expander("Load a different report JSON (optional)"):
        uploaded = st.file_uploader("Upload JSON file", type=["json"])
        if uploaded is not None:
            try:
                loaded = json.load(uploaded)
                st.success("Loaded custom report JSON.")
                report = loaded
            except Exception as e:
                st.error(f"Failed to parse JSON: {e}")
                report = json_report
        else:
            report = json_report
    if uploaded is None:
        report = json_report

    # Summary
    st.subheader("Summary")
    summary_list = report.get("summary", [])
    if isinstance(summary_list, list) and summary_list:
        st.markdown("\n".join([f"- {s}" for s in summary_list]))
    elif isinstance(summary_list, str) and summary_list:
        st.markdown(f"- {summary_list}")
    else:
        st.info("No summary provided.")

    # Issues (if any)
    issues = report.get("issues", [])
    if issues:
        st.subheader("Issues")
        st.markdown("\n".join([f"- {i}" for i in issues]))

    # Tables
    st.subheader("Tables")
    raw_tables = report.get("tables", [])
    parsed_tables: List[Dict[str, Any]] = []
    if raw_tables:
        for idx, t in enumerate(raw_tables):
            name = t.get("name") or f"Table {idx+1}"
            columns = t.get("columns", [])
            rows = t.get("rows", [])
            try:
                df = pd.DataFrame(rows, columns=columns)
                df = _coerce_numeric_columns(df)
            except Exception:
                # Fallback: best-effort construction
                df = pd.DataFrame(rows)
                df.columns = columns[: len(df.columns)] + [f"col_{i}" for i in range(len(df.columns) - len(columns))]
                df = _coerce_numeric_columns(df)
            parsed_tables.append({"name": name, "df": df})
            st.markdown(f"**{name}**")
            st.dataframe(df, use_container_width=True)
    else:
        st.info("No tables in the report.")

    # Charts
    st.subheader("Charts")
    charts = report.get("charts", [])
    if charts:
        for chart_def in charts:
            chart_id = chart_def.get("id") or "Chart"
            st.markdown(f"**{chart_id}**")
            _build_chart(chart_def, parsed_tables)
    else:
        st.info("No charts in the report.")

    # Technical details
    with st.expander("Technical details (raw JSON)"):
        st.code(json.dumps(report, indent=2), language="json")


if __name__ == "__main__":
    main()
