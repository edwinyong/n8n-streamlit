from typing import Dict, List, Tuple, Callable, Optional
import streamlit as st
import pandas as pd
import altair as alt


def sanitize_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Return a copy of df with sanitized, safe column names and a mapping from original->safe.
    Safe names are lowercase, spaces to underscores, only [A-Za-z0-9_], and unique.
    """
    def make_safe(name: str) -> str:
        s = str(name).strip().lower().replace(" ", "_")
        safe = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in s)
        if safe and safe[0].isdigit():
            safe = "_" + safe
        # Collapse multiple underscores
        while "__" in safe:
            safe = safe.replace("__", "_")
        return safe

    mapping: Dict[str, str] = {}
    used: set = set()
    for col in df.columns:
        base = make_safe(col)
        safe = base
        i = 1
        while safe in used:
            i += 1
            safe = f"{base}_{i}"
        mapping[col] = safe
        used.add(safe)
    df_copy = df.copy()
    df_copy.columns = [mapping[c] for c in df.columns]
    return df_copy, mapping


def _strip_to_numeric_str(x: str) -> str:
    # Keep digits, decimal point, and minus sign only
    allowed = set("0123456789.-")
    return "".join(ch for ch in x if ch in allowed)


def coerce_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    """Coerce specified columns to numeric, stripping non-numeric characters first."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].apply(lambda v: _strip_to_numeric_str(str(v)) if pd.notna(v) else v), errors="coerce")
    return df


def coerce_datetime(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    """Coerce specified columns to datetime where possible."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable: Callable[[], Optional[Tuple[Optional[alt.Chart], Optional[pd.DataFrame]]]]):
    """Execute chart builder safely; on failure, show a warning and fallback table if provided.
    The builder should return (chart, fallback_df). Either may be None.
    """
    try:
        result = chart_builder_callable()
        chart, fallback_df = None, None
        if isinstance(result, tuple) and len(result) == 2:
            chart, fallback_df = result
        else:
            chart = result  # type: ignore
        if chart is None:
            st.warning("Chart unavailable")
            if isinstance(fallback_df, pd.DataFrame):
                st.dataframe(fallback_df)
            return
        try:
            st.altair_chart(chart, use_container_width=True)
        except Exception:
            st.warning("Chart unavailable")
            if isinstance(fallback_df, pd.DataFrame):
                st.dataframe(fallback_df)
    except Exception:
        st.warning("Chart unavailable")


def render_app():
    # Guard page config for multi-run/import contexts
    if "_page_config_set" not in st.session_state:
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_set"] = True

    alt.data_transformers.disable_max_rows()

    # The provided JSON data
    report_data = {
        "valid": True,
        "issues": [],
        "summary": [
            "Quarterly sales, purchases, units sold, and buyer counts are reported for 2024 and 2025.",
            "Total sales peaked in Q4 2024 (448,770.42) and Q1 2025 (463,266.60).",
            "Purchases and total units generally increased from Q1 2024 to Q1 2025, then declined by Q3 2025.",
            "Buyer count was highest in Q4 2024 (5,245) and Q1 2025 (4,999), indicating strong seasonal demand."
        ],
        "tables": [
            {
                "name": "Table",
                "columns": ["yr", "q", "purchases", "total_sales", "total_units", "buyers"],
                "rows": [
                    [2024, 1, "3702", 259402.10999999472, "9002", "2579"],
                    [2024, 2, "5281", 299314.9499999972, "9713", "3055"],
                    [2024, 3, "8402", 300075.42999999237, "13323", "2494"],
                    [2024, 4, "10060", 448770.4200000053, "18388", "5245"],
                    [2025, 1, "9913", 463266.6000000094, "19670", "4999"],
                    [2025, 2, "9008", 371077.9300000016, "15482", "3826"],
                    [2025, 3, "5689", 210964.6999999934, "8576", "1711"]
                ]
            }
        ],
        "charts": [
            {
                "id": "quarterly_trends",
                "type": "line",
                "spec": {
                    "xKey": "q",
                    "yKey": "total_sales",
                    "series": [
                        {"name": "Total Sales", "yKey": "total_sales"},
                        {"name": "Purchases", "yKey": "purchases"},
                        {"name": "Total Units", "yKey": "total_units"},
                        {"name": "Buyers", "yKey": "buyers"}
                    ]
                }
            }
        ],
        "echo": {
            "intent": "trend",
            "used": {"tables": ["json"], "columns": ["yr", "q", "purchases", "total_sales", "total_units", "buyers"]},
            "stats": {"elapsed": 0},
            "sql_present": False
        }
    }

    st.title("AI Report")

    # Summary section
    summary_items = report_data.get("summary", [])
    if summary_items:
        st.subheader("Summary")
        for item in summary_items:
            st.markdown(f"- {item}")

    # Tables section
    tables = report_data.get("tables", [])
    original_dataframes: List[pd.DataFrame] = []
    if tables:
        st.subheader("Tables")
        for idx, tbl in enumerate(tables, start=1):
            name = tbl.get("name") or f"Table {idx}"
            cols = tbl.get("columns", [])
            rows = tbl.get("rows", [])
            try:
                df = pd.DataFrame(rows, columns=cols)
            except Exception:
                df = pd.DataFrame(rows)
            original_dataframes.append(df)
            st.markdown(f"**{name}**")
            st.dataframe(df)

    # Charts section
    charts = report_data.get("charts", [])
    if charts:
        st.subheader("Charts")

    # Use the first table as the data source for charts unless otherwise specified
    source_df: Optional[pd.DataFrame] = original_dataframes[0] if original_dataframes else None

    for chart_def in charts:
        chart_id = chart_def.get("id", "chart")
        chart_type = (chart_def.get("type") or "").lower()
        spec = chart_def.get("spec", {})
        st.markdown(f"**Chart: {chart_id} ({chart_type})**")

        if source_df is None or source_df.empty:
            st.warning("Chart unavailable")
            continue

        # Prepare data: sanitize and coerce types
        sdf, mapping = sanitize_columns(source_df)
        # Determine candidate numeric columns to coerce (all columns by default)
        numeric_candidate_cols = list(sdf.columns)
        sdf = coerce_numeric(sdf, numeric_candidate_cols)
        # No datetime fields detected in this dataset; function available for future use

        # Resolve keys through mapping
        def resolve_key(k: str) -> str:
            if k in mapping:
                return mapping[k]
            # Fallback: sanitize the provided key name directly
            temp_df = pd.DataFrame(columns=[k])
            temp_sdf, temp_map = sanitize_columns(temp_df)
            return temp_map.get(k, k)

        if chart_type in ("line", "bar", "area"):
            x_key = spec.get("xKey")
            series = spec.get("series", [])
            if not x_key or not isinstance(series, list) or len(series) == 0:
                st.warning("Chart unavailable")
                st.dataframe(sdf)
                continue

            safe_x = resolve_key(str(x_key))

            # For each y series, render a separate simple chart to avoid complex transforms
            for s in series:
                y_key = s.get("yKey")
                display_name = s.get("name") or str(y_key)
                if not y_key:
                    st.warning("Chart unavailable")
                    st.dataframe(sdf)
                    continue
                safe_y = resolve_key(str(y_key))

                def build_chart(_safe_x=safe_x, _safe_y=safe_y, _display_name=display_name):
                    # Validate required columns
                    if _safe_x not in sdf.columns or _safe_y not in sdf.columns:
                        return None, sdf

                    # Filter to rows with non-null x and y
                    df_plot = sdf[[_safe_x, _safe_y]].copy()
                    df_plot = df_plot[df_plot[_safe_x].notna() & df_plot[_safe_y].notna()]
                    if df_plot.empty:
                        return None, sdf

                    # Build Altair chart with safe encodings
                    # Treat x as nominal to avoid temporal assumptions for quarter index
                    x_enc = alt.X(_safe_x, type="nominal", title=str(x_key))
                    y_enc = alt.Y(_safe_y, type="quantitative", title=_display_name)
                    tooltips = []
                    if _safe_x in df_plot.columns:
                        tooltips.append(_safe_x)
                    if _safe_y in df_plot.columns and _safe_y != _safe_x:
                        tooltips.append(_safe_y)

                    mark = alt.MarkDef(type="line", point=True)
                    chart = alt.Chart(df_plot).mark_line(point=True).encode(
                        x=x_enc,
                        y=y_enc,
                        tooltip=tooltips
                    )
                    return chart, df_plot

                st.markdown(f"- {_display_name} vs {x_key}")
                safe_altair_chart(build_chart)

        elif chart_type == "pie":
            # Pie charts are implemented with mark_arc(); expecting spec with category and value
            category_key = spec.get("category")
            value_key = spec.get("value")
            if not category_key or not value_key:
                st.warning("Chart unavailable")
                st.dataframe(source_df)
                continue
            safe_cat = resolve_key(str(category_key))
            safe_val = resolve_key(str(value_key))

            # Ensure numeric coercion for values
            sdf = coerce_numeric(sdf, [safe_val])

            def build_pie():
                if safe_cat not in sdf.columns or safe_val not in sdf.columns:
                    return None, sdf
                df_plot = sdf[[safe_cat, safe_val]].copy()
                df_plot = df_plot[df_plot[safe_cat].notna() & df_plot[safe_val].notna()]
                if df_plot.empty:
                    return None, sdf
                chart = alt.Chart(df_plot).mark_arc().encode(
                    theta=alt.Theta(field=safe_val, type="quantitative"),
                    color=alt.Color(field=safe_cat, type="nominal"),
                    tooltip=[safe_cat, safe_val]
                )
                return chart, df_plot

            safe_altair_chart(build_pie)
        else:
            st.warning("Chart type not supported in this app. Showing data instead.")
            st.dataframe(source_df)


# Note: This module is import-safe. To run the app in Streamlit, call:
# from streamlit_app import render_app
# render_app()
