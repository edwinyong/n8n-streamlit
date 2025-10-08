from datetime import datetime
import streamlit as st
import pandas as pd
import altair as alt

# Embedded report JSON
REPORT = {
    "valid": True,
    "issues": [],
    "summary": [
        "Quarterly sales and activity have generally increased from Q1 2024 to Q1 2025, peaking in Q4 2024 for most measures.",
        "Total sales rose sharply from RM259,402 (Q1 2024) to a peak of RM463,266 (Q1 2025), then declined in Q3 2025.",
        "Buyer base expanded significantly in Q4 2024 (5,245) and Q1 2025 (4,999), suggesting effective seasonal or promotional activities.",
        "Despite gains, there is a noticeable decline in both buyers and total sales in Q3 2025, highlighting seasonal volatility or potential market saturation.",
        "Purchases per buyer increased substantially during high-performing quarters, indicating successful engagement or cross-selling.",
        "Suggestions: Investigate causes for Q3 2025 drop (seasonality, market, or competitive factors); enhance retention programs, and sustain Q4-Q1 growth momentum with targeted offers or new product launches following strong quarters."
    ],
    "tables": [
        {
            "name": "Quarterly Performance 2024-2025",
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
            "id": "trend_buyers_purchases",
            "type": "groupedBar",
            "spec": {
                "xKey": "yr_q",
                "yKey": "value",
                "series": [
                    {"name": "Buyers", "yKey": "buyers"},
                    {"name": "Purchases", "yKey": "purchases"}
                ]
            }
        },
        {
            "id": "trend_units",
            "type": "line",
            "spec": {
                "xKey": "yr_q",
                "yKey": "total_units",
                "series": [
                    {"name": "Total Units", "yKey": "total_units"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "trend",
        "used": {"tables": ["Quarterly Performance 2024-2025"], "columns": ["yr", "q", "buyers", "purchases", "total_sales", "total_units"]},
        "stats": {"elapsed": 0},
        "sql_present": False
    }
}

# Utilities

def sanitize_columns(df: pd.DataFrame):
    """Return a copy with safe snake_case columns and a mapping original->safe.
    Only [A-Za-z0-9_] allowed; lowercased. Ensures uniqueness by suffixing."""
    def to_safe(name: str) -> str:
        s = str(name).strip().lower()
        s = s.replace("-", "_").replace(" ", "_").replace("/", "_")
        # keep only alnum and underscore
        s = "".join(ch for ch in s if ch.isalnum() or ch == "_")
        if not s:
            s = "col"
        return s

    mapping = {}
    used = set()
    for col in df.columns:
        base = to_safe(col)
        safe = base
        i = 1
        while safe in used:
            safe = f"{base}_{i}"
            i += 1
        used.add(safe)
        mapping[col] = safe
    return df.rename(columns=mapping).copy(), mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """Coerce given columns to numeric by stripping non-numeric characters."""
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype(str).str.replace(r"[^0-9\.-]", "", regex=True)
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce given columns to datetime."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable, df_fallback: pd.DataFrame):
    """Safely build and render an Altair chart. On failure, show warning and fallback table."""
    try:
        chart = chart_builder_callable()
        if chart is None:
            st.warning("Chart unavailable")
            st.dataframe(df_fallback)
            return
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.warning("Chart unavailable")
        st.dataframe(df_fallback)


# Main app renderer

def render_app():
    # Guard page config to avoid repeated calls in multi-run contexts
    if not st.session_state.get("_page_config_set", False):
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_set"] = True

    # Avoid Altair row limits
    alt.data_transformers.disable_max_rows()

    st.title("AI Report")

    # Summary section
    if REPORT.get("summary"):
        st.subheader("Summary")
        for s in REPORT["summary"]:
            st.markdown(f"- {s}")

    # Load tables
    tables_data = []  # list of dicts: {name, original_df, sanitized_df, mapping}
    for t in REPORT.get("tables", []):
        name = t.get("name") or "Table"
        cols = t.get("columns") or []
        rows = t.get("rows") or []
        df = pd.DataFrame(rows, columns=cols)

        # Show original table with original column names
        st.subheader(name)
        st.dataframe(df)

        # Prepare sanitized copy for charting
        sdf, mapping = sanitize_columns(df)
        # Create derived yr_q if possible in sanitized df
        safe_yr = mapping.get("yr")
        safe_q = mapping.get("q")
        if safe_yr in sdf.columns and safe_q in sdf.columns:
            try:
                sdf["yr_q"] = sdf[safe_yr].astype(str) + "-Q" + sdf[safe_q].astype(str)
            except Exception:
                # If concatenation fails, skip creating yr_q
                pass
        tables_data.append({
            "name": name,
            "original_df": df,
            "sanitized_df": sdf,
            "mapping": mapping
        })

    # If no tables, stop
    if not tables_data:
        st.info("No data tables available.")
        return

    # We'll use the first table for charts as per the provided JSON
    base = tables_data[0]
    sdf = base["sanitized_df"].copy()
    mapping = base["mapping"]

    # Helper to get safe column name from original name
    def safe_col(orig_name):
        return mapping.get(orig_name)

    # Ensure derived yr_q exists if possible
    if "yr_q" not in sdf.columns:
        s_yr = safe_col("yr")
        s_q = safe_col("q")
        if s_yr in sdf.columns and s_q in sdf.columns:
            try:
                sdf["yr_q"] = sdf[s_yr].astype(str) + "-Q" + sdf[s_q].astype(str)
            except Exception:
                pass

    # Build charts defensively

    # 1) Trend: Total Sales (line)
    st.subheader("Trend: Total Sales")
    def build_trend_sales():
        x_col = "yr_q"
        y_col = safe_col("total_sales") or "total_sales"
        if x_col not in sdf.columns or y_col not in sdf.columns:
            return None
        local = sdf[[x_col, y_col]].copy()
        coerce_numeric(local, [y_col])
        local = local[local[x_col].notna() & local[y_col].notna()]
        if local.empty:
            return None
        order = local[x_col].dropna().unique().tolist()
        tooltip_fields = [c for c in [x_col, y_col] if c in local.columns]
        chart = alt.Chart(local).mark_line().encode(
            x=alt.X(f"{x_col}:N", sort=order, title="Quarter"),
            y=alt.Y(f"{y_col}:Q", title="Total Sales"),
            tooltip=tooltip_fields
        )
        return chart.properties(height=350)

    safe_altair_chart(build_trend_sales, sdf)

    # 2) Trend: Buyers vs Purchases (grouped bar)
    st.subheader("Trend: Buyers vs Purchases")
    def build_grouped_bar():
        x_col = "yr_q"
        buyers_col = safe_col("buyers") or "buyers"
        purchases_col = safe_col("purchases") or "purchases"
        if x_col not in sdf.columns or buyers_col not in sdf.columns or purchases_col not in sdf.columns:
            return None
        local = sdf[[x_col, buyers_col, purchases_col]].copy()
        coerce_numeric(local, [buyers_col, purchases_col])
        # Melt to long format for simple Altair encodings
        long_df = pd.melt(local, id_vars=[x_col], value_vars=[buyers_col, purchases_col],
                          var_name="metric", value_name="value")
        coerce_numeric(long_df, ["value"])  # ensure numeric after melt
        long_df = long_df[long_df[x_col].notna() & long_df["value"].notna()]
        if long_df.empty:
            return None
        order = long_df[x_col].dropna().unique().tolist()
        chart = alt.Chart(long_df).mark_bar().encode(
            x=alt.X(f"{x_col}:N", sort=order, title="Quarter"),
            y=alt.Y("value:Q", title="Count"),
            color=alt.Color("metric:N", title="Metric"),
            tooltip=[x_col, "metric", "value"]
        )
        return chart.properties(height=350)

    safe_altair_chart(build_grouped_bar, sdf)

    # 3) Trend: Total Units (line)
    st.subheader("Trend: Total Units")
    def build_trend_units():
        x_col = "yr_q"
        y_col = safe_col("total_units") or "total_units"
        if x_col not in sdf.columns or y_col not in sdf.columns:
            return None
        local = sdf[[x_col, y_col]].copy()
        coerce_numeric(local, [y_col])
        local = local[local[x_col].notna() & local[y_col].notna()]
        if local.empty:
            return None
        order = local[x_col].dropna().unique().tolist()
        tooltip_fields = [c for c in [x_col, y_col] if c in local.columns]
        chart = alt.Chart(local).mark_line().encode(
            x=alt.X(f"{x_col}:N", sort=order, title="Quarter"),
            y=alt.Y(f"{y_col}:Q", title="Total Units"),
            tooltip=tooltip_fields
        )
        return chart.properties(height=350)

    safe_altair_chart(build_trend_units, sdf)


# Note: Do not call render_app() on import.
