from datetime import datetime
import re
from typing import Dict, List, Tuple

import altair as alt
import pandas as pd
import streamlit as st


def sanitize_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Return a copy of df with sanitized, unique, safe column names and a mapping
    from original -> safe. Safe names are lower_snake_case using only [A-Za-z0-9_].
    """
    def to_safe(name: str) -> str:
        s = str(name).strip().lower()
        s = re.sub(r"\s+", "_", s)
        s = re.sub(r"[^a-z0-9_]", "_", s)
        s = re.sub(r"_+", "_", s).strip("_")
        if s == "":
            s = "col"
        return s

    original_cols = list(df.columns)
    safe_names = {}
    used = set()
    for col in original_cols:
        base = to_safe(col)
        cand = base
        i = 1
        while cand in used:
            i += 1
            cand = f"{base}_{i}"
        used.add(cand)
        safe_names[col] = cand

    df_safe = df.copy()
    df_safe.columns = [safe_names[c] for c in original_cols]
    return df_safe, safe_names


def coerce_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    """Coerce listed columns to numeric by stripping non-numeric characters."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c].apply(lambda x: re.sub(r"[^0-9.\-]", "", str(x)) if pd.notnull(x) else x),
                errors="coerce",
            )
    return df


def coerce_datetime(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    """Coerce listed columns to datetimes with errors coerced to NaT."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable):
    """
    Executes chart_builder_callable() inside try/except and renders the chart safely.
    On failure, shows a warning and the sanitized fallback table if provided via
    chart_builder_callable._fallback_df.
    """
    try:
        chart = chart_builder_callable()
        if chart is None:
            st.warning("Chart unavailable")
            fallback_df = getattr(chart_builder_callable, "_fallback_df", None)
            if isinstance(fallback_df, pd.DataFrame):
                st.dataframe(fallback_df)
            return
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.warning("Chart unavailable")
        fallback_df = getattr(chart_builder_callable, "_fallback_df", None)
        if isinstance(fallback_df, pd.DataFrame):
            st.dataframe(fallback_df)


def render_app():
    # Guard page config to avoid duplicate configuration on reruns/imports
    if not st.session_state.get("_page_configured", False):
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_configured"] = True

    # Altair safe row handling
    alt.data_transformers.disable_max_rows()

    # ---- Report JSON (embedded) ----
    report = {
        "valid": True,
        "issues": [],
        "summary": [
            "Quarterly sales, buyers, purchases, and units all peaked in Q4 2024 and Q1 2025, with Q1 2025 showing the highest total sales (463,266.60) and units (19,670).",
            "There was strong growth from Q1 to Q2 2024 in buyers (+18.5%), purchases (+42.7%), and sales (+15.4%), with continued increases into Q3 and Q4 2024.",
            "Q4 2024 saw a surge in buyers (5,245) and purchases (10,060), resulting in a significant sales jump to 448,770.42, up 49.6% from Q3 2024.",
            "After the Q1 2025 peak, Q2 2025 saw declines in buyers (-23.5%), purchases (-9.1%), sales (-19.9%), and units (-21.3%) compared to Q1 2025.",
            "Q3 2025 continued the downward trend, with buyers, purchases, sales, and units all dropping to the lowest levels in the period (buyers: 1,711; sales: 210,964.70).",
            "Overall, the period shows a strong upward trend through 2024, peaking in Q1 2025, followed by a notable contraction in Q2 and Q3 2025."
        ],
        "tables": [
            {
                "name": "Quarterly Report 2024-2025",
                "columns": ["yr", "q", "buyers", "purchases", "total_sales", "total_units"],
                "rows": [
                    [2024, 1, "2579", "3702", 259402.10999999472, "9002"],
                    [2024, 2, "3055", "5281", 299314.9499999972, "9713"],
                    [2024, 3, "2494", "8402", 300075.42999999237, "13323"],
                    [2024, 4, "5245", "10060", 448770.4200000053, "18388"],
                    [2025, 1, "4999", "9913", 463266.6000000094, "19670"],
                    [2025, 2, "3826", "9008", 371077.9300000016, "15482"],
                    [2025, 3, "1711", "5689", 210964.6999999934, "8576"]
                ]
            }
        ],
        "charts": [
            {
                "id": "quarterly_trends",
                "type": "line",
                "spec": {
                    "xKey": "quarter",
                    "yKey": "total_sales",
                    "series": [
                        {"name": "Total Sales", "yKey": "total_sales"},
                        {"name": "Total Units", "yKey": "total_units"},
                        {"name": "Buyers", "yKey": "buyers"},
                        {"name": "Purchases", "yKey": "purchases"}
                    ]
                }
            },
            {
                "id": "buyers_sales_bar",
                "type": "groupedBar",
                "spec": {
                    "xKey": "quarter",
                    "yKey": "value",
                    "series": [
                        {"name": "Buyers", "yKey": "buyers"},
                        {"name": "Purchases", "yKey": "purchases"}
                    ]
                }
            }
        ],
        "echo": {
            "intent": "trend",
            "used": {
                "tables": ["Quarterly Report 2024-2025"],
                "columns": ["yr", "q", "buyers", "purchases", "total_sales", "total_units"]
            },
            "stats": {"elapsed": 0},
            "sql_present": False
        }
    }

    # ---- Title ----
    st.title("AI Report")

    # ---- Summary ----
    if report.get("summary"):
        st.subheader("Summary")
        for item in report["summary"]:
            st.markdown(f"- {item}")

    # ---- Tables ----
    dfs_original = {}
    dfs_sanitized = {}
    mappings = {}

    if report.get("tables"):
        for tbl in report["tables"]:
            name = tbl.get("name", "Table")
            cols = tbl.get("columns", [])
            rows = tbl.get("rows", [])
            try:
                df = pd.DataFrame(rows, columns=cols)
            except Exception:
                df = pd.DataFrame(rows)
            dfs_original[name] = df

            st.subheader(name)
            st.dataframe(df)

            # Prepare sanitized version for downstream charting
            df_safe, mapping = sanitize_columns(df)
            dfs_sanitized[name] = df_safe
            mappings[name] = mapping

    # Helper to add quarter columns to sanitized df when possible
    def add_quarter_columns(df_safe: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        df2 = df_safe.copy()
        safe_yr = mapping.get("yr")
        safe_q = mapping.get("q")
        # Coerce year/quarter to numeric for computation
        numeric_candidates = [c for c in [safe_yr, safe_q] if c in df2.columns]
        df2 = coerce_numeric(df2, numeric_candidates)
        if safe_yr in df2.columns and safe_q in df2.columns:
            try:
                # quarter start month: 1, 4, 7, 10
                q_num = df2[safe_q]
                y_num = df2[safe_yr]
                # Create label like YYYY-Qn
                df2["quarter_label"] = (
                    y_num.fillna(0).astype(int).astype(str)
                    + "-Q"
                    + q_num.fillna(0).astype(int).astype(str)
                )
                # Create a quarter start date for temporal x-axis
                def to_quarter_date(row):
                    try:
                        y = int(row[safe_yr])
                        q = int(row[safe_q])
                        month = (max(q, 1) - 1) * 3 + 1
                        month = min(max(month, 1), 12)
                        return datetime(y, month, 1)
                    except Exception:
                        return pd.NaT
                df2["quarter_date"] = df2.apply(to_quarter_date, axis=1)
                df2 = coerce_datetime(df2, ["quarter_date"])
            except Exception:
                # If anything goes wrong, at least ensure quarter_label exists as string
                try:
                    df2["quarter_label"] = df2[safe_yr].astype(str) + "-Q" + df2[safe_q].astype(str)
                except Exception:
                    pass
        return df2

    # ---- Charts ----
    st.subheader("Charts")

    # Use the first table for charts if present
    table_for_charts = None
    if report.get("tables"):
        table_for_charts = report["tables"][0].get("name")

    if table_for_charts and table_for_charts in dfs_sanitized:
        base_df_safe = dfs_sanitized[table_for_charts]
        mapping = mappings[table_for_charts]
        dfc = add_quarter_columns(base_df_safe, mapping)
        # Coerce numeric columns commonly used
        numeric_cols_original = ["buyers", "purchases", "total_sales", "total_units"]
        numeric_cols_safe = [mapping.get(c) for c in numeric_cols_original if mapping.get(c) in dfc.columns]
        dfc = coerce_numeric(dfc, numeric_cols_safe)

        # Chart 1: Quarterly trends (line, multiple series)
        st.markdown("#### Quarterly Trends")
        def build_trends_chart():
            # Determine x column: prefer temporal quarter_date, else quarter_label
            if "quarter_date" in dfc.columns and dfc["quarter_date"].notna().sum() > 0:
                x_col = "quarter_date"
                x_type = "temporal"
            elif "quarter_label" in dfc.columns and dfc["quarter_label"].notna().sum() > 0:
                x_col = "quarter_label"
                x_type = "nominal"
            else:
                return None

            # Determine series columns that exist
            series_original = ["total_sales", "total_units", "buyers", "purchases"]
            series_safe = [mapping.get(s) for s in series_original if mapping.get(s) in dfc.columns]
            series_safe = [s for s in series_safe if s is not None]
            if not series_safe:
                return None

            # Melt to long format
            long_df = pd.melt(
                dfc,
                id_vars=[x_col],
                value_vars=series_safe,
                var_name="metric",
                value_name="value",
            )
            # Ensure numeric y
            long_df = coerce_numeric(long_df, ["value"]).copy()

            # Drop rows with missing x or y
            plot_df = long_df.dropna(subset=[x_col, "value"]).copy()
            if plot_df.empty:
                return None

            # Build human-friendly metric names in tooltip by mapping back if possible
            inv_map = {v: k for k, v in mapping.items()}
            plot_df["metric_label"] = plot_df["metric"].apply(lambda m: inv_map.get(m, m))

            tooltip_fields = []
            for f in ["quarter_label", x_col, "metric_label", "value"]:
                if f in plot_df.columns:
                    # Add type hints only for known fields
                    if f == x_col and x_type == "temporal":
                        tooltip_fields.append(alt.Tooltip(f, type="temporal"))
                    elif f == "value":
                        tooltip_fields.append(alt.Tooltip(f, type="quantitative"))
                    else:
                        tooltip_fields.append(alt.Tooltip(f, type="nominal"))

            chart = (
                alt.Chart(plot_df)
                .mark_line(point=True)
                .encode(
                    x=alt.X(f"{x_col}:{'T' if x_type=='temporal' else 'N'}", title="Quarter"),
                    y=alt.Y("value:Q", title="Value"),
                    color=alt.Color("metric_label:N", title="Metric"),
                    tooltip=tooltip_fields,
                )
            )
            return chart

        # Attach fallback df for safe_altair_chart
        build_trends_chart._fallback_df = dfc
        safe_altair_chart(build_trends_chart)

        # Chart 2: Buyers vs Purchases (grouped bar)
        st.markdown("#### Buyers vs Purchases (Grouped Bar)")
        def build_grouped_bar_chart():
            # X as quarter_label nominal (fallback to quarter_date if needed)
            if "quarter_label" in dfc.columns and dfc["quarter_label"].notna().sum() > 0:
                x_col = "quarter_label"
                x_type = "nominal"
            elif "quarter_date" in dfc.columns and dfc["quarter_date"].notna().sum() > 0:
                x_col = "quarter_date"
                x_type = "temporal"
            else:
                return None

            series_original = ["buyers", "purchases"]
            series_safe = [mapping.get(s) for s in series_original if mapping.get(s) in dfc.columns]
            series_safe = [s for s in series_safe if s is not None]
            if not series_safe:
                return None

            long_df = pd.melt(
                dfc,
                id_vars=[x_col],
                value_vars=series_safe,
                var_name="metric",
                value_name="value",
            )
            long_df = coerce_numeric(long_df, ["value"]).copy()
            plot_df = long_df.dropna(subset=[x_col, "value"]).copy()
            if plot_df.empty:
                return None

            inv_map = {v: k for k, v in mapping.items()}
            plot_df["metric_label"] = plot_df["metric"].apply(lambda m: inv_map.get(m, m))

            tooltip_fields = []
            for f in ["quarter_label", x_col, "metric_label", "value"]:
                if f in plot_df.columns:
                    if f == x_col and x_type == "temporal":
                        tooltip_fields.append(alt.Tooltip(f, type="temporal"))
                    elif f == "value":
                        tooltip_fields.append(alt.Tooltip(f, type="quantitative"))
                    else:
                        tooltip_fields.append(alt.Tooltip(f, type="nominal"))

            chart = (
                alt.Chart(plot_df)
                .mark_bar()
                .encode(
                    x=alt.X(f"{x_col}:{'T' if x_type=='temporal' else 'N'}", title="Quarter"),
                    y=alt.Y("value:Q", title="Value"),
                    color=alt.Color("metric_label:N", title="Metric"),
                    tooltip=tooltip_fields,
                )
            )
            return chart

        build_grouped_bar_chart._fallback_df = dfc
        safe_altair_chart(build_grouped_bar_chart)
    else:
        st.info("No data available for charts.")


# Note: render_app() is defined for import-safe usage. Nothing runs on import.
