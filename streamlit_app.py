import json
from typing import Dict, Any, List

import streamlit as st
import pandas as pd
import altair as alt

# Disable Altair max rows limit for larger datasets
alt.data_transformers.disable_max_rows()

# -------------------------------------------------------------
# Embedded report data (provided JSON)
# -------------------------------------------------------------
REPORT: Dict[str, Any] = {
    "valid": True,
    "issues": [],
    "summary": [
        "Registered users peaked in February 2025 at 2,093, then declined steadily to 194 by September.",
        "There is a clear downward trend in monthly registered users from Q1 to Q3 2025."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": [
                "month",
                "registered_users"
            ],
            "rows": [
                [
                    "2025-01-01",
                    "1416"
                ],
                [
                    "2025-02-01",
                    "2093"
                ],
                [
                    "2025-03-01",
                    "1946"
                ],
                [
                    "2025-04-01",
                    "1621"
                ],
                [
                    "2025-05-01",
                    "1096"
                ],
                [
                    "2025-06-01",
                    "1491"
                ],
                [
                    "2025-07-01",
                    "1036"
                ],
                [
                    "2025-08-01",
                    "762"
                ],
                [
                    "2025-09-01",
                    "194"
                ]
            ]
        }
    ],
    "charts": [
        {
            "id": "monthly_users_trend",
            "type": "line",
            "spec": {
                "xKey": "month",
                "yKey": "registered_users",
                "series": [
                    {
                        "name": "Registered Users",
                        "yKey": "registered_users"
                    }
                ]
            }
        }
    ],
    "echo": {
        "intent": "trend",
        "used": {
            "tables": [
                "`Haleon_Rewards_User_Performance_110925_user_list`",
                "`Haleon_Rewards_User_Performance_110925_SKUs`"
            ],
            "columns": [
                "Upload_Date",
                "user_id",
                "comuserid"
            ]
        },
        "stats": {
            "elapsed": 0.026676537
        },
        "sql_present": True
    }
}

# -------------------------------------------------------------
# Utilities
# -------------------------------------------------------------

def coerce_dataframe_types(df: pd.DataFrame) -> pd.DataFrame:
    """Attempt to convert common date and numeric fields to proper dtypes."""
    df = df.copy()
    for col in df.columns:
        low = str(col).lower()
        # Date-like columns
        if any(k in low for k in ["date", "month", "time", "timestamp"]):
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            except Exception:
                pass
        # Numeric-like columns: try numeric if objects look numeric
        if df[col].dtype == object:
            try:
                # If many values look numeric, coerce
                sample = df[col].dropna().astype(str).head(20)
                looks_numeric_ratio = 0.0
                if not sample.empty:
                    looks_numeric_ratio = (sample.str.replace(",", "", regex=False)
                                                  .str.match(r"^[+-]?\d*\.?\d+$")
                                                  .mean())
                if looks_numeric_ratio >= 0.6:  # heuristic
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "", regex=False), errors="coerce")
            except Exception:
                pass
    return df


def build_dataframes(report: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    tables = report.get("tables", [])
    dfs: Dict[str, pd.DataFrame] = {}
    for idx, t in enumerate(tables):
        name = t.get("name") or f"table_{idx+1}"
        columns: List[str] = t.get("columns", [])
        rows: List[List[Any]] = t.get("rows", [])
        df = pd.DataFrame(rows, columns=columns)
        df = coerce_dataframe_types(df)
        dfs[name] = df
    return dfs


def pick_dataframe_for_chart(dfs: Dict[str, pd.DataFrame], chart_spec: Dict[str, Any]) -> pd.DataFrame:
    """Pick a DataFrame that contains the required x and y keys. Fallback to the first df."""
    x_key = chart_spec.get("spec", {}).get("xKey")
    y_key = chart_spec.get("spec", {}).get("yKey")
    for df in dfs.values():
        if x_key in df.columns and (y_key is None or y_key in df.columns):
            return df
    # Fallback: first df
    if dfs:
        return list(dfs.values())[0]
    return pd.DataFrame()


def render_chart(df: pd.DataFrame, chart: Dict[str, Any]) -> alt.Chart:
    ctype = (chart.get("type") or "").lower()
    spec = chart.get("spec", {})
    x_key = spec.get("xKey")
    y_key = spec.get("yKey")
    series = spec.get("series") or []
    title = series[0].get("name") if series and isinstance(series[0], dict) else None

    # Determine encodings
    if x_key is None:
        raise ValueError("Chart spec missing xKey")
    if ctype != "pie" and y_key is None:
        raise ValueError("Chart spec missing yKey for non-pie chart")

    # Sort by x for better readability when temporal or numeric
    df_plot = df.copy()
    if x_key in df_plot.columns:
        try:
            if pd.api.types.is_datetime64_any_dtype(df_plot[x_key]) or pd.api.types.is_numeric_dtype(df_plot[x_key]):
                df_plot = df_plot.sort_values(by=x_key)
        except Exception:
            pass

    # Build encodings
    if x_key in df_plot.columns and pd.api.types.is_datetime64_any_dtype(df_plot[x_key]):
        x_enc = alt.X(x_key + ":T", title=x_key)
        tooltip_x = alt.Tooltip(x_key + ":T", title=x_key)
    else:
        # Decide between nominal/quantitative for x if not datetime
        if x_key in df_plot.columns and pd.api.types.is_numeric_dtype(df_plot[x_key]):
            x_enc = alt.X(x_key + ":Q", title=x_key)
            tooltip_x = alt.Tooltip(x_key + ":Q", title=x_key)
        else:
            x_enc = alt.X(x_key + ":N", title=x_key, sort=None)
            tooltip_x = alt.Tooltip(x_key + ":N", title=x_key)

    if y_key is not None:
        y_enc = alt.Y(y_key + ":Q", title=y_key)
        tooltip_y = alt.Tooltip(y_key + ":Q", title=y_key)
    else:
        y_enc = None
        tooltip_y = None

    # Create chart by type
    if ctype == "line":
        base = alt.Chart(df_plot)
        chart_obj = base.mark_line(point=True).encode(
            x=x_enc,
            y=y_enc,
            tooltip=[v for v in [tooltip_x, tooltip_y] if v is not None]
        )
    elif ctype == "bar":
        base = alt.Chart(df_plot)
        chart_obj = base.mark_bar().encode(
            x=x_enc,
            y=y_enc,
            tooltip=[v for v in [tooltip_x, tooltip_y] if v is not None]
        )
    elif ctype == "area":
        base = alt.Chart(df_plot)
        chart_obj = base.mark_area(opacity=0.6).encode(
            x=x_enc,
            y=y_enc,
            tooltip=[v for v in [tooltip_x, tooltip_y] if v is not None]
        )
    elif ctype == "scatter":
        base = alt.Chart(df_plot)
        chart_obj = base.mark_point(filled=True).encode(
            x=x_enc,
            y=y_enc,
            tooltip=[v for v in [tooltip_x, tooltip_y] if v is not None]
        )
    elif ctype == "pie":
        # For pie, interpret xKey as category and yKey as value; aggregate if needed
        category = x_key
        value = y_key
        data = df_plot
        if value is None:
            # If no value provided, count rows per category
            data = data.groupby(category, dropna=False).size().reset_index(name="value")
            theta = alt.Theta("value:Q")
        else:
            data = data.groupby(category, dropna=False)[value].sum().reset_index()
            theta = alt.Theta(f"{value}:Q")
        chart_obj = alt.Chart(data).mark_arc().encode(
            theta=theta,
            color=alt.Color(f"{category}:N", legend=True),
            tooltip=list(data.columns)
        )
    else:
        # Default to line if unknown
        base = alt.Chart(df_plot)
        chart_obj = base.mark_line(point=True).encode(
            x=x_enc,
            y=y_enc,
            tooltip=[v for v in [tooltip_x, tooltip_y] if v is not None]
        )

    if title:
        chart_obj = chart_obj.properties(title=title)
    return chart_obj


# -------------------------------------------------------------
# Streamlit App
# -------------------------------------------------------------

def main():
    st.set_page_config(page_title="AI Report Dashboard", layout="wide")

    st.title("AI Report Dashboard")

    # Summary
    st.subheader("Summary")
    summary_items = REPORT.get("summary", [])
    if summary_items:
        for item in summary_items:
            st.markdown(f"- {item}")
    else:
        st.info("No summary provided.")

    # Tables
    st.subheader("Tables")
    dfs = build_dataframes(REPORT)
    if dfs:
        for name, df in dfs.items():
            st.markdown(f"#### {name}")
            st.dataframe(df, use_container_width=True)
    else:
        st.info("No tables available.")

    # Charts
    st.subheader("Charts")
    charts = REPORT.get("charts", [])
    if charts:
        for ch in charts:
            df_for_chart = pick_dataframe_for_chart(dfs, ch)
            try:
                chart_obj = render_chart(df_for_chart, ch)
                st.altair_chart(chart_obj, use_container_width=True)
            except Exception as e:
                st.error(f"Failed to render chart {ch.get('id')}: {e}")
    else:
        st.info("No charts available.")

    # Validation and debug info
    with st.expander("Validation and Debug Info"):
        st.write("Valid:", REPORT.get("valid"))
        issues = REPORT.get("issues", [])
        if issues:
            st.write("Issues:")
            for i in issues:
                st.write("-", i)
        else:
            st.write("Issues: None")
        st.write("Echo:")
        st.json(REPORT.get("echo", {}))


if __name__ == "__main__":
    main()
