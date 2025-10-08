from datetime import datetime
import re
import pandas as pd
import altair as alt
import streamlit as st

# -----------------------------
# Utilities
# -----------------------------

def sanitize_columns(df: pd.DataFrame):
    """Return a copy of df with safe lower_snake_case columns and a mapping original->safe.
    Ensures only [A-Za-z0-9_] and uniqueness.
    """
    def to_safe(name: str) -> str:
        s = str(name).strip().lower()
        s = re.sub(r"\s+", "_", s)
        s = re.sub(r"[^0-9a-zA-Z_]", "_", s)
        s = re.sub(r"_+", "_", s)
        s = s.strip("_")
        if s == "":
            s = "col"
        return s

    mapping = {}
    used = set()
    for col in df.columns.tolist():
        base = to_safe(col)
        new = base
        i = 1
        while new in used:
            new = f"{base}_{i}"
            i += 1
        mapping[col] = new
        used.add(new)
    df_copy = df.copy()
    df_copy.columns = [mapping[c] for c in df.columns]
    return df_copy, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """Coerce provided columns to numeric by stripping non-numeric characters.
    Keeps digits, decimal point, minus sign, and exponent markers.
    """
    if not isinstance(cols, (list, tuple, set)):
        cols = [cols]
    for c in cols:
        if c in df.columns:
            ser = df[c]
            # Convert to string and strip non-numeric characters
            ser = ser.astype(str).str.replace(r"[^0-9eE\-\.]", "", regex=True)
            df[c] = pd.to_numeric(ser, errors="coerce")
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    if not isinstance(cols, (list, tuple, set)):
        cols = [cols]
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable, fallback_df: pd.DataFrame | None = None):
    """Run chart_builder_callable() in try/except and render a fallback table if needed."""
    try:
        chart = chart_builder_callable()
        if chart is None:
            raise ValueError("Chart builder returned None")
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.warning("Chart unavailable")
        if isinstance(fallback_df, pd.DataFrame):
            st.dataframe(fallback_df)


# -----------------------------
# Provided report JSON (embedded)
# -----------------------------
REPORT = {
    "valid": True,
    "issues": [
        {"code": "merged_duplicate_series", "severity": "info", "message": "Merged per-Year duplicates into one multi-series chart."}
    ],
    "summary": [
        "Quarterly sales, purchases, total units, and buyer counts varied across 2024 and 2025, with a noticeable growth trend in Q4 2024 and Q1 2025.",
        "Q4 2024 and Q1 2025 achieved the highest sales and buyer numbers, signaling strong seasonal or campaign-linked performance during these periods.",
        "Q2 and Q3 2025 saw declines in all metrics, indicating either seasonal dips or lower campaign effectiveness—especially Q3 2025, where sales and buyers dropped sharply compared to prior quarters.",
        "To improve: Analyze the causes behind Q2/Q3 2025 declines—review product offerings, promotions, and customer engagement for these quarters.",
        "Strengthen conversion strategies ahead of low quarters and optimize marketing/stock for Q2 and Q3 to smoothen performance volatility."
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
            "id": "quarterly_trend_2024_2025",
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
        "used": {"tables": ["detail"], "columns": ["yr", "q", "purchases", "total_sales", "total_units", "buyers"]},
        "stats": {"elapsed": 0},
        "sql_present": False
    }
}


# -----------------------------
# Streamlit app
# -----------------------------

def render_app():
    # Guarded page config
    if not st.session_state.get("_page_config_set", False):
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_set"] = True

    # Altair: avoid row-limit issues
    try:
        alt.data_transformers.disable_max_rows()
    except Exception:
        pass

    st.title("AI Report")

    # Summary section
    summaries = REPORT.get("summary", []) or []
    if summaries:
        st.subheader("Summary")
        for s in summaries:
            st.markdown(f"- {s}")

    # Render tables
    st.subheader("Data Tables")
    dataframes = []
    for idx, t in enumerate(REPORT.get("tables", []) or []):
        name = t.get("name") or f"Table {idx+1}"
        cols = t.get("columns", [])
        rows = t.get("rows", [])
        try:
            df = pd.DataFrame(rows, columns=cols)
        except Exception:
            # Fallback if malformed
            df = pd.DataFrame(rows)
        dataframes.append((name, df))
        st.markdown(f"**{name}**")
        st.dataframe(df)

    # Helper to get the primary table for charting
    base_df = dataframes[0][1] if dataframes else pd.DataFrame()

    # Charts section
    charts = REPORT.get("charts", []) or []
    if charts:
        st.subheader("Charts")

    def build_grouped_bar(df: pd.DataFrame, chart_meta: dict):
        # Sanitize
        sdf, mapping = sanitize_columns(df)

        # Attempt to ensure expected keys
        # Prefer existing 'quarter'; else derive from 'q'
        if "quarter" not in sdf.columns:
            if "q" in sdf.columns:
                q_num = pd.to_numeric(sdf["q"], errors="coerce")
                q_str = q_num.round(0).astype("Int64").astype(str)
                q_str = q_str.replace("<NA>", "")
                sdf["quarter"] = ("Q" + q_str).where(q_str != "", None)
            # else: leave missing

        # Coerce numeric fields that commonly need it
        for cand in ["total_sales", "purchases", "total_units", "buyers", "yr", "q"]:
            if cand in sdf.columns:
                coerce_numeric(sdf, [cand])

        # Validate required columns
        required = ["quarter", "total_sales"]
        for col in required:
            if col not in sdf.columns:
                raise ValueError(f"Required column '{col}' missing for grouped bar chart")

        # Drop rows with missing x or y
        sdf_valid = sdf.copy()
        sdf_valid = sdf_valid[sdf_valid["quarter"].notna() & sdf_valid["total_sales"].notna()]

        if sdf_valid.empty:
            raise ValueError("No valid data to plot after coercion")

        # If year exists, use as color; otherwise single-color bars
        has_year = "yr" in sdf_valid.columns

        # Build chart
        base = alt.Chart(sdf_valid)
        enc_x = alt.X("quarter:N", title="quarter")
        enc_y = alt.Y("total_sales:Q", title="total_sales")
        tooltips = ["quarter:N", "total_sales:Q"]
        if has_year:
            enc_color = alt.Color("yr:N", title="yr")
            tooltips = ["quarter:N", "yr:N", "total_sales:Q"]
            chart = base.mark_bar().encode(x=enc_x, y=enc_y, color=enc_color, tooltip=tooltips)
        else:
            chart = base.mark_bar().encode(x=enc_x, y=enc_y, tooltip=tooltips)
        return chart.properties(width="container", height=360)

    for ch in charts:
        ch_type = (ch.get("type") or "").lower()
        ch_id = ch.get("id") or "Chart"
        st.markdown(f"**{ch_id}**")

        if base_df is None or base_df.empty:
            st.warning("No data available for chart")
            continue

        if ch_type in ("groupedbar", "grouped_bar", "bar_grouped"):
            # Use safe wrapper and fallback to sanitized table
            sdf_fallback, _ = sanitize_columns(base_df)
            safe_altair_chart(lambda: build_grouped_bar(base_df, ch), fallback_df=sdf_fallback)
        elif ch_type in ("bar", "line", "area"):
            # Generic simple chart if requested (not present here, but supported defensively)
            sdf, _ = sanitize_columns(base_df)
            # Try to pick reasonable defaults
            x_col = None
            for cand in ["date", "month", "quarter", "q", "yr"]:
                if cand in sdf.columns:
                    x_col = cand
                    break
            y_col = None
            for cand in ["total_sales", "purchases", "total_units", "buyers"]:
                if cand in sdf.columns:
                    y_col = cand
                    break
            if x_col == "q" and "quarter" not in sdf.columns:
                q_num = pd.to_numeric(sdf["q"], errors="coerce")
                q_str = q_num.round(0).astype("Int64").astype(str).replace("<NA>", "")
                sdf["quarter"] = ("Q" + q_str).where(q_str != "", None)
                x_col = "quarter"
            # Coerce
            if y_col:
                coerce_numeric(sdf, [y_col])
            if x_col in ("date", "month"):
                coerce_datetime(sdf, [x_col])
            # Validate
            if not x_col or not y_col:
                st.warning("Chart unavailable")
                st.dataframe(sdf)
                continue
            sdf_valid = sdf[sdf[x_col].notna() & sdf[y_col].notna()]
            if sdf_valid.empty:
                st.warning("Chart unavailable")
                st.dataframe(sdf)
                continue
            def _build():
                base = alt.Chart(sdf_valid)
                mark = {"bar": base.mark_bar, "line": base.mark_line, "area": base.mark_area}[ch_type]()
                # Type inference: treat x as temporal if datetime-like, else nominal
                x_type = "T" if pd.api.types.is_datetime64_any_dtype(sdf_valid[x_col]) else "N"
                enc = mark.encode(
                    x=alt.X(f"{x_col}:{x_type}", title=x_col),
                    y=alt.Y(f"{y_col}:Q", title=y_col),
                    tooltip=[f"{x_col}:{x_type}", f"{y_col}:Q"],
                )
                return enc.properties(width="container", height=360)
            safe_altair_chart(_build, fallback_df=sdf)
        elif ch_type in ("pie", "donut"):
            # Attempt a simple pie from first two suitable columns
            sdf, _ = sanitize_columns(base_df)
            # Find dimension and value
            dim = None
            for cand in ["category", "quarter", "q", "yr"]:
                if cand in sdf.columns:
                    dim = cand
                    break
            val = None
            for cand in ["total_sales", "purchases", "total_units", "buyers"]:
                if cand in sdf.columns:
                    val = cand
                    break
            if dim == "q" and "quarter" not in sdf.columns:
                q_num = pd.to_numeric(sdf["q"], errors="coerce")
                q_str = q_num.round(0).astype("Int64").astype(str).replace("<NA>", "")
                sdf["quarter"] = ("Q" + q_str).where(q_str != "", None)
                dim = "quarter"
            if val:
                coerce_numeric(sdf, [val])
            if not dim or not val:
                st.warning("Chart unavailable")
                st.dataframe(sdf)
                continue
            sdf_valid = sdf[sdf[dim].notna() & sdf[val].notna()]
            if sdf_valid.empty:
                st.warning("Chart unavailable")
                st.dataframe(sdf)
                continue
            def _build_pie():
                base = alt.Chart(sdf_valid)
                chart = base.mark_arc().encode(
                    theta=alt.Theta(f"{val}:Q", aggregate="sum"),
                    color=alt.Color(f"{dim}:N"),
                    tooltip=[f"{dim}:N", f"{val}:Q"],
                )
                return chart.properties(width=400, height=360)
            safe_altair_chart(_build_pie, fallback_df=sdf)
        else:
            # Unknown chart type -> fallback
            st.warning("Chart type not supported")
            st.dataframe(base_df)


# Note: Do not auto-run; the render_app() function will be invoked by the host.
