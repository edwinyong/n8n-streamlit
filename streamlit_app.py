from datetime import datetime
import pandas as pd
import streamlit as st
import altair as alt


# Embedded report JSON converted to a Python dict
REPORT = {
    "valid": True,
    "issues": [],
    "summary": [
        "Overall totals for 2025-05-02 to 2025-08-01 — purchases: 8726; total sales: 348298.84000000014; total units: 14195; buyers: 3258"
    ],
    "tables": [
        {
            "name": "Overall Totals (2025-05-02 to 2025-08-01)",
            "columns": ["purchases", "total_sales", "total_units", "buyers"],
            "rows": [["8726", 348298.84000000014, "14195", "3258"]],
        }
    ],
    "charts": [
        {
            "id": "totals_bar",
            "type": "bar",
            "spec": {
                "xKey": "metric",
                "yKey": "value",
                "series": [{"name": "value", "yKey": "value"}],
            },
        }
    ],
    "echo": {
        "intent": "single_number",
        "used": {
            "tables": ["`Haleon_Rewards_User_Performance_110925_SKUs`"],
            "columns": [
                "receiptid",
                "Total Sales Amount",
                "Total_Purchase_Units",
                "comuserid",
                "Upload_Date",
            ],
        },
        "stats": {"elapsed": 0.014108018},
        "sql_present": True,
    },
}


# -----------------------------
# Utilities
# -----------------------------

def sanitize_columns(df: pd.DataFrame):
    """Return a copy of df with sanitized lower_snake_case columns and a mapping original->safe.
    Rules: only [A-Za-z0-9_], collapse spaces/punct to underscore, ensure uniqueness.
    """
    import re

    mapping = {}
    safe_cols = []
    used = set()
    for col in df.columns:
        s = str(col).strip().lower()
        s = re.sub(r"[^0-9a-zA-Z]+", "_", s)
        s = re.sub(r"_+", "_", s).strip("_")
        if s == "":
            s = "col"
        base = s
        i = 1
        while s in used:
            s = f"{base}_{i}"
            i += 1
        used.add(s)
        mapping[col] = s
        safe_cols.append(s)
    df_copy = df.copy()
    df_copy.columns = safe_cols
    return df_copy, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """Coerce specified columns to numeric by stripping non-numeric chars and using to_numeric(coerce)."""
    import re

    for c in cols:
        if c in df.columns:
            # Convert to string, strip currency/symbols/commas/letters
            df[c] = (
                df[c]
                .astype(str)
                .str.replace(r"[^0-9\-\.]", "", regex=True)
                .replace({"": None})
            )
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce specified columns to datetime with errors='coerce'."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(chart_builder_callable):
    """Execute a chart builder callable that returns (chart, fallback_df).
    On any error or None chart, show a warning and the fallback table instead.
    """
    fallback_df = None
    try:
        result = chart_builder_callable()
        if isinstance(result, tuple) and len(result) == 2:
            chart, fallback_df = result
        else:
            chart = result
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


# -----------------------------
# App Renderer
# -----------------------------

def render_app():
    # Configure page once per session
    if "_page_configured" not in st.session_state:
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_configured"] = True

    # Disable altair max rows limit for safety
    alt.data_transformers.disable_max_rows()

    st.title("AI Report")

    # Summary section
    summaries = REPORT.get("summary", [])
    if summaries:
        st.subheader("Summary")
        for s in summaries:
            st.markdown(f"- {s}")

    # Tables section
    table_dfs = []  # keep for chart data source
    tables = REPORT.get("tables", [])
    if tables:
        st.subheader("Tables")
        for idx, tbl in enumerate(tables):
            name = tbl.get("name") or f"Table {idx+1}"
            columns = tbl.get("columns", [])
            rows = tbl.get("rows", [])
            try:
                df = pd.DataFrame(rows, columns=columns)
            except Exception:
                # Fallback if malformed
                df = pd.DataFrame(rows)
            st.markdown(f"**{name}**")
            st.dataframe(df)
            table_dfs.append((name, df))

    # Charts section
    charts = REPORT.get("charts", [])
    if charts:
        st.subheader("Charts")

        # Default data source: first table if available, else empty DF
        default_df = table_dfs[0][1] if table_dfs else pd.DataFrame()

        for ch in charts:
            ch_id = ch.get("id") or "chart"
            ch_type = (ch.get("type") or "").lower()
            spec = ch.get("spec", {})
            st.markdown(f"**{ch_type.capitalize()} — {ch_id}**")

            # Builder for bar/line/area/pie
            def build_chart():
                # Choose base DF and sanitize
                base_df = default_df.copy()
                safe_df, mapping = sanitize_columns(base_df)

                x_key = spec.get("xKey")
                y_key = spec.get("yKey")

                # If keys are missing from the sanitized DF, attempt a long-form pivot for single-row totals
                df_for_chart = safe_df.copy()

                # For bar/line/area, we need x and y
                if ch_type in ("bar", "line", "area"):
                    # If required keys not present, attempt to create them via melt
                    needs_melt = False
                    if x_key not in df_for_chart.columns or y_key not in df_for_chart.columns:
                        needs_melt = True

                    if needs_melt:
                        if not df_for_chart.empty:
                            # Melt into metric/value
                            temp = df_for_chart.copy()
                            temp = temp.reset_index(drop=True)
                            # Create a row_id to preserve structure even if multiple rows
                            temp["row_id"] = temp.index
                            melted = temp.melt(id_vars=["row_id"], var_name="metric", value_name="value")
                            df_for_chart = melted[["metric", "value"]].copy()
                            x_key = x_key or "metric"
                            y_key = y_key or "value"
                        else:
                            # No data
                            return None, df_for_chart

                    # Coerce numeric for y
                    df_for_chart = coerce_numeric(df_for_chart, [y_key])

                    # Drop rows with nulls in required fields
                    if x_key not in df_for_chart.columns or y_key not in df_for_chart.columns:
                        return None, df_for_chart

                    filtered = df_for_chart[[x_key, y_key]].copy()
                    filtered = filtered.dropna(subset=[x_key, y_key])
                    if filtered.empty:
                        return None, df_for_chart

                    # Build chart
                    if ch_type == "bar":
                        chart = (
                            alt.Chart(filtered)
                            .mark_bar()
                            .encode(
                                x=alt.X(f"{x_key}:N"),
                                y=alt.Y(f"{y_key}:Q"),
                                tooltip=[f"{x_key}:N", f"{y_key}:Q"],
                            )
                        )
                    elif ch_type == "line":
                        chart = (
                            alt.Chart(filtered)
                            .mark_line(point=True)
                            .encode(
                                x=alt.X(f"{x_key}:N"),
                                y=alt.Y(f"{y_key}:Q"),
                                tooltip=[f"{x_key}:N", f"{y_key}:Q"],
                            )
                        )
                    else:  # area
                        chart = (
                            alt.Chart(filtered)
                            .mark_area()
                            .encode(
                                x=alt.X(f"{x_key}:N"),
                                y=alt.Y(f"{y_key}:Q"),
                                tooltip=[f"{x_key}:N", f"{y_key}:Q"],
                            )
                        )

                    chart = chart.properties(width="container", height=300)
                    return chart, df_for_chart

                elif ch_type in ("pie", "donut", "arc"):
                    # Expect one dimension and a quantitative value; try to use spec or fallback to first two columns
                    dim = spec.get("categoryKey") or spec.get("xKey")
                    val = spec.get("valueKey") or spec.get("yKey")

                    if dim not in safe_df.columns or val not in safe_df.columns:
                        # Try to create a basic metric/value from safe_df if possible
                        if not safe_df.empty:
                            temp = safe_df.copy().reset_index(drop=True)
                            temp["row_id"] = temp.index
                            melted = temp.melt(id_vars=["row_id"], var_name="metric", value_name="value")
                            df_for_chart = melted[["metric", "value"]].copy()
                            dim, val = "metric", "value"
                        else:
                            return None, safe_df
                    else:
                        df_for_chart = safe_df.copy()

                    df_for_chart = coerce_numeric(df_for_chart, [val])
                    filtered = df_for_chart[[dim, val]].dropna()
                    if filtered.empty:
                        return None, df_for_chart

                    chart = (
                        alt.Chart(filtered)
                        .mark_arc()
                        .encode(
                            theta=alt.Theta(f"{val}:Q", stack=True),
                            color=alt.Color(f"{dim}:N"),
                            tooltip=[f"{dim}:N", f"{val}:Q"],
                        )
                    ).properties(width=350, height=350)
                    return chart, df_for_chart

                # Unknown chart type
                return None, safe_df

            # Render chart safely
            safe_altair_chart(build_chart)


# The module exposes render_app() and does not run on import
if __name__ == "__main__":
    # Optional manual run guard (won't execute when imported)
    render_app()
