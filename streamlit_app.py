from datetime import datetime
import streamlit as st
import pandas as pd
import altair as alt


# -------------------- Utilities --------------------
def sanitize_columns(df: pd.DataFrame):
    """Return a copy of df with safe snake_case columns and a mapping {original: safe}.
    Ensures only [A-Za-z0-9_] and uniqueness.
    """
    import re

    def to_safe(name: str) -> str:
        # Lower, replace spaces/hyphens with underscore, drop non-alnum/underscore
        s = str(name).strip().lower()
        s = re.sub(r"[\s\-]+", "_", s)
        s = re.sub(r"[^0-9a-zA-Z_]", "", s)
        # Avoid leading digits
        if re.match(r"^[0-9]", s):
            s = f"col_{s}"
        return s or "col"

    mapping = {}
    used = set()
    for c in df.columns:
        base = to_safe(c)
        candidate = base
        i = 1
        while candidate in used:
            candidate = f"{base}_{i}"
            i += 1
        mapping[c] = candidate
        used.add(candidate)
    return df.rename(columns=mapping).copy(), mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """Coerce given columns to numeric by stripping non-numeric chars and using to_numeric."""
    if not isinstance(cols, (list, tuple, set)):
        cols = [cols]
    for c in cols:
        if c in df.columns:
            # Convert to string then strip everything except digits, minus, and dot
            df[c] = pd.to_numeric(
                df[c]
                .astype(str)
                .str.replace(r"[^0-9\-\.]+", "", regex=True)
                .replace({"": pd.NA}),
                errors="coerce",
            )
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce given columns to datetime with errors coerced to NaT."""
    if not isinstance(cols, (list, tuple, set)):
        cols = [cols]
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable, fallback_df: pd.DataFrame):
    """Safely build and render an Altair chart. On failure, warn and show the sanitized table."""
    try:
        chart = chart_builder_callable()
        if chart is None:
            st.warning("Chart unavailable")
            st.dataframe(fallback_df, use_container_width=True)
            return
        try:
            st.altair_chart(chart, use_container_width=True)
        except Exception:
            st.warning("Chart unavailable")
            st.dataframe(fallback_df, use_container_width=True)
    except Exception:
        st.warning("Chart unavailable")
        st.dataframe(fallback_df, use_container_width=True)


# -------------------- Embedded Report Data --------------------
REPORT = {
    "valid": True,
    "issues": [
        {"code": "merged_duplicate_series", "severity": "info", "message": "Merged per-Year duplicates into one multi-series chart."}
    ],
    "summary": [
        "Total sales generally increased from Q1 2024 (259,402.11) to Q1 2025 (463,266.60), with Q4 2024 and Q1 2025 being peak quarters.",
        "Q4 2024 shows the highest total sales (448,770.42), units sold (18,388), and buyers (5,245), followed by Q1 2025.",
        "Sales and buyer count sharply drop in Q3 2025 (total_sales: 210,964.70; buyers: 1,711), indicating potential seasonality or business challenges.",
        "Buyer growth occurred from Q1 2024 (2,579) through Q4 2024 (5,245), with overall higher quarterly sales in 2025.",
        "Suggestions: Focus on sustaining momentum post-Q1 2025, investigate causes for the drop-off in Q3 2025, improve retention and reactivation strategies, and consider campaign or product launches ahead of Q3 to offset the sales dip."
    ],
    "tables": [
        {
            "name": "Table",
            "columns": ["yr", "q", "purchases", "total_sales", "total_units", "buyers"],
            "rows": [
                [2024, 1, "3702", 259402.10999999472, "9002", 2579],
                [2024, 2, "5281", 299314.9499999972, "9713", 3055],
                [2024, 3, "8402", 300075.42999999237, "13323", 2494],
                [2024, 4, "10060", 448770.4200000053, "18388", 5245],
                [2025, 1, "9913", 463266.6000000094, "19670", 4999],
                [2025, 2, "9008", 371077.9300000016, "15482", 3826],
                [2025, 3, "5689", 210964.6999999934, "8576", 1711]
            ]
        }
    ],
    "charts": [
        {
            "id": "quarterly_trends_sales_2024_2025",
            "type": "groupedBar",
            "spec": {
                "xKey": "quarter",
                "yKey": "total_sales",
                "series": [
                    {"name": "2024", "yKey": "total_sales_2024"},
                    {"name": "2025", "yKey": "total_sales_2025"}
                ]
            }
        },
        {
            "id": "quarterly_trends_buyers_2024_2025",
            "type": "groupedBar",
            "spec": {
                "xKey": "quarter",
                "yKey": "buyers",
                "series": [
                    {"name": "2024", "yKey": "buyers_2024"},
                    {"name": "2025", "yKey": "buyers_2025"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "trend",
        "used": {"tables": ["Table"], "columns": ["yr", "q", "purchases", "total_sales", "total_units", "buyers"]},
        "stats": {"elapsed": 0},
        "sql_present": False
    }
}


# -------------------- Streamlit App Renderer --------------------
def render_app():
    # Configure page once per session
    if not st.session_state.get("_page_config_set", False):
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_set"] = True

    # Altair setting to avoid row-limit issues
    alt.data_transformers.disable_max_rows()

    st.title("AI Report")

    # Summary Section
    if REPORT.get("summary"):
        st.subheader("Summary")
        for item in REPORT["summary"]:
            st.markdown(f"- {item}")

    # Optional issues/messages
    if REPORT.get("issues"):
        for issue in REPORT["issues"]:
            sev = (issue.get("severity") or "info").lower()
            msg = issue.get("message") or ""
            if sev == "warning":
                st.warning(msg)
            elif sev == "error":
                st.error(msg)
            else:
                st.info(msg)

    # Tables Section
    st.subheader("Tables")
    tables = REPORT.get("tables", [])

    original_dfs = {}
    sanitized_dfs = {}
    mappings = {}

    for t in tables:
        name = t.get("name") or "Table"
        cols = t.get("columns", [])
        rows = t.get("rows", [])
        try:
            df = pd.DataFrame(rows, columns=cols)
        except Exception:
            df = pd.DataFrame()
        original_dfs[name] = df

        # Show original table with original column names
        st.markdown(f"### {name}")
        st.dataframe(df, use_container_width=True)

        # Prepare sanitized copy for charting
        df_sanitized, mapping = sanitize_columns(df)
        # Coerce potential numeric columns commonly used
        numeric_candidates = [c for c in [
            mapping.get("purchases"), mapping.get("total_sales"), mapping.get("total_units"), mapping.get("buyers")
        ] if c in df_sanitized.columns]
        coerce_numeric(df_sanitized, numeric_candidates)
        # Coerce temporal if present (none in this dataset, but kept for completeness)
        datetime_candidates = [c for c in [mapping.get("date"), mapping.get("quarter_date")] if c in df_sanitized.columns]
        coerce_datetime(df_sanitized, datetime_candidates)

        sanitized_dfs[name] = df_sanitized
        mappings[name] = mapping

    # Choose the main data table for charts (use the first one if named differently)
    main_table_name = tables[0]["name"] if tables else None
    sdf = sanitized_dfs.get(main_table_name) if main_table_name else None
    mapping = mappings.get(main_table_name) if main_table_name else {}

    # Charts Section
    if REPORT.get("charts"):
        st.subheader("Charts")

        def build_grouped_bar(df_sanitized: pd.DataFrame, x_field: str, y_field: str, color_field: str, x_title: str, y_title: str, color_title: str):
            # Validate required fields
            for fld in [x_field, y_field, color_field]:
                if fld not in df_sanitized.columns:
                    return None

            # Ensure numeric y
            coerce_numeric(df_sanitized, [y_field])

            # Filter valid rows
            valid = df_sanitized[[x_field, y_field, color_field]].copy()
            valid = valid[valid[y_field].notna() & valid[x_field].notna() & valid[color_field].notna()]
            if len(valid) == 0:
                return None

            # Build chart
            chart = (
                alt.Chart(valid)
                .mark_bar()
                .encode(
                    x=alt.X(f"{x_field}:N", title=x_title),
                    y=alt.Y(f"{y_field}:Q", title=y_title),
                    color=alt.Color(f"{color_field}:N", title=color_title),
                    tooltip=[f"{color_field}:N", f"{x_field}:N", f"{y_field}:Q"]
                )
            )
            return chart

        for ch in REPORT.get("charts", []):
            chart_id = ch.get("id") or "Chart"
            ch_type = (ch.get("type") or "").lower()
            spec = ch.get("spec") or {}

            # If no data available, show warning and continue
            if sdf is None or sdf.empty:
                st.markdown(f"### {chart_id}")
                st.warning("No data available for chart")
                continue

            # Determine columns from sanitized mapping
            # Expected fields present in data: yr, q, total_sales, buyers
            yr_col = mapping.get("yr") if mapping else "yr"
            q_col = mapping.get("q") if mapping else "q"
            total_sales_col = mapping.get("total_sales") if mapping else "total_sales"
            buyers_col = mapping.get("buyers") if mapping else "buyers"

            # Chart title heuristic
            pretty_title = chart_id.replace("_", " ").title()
            if "sales" in (chart_id or "").lower():
                pretty_title = "Quarterly Total Sales by Year"
            elif "buyers" in (chart_id or "").lower():
                pretty_title = "Quarterly Buyers by Year"

            st.markdown(f"### {pretty_title}")

            if ch_type == "groupedbar":
                # Determine y from spec if present
                y_key = (spec.get("yKey") or "").strip()
                if y_key.lower() == "buyers":
                    y_field = buyers_col
                    y_title = "Buyers"
                else:
                    y_field = total_sales_col if total_sales_col in sdf.columns else buyers_col
                    y_title = "Total Sales" if y_field == total_sales_col else "Buyers"

                # Build and render safely
                def _builder():
                    if q_col not in sdf.columns or yr_col not in sdf.columns or y_field not in sdf.columns:
                        return None
                    return build_grouped_bar(
                        df_sanitized=sdf.copy(),
                        x_field=q_col,
                        y_field=y_field,
                        color_field=yr_col,
                        x_title="Quarter",
                        y_title=y_title,
                        color_title="Year",
                    )

                safe_altair_chart(_builder, fallback_df=sdf)
            else:
                # Unsupported type: show fallback
                st.warning("Chart type not supported in this viewer")
                st.dataframe(sdf, use_container_width=True)


# Note: Do not auto-run render_app() on import.
