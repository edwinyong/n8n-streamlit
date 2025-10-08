import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime


def sanitize_columns(df: pd.DataFrame):
    """
    Returns a copy of df with safe snake_case columns and a mapping of original->safe.
    Only uses [A-Za-z0-9_] and lowercases names. Ensures uniqueness.
    """
    original_cols = list(df.columns)
    safe_cols = []
    mapping = {}
    for col in original_cols:
        safe = ''.join(ch if ch.isalnum() else '_' for ch in str(col))
        safe = safe.lower().strip('_')
        # collapse multiple underscores
        safe = '_'.join([s for s in safe.split('_') if s])
        if not safe:
            safe = 'col'
        base = safe
        i = 1
        while safe in safe_cols:
            safe = f"{base}_{i}"
            i += 1
        mapping[col] = safe
        safe_cols.append(safe)
    df_copy = df.copy()
    df_copy.columns = safe_cols
    return df_copy, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """Coerce given columns to numeric after stripping non-numeric chars (commas, currency, text)."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace(r"[^0-9\.-]", "", regex=True),
                errors="coerce",
            )
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce given columns to datetime where possible."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable, fallback_df: pd.DataFrame):
    """
    Execute chart builder inside try/except. If anything fails, show a warning and the fallback table.
    """
    try:
        chart = chart_builder_callable()
        if chart is None:
            st.warning("Chart unavailable")
            st.dataframe(fallback_df)
            return
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.warning("Chart unavailable")
        st.dataframe(fallback_df)


def render_app():
    # Guard page config to avoid re-running in multi-import contexts
    if not st.session_state.get("_page_configured", False):
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_configured"] = True

    # Disable max rows limit to avoid truncation warnings
    alt.data_transformers.disable_max_rows()

    # -----------------------------
    # Report data (embedded)
    # -----------------------------
    report = {
        "valid": True,
        "issues": [],
        "summary": [
            "2025-05-02 to 2025-08-01: 8,726 purchases; 348,298.84 sales; 14,195 units; 3,258 buyers",
            "Avg order value: 39.92; units per purchase: 1.63",
            "Per buyer: 2.68 purchases; 106.91 sales; 4.36 units",
        ],
        "tables": [
            {
                "name": "Overall Totals (Raw)",
                "columns": ["purchases", "total_sales", "total_units", "buyers"],
                "rows": [["8726", 348298.84000000014, "14195", "3258"]],
            }
        ],
        "charts": [
            {
                "id": "kpi_purchases",
                "type": "kpi",
                "spec": {
                    "xKey": "purchases",
                    "yKey": "purchases",
                    "series": [{"name": "purchases", "yKey": "purchases"}],
                },
            },
            {
                "id": "kpi_total_sales",
                "type": "kpi",
                "spec": {
                    "xKey": "total_sales",
                    "yKey": "total_sales",
                    "series": [{"name": "total_sales", "yKey": "total_sales"}],
                },
            },
            {
                "id": "kpi_total_units",
                "type": "kpi",
                "spec": {
                    "xKey": "total_units",
                    "yKey": "total_units",
                    "series": [{"name": "total_units", "yKey": "total_units"}],
                },
            },
            {
                "id": "kpi_buyers",
                "type": "kpi",
                "spec": {
                    "xKey": "buyers",
                    "yKey": "buyers",
                    "series": [{"name": "buyers", "yKey": "buyers"}],
                },
            },
        ],
        "echo": {
            "intent": "comparison_totals",
            "used": {
                "tables": ["`Haleon_Rewards_User_Performance_110925_SKUs`"],
                "columns": [
                    "Upload_Date",
                    "receiptid",
                    "Total Sales Amount",
                    "Total_Purchase_Units",
                    "comuserid",
                ],
            },
            "stats": {"elapsed": 0.014049038},
            "sql_present": True,
        },
    }

    # -----------------------------
    # Title
    # -----------------------------
    st.title("AI Report")

    # -----------------------------
    # Summary
    # -----------------------------
    if report.get("summary"):
        st.subheader("Summary")
        for item in report["summary"]:
            st.markdown(f"- {item}")

    # -----------------------------
    # Tables
    # -----------------------------
    st.subheader("Tables")
    table_dfs = []  # store (name, original_df, sanitized_df)
    for idx, t in enumerate(report.get("tables", [])):
        name = t.get("name") or f"Table {idx+1}"
        cols = t.get("columns") or []
        rows = t.get("rows") or []
        try:
            original_df = pd.DataFrame(rows, columns=cols)
        except Exception:
            # Fallback empty frame if construction fails
            original_df = pd.DataFrame(columns=cols)
        st.markdown(f"**{name}**")
        st.dataframe(original_df)
        sanitized_df, mapping = sanitize_columns(original_df)
        table_dfs.append({
            "name": name,
            "original": original_df,
            "sanitized": sanitized_df,
            "mapping": mapping,
        })

    # Pick a default source table for charts (first available)
    default_table = table_dfs[0] if table_dfs else None

    # -----------------------------
    # Charts
    # -----------------------------
    if report.get("charts"):
        st.subheader("Charts")

    def build_kpi_chart(title: str, y_key: str, source_df: pd.DataFrame):
        # Ensure y_key exists and is numeric
        if y_key not in source_df.columns:
            return None, pd.DataFrame()
        temp_df = source_df.copy()
        temp_df = coerce_numeric(temp_df, [y_key])
        if temp_df[y_key].dropna().empty:
            return None, temp_df
        # Build a tiny dataframe for KPI bar: metric (nominal) vs value (quantitative)
        value = temp_df[y_key].dropna().iloc[0]
        kpi_df = pd.DataFrame({"metric": [y_key], "value": [value]})
        kpi_df_sanitized, _ = sanitize_columns(kpi_df)
        # Pre-verify fields
        if "metric" not in kpi_df_sanitized.columns or "value" not in kpi_df_sanitized.columns:
            return None, kpi_df_sanitized
        if kpi_df_sanitized["value"].dropna().empty:
            return None, kpi_df_sanitized
        def builder():
            chart = (
                alt.Chart(kpi_df_sanitized, title=title)
                .mark_bar()
                .encode(
                    x=alt.X("metric:N", title="Metric"),
                    y=alt.Y("value:Q", title="Value"),
                    tooltip=[c for c in kpi_df_sanitized.columns]
                )
            )
            return chart
        return builder, kpi_df_sanitized

    for ch in report.get("charts", []):
        ch_id = ch.get("id") or "chart"
        ch_type = (ch.get("type") or "").lower()
        spec = ch.get("spec", {})

        # Choose source table
        src = default_table["sanitized"] if default_table else pd.DataFrame()

        if ch_type in ("bar", "line", "area", "pie", "kpi"):
            # Handle KPI as a single-bar chart using yKey
            if ch_type == "kpi":
                y_key = spec.get("yKey")
                if src.empty or not y_key:
                    st.markdown(f"**{ch_id}**")
                    st.warning("Chart unavailable")
                    # Show original table if exists, else empty fallback
                    if default_table:
                        st.dataframe(default_table["sanitized"])
                    else:
                        st.dataframe(pd.DataFrame())
                    continue
                st.markdown(f"**{ch_id} — {y_key}**")
                builder, fallback_df = build_kpi_chart(ch_id, y_key, src)
                if builder is None:
                    st.warning("Chart unavailable")
                    if fallback_df is not None and not fallback_df.empty:
                        st.dataframe(fallback_df)
                    elif default_table:
                        st.dataframe(default_table["sanitized"])
                    else:
                        st.dataframe(pd.DataFrame())
                else:
                    safe_altair_chart(builder, fallback_df)
            else:
                # For other chart types without explicit usable spec, fall back safely
                st.markdown(f"**{ch_id} — {ch_type}**")
                st.warning("Chart unavailable")
                if default_table:
                    st.dataframe(default_table["sanitized"])
                else:
                    st.dataframe(pd.DataFrame())
        else:
            # Unknown chart type fallback
            st.markdown(f"**{ch_id}**")
            st.warning("Chart unavailable")
            if default_table:
                st.dataframe(default_table["sanitized"])
            else:
                st.dataframe(pd.DataFrame())

    # Footer or spacing
    st.write("")
