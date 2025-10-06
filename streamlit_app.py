import json
from typing import Dict, List

import altair as alt
import pandas as pd
import streamlit as st


# Raw report JSON provided
REPORT_JSON = r'''{"valid":true,"issues":[],"summary":["Total sales peaked in February 2025 at 181,249.13 and then generally declined through September.","The lowest monthly sales occurred in September 2025 at 18,826.01.","Overall, there is a downward trend in monthly sales from Q1 to Q3 2025."],"tables":[{"name":"Table","columns":["month","registered_users","total_sales"],"rows":[["2025-01-01","1416",119626.18999999885],["2025-02-01","2093",181249.12999999718],["2025-03-01","1946",162391.27999999782],["2025-04-01","1621",122584.14999999863],["2025-05-01","1096",110036.75999999886],["2025-06-01","1491",138457.01999999848],["2025-07-01","1036",101228.30999999943],["2025-08-01","762",90910.37999999947],["2025-09-01","194",18826.00999999998]]}],"charts":[{"id":"monthly_sales_trend","type":"line","spec":{"xKey":"month","yKey":"total_sales","series":[{"name":"Total Sales","yKey":"total_sales"}]}}],"echo":{"intent":"trend","used":{"tables":["`Haleon_Rewards_User_Performance_110925_SKUs`"],"columns":["Upload_Date","comuserid","Total Sales Amount"]},"stats":{"elapsed":0.01014826},"sql_present":true}}'''


def _altair_type_for_series(s: pd.Series) -> str:\n    """Infer Altair type shorthand for a pandas Series."""
    if pd.api.types.is_datetime64_any_dtype(s):
        return "T"  # Temporal
    if pd.api.types.is_numeric_dtype(s):
        return "Q"  # Quantitative
    return "N"  # Nominal


def _coerce_dataframe_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Try to coerce commonly-named date columns
    date_like = {"date", "month", "day", "timestamp", "upload_date"}
    for col in df.columns:
        lower = str(col).lower()
        if lower in date_like:
            coerced = pd.to_datetime(df[col], errors="coerce")
            # If at least one value parsed, adopt it
            if coerced.notna().any():
                df[col] = coerced
            continue
        # Try numeric coercion for non-date columns
        if df[col].dtype == object:
            numeric = pd.to_numeric(df[col], errors="ignore")
            df[col] = numeric
    return df


def build_line_chart(df: pd.DataFrame, chart_spec: Dict) -> alt.Chart:
    spec = chart_spec.get("spec", {})
    x_key = spec.get("xKey")
    # Determine series configuration
    series_cfg = spec.get("series") or []
    # Fallback to yKey if present
    y_key = spec.get("yKey") or (series_cfg[0]["yKey"] if series_cfg else None)

    if x_key is None:
        raise ValueError("Line chart spec is missing 'xKey'.")
    if y_key is None and not series_cfg:
        raise ValueError("Line chart spec is missing 'yKey' or 'series'.")

    # Prepare data for single or multi-series
    if series_cfg and len(series_cfg) > 1:
        # Long-form assemble from multiple yKeys
        frames = []
        for s in series_cfg:
            name = s.get("name", s.get("yKey", "series"))
            yk = s.get("yKey")
            if yk not in df.columns:
                continue
            part = df[[x_key, yk]].rename(columns={yk: "value"}).copy()
            part["series"] = name
            frames.append(part)
        if not frames:
            raise ValueError("No valid yKeys found for multi-series line chart.")
        long_df = pd.concat(frames, ignore_index=True)
        x_type = _altair_type_for_series(long_df[x_key])
        chart = (
            alt.Chart(long_df)
            .mark_line(point=True)
            .encode(
                x=alt.X(f"{x_key}:{x_type}", title=x_key.replace("_", " ").title()),
                y=alt.Y("value:Q", title="Value", axis=alt.Axis(format="$,.2f")),
                color=alt.Color("series:N", title="Series"),
                tooltip=[
                    alt.Tooltip(f"{x_key}:{'T' if x_type=='T' else 'N'}", title=x_key.replace("_", " ").title()),
                    alt.Tooltip("series:N", title="Series"),
                    alt.Tooltip("value:Q", title="Value", format="$,.2f"),
                ],
            )
        )
        return chart
    else:
        # Single series
        if y_key not in df.columns:
            raise ValueError(f"yKey '{y_key}' not found in data columns.")
        x_type = _altair_type_for_series(df[x_key])
        y_title = next((s.get("name") for s in series_cfg if s.get("yKey") == y_key), None) or y_key.replace("_", " ").title()
        tooltip_fields: List = [
            alt.Tooltip(f"{x_key}:{'T' if x_type=='T' else 'N'}", title=x_key.replace("_", " ").title()),
            alt.Tooltip(f"{y_key}:Q", title=y_title, format="$,.2f"),
        ]
        # Include a few common supplemental fields if available
        for extra in ["registered_users"]:
            if extra in df.columns and extra != y_key:
                t = _altair_type_for_series(df[extra])
                tooltip_fields.append(alt.Tooltip(f"{extra}:{'Q' if t=='Q' else 'N'}", title=extra.replace("_", " ").title()))

        chart = (
            alt.Chart(df)
            .mark_line(point=True)
            .encode(
                x=alt.X(f"{x_key}:{x_type}", title=x_key.replace("_", " ").title()),
                y=alt.Y(f"{y_key}:Q", title=y_title, axis=alt.Axis(format="$,.2f")),
                tooltip=tooltip_fields,
            )
        )
        return chart


def build_bar_chart(df: pd.DataFrame, chart_spec: Dict) -> alt.Chart:
    spec = chart_spec.get("spec", {})
    x_key = spec.get("xKey")
    y_key = spec.get("yKey")
    if x_key is None or y_key is None:
        raise ValueError("Bar chart spec requires 'xKey' and 'yKey'.")

    x_type = _altair_type_for_series(df[x_key])
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_key}:{x_type}", title=x_key.replace("_", " ").title()),
            y=alt.Y(f"{y_key}:Q", title=y_key.replace("_", " ").title(), axis=alt.Axis(format="$,.2f")),
            tooltip=[
                alt.Tooltip(f"{x_key}:{'T' if x_type=='T' else 'N'}", title=x_key.replace("_", " ").title()),
                alt.Tooltip(f"{y_key}:Q", title=y_key.replace("_", " ").title(), format="$,.2f"),
            ],
        )
    )
    return chart


def build_pie_chart(df: pd.DataFrame, chart_spec: Dict) -> alt.Chart:
    spec = chart_spec.get("spec", {})
    category = spec.get("category") or spec.get("xKey")
    value = spec.get("value") or spec.get("yKey")
    if category is None or value is None:
        raise ValueError("Pie chart spec requires 'category' (or xKey) and 'value' (or yKey').")

    chart = (
        alt.Chart(df)
        .mark_arc(innerRadius=50)
        .encode(
            theta=alt.Theta(f"{value}:Q", stack=True),
            color=alt.Color(f"{category}:N", title=category.replace("_", " ").title()),
            tooltip=[
                alt.Tooltip(f"{category}:N", title=category.replace("_", " ").title()),
                alt.Tooltip(f"{value}:Q", title=value.replace("_", " ").title(), format="$,.2f"),
            ],
        )
    )
    return chart


def render_chart(chart_spec: Dict, dataframes: Dict[str, pd.DataFrame]) -> alt.Chart:
    # Use the first table by default if no explicit mapping
    df = next(iter(dataframes.values()))
    ctype = (chart_spec.get("type") or "").lower()

    if ctype == "line":
        return build_line_chart(df, chart_spec)
    if ctype == "bar":
        return build_bar_chart(df, chart_spec)
    if ctype == "pie":
        return build_pie_chart(df, chart_spec)

    # Fallback: try line with provided keys
    return build_line_chart(df, chart_spec)


def main():
    st.set_page_config(page_title="AI Report App", page_icon="📊", layout="wide")
    st.title("AI Report Viewer")
    st.caption("Interactive Streamlit app generated from an AI JSON report")

    report = json.loads(REPORT_JSON)

    # Summary section
    st.subheader("Summary")
    summary_items = report.get("summary") or []
    if summary_items:
        for item in summary_items:
            st.markdown(f"- {item}")
    else:
        st.info("No summary available.")

    # Tables section
    st.subheader("Tables")
    tables = report.get("tables") or []
    dataframes: Dict[str, pd.DataFrame] = {}

    if not tables:
        st.info("No tables found in the report.")
    else:
        for idx, tbl in enumerate(tables, start=1):
            name = tbl.get("name") or f"Table {idx}"
            columns = tbl.get("columns") or []
            rows = tbl.get("rows") or []
            try:
                df = pd.DataFrame(rows, columns=columns)
            except Exception:
                # Fallback if columns mismatch; let pandas infer
                df = pd.DataFrame(rows)
                if columns and len(columns) == df.shape[1]:
                    df.columns = columns
            df = _coerce_dataframe_types(df)

            st.markdown(f"**{name}**")
            st.dataframe(df, use_container_width=True)

            # Store by name; if duplicate names occur, index them
            key = name if name not in dataframes else f"{name}_{idx}"
            dataframes[key] = df

    # Charts section
    st.subheader("Charts")
    charts = report.get("charts") or []
    if not charts:
        st.info("No charts found in the report.")
    else:
        for ch in charts:
            chart_id = ch.get("id") or ch.get("type") or "Chart"
            st.markdown(f"**{chart_id.replace('_', ' ').title()}**")
            try:
                chart = render_chart(ch, dataframes)
                st.altair_chart(chart.properties(height=380), use_container_width=True)
            except Exception as e:
                st.error(f"Failed to render chart '{chart_id}': {e}")

    # Optional: show raw JSON in an expander for transparency
    with st.expander("Show raw report JSON"):
        st.code(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
