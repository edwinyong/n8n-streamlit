from datetime import datetime
import streamlit as st
import pandas as pd
import altair as alt

# -------------------------------
# Embedded report (as Python dict)
# -------------------------------
REPORT = {
    "valid": True,
    "issues": [],
    "summary": [
        "Weekly KPIs by brand include purchases (distinct receipts), buyers (unique users), total sales, and total units.",
        "Sensodyne and Scotts are consistently top-performing brands in weekly sales, units, and buyer engagement.",
        "Some brands (e.g., Parodontax, Panadol, Calsource) have intermittent or low activity.",
        "Redemption data is not available in this dataset; only purchase, buyer, sales, and unit metrics are provided."
    ],
    "tables": [
        {
            "name": "Weekly Brand KPIs",
            "columns": ["week_start", "Brand", "purchases", "buyers", "total_sales", "total_units"],
            "rows": [
                ["2023-12-31", "Caltrate", "238", "224", 23176.70000000002, "259"],
                ["2023-12-31", "Centrum", "84", "75", 6240.799999999993, "100"],
                ["2023-12-31", "Eno", "4", "4", 50.980000000000004, "5"],
                ["2023-12-31", "Panaflex", "4", "3", 48.4, "9"],
                ["2023-12-31", "Polident", "107", "100", 4962.539999999996, "196"],
                ["2023-12-31", "Scotts", "202", "189", 12736.260000000022, "390"],
                ["2023-12-31", "Sensodyne", "504", "470", 32640.6399999999, "2156"],
                ["2024-01-07", "Caltrate", "99", "92", 9210.350000000008, "104"],
                ["2024-01-07", "Centrum", "45", "45", 3550.1000000000004, "62"],
                ["2024-01-07", "Eno", "7", "7", 263.41, "14"],
                ["2024-01-07", "Panaflex", "3", "3", 21.78, "4"],
                ["2024-01-07", "Parodontax", "10", "10", 260.3, "15"],
                ["2024-01-07", "Polident", "64", "58", 3105.7200000000007, "128"],
                ["2024-01-07", "Scotts", "101", "96", 5931.519999999991, "196"],
                ["2024-01-07", "Sensodyne", "203", "185", 12473.040000000003, "725"],
                ["2024-01-14", "Calsource", "1", "1", 40, "1"],
                ["2024-01-14", "Caltrate", "54", "48", 4345.41, "55"],
                ["2024-01-14", "Centrum", "35", "27", 2626.4000000000005, "35"],
                ["2024-01-14", "Eno", "10", "10", 137.4, "15"],
                ["2024-01-14", "Panaflex", "2", "2", 23.2, "4"],
                ["2024-01-14", "Parodontax", "15", "13", 438.89999999999986, "28"],
                ["2024-01-14", "Polident", "63", "62", 2594.540000000001, "136"],
                ["2024-01-14", "Scotts", "39", "36", 2451.65, "81"],
                ["2024-01-14", "Sensodyne", "79", "72", 3466.3200000000015, "194"],
                ["2024-01-21", "Caltrate", "80", "66", 6916.88, "86"],
                ["2024-01-21", "Centrum", "30", "25", 2708.4000000000005, "33"],
                ["2024-01-21", "Eno", "4", "4", 59.8, "20"],
                ["2024-01-21", "Panaflex", "3", "3", 64.9, "10"],
                ["2024-01-21", "Parodontax", "4", "4", 67.19999999999999, "4"],
                ["2024-01-21", "Polident", "62", "56", 2816.16, "136"],
                ["2024-01-21", "Scotts", "34", "32", 1998.2200000000007, "61"],
                ["2024-01-21", "Sensodyne", "66", "63", 3554.3700000000013, "194"],
                ["2024-01-28", "Caltrate", "60", "56", 4892.759999999999, "64"],
                ["2024-01-28", "Centrum", "27", "21", 2285.87, "27"],
                ["2024-01-28", "Eno", "4", "4", 37.25, "5"],
                ["2024-01-28", "Panaflex", "2", "2", 37.3, "5"],
                ["2024-01-28", "Parodontax", "1", "1", 12.9, "1"],
                ["2024-01-28", "Polident", "47", "43", 2253.7, "115"],
                ["2024-01-28", "Scotts", "27", "23", 1357.92, "44"],
                ["2024-01-28", "Sensodyne", "47", "45", 2457.800000000001, "126"]
            ]
        }
    ],
    "charts": [
        {
            "id": "weekly_brand_kpis",
            "type": "stackedBar",
            "spec": {
                "xKey": "week_start",
                "yKey": "total_sales",
                "series": [
                    {"name": "Caltrate", "yKey": "Caltrate"},
                    {"name": "Centrum", "yKey": "Centrum"},
                    {"name": "Eno", "yKey": "Eno"},
                    {"name": "Panaflex", "yKey": "Panaflex"},
                    {"name": "Parodontax", "yKey": "Parodontax"},
                    {"name": "Polident", "yKey": "Polident"},
                    {"name": "Scotts", "yKey": "Scotts"},
                    {"name": "Sensodyne", "yKey": "Sensodyne"},
                    {"name": "Calsource", "yKey": "Calsource"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "trend",
        "used": {
            "tables": ["`Haleon_Rewards_User_Performance_110925_SKUs`"],
            "columns": ["Upload_Date", "Brand", "receiptid", "comuserid", "Total Sales Amount", "Total_Purchase_Units"]
        },
        "stats": {"elapsed": 0.030837454},
        "sql_present": True
    }
}


# -------------------------------
# Utilities
# -------------------------------

def sanitize_columns(df: pd.DataFrame):
    """Return a copy of df with safe lower_snake_case columns and a mapping original->safe."""
    def to_safe(name: str) -> str:
        s = str(name).strip().lower()
        # Replace spaces and dashes with underscore
        s = s.replace("-", "_").replace(" ", "_").replace("/", "_")
        # Keep only alphanumeric and underscore
        s = "".join(ch for ch in s if (ch.isalnum() or ch == "_"))
        # Collapse multiple underscores
        while "__" in s:
            s = s.replace("__", "_")
        if s == "":
            s = "col"
        return s

    mapping = {}
    used = set()
    for c in df.columns:
        safe = to_safe(c)
        # Ensure uniqueness
        base = safe
        i = 1
        while safe in used:
            i += 1
            safe = f"{base}_{i}"
        used.add(safe)
        mapping[c] = safe
    df_copy = df.copy()
    df_copy.columns = [mapping[c] for c in df.columns]
    return df_copy, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    df = df.copy()
    for c in cols:
        if c in df.columns:
            # If already numeric, keep; else strip non-numeric chars then convert
            if not pd.api.types.is_numeric_dtype(df[c]):
                df[c] = (
                    df[c]
                    .astype(str)
                    .str.replace(r"[^0-9\.-]", "", regex=True)
                    .replace({"": None})
                )
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable):
    """Execute chart builder in try/except; on failure show warning and fallback table if provided by builder.
    The builder may return either:
      - chart
      - (chart, fallback_df)
    """
    fallback_df = None
    try:
        result = chart_builder_callable()
        if isinstance(result, tuple) and len(result) >= 1:
            chart = result[0]
            if len(result) > 1:
                fallback_df = result[1]
        else:
            chart = result
        if chart is None:
            st.warning("Chart unavailable")
            if fallback_df is not None and isinstance(fallback_df, pd.DataFrame) and not fallback_df.empty:
                st.dataframe(fallback_df)
            return
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.warning("Chart unavailable")
        try:
            if fallback_df is not None and isinstance(fallback_df, pd.DataFrame) and not fallback_df.empty:
                st.dataframe(fallback_df)
        except Exception:
            pass


# -------------------------------
# Streamlit App
# -------------------------------

def render_app():
    # Configure page once per session
    if "_page_configured" not in st.session_state:
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_configured"] = True

    # Altair settings to avoid row limit issues
    alt.data_transformers.disable_max_rows()

    st.title("AI Report")

    # Summary section
    if REPORT.get("summary"):
        st.subheader("Summary")
        for item in REPORT["summary"]:
            st.markdown(f"- {item}")

    # Process and display tables
    st.subheader("Data Tables")
    processed_tables = []  # list of dicts: {name, df_original, df_sanitized, mapping}

    for tbl in REPORT.get("tables", []):
        name = tbl.get("name", "Table")
        cols = tbl.get("columns", [])
        rows = tbl.get("rows", [])
        try:
            df_original = pd.DataFrame(rows, columns=cols)
        except Exception:
            df_original = pd.DataFrame()

        st.markdown(f"**{name}**")
        st.dataframe(df_original)

        df_sanitized, mapping = sanitize_columns(df_original)

        # Attempt type coercions for common column types
        # Determine likely numeric columns from known metric names if present
        numeric_candidates = [c for c in ["purchases", "buyers", "total_sales", "total_units"] if c in df_sanitized.columns]
        df_sanitized = coerce_numeric(df_sanitized, numeric_candidates)
        # Datetime candidates
        dt_candidates = []
        # try to locate week_start's safe name via mapping
        for k, v in mapping.items():
            if str(k).lower() == "week_start":
                dt_candidates.append(v)
        df_sanitized = coerce_datetime(df_sanitized, dt_candidates)

        processed_tables.append({
            "name": name,
            "df_original": df_original,
            "df_sanitized": df_sanitized,
            "mapping": mapping
        })

    # Charts section
    if REPORT.get("charts"):
        st.subheader("Charts")

    def find_table_with_fields(x_key: str, y_key: str, extra_fields=None):
        extra_fields = extra_fields or []
        for item in processed_tables:
            mapping = item["mapping"]
            df = item["df_sanitized"]
            safe_x = mapping.get(x_key, x_key)
            safe_y = mapping.get(y_key, y_key)
            # For extra fields, we map from original if provided, otherwise assume already safe
            safe_extras = []
            for ef in extra_fields:
                safe_extras.append(mapping.get(ef, ef))
            needed = [safe_x, safe_y] + safe_extras
            if all(col in df.columns for col in needed):
                return item, safe_x, safe_y, safe_extras
        return None, None, None, None

    for ch in REPORT.get("charts", []):
        ch_id = ch.get("id", "chart")
        ch_type = ch.get("type", "")
        spec = ch.get("spec", {})
        st.markdown(f"**{ch_id}**")

        if ch_type == "stackedBar":
            x_key = spec.get("xKey")
            y_key = spec.get("yKey")
            # We expect a categorical stack by brand if present
            # Try to find a table with Brand
            item, safe_x, safe_y, _ = find_table_with_fields(x_key, y_key, extra_fields=["Brand"])  # original name
            stack_col = None
            if item is not None:
                # Determine stack column safe name for Brand
                mapping = item["mapping"]
                stack_col = mapping.get("Brand", "brand")
                if stack_col not in item["df_sanitized"].columns:
                    stack_col = None

            if item is None or safe_x is None or safe_y is None or stack_col is None:
                # Fallback when required fields are missing
                st.warning("Chart unavailable")
                # If possible, show the first sanitized table
                if processed_tables:
                    st.dataframe(processed_tables[0]["df_sanitized"]) 
                continue

            df_safe = item["df_sanitized"].copy()

            # Builder closure returns (chart, fallback_df)
            def builder():
                # Ensure required fields exist and have data
                cols_needed = [safe_x, safe_y, stack_col]
                if not all(c in df_safe.columns for c in cols_needed):
                    raise ValueError("Required columns missing for chart")

                dfx = df_safe[cols_needed].copy()
                # Drop rows missing x or y
                dfx = dfx.dropna(subset=[safe_x, safe_y])

                if dfx.empty or dfx[safe_y].notna().sum() == 0:
                    # Nothing to chart
                    return None, df_safe

                # Group to ensure a clean stack per x/stack_col
                try:
                    dfg = dfx.groupby([safe_x, stack_col], as_index=False)[safe_y].sum()
                except Exception:
                    dfg = dfx

                # Determine x type
                if pd.api.types.is_datetime64_any_dtype(dfg[safe_x]):
                    x_enc = alt.X(f"{safe_x}:T", title=x_key)
                else:
                    x_enc = alt.X(f"{safe_x}:N", title=x_key)

                y_enc = alt.Y(f"{safe_y}:Q", title=y_key)
                color_enc = alt.Color(f"{stack_col}:N", title="brand")

                tooltip_fields = []
                for f in [safe_x, stack_col, safe_y]:
                    if f in dfg.columns:
                        tooltip_fields.append(f)

                chart = (
                    alt.Chart(dfg)
                    .mark_bar()
                    .encode(
                        x=x_enc,
                        y=y_enc,
                        color=color_enc,
                        tooltip=tooltip_fields,
                    )
                    .properties(height=380)
                )
                return chart, dfg

            safe_altair_chart(builder)
        else:
            # Unsupported chart type: fallback
            st.warning("Chart unavailable")
            if processed_tables:
                st.dataframe(processed_tables[0]["df_sanitized"])

    # Optional echo/metadata
    echo = REPORT.get("echo")
    if echo:
        with st.expander("Details / Query Context"):
            st.write(echo)


# Note: do not execute render_app() on import. It should be called by the runner.
