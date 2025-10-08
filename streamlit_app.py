from typing import Dict, Tuple, Callable, Optional
import re
from datetime import datetime

import streamlit as st
import pandas as pd
import altair as alt


# Guard to avoid multiple page_config calls in multi-import contexts
_PAGE_CONFIG_SET = False


def sanitize_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Return a copy of df with safe snake_case columns and a mapping of original->safe.
    Rules: lowercased, spaces/hyphens to underscores, non-alnum removed, ensure unique.
    If a name starts with a non-letter, prefix with 'col_'.
    """
    original_cols = list(df.columns)
    safe_cols = []
    mapping: Dict[str, str] = {}

    def make_safe(name: str) -> str:
        s = str(name).strip().lower()
        s = re.sub(r"[\s\-]+", "_", s)
        s = re.sub(r"[^a-z0-9_]", "", s)
        s = re.sub(r"_+", "_", s)
        s = s.strip("_")
        if not s or not re.match(r"^[a-z]", s):
            s = f"col_{s}" if s else "col"
        return s

    used = set()
    for col in original_cols:
        base = make_safe(col)
        candidate = base
        i = 1
        while candidate in used:
            candidate = f"{base}_{i}"
            i += 1
        used.add(candidate)
        safe_cols.append(candidate)
        mapping[col] = candidate

    df_safe = df.copy()
    df_safe.columns = safe_cols
    return df_safe, mapping


def coerce_numeric(df: pd.DataFrame, cols) -> pd.DataFrame:
    """Coerce the specified columns to numeric by stripping non-numeric chars.
    Returns the same DataFrame reference for chaining.
    """
    if not isinstance(cols, (list, tuple, pd.Index)):
        cols = [cols]
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c]
                .astype(str)
                .str.replace(r"[^0-9.\-]", "", regex=True)
                .replace({"": None}),
                errors="coerce",
            )
    return df


def coerce_datetime(df: pd.DataFrame, cols) -> pd.DataFrame:
    """Coerce specified columns to datetime with errors coerced to NaT."""
    if not isinstance(cols, (list, tuple, pd.Index)):
        cols = [cols]
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable: Callable[[], Tuple[alt.Chart, Optional[pd.DataFrame]]]):
    """
    Execute a chart builder inside try/except. The builder should return either:
      - chart
      - (chart, fallback_df)
    If an exception occurs, show a warning and (if provided) the fallback_df via st.dataframe.
    """
    try:
        built = chart_builder_callable()
        if isinstance(built, tuple):
            chart, fallback_df = built
        else:
            chart, fallback_df = built, None
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.warning("Chart unavailable")
        try:
            # try to fetch a fallback df if the builder captured one
            if isinstance(built, tuple) and len(built) > 1 and built[1] is not None:
                st.dataframe(built[1])
        except Exception:
            pass


def render_app():
    global _PAGE_CONFIG_SET
    if not _PAGE_CONFIG_SET:
        st.set_page_config(page_title="AI Report", layout="wide")
        _PAGE_CONFIG_SET = True

    # Altair row-limit disable (defensive)
    alt.data_transformers.disable_max_rows()

    # Embedded report data from the provided JSON
    REPORT = {
        "valid": True,
        "issues": [],
        "summary": [
            "Total sales grew through 2024, with Q4 2024 (448770.4200000053) +49.55% vs Q3 2024 (300075.42999999237).",
            "2025 started above 2024 Q4 (Q1 2025 = 463266.6000000094, +3.23% vs Q4 2024), then fell sharply: Q2 2025 = 371077.9300000016 (-19.90% vs Q1 2025) and Q3 2025 = 210964.6999999934 (-43.15% vs Q2 2025).",
            "Buyers and purchases mirror the sales trend: buyers peak in 2024 Q4 (5245) and fall to 1711 by 2025 Q3; purchases fall from 9913 (2025 Q1) to 5689 (2025 Q3).",
            "Year-to-date totals (available rows): 2024 total_sales sum = 1307562.9099999894 (4 quarters); 2025 total_sales sum (Q1–Q3) = 1045309.2300000044 — 2025 trailing three-quarter sales are below 2024 full-year total, signaling weakening momentum.",
            "Recommendations: investigate causes for 2025 decline (demand, supply, pricing, promotions); prioritize customer retention and reactivation campaigns; replicate successful Q4 2024 tactics earlier (promo timing, inventory readiness); monitor buyer counts as leading indicator.",
        ],
        "tables": [
            {
                "name": "Quarterly performance (raw)",
                "columns": ["yr", "q", "purchases", "total_sales", "total_units", "buyers"],
                "rows": [
                    [2024, 1, "3702", 259402.10999999472, "9002", "2579"],
                    [2024, 2, "5281", 299314.9499999972, "9713", "3055"],
                    [2024, 3, "8402", 300075.42999999237, "13323", "2494"],
                    [2024, 4, "10060", 448770.4200000053, "18388", "5245"],
                    [2025, 1, "9913", 463266.6000000094, "19670", "4999"],
                    [2025, 2, "9008", 371077.9300000016, "15482", "3826"],
                    [2025, 3, "5689", 210964.6999999934, "8576", "1711"],
                ],
            }
        ],
        "charts": [
            {
                "id": "total_sales_trend",
                "type": "line",
                "spec": {
                    "xKey": "yr_q",
                    "yKey": "total_sales",
                    "series": [
                        {"name": "Total Sales", "yKey": "total_sales"}
                    ],
                },
            }
        ],
        "echo": {
            "intent": "trend",
            "used": {"tables": ["Quarterly performance (raw)"], "columns": ["yr", "q", "purchases", "total_sales", "total_units", "buyers"]},
            "stats": {"elapsed": 0},
            "sql_present": False,
        },
    }

    # Title
    st.title("AI Report")

    # Summary bullets
    if REPORT.get("summary"):
        st.subheader("Summary")
        for bullet in REPORT["summary"]:
            st.markdown(f"- {bullet}")

    # Render tables
    tables = REPORT.get("tables", [])
    dfs_original = []  # Keep originals for display
    dfs_sanitized = []  # Keep sanitized copies for charting
    mappings = []  # original -> safe mappings

    for t in tables:
        name = t.get("name", "Table")
        cols = t.get("columns", [])
        rows = t.get("rows", [])
        try:
            df = pd.DataFrame(rows, columns=cols)
        except Exception:
            df = pd.DataFrame(rows)
        dfs_original.append(df)
        st.subheader(name)
        st.dataframe(df)  # show original column names

        # Prepare sanitized version for charting
        df_safe, mapping = sanitize_columns(df)
        # Attempt type coercions for likely numeric/datetime fields
        numeric_candidates = []
        for k in ["yr", "q", "purchases", "total_sales", "total_units", "buyers"]:
            if k in mapping:
                numeric_candidates.append(mapping[k])
        df_safe = coerce_numeric(df_safe, numeric_candidates)
        dfs_sanitized.append(df_safe)
        mappings.append(mapping)

    # Helper to build charts using the first table by default (defensive fallback)
    def get_primary_table():
        if dfs_sanitized:
            return dfs_sanitized[0], mappings[0], dfs_original[0]
        return pd.DataFrame(), {}, pd.DataFrame()

    # Render charts
    charts = REPORT.get("charts", [])
    if charts:
        st.subheader("Charts")

    for ch in charts:
        ch_type = (ch.get("type") or "").lower()
        spec = ch.get("spec", {})
        x_key_raw = spec.get("xKey")
        y_key_raw = spec.get("yKey")

        df_safe, mapping, df_orig = get_primary_table()
        # We'll work on a copy to avoid mutating shared state across charts
        sdf = df_safe.copy()

        # Derive fields if requested (e.g., yr_q)
        # If x_key_raw is 'yr_q', create it from yr and q when possible
        if x_key_raw == "yr_q":
            yr_safe = mapping.get("yr")
            q_safe = mapping.get("q")
            if yr_safe in sdf.columns and q_safe in sdf.columns:
                # Ensure numeric for ordering/formatting
                sdf = coerce_numeric(sdf, [yr_safe, q_safe])
                def _fmt_yq(r):
                    try:
                        yv = int(r.get(yr_safe)) if pd.notna(r.get(yr_safe)) else None
                        qv = int(r.get(q_safe)) if pd.notna(r.get(q_safe)) else None
                        if yv is None or qv is None:
                            return None
                        return f"{yv}-Q{qv}"
                    except Exception:
                        return None
                sdf["yr_q"] = sdf.apply(_fmt_yq, axis=1)
            else:
                # Keep x as-is; it will fail validation below and fallback
                pass

        # Prepare safe column names for x and y
        # If x_key_raw is derived ('yr_q'), it already exists as "yr_q"; otherwise map original->safe
        x_safe = x_key_raw if x_key_raw == "yr_q" else mapping.get(x_key_raw, x_key_raw)
        y_safe = mapping.get(y_key_raw, y_key_raw)

        # Coerce numeric for y axis
        sdf = coerce_numeric(sdf, [y_safe])

        # Validate required columns and non-null data
        def build_line_chart():
            # Local validation
            if x_safe not in sdf.columns or y_safe not in sdf.columns:
                raise ValueError("Required columns missing for chart")
            df_valid = sdf[[x_safe, y_safe]].dropna(subset=[x_safe, y_safe])
            if df_valid.empty:
                raise ValueError("No valid data for chart")

            # If sortable by year/quarter, sort accordingly; else keep order
            if x_key_raw == "yr_q":
                # If we still have yr and q, sort by them; else by x_safe
                yr_safe = mapping.get("yr")
                q_safe = mapping.get("q")
                if yr_safe in sdf.columns and q_safe in sdf.columns:
                    df_valid = df_valid.join(sdf[[yr_safe, q_safe]], how="left")
                    try:
                        df_valid = coerce_numeric(df_valid, [yr_safe, q_safe])
                        df_valid = df_valid.sort_values([yr_safe, q_safe])
                        df_valid = df_valid[[x_safe, y_safe]]  # restore cols
                    except Exception:
                        df_valid = df_valid
                else:
                    # fallback: keep current order
                    pass

            # Build Altair line chart
            chart = (
                alt.Chart(df_valid)
                .mark_line(point=True)
                .encode(
                    x=alt.X(x_safe, type="nominal", title=x_key_raw if x_key_raw else "x"),
                    y=alt.Y(y_safe, type="quantitative", title=y_key_raw if y_key_raw else "y"),
                    tooltip=[c for c in [x_safe, y_safe] if c in df_valid.columns],
                )
            )
            return chart, sdf

        def build_bar_chart():
            # Local validation
            if x_safe not in sdf.columns or y_safe not in sdf.columns:
                raise ValueError("Required columns missing for chart")
            df_valid = sdf[[x_safe, y_safe]].dropna(subset=[x_safe, y_safe])
            if df_valid.empty:
                raise ValueError("No valid data for chart")
            chart = (
                alt.Chart(df_valid)
                .mark_bar()
                .encode(
                    x=alt.X(x_safe, type="nominal", title=x_key_raw if x_key_raw else "x"),
                    y=alt.Y(y_safe, type="quantitative", title=y_key_raw if y_key_raw else "y"),
                    tooltip=[c for c in [x_safe, y_safe] if c in df_valid.columns],
                )
            )
            return chart, sdf

        def build_area_chart():
            if x_safe not in sdf.columns or y_safe not in sdf.columns:
                raise ValueError("Required columns missing for chart")
            df_valid = sdf[[x_safe, y_safe]].dropna(subset=[x_safe, y_safe])
            if df_valid.empty:
                raise ValueError("No valid data for chart")
            chart = (
                alt.Chart(df_valid)
                .mark_area()
                .encode(
                    x=alt.X(x_safe, type="nominal", title=x_key_raw if x_key_raw else "x"),
                    y=alt.Y(y_safe, type="quantitative", title=y_key_raw if y_key_raw else "y"),
                    tooltip=[c for c in [x_safe, y_safe] if c in df_valid.columns],
                )
            )
            return chart, sdf

        def build_pie_chart():
            # For completeness if any future pie specs appear; not used here directly
            dim = x_safe
            val = y_safe
            if dim not in sdf.columns or val not in sdf.columns:
                raise ValueError("Required columns missing for pie chart")
            df_valid = sdf[[dim, val]].dropna(subset=[dim, val])
            if df_valid.empty:
                raise ValueError("No valid data for pie chart")
            chart = (
                alt.Chart(df_valid)
                .mark_arc()
                .encode(
                    theta=alt.Theta(val, type="quantitative"),
                    color=alt.Color(dim, type="nominal"),
                    tooltip=[c for c in [dim, val] if c in df_valid.columns],
                )
            )
            return chart, sdf

        # Subheader per chart
        chart_title = ch.get("id") or f"Chart: {ch_type.title()}"
        st.markdown(f"**{chart_title}**")

        # Choose builder based on type
        if ch_type == "line":
            safe_altair_chart(build_line_chart)
        elif ch_type == "bar":
            safe_altair_chart(build_bar_chart)
        elif ch_type == "area":
            safe_altair_chart(build_area_chart)
        elif ch_type in ("pie", "donut"):
            safe_altair_chart(build_pie_chart)
        else:
            # Unknown type — warn and show sanitized data
            st.warning("Chart type not supported")
            st.dataframe(sdf)


# Note: No top-level execution. The app runs when render_app() is called:
# from streamlit_app import render_app
# render_app()
