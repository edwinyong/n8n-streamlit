from typing import Dict, List, Tuple, Callable
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

# ------------------------------------------------------------
# Embedded report data (provided JSON converted to Python dict)
# ------------------------------------------------------------
REPORT_DATA = {
    "valid": True,
    "issues": [],
    "summary": [
        "2025 YTD total sales: 1,045,309.23; average per month: 116,145.47.",
        "Peak month: 2025-02 (181,249.13); lowest: 2025-09 (18,826.01).",
        "MoM highlights: Feb vs Jan +51.51%; Jul vs Jun -26.89%; Aug vs Jul -10.19%; Sep vs Aug -79.29%.",
        "Trend weak after June: three consecutive monthly declines culminating in September’s sharp drop."
    ],
    "tables": [
        {
            "name": "Monthly Sales 2025",
            "columns": ["month", "registered_users", "total_sales"],
            "rows": [
                ["2025-01-01", "1416", 119626.18999999885],
                ["2025-02-01", "2093", 181249.12999999718],
                ["2025-03-01", "1946", 162391.27999999782],
                ["2025-04-01", "1621", 122584.14999999863],
                ["2025-05-01", "1096", 110036.75999999886],
                ["2025-06-01", "1491", 138457.01999999848],
                ["2025-07-01", "1036", 101228.30999999943],
                ["2025-08-01", "762", 90910.37999999947],
                ["2025-09-01", "194", 18826.00999999998]
            ]
        }
    ],
    "charts": [
        {
            "id": "monthly_sales_2025",
            "type": "line",
            "spec": {
                "xKey": "month",
                "yKey": "total_sales",
                "series": [
                    {"name": "Total Sales", "yKey": "total_sales"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "trend",
        "used": {
            "tables": ["`Haleon_Rewards_User_Performance_110925_SKUs`"],
            "columns": ["Upload_Date", "comuserid", "Total Sales Amount"]
        },
        "stats": {"elapsed": 0.01166004},
        "sql_present": True
    }
}

# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------

def _sanitize_name(name: str) -> str:
    s = str(name).strip().lower()
    # replace spaces and hyphens with underscore
    s = s.replace("-", "_").replace(" ", "_")
    # keep only [A-Za-z0-9_]
    out = []
    for ch in s:
        if ("a" <= ch <= "z") or ("0" <= ch <= "9") or ch == "_":
            out.append(ch)
    s = "".join(out)
    while "__" in s:
        s = s.replace("__", "_")
    s = s.strip("_")
    if s == "":
        s = "col"
    return s

def sanitize_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Return a copy with safe snake_case columns and mapping original->safe.
    Ensures uniqueness of safe names.
    """
    original_cols = list(df.columns)
    safe_cols = []
    mapping: Dict[str, str] = {}
    used = {}
    for col in original_cols:
        base = _sanitize_name(col)
        new = base
        idx = 1
        while new in used:
            idx += 1
            new = f"{base}_{idx}"
        used[new] = True
        mapping[col] = new
        safe_cols.append(new)
    df_copy = df.copy()
    df_copy.columns = safe_cols
    return df_copy, mapping

def coerce_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            # Strip currency symbols, commas, spaces, and any non-numeric except . - e E
            df[c] = pd.to_numeric(
                df[c]
                .astype(str)
                .str.replace(r"[^0-9eE\.-]", "", regex=True)
                .str.replace(r"\(([^)]*)\)", r"-\1", regex=True),
                errors="coerce",
            )
    return df

def coerce_datetime(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df

def safe_altair_chart(builder: Callable[[], alt.Chart], fallback_df: pd.DataFrame) -> None:
    try:
        chart = builder()
        if chart is None:
            st.warning("Chart unavailable")
            st.dataframe(fallback_df)
            return
        st.altair_chart(chart, use_container_width=True)
    except Exception as e:
        st.warning("Chart unavailable")
        st.dataframe(fallback_df)

# ------------------------------------------------------------
# Core rendering logic
# ------------------------------------------------------------

def _build_altair_chart(df_original: pd.DataFrame, chart_meta: Dict) -> Tuple[alt.Chart, pd.DataFrame]:
    """Build an Altair chart from a DataFrame and chart metadata.
    Returns (chart, sanitized_df_for_fallback). May raise; caller should guard.
    """
    # Sanitize columns
    df_sanitized, mapping = sanitize_columns(df_original)

    # Resolve keys
    spec = chart_meta.get("spec", {})
    x_key_orig = spec.get("xKey")
    y_key_orig = spec.get("yKey")

    chart_type = (chart_meta.get("type") or "").lower()

    # Map to sanitized names if present
    x_key = mapping.get(x_key_orig, _sanitize_name(x_key_orig) if x_key_orig else None)
    y_key = mapping.get(y_key_orig, _sanitize_name(y_key_orig) if y_key_orig else None)

    # Validate presence
    needed = []
    if chart_type == "pie":
        # For pie we need one dimension (x) and one value (y)
        needed = [x_key, y_key]
    else:
        needed = [x_key, y_key]

    # If any key missing or not in df, fallback
    if any((k is None or k not in df_sanitized.columns) for k in needed):
        raise ValueError("Required fields not available for chart")

    # Coerce types
    # For x, try datetime; if not parseable, it will be NaT; otherwise keep as string
    df_sanitized = coerce_datetime(df_sanitized, [x_key])
    # For y, force numeric
    df_sanitized = coerce_numeric(df_sanitized, [y_key])

    # Prepare plot DataFrame: rows where both x and y are not null
    df_plot = df_sanitized[[x_key, y_key]].copy()

    # If x is all NaT, treat as nominal string from original column
    if pd.api.types.is_datetime64_any_dtype(df_plot[x_key]):
        pass
    else:
        # keep as-is (nominal)
        pass

    df_plot = df_plot.dropna(subset=[x_key, y_key])
    if df_plot.shape[0] == 0:
        raise ValueError("No valid data points for chart")

    # Build chart
    base = alt.Chart(df_plot)

    if chart_type == "bar":
        # Determine x type
        if pd.api.types.is_datetime64_any_dtype(df_plot[x_key]):
            x_enc = alt.X(f"{x_key}:T", title=x_key_orig or x_key)
        else:
            x_enc = alt.X(f"{x_key}:N", title=x_key_orig or x_key)
        chart = base.mark_bar().encode(
            x=x_enc,
            y=alt.Y(f"{y_key}:Q", title=y_key_orig or y_key),
            tooltip=[x_enc, alt.Tooltip(f"{y_key}:Q", title=y_key_orig or y_key)],
        )
        return chart, df_sanitized

    if chart_type == "area":
        if pd.api.types.is_datetime64_any_dtype(df_plot[x_key]):
            x_enc = alt.X(f"{x_key}:T", title=x_key_orig or x_key)
        else:
            x_enc = alt.X(f"{x_key}:N", title=x_key_orig or x_key)
        chart = base.mark_area(opacity=0.6).encode(
            x=x_enc,
            y=alt.Y(f"{y_key}:Q", title=y_key_orig or y_key),
            tooltip=[x_enc, alt.Tooltip(f"{y_key}:Q", title=y_key_orig or y_key)],
        )
        return chart, df_sanitized

    if chart_type == "pie":
        # For pie, x is category, y is value
        # Ensure y is numeric already; x nominal
        chart = base.mark_arc().encode(
            theta=alt.Theta(field=y_key, type="quantitative"),
            color=alt.Color(field=x_key, type="nominal", title=x_key_orig or x_key),
            tooltip=[alt.Tooltip(field=x_key, type="nominal", title=x_key_orig or x_key),
                     alt.Tooltip(field=y_key, type="quantitative", title=y_key_orig or y_key)],
        )
        return chart, df_sanitized

    # Default to line
    if pd.api.types.is_datetime64_any_dtype(df_plot[x_key]):
        x_enc = alt.X(f"{x_key}:T", title=x_key_orig or x_key)
    else:
        x_enc = alt.X(f"{x_key}:N", title=x_key_orig or x_key)
    chart = base.mark_line(point=True).encode(
        x=x_enc,
        y=alt.Y(f"{y_key}:Q", title=y_key_orig or y_key),
        tooltip=[x_enc, alt.Tooltip(f"{y_key}:Q", title=y_key_orig or y_key)],
    )
    return chart, df_sanitized


def render_app():
    # Guard page config to avoid reruns in multi-import contexts
    if not st.session_state.get("_page_config_set", False):
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_set"] = True

    # Altair settings
    alt.data_transformers.disable_max_rows()

    st.title("AI Report")

    # Summary section
    summary = REPORT_DATA.get("summary", [])
    if summary:
        st.subheader("Summary")
        for item in summary:
            st.markdown(f"- {item}")

    # Tables: load into DataFrames and display
    st.subheader("Tables")
    table_dfs: Dict[str, pd.DataFrame] = {}
    for t in REPORT_DATA.get("tables", []):
        name = t.get("name") or "Table"
        cols = t.get("columns", [])
        rows = t.get("rows", [])
        try:
            df = pd.DataFrame(rows, columns=cols)
        except Exception:
            # Fallback: try simple construction
            df = pd.DataFrame(rows)
            df.columns = cols[: len(df.columns)]
        table_dfs[name] = df
        st.markdown(f"**{name}**")
        st.dataframe(df)

    # Charts section
    charts = REPORT_DATA.get("charts", [])
    if charts:
        st.subheader("Charts")

    # Helper to find a table that contains required columns
    def _find_table_with_columns(x_key: str, y_key: str) -> Tuple[str, pd.DataFrame]:
        for name, df in table_dfs.items():
            if x_key in df.columns and y_key in df.columns:
                return name, df
        # If not found exactly, try case-insensitive match
        for name, df in table_dfs.items():
            lower_map = {c.lower(): c for c in df.columns}
            if x_key and y_key and (x_key.lower() in lower_map) and (y_key.lower() in lower_map):
                df2 = df.rename(columns=lower_map)
                return name, df2
        # Fallback: return first table
        if table_dfs:
            first_name = list(table_dfs.keys())[0]
            return first_name, table_dfs[first_name]
        return "", pd.DataFrame()

    for ch in charts:
        ch_id = ch.get("id") or "Chart"
        ch_type = (ch.get("type") or "").capitalize()
        st.markdown(f"**{ch_id} ({ch_type})**")

        spec = ch.get("spec", {})
        x_key = spec.get("xKey")
        y_key = spec.get("yKey")

        tbl_name, df_src = _find_table_with_columns(x_key, y_key) if (x_key and y_key) else ("", pd.DataFrame())

        if df_src.empty:
            st.warning("Chart unavailable")
            continue

        # Build and render chart safely
        def _builder():
            chart, _sanitized = _build_altair_chart(df_src, ch)
            # Set common properties
            return chart.properties(width="container", height=320)

        # For fallback, provide sanitized table so users see what was used
        sanitized_fallback, _ = sanitize_columns(df_src)
        safe_altair_chart(_builder, sanitized_fallback)

# Note: No top-level execution. The app runs only when render_app() is called.
