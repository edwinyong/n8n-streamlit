from typing import Callable, Dict, Tuple, List
import re
from datetime import datetime  # potentially useful for future extensions

import streamlit as st
import pandas as pd
import altair as alt


# Embedded report data provided by the user
REPORT_DATA = {
    "valid": True,
    "issues": [],
    "summary": [
        "Quarterly sales and activity increased from Q1 2024 to Q1 2025, with total sales peaking in Q1 2025 at 463,266.60.",
        "Registered purchasers, buyers, purchases, and total units generally trended upward through 2024, peaking in Q1 2025 before declining in Q3 2025.",
        "Q4 2024 saw a significant jump in both total sales and activity compared to previous quarters, indicating strong year-end performance.",
        "After Q1 2025, there is a noticeable decline in all metrics, especially in Q3 2025, suggesting possible seasonality or market saturation.",
        "Improvement opportunities: Investigate causes for post-Q1 2025 declines, optimize marketing and retention strategies for mid-to-late 2025, and analyze Q4 2024 drivers for replication."
    ],
    "tables": [
        {
            "name": "Quarterly Report 2024-2025",
            "columns": [
                "yr",
                "q",
                "registered_purchasers",
                "buyers",
                "purchases",
                "total_units",
                "total_sales"
            ],
            "rows": [
                [2024, 1, "2579", "2579", "3702", "9002", 259402.10999999472],
                [2024, 2, "3055", "3055", "5281", "9713", 299314.9499999972],
                [2024, 3, "2494", "2494", "8402", "13323", 300075.42999999237],
                [2024, 4, "5245", "5245", "10060", "18388", 448770.4200000053],
                [2025, 1, "4998", "4999", "9913", "19670", 463266.6000000094],
                [2025, 2, "3826", "3826", "9008", "15482", 371077.9300000016],
                [2025, 3, "1711", "1711", "5689", "8576", 210964.6999999934]
            ]
        }
    ],
    "charts": [
        {
            "id": "trend_sales",
            "type": "line",
            "spec": {
                "xKey": "yr_q",
                "yKey": "total_sales",
                "series": [
                    {"name": "Total Sales", "yKey": "total_sales"}
                ]
            }
        },
        {
            "id": "trend_activity",
            "type": "groupedBar",
            "spec": {
                "xKey": "yr_q",
                "yKey": "value",
                "series": [
                    {"name": "Registered Purchasers", "yKey": "registered_purchasers"},
                    {"name": "Buyers", "yKey": "buyers"},
                    {"name": "Purchases", "yKey": "purchases"},
                    {"name": "Total Units", "yKey": "total_units"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "trend",
        "used": {
            "tables": ["Quarterly Report 2024-2025"],
            "columns": ["yr", "q", "registered_purchasers", "buyers", "purchases", "total_units", "total_sales"]
        },
        "stats": {"elapsed": 0},
        "sql_present": False
    }
}


def sanitize_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Return a copy of df with safe snake_case columns and a mapping of original->safe."""
    def to_safe(name: str) -> str:
        s = str(name)
        s = s.strip()
        s = re.sub(r"[^A-Za-z0-9_]+", "_", s)
        s = re.sub(r"__+", "_", s)
        s = s.strip("_")
        s = s.lower()
        if not s:
            s = "col"
        return s

    mapping = {col: to_safe(col) for col in df.columns}
    df_safe = df.copy()
    df_safe.columns = [mapping[c] for c in df.columns]
    return df_safe, mapping


def coerce_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    """Coerce specified columns to numeric by stripping non-numeric characters."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace(r"[^0-9.\-]+", "", regex=True), errors="coerce"
            )
    return df


def coerce_datetime(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    """Coerce specified columns to datetime (errors coerced to NaT)."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable: Callable[[], alt.Chart], fallback_df: pd.DataFrame = None) -> None:
    """Safely build and render an Altair chart; on failure, warn and show fallback table."""
    try:
        chart = chart_builder_callable()
        if chart is None:
            st.warning("Chart unavailable")
            if fallback_df is not None:
                st.dataframe(fallback_df)
            return
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.warning("Chart unavailable")
        if fallback_df is not None:
            st.dataframe(fallback_df)


def _build_dataframe(table_obj: Dict) -> pd.DataFrame:
    cols = table_obj.get("columns", [])
    rows = table_obj.get("rows", [])
    df = pd.DataFrame(rows, columns=cols)
    return df


def render_app():
    # Guard page config so it's only set once in shared/multi-run contexts
    if not st.session_state.get("_page_config_set", False):
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_set"] = True

    # Avoid Altair row-limit issues
    alt.data_transformers.disable_max_rows()

    st.title("AI Report")

    # Summary section
    st.header("Summary")
    if isinstance(REPORT_DATA.get("summary"), list) and REPORT_DATA["summary"]:
        for item in REPORT_DATA["summary"]:
            st.markdown(f"- {item}")
    else:
        st.write("No summary available.")

    # Tables section
    st.header("Tables")
    tables = REPORT_DATA.get("tables", [])
    original_dfs: Dict[str, pd.DataFrame] = {}
    sanitized_dfs: Dict[str, Tuple[pd.DataFrame, Dict[str, str]]] = {}

    for idx, t in enumerate(tables):
        name = t.get("name") or f"Table {idx+1}"
        st.subheader(name)
        df = _build_dataframe(t)
        original_dfs[name] = df
        st.dataframe(df)  # Show original columns as required

        # Prepare sanitized copy for charting
        df_safe, mapping = sanitize_columns(df)

        # Identify potential numeric columns from known fields (intersection)
        numeric_candidates = {
            "yr",
            "q",
            "registered_purchasers",
            "buyers",
            "purchases",
            "total_units",
            "total_sales",
            "value",
        }
        numeric_cols_to_coerce = [c for c in df_safe.columns if c in numeric_candidates]
        df_safe = coerce_numeric(df_safe, numeric_cols_to_coerce)

        # Add derived yr_q if yr and q exist
        if "yr" in df_safe.columns and "q" in df_safe.columns:
            def _format_yq(row):
                y = row.get("yr")
                q = row.get("q")
                if pd.notnull(y) and pd.notnull(q):
                    try:
                        return f"{int(float(y))}-Q{int(float(q))}"
                    except Exception:
                        return None
                return None
            df_safe["yr_q"] = df_safe.apply(_format_yq, axis=1)

        sanitized_dfs[name] = (df_safe, mapping)

    # Charts section
    st.header("Charts")

    # For this report, charts reference the "Quarterly Report 2024-2025" table.
    # If not found, default to the first available table.
    preferred_table_name = None
    try:
        used_tables = REPORT_DATA.get("echo", {}).get("used", {}).get("tables", [])
        if used_tables:
            preferred_table_name = used_tables[0]
    except Exception:
        preferred_table_name = None

    if tables:
        if preferred_table_name not in sanitized_dfs:
            preferred_table_name = list(sanitized_dfs.keys())[0]
        df_safe_ref, _ = sanitized_dfs.get(preferred_table_name, (None, None))
    else:
        df_safe_ref = None

    charts = REPORT_DATA.get("charts", [])
    if not charts:
        st.write("No charts available.")
        return

    for ch in charts:
        ch_id = ch.get("id", "chart")
        ch_type = ch.get("type", "")
        spec = ch.get("spec", {})

        # Build each chart defensively
        if ch_type.lower() == "line":
            st.subheader("Total Sales Trend")

            def build_line_chart():
                dfc = df_safe_ref
                if dfc is None:
                    return None
                x_key = spec.get("xKey", "yr_q")
                y_key = spec.get("yKey", "total_sales")

                # Ensure required fields exist
                if x_key not in dfc.columns or y_key not in dfc.columns:
                    return None

                # Ensure y is numeric; if not, attempt coercion
                if not pd.api.types.is_numeric_dtype(dfc[y_key]):
                    temp = dfc.copy()
                    temp = coerce_numeric(temp, [y_key])
                    dfc = temp

                # Filter to non-null x and y rows
                mask = dfc[[x_key, y_key]].notnull().all(axis=1)
                data = dfc.loc[mask, [x_key, y_key]]
                if data.empty:
                    return None

                chart = (
                    alt.Chart(data)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X(f"{x_key}:N", title="Year-Quarter"),
                        y=alt.Y(f"{y_key}:Q", title="Total Sales"),
                        tooltip=[x_key, y_key],
                    )
                )
                return chart

            safe_altair_chart(build_line_chart, fallback_df=df_safe_ref)

        elif ch_type.lower() in ("bar", "groupedbar"):
            st.subheader("Activity by Quarter (Grouped)")

            def build_grouped_bar():
                dfc = df_safe_ref
                if dfc is None:
                    return None
                x_key = spec.get("xKey", "yr_q")
                series = spec.get("series", [])
                if x_key not in dfc.columns:
                    return None

                value_columns = []
                for s in series:
                    yk = s.get("yKey")
                    if yk and yk in dfc.columns:
                        value_columns.append(yk)
                if not value_columns:
                    return None

                # Ensure numeric coercion for values
                temp = dfc.copy()
                temp = coerce_numeric(temp, value_columns)

                # Melt to long format: yr_q, metric, value
                melted = temp.melt(
                    id_vars=[x_key],
                    value_vars=value_columns,
                    var_name="metric",
                    value_name="value",
                )

                # Remove rows with nulls
                melted = melted[melted[[x_key, "value"]].notnull().all(axis=1)]
                if melted.empty:
                    return None

                chart = (
                    alt.Chart(melted)
                    .mark_bar()
                    .encode(
                        x=alt.X(f"{x_key}:N", title="Year-Quarter"),
                        y=alt.Y("value:Q", title="Value"),
                        color=alt.Color("metric:N", title="Metric"),
                        tooltip=[x_key, "metric", "value"],
                    )
                )
                return chart

            safe_altair_chart(build_grouped_bar, fallback_df=df_safe_ref)

        elif ch_type.lower() == "pie":
            # Not used in this report, but included for completeness
            st.subheader("Pie Chart")

            def build_pie_chart():
                dfc = df_safe_ref
                if dfc is None:
                    return None
                x_key = spec.get("xKey")
                y_key = spec.get("yKey")
                if not x_key or not y_key:
                    return None
                if x_key not in dfc.columns or y_key not in dfc.columns:
                    return None
                # Ensure numeric coercion for values
                temp = dfc.copy()
                temp = coerce_numeric(temp, [y_key])
                data = temp[[x_key, y_key]].dropna()
                if data.empty:
                    return None

                chart = (
                    alt.Chart(data)
                    .mark_arc()
                    .encode(
                        theta=alt.Theta(f"{y_key}:Q", stack=True),
                        color=alt.Color(f"{x_key}:N", title=x_key),
                        tooltip=[x_key, y_key],
                    )
                )
                return chart

            safe_altair_chart(build_pie_chart, fallback_df=df_safe_ref)

        else:
            # Unknown chart type; gracefully warn
            st.subheader(f"Chart: {ch_id}")
            st.warning("Chart type not recognized")
            if df_safe_ref is not None:
                st.dataframe(df_safe_ref)


# Note: No automatic execution on import. Call render_app() from the host script.
