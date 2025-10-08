from datetime import datetime
import pandas as pd
import altair as alt
import streamlit as st


# -----------------------------
# Utilities
# -----------------------------

def sanitize_identifier(name: str) -> str:
    """Convert a column name to a safe lower_snake_case identifier with [A-Za-z0-9_].
    No external libs; avoid regex.
    """
    if name is None:
        return ""
    s = str(name).strip().lower()
    # replace common separators with underscore
    for ch in [" ", "-", "/", "\\", ".", "|", ":", ";", ",", "(", ")", "[", "]", "{", "}"]:
        s = s.replace(ch, "_")
    # keep only alnum and underscore
    safe = "".join([c if (c.isalnum() or c == "_") else "" for c in s])
    while "__" in safe:
        safe = safe.replace("__", "_")
    safe = safe.strip("_")
    if safe and safe[0].isdigit():
        safe = f"_{safe}"
    return safe or "col"


def sanitize_columns(df: pd.DataFrame):
    """Return a copy with sanitized columns and a mapping original->safe."""
    mapping = {}
    for c in df.columns:
        safe = sanitize_identifier(c)
        # ensure uniqueness if collisions
        base = safe
        i = 1
        while safe in mapping.values():
            i += 1
            safe = f"{base}_{i}"
        mapping[c] = safe
    df_copy = df.copy()
    df_copy.columns = [mapping[c] for c in df.columns]
    return df_copy, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """Coerce specified columns to numeric by stripping non-numeric chars and using to_numeric."""
    if not isinstance(cols, (list, tuple, pd.Index)):
        cols = [cols]
    for c in cols:
        if c in df.columns:
            def _clean_val(v):
                if pd.isna(v):
                    return v
                if isinstance(v, (int, float)):
                    return v
                s = str(v)
                # remove common currency symbols and thousands separators
                for sym in [",", "$", "€", "£", "RM", "C$", "A$", "¥"]:
                    s = s.replace(sym, "")
                # keep digits, dot, and minus
                kept = []
                for ch in s:
                    if ch.isdigit() or ch in [".", "-"]:
                        kept.append(ch)
                s2 = "".join(kept)
                if s2 in ("", ".", "-", "-.", ".-"):
                    return pd.NA
                return s2
            df[c] = pd.to_numeric(df[c].map(_clean_val), errors="coerce")
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce specified columns to datetime with errors coerced to NaT."""
    if not isinstance(cols, (list, tuple, pd.Index)):
        cols = [cols]
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable, fallback_df: pd.DataFrame):
    """Build and render an Altair chart in a try/except. On failure, warn and show fallback table."""
    try:
        chart = chart_builder_callable()
        if chart is None:
            raise ValueError("Chart builder returned None")
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.warning("Chart unavailable")
        st.dataframe(fallback_df)


# -----------------------------
# App
# -----------------------------

def render_app():
    # Protect page config in multi-import contexts
    if "_page_configured" not in st.session_state:
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_configured"] = True

    # Avoid Altair row limits
    alt.data_transformers.disable_max_rows()

    # The input report JSON (embedded)
    report = {
        "valid": True,
        "issues": [
            {
                "code": "merged_duplicate_series",
                "severity": "info",
                "message": "Merged per-Year quarterly series into a single multi-series chart."
            }
        ],
        "summary": [
            "Quarterly sales and activity increased from early 2024 to peak in Q4 2024 and Q1 2025, then softened in following quarters of 2025.",
            "Q4 2024 and Q1 2025 show the highest total sales, buyers, purchases, and units overall.",
            "There is a noticeable drop in all KPIs in Q3 2025 versus Q1/Q2 2025, indicating potential seasonality or operational issues.",
            "Improvement opportunities include: focusing on sustaining engagement post-Q1 each year; identifying drivers of Q4 and Q1 peaks to replicate success; addressing dips in Q3 2025 via campaigns, buyer reactivation, or product launches."
        ],
        "tables": [
            {
                "name": "Table",
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
                "id": "quarterly_performance_2024_2025",
                "type": "groupedBar",
                "spec": {
                    "xKey": "quarter",
                    "yKey": "total_sales",
                    "series": [
                        {"name": "2024", "yKey": "total_sales_2024"},
                        {"name": "2025", "yKey": "total_sales_2025"}
                    ]
                }
            }
        ],
        "echo": {
            "intent": "trend",
            "used": {"tables": ["detail"], "columns": ["yr", "q", "buyers", "purchases", "total_sales", "total_units"]},
            "stats": {"elapsed": 0},
            "sql_present": False
        }
    }

    st.title("AI Report")

    # Summary section
    if isinstance(report.get("summary"), list) and report["summary"]:
        st.subheader("Summary")
        for item in report["summary"]:
            st.markdown(f"- {item}")

    # Tables section
    st.subheader("Tables")
    tables = report.get("tables", [])
    dataframes = []
    for idx, tbl in enumerate(tables):
        name = tbl.get("name") or f"Table {idx+1}"
        cols = tbl.get("columns", [])
        rows = tbl.get("rows", [])
        try:
            df = pd.DataFrame(rows, columns=cols)
        except Exception:
            # Fallback if shape mismatch
            df = pd.DataFrame(rows)
            df.columns = cols[: len(df.columns)] + [f"col_{i}" for i in range(len(df.columns) - len(cols))]
        dataframes.append((name, df))
        st.markdown(f"**{name}**")
        st.dataframe(df)

    # Charts section
    st.subheader("Charts")

    # Use the first table as the primary data source for charts
    base_df = dataframes[0][1] if dataframes else pd.DataFrame()
    safe_df, mapping = sanitize_columns(base_df)

    # Guess and coerce numeric columns commonly used
    numeric_candidates = [c for c in [
        "buyers", "purchases", "total_sales", "total_units", "yr", "q"
    ] if c in safe_df.columns]
    safe_df = coerce_numeric(safe_df, numeric_candidates)

    # Attempt datetime coercion for common date-like columns (none in this dataset, but safe to try)
    datetime_candidates = [c for c in ["date", "dt", "period", "month", "quarter", "year"] if c in safe_df.columns]
    safe_df = coerce_datetime(safe_df, datetime_candidates)

    # Helper to pick a field by preferred candidates
    def pick_field(df: pd.DataFrame, candidates):
        for c in candidates:
            cand = sanitize_identifier(c)
            if cand in df.columns:
                return cand
        return None

    charts = report.get("charts", [])
    for ch in charts:
        ch_id = ch.get("id") or "Chart"
        ch_type = (ch.get("type") or "").lower()
        spec = ch.get("spec", {})
        st.markdown(f"**{ch_id}**")

        # Build a grouped bar from available fields. We avoid non-existent fields.
        # Preferred mappings
        requested_x = spec.get("xKey")
        requested_y = spec.get("yKey")

        x_field = None
        if requested_x:
            x_field = pick_field(safe_df, [requested_x])
        if not x_field:
            x_field = pick_field(safe_df, ["quarter", "q", "month", "period", "yr", "year"])  # fallback order

        y_field = None
        if requested_y:
            y_field = pick_field(safe_df, [requested_y])
        if not y_field:
            # prioritize sales-like columns if present
            y_field = pick_field(safe_df, ["total_sales", "sales", "amount", "value", "metric", "purchases", "buyers", "total_units"])  # fallback order

        # Use year as color series if present
        series_field = None
        if "yr" in safe_df.columns:
            series_field = "yr"
        elif pick_field(safe_df, ["year"])):
            series_field = pick_field(safe_df, ["year"])  # may be None if absent

        # Validate fields
        valid = True
        reasons = []
        if not x_field or x_field not in safe_df.columns:
            valid = False
            reasons.append("x field missing")
        if not y_field or y_field not in safe_df.columns:
            valid = False
            reasons.append("y field missing")
        data_view_cols = [c for c in [x_field, y_field, series_field] if c]
        data_view = safe_df[data_view_cols].copy() if valid else safe_df.copy()

        if valid:
            # Ensure y is numeric
            if not pd.api.types.is_numeric_dtype(data_view[y_field]):
                # try coercion again if missed
                data_view = coerce_numeric(data_view, [y_field])
            if not pd.api.types.is_numeric_dtype(data_view[y_field]):
                valid = False
                reasons.append("y not numeric")

        if valid:
            # Drop rows without x or y
            data_view = data_view.dropna(subset=[x_field, y_field])
            if data_view.empty:
                valid = False
                reasons.append("no data after cleaning")

        def build_grouped_bar():
            if not valid:
                return None
            # Determine x type
            x_dtype = data_view[x_field].dtype
            x_type = "T" if pd.api.types.is_datetime64_any_dtype(x_dtype) else "O"

            enc = {
                "x": alt.X(f"{x_field}:{x_type}", title=x_field),
                "y": alt.Y(f"{y_field}:Q", title=y_field),
                "tooltip": [c for c in [x_field, y_field, series_field] if c]
            }
            if series_field:
                enc["color"] = alt.Color(f"{series_field}:N", title=series_field)

            chart = alt.Chart(data_view).mark_bar().encode(**enc)
            return chart.properties(height=350)

        # Render safely
        safe_altair_chart(build_grouped_bar, fallback_df=safe_df)

    # If there were no charts specified, offer a gentle note
    if not charts:
        st.info("No charts available in the report.")


# Note: no top-level execution. The app renders only when render_app() is called.
