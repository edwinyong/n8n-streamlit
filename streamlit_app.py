import streamlit as st
import pandas as pd
import altair as alt
from typing import List, Dict, Any

# Embedded report JSON (provided input)
REPORT: Dict[str, Any] = {
    "valid": True,
    "issues": [],
    "summary": [
        "User registrations and total sales peaked in February 2025 (2,093 users, 181,249.13 sales).",
        "Both metrics declined steadily from March to September 2025, with the lowest in September (194 users, 18,826.01 sales).",
        "Overall, Q1 (Jan–Mar) outperformed subsequent months in both registrations and sales."
    ],
    "tables": [
        {
            "name": "Monthly User Performance 2025",
            "columns": ["month", "registered_users", "total_sales"],
            "rows": [
                ["2025-01-01", "1416", 119626.18999999885],
                ["2025-02-01", "2093", 181249.12999999718],
                ["2025-03-01", "1946", 162391.27999999782],
                ["2025-04-01", "1621", 122584.14999999863],
                ["2025-05-01", "1096", 110036.75999999886],
                ["2025-06-01", "1491", 138457.01999999848],
                ["2025-07-01", "1036", 101228.30999999943],
                ["2025-08-01", "762", 90910.37999999947],
                ["2025-09-01", "194", 18826.00999999998]
            ]
        }
    ],
    "charts": [
        {
            "id": "main",
            "type": "line",
            "spec": {
                "xKey": "month",
                "yKey": "value",
                "series": [
                    {"name": "Registered Users", "yKey": "registered_users"},
                    {"name": "Total Sales", "yKey": "total_sales"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "trend",
        "used": {"tables": ["`Haleon_Rewards_User_Performance_110925_SKUs`"], "columns": ["Upload_Date", "comuserid", "Total Sales Amount"]},
        "stats": {"elapsed": 0.010482119},
        "sql_present": True
    }
}

st.set_page_config(page_title="AI Report App", page_icon="📈", layout="wide")
st.title("AI Report App")

# Helper functions

def preprocess_table(table: Dict[str, Any]) -> pd.DataFrame:
    """Create a pandas DataFrame from a table dict and coerce types."""
    df = pd.DataFrame(table["rows"], columns=table["columns"])

    # Attempt to parse a 'month' column as datetime if present
    if "month" in df.columns:
        df["month"] = pd.to_datetime(df["month"], errors="coerce")

    # Coerce numerics for known numeric columns
    for col in df.columns:
        if col == "month":
            continue
        # try numeric conversion when feasible
        coerced = pd.to_numeric(df[col], errors="ignore")
        df[col] = coerced
    return df


def build_line_chart(df: pd.DataFrame, chart: Dict[str, Any]) -> alt.Chart:
    """Build a line chart using Altair, supporting multiple series. If two series with disparate scales are present, use dual y-axes."""
    spec = chart.get("spec", {})
    x_key = spec.get("xKey") or (df.columns[0] if len(df.columns) > 0 else None)
    series = spec.get("series", [])

    # Base x encoding
    # If x column is datetime-like, use temporal type; otherwise, nominal/ordinal
    if pd.api.types.is_datetime64_any_dtype(df.get(x_key)):
        x_enc = alt.X(f"{x_key}:T", title=x_key.capitalize(), axis=alt.Axis(format="%b %Y"))
    else:
        x_enc = alt.X(f"{x_key}:O", title=x_key.capitalize())

    base = alt.Chart(df).encode(x=x_enc)

    # If there are multiple series, layer them; use independent y scales to handle different magnitudes
    layers = []

    palette = [
        "#1f77b4",  # blue
        "#ff7f0e",  # orange
        "#2ca02c",  # green
        "#d62728",  # red
        "#9467bd",  # purple
        "#8c564b",  # brown
    ]

    if series:
        for idx, s in enumerate(series):
            y_key = s.get("yKey")
            name = s.get("name", y_key)
            color_val = palette[idx % len(palette)]

            # Choose axis orientation: first series left, second right, others left
            orient = "left" if idx == 0 else ("right" if idx == 1 else "left")
            axis = alt.Axis(title=name, orient=orient, titleColor=color_val, labelColor=color_val)

            # Tooltip formatting heuristics
            if pd.api.types.is_integer_dtype(df.get(y_key)):
                tooltip_format = ",d"
            else:
                tooltip_format = ",.2f"

            layer = (
                base.mark_line(point=True, stroke=color_val)
                .encode(
                    y=alt.Y(f"{y_key}:Q", axis=axis),
                    tooltip=[
                        alt.Tooltip(f"{x_key}", title="Month", type="temporal" if pd.api.types.is_datetime64_any_dtype(df.get(x_key)) else "nominal", format="%b %Y" if pd.api.types.is_datetime64_any_dtype(df.get(x_key)) else None),
                        alt.Tooltip(f"{y_key}:Q", title=name, format=tooltip_format),
                    ],
                )
            )
            layers.append(layer)

        chart_title = " vs. ".join([s.get("name", s.get("yKey", "")) for s in series])
        combined = alt.layer(*layers).resolve_scale(y="independent").properties(title=chart_title)
        return combined

    # Fallback single-series line chart if no series array provided
    # Try to pick a numeric column other than x
    y_candidates = [c for c in df.columns if c != x_key and pd.api.types.is_numeric_dtype(df[c])]
    if not y_candidates:
        # As a last resort, just plot the first other column
        y_candidates = [c for c in df.columns if c != x_key]
    y_key = y_candidates[0] if y_candidates else None

    if y_key is None:
        return base.mark_text().encode(text=alt.value("No numeric data to plot"))

    line = base.mark_line(point=True).encode(
        y=alt.Y(f"{y_key}:Q", title=y_key.replace("_", " ").title()),
        tooltip=[
            alt.Tooltip(f"{x_key}", title=x_key.capitalize(), type="temporal" if pd.api.types.is_datetime64_any_dtype(df.get(x_key)) else "nominal", format="%b %Y" if pd.api.types.is_datetime64_any_dtype(df.get(x_key)) else None),
            alt.Tooltip(f"{y_key}:Q", title=y_key.replace("_", " ").title(), format=",.2f"),
        ],
    )
    return line


def build_bar_chart(df: pd.DataFrame, chart: Dict[str, Any]) -> alt.Chart:
    spec = chart.get("spec", {})
    x_key = spec.get("xKey") or (df.columns[0] if len(df.columns) > 0 else None)

    # Choose a y metric
    series = spec.get("series", [])
    if series:
        y_key = series[0].get("yKey")
        name = series[0].get("name", y_key)
    else:
        y_candidates = [c for c in df.columns if c != x_key and pd.api.types.is_numeric_dtype(df[c])]
        y_key = y_candidates[0] if y_candidates else None
        name = y_key

    if y_key is None:
        return alt.Chart(df).mark_text().encode(text=alt.value("No numeric data to plot"))

    if pd.api.types.is_datetime64_any_dtype(df.get(x_key)):
        x_enc = alt.X(f"{x_key}:T", axis=alt.Axis(format="%b %Y"), title=x_key.capitalize())
    else:
        x_enc = alt.X(f"{x_key}:O", title=x_key.capitalize())

    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=x_enc,
            y=alt.Y(f"{y_key}:Q", title=name),
            tooltip=[
                alt.Tooltip(f"{x_key}", title=x_key.capitalize(), type="temporal" if pd.api.types.is_datetime64_any_dtype(df.get(x_key)) else "nominal", format="%b %Y" if pd.api.types.is_datetime64_any_dtype(df.get(x_key)) else None),
                alt.Tooltip(f"{y_key}:Q", title=name, format=",.2f"),
            ],
        )
    )


def build_pie_chart(df: pd.DataFrame, chart: Dict[str, Any]) -> alt.Chart:
    spec = chart.get("spec", {})
    category_key = spec.get("xKey") or (df.columns[0] if len(df.columns) > 0 else None)

    series = spec.get("series", [])
    if series:
        value_key = series[0].get("yKey")
        name = series[0].get("name", value_key)
    else:
        value_candidates = [c for c in df.columns if c != category_key and pd.api.types.is_numeric_dtype(df[c])]
        value_key = value_candidates[0] if value_candidates else None
        name = value_key

    if value_key is None or category_key is None:
        return alt.Chart(df).mark_text().encode(text=alt.value("Insufficient data for pie chart"))

    return (
        alt.Chart(df)
        .mark_arc()
        .encode(
            theta=alt.Theta(f"{value_key}:Q", title=name),
            color=alt.Color(f"{category_key}:N", title=category_key.replace("_", " ").title()),
            tooltip=[
                alt.Tooltip(f"{category_key}:N", title=category_key.replace("_", " ").title()),
                alt.Tooltip(f"{value_key}:Q", title=name, format=",.2f"),
            ],
        )
    )


# Render summary
st.subheader("Summary")
if REPORT.get("summary"):
    for item in REPORT["summary"]:
        st.markdown(f"- {item}")
else:
    st.info("No summary available.")

# Render tables
st.subheader("Tables")
processed_tables: List[pd.DataFrame] = []
for idx, table in enumerate(REPORT.get("tables", [])):
    st.markdown(f"Table {idx + 1}: {table.get('name', 'Untitled')}")
    df = preprocess_table(table)
    processed_tables.append(df)
    st.dataframe(df, use_container_width=True)

# Render charts (Altair)
st.subheader("Charts")
if REPORT.get("charts"):
    # For simplicity, bind charts to the first processed table when dataset linkage is not specified
    df_for_charts = processed_tables[0] if processed_tables else None

    if df_for_charts is None or df_for_charts.empty:
        st.warning("No data available to render charts.")
    else:
        for chart in REPORT["charts"]:
            chart_id = chart.get("id", "chart")
            chart_type = (chart.get("type") or "").lower()
            st.markdown(f"Chart: {chart_id} ({chart_type})")

            if chart_type == "line":
                alt_chart = build_line_chart(df_for_charts, chart)
            elif chart_type == "bar":
                alt_chart = build_bar_chart(df_for_charts, chart)
            elif chart_type == "pie":
                alt_chart = build_pie_chart(df_for_charts, chart)
            else:
                # Default to line chart if type unrecognized
                alt_chart = build_line_chart(df_for_charts, chart)

            st.altair_chart(alt_chart.interactive(), use_container_width=True)
else:
    st.info("No charts found in the report.")

# Optional: Show echo/debug info if present
with st.expander("Report metadata"):
    st.json({k: v for k, v in REPORT.items() if k in ("valid", "issues", "echo")})
