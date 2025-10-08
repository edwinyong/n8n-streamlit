from typing import Callable, Dict, List, Tuple
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

# -----------------------------
# Embedded report data (from JSON input)
# -----------------------------
REPORT = {
    "valid": True,
    "issues": [],
    "summary": [
        "10 brands present with columns: Brand, buyers, purchases, total_sales.",
        "Totals — buyers: 27,575; purchases: 55,979; total_sales: 2,352,872.14.",
        "Top brand by total_sales: Sensodyne — 808,739.14 (34.39% of total sales). Sensodyne also leads in buyers (11,944) and purchases (20,529).",
    ],
    "tables": [
        {
            "name": "user_purchases_and_sales_by_brand",
            "columns": ["Brand", "buyers", "purchases", "total_sales"],
            "rows": [
                ["Sensodyne", "11944", "20529", 808739.14000007],
                ["Scotts", "5859", "11628", 493057.3000000183],
                ["Polident", "3476", "12206", 392956.0600000011],
                ["Caltrate", "2863", "4592", 371326.40000000445],
                ["Centrum", "1523", "2444", 193685.1399999982],
                ["Panaflex", "870", "2513", 37043.94000000076],
                ["Panadol", "316", "416", 29882.030000000028],
                ["Parodontax", "415", "498", 15701.869999999963],
                ["Eno", "301", "1145", 10154.350000000082],
                ["Calsource", "8", "8", 325.9099999999999],
            ],
        }
    ],
    "charts": [
        {
            "id": "sales_by_brand",
            "type": "bar",
            "spec": {
                "xKey": "Brand",
                "yKey": "total_sales",
                "series": [{"name": "total_sales", "yKey": "total_sales"}],
            },
        },
        {
            "id": "buyers_vs_purchases",
            "type": "groupedBar",
            "spec": {
                "xKey": "Brand",
                "yKey": "purchases",
                "series": [
                    {"name": "buyers", "yKey": "buyers"},
                    {"name": "purchases", "yKey": "purchases"},
                ],
            },
        },
    ],
}

# -----------------------------
# Utilities
# -----------------------------

def sanitize_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Return a copy with safe snake_case columns and a mapping from original to safe.
    - Only [A-Za-z0-9_] allowed
    - Lowercase
    - Ensure uniqueness
    """
    def to_safe(name: str) -> str:
        s = str(name).strip().lower()
        # Replace spaces and hyphens with underscores
        s = s.replace("-", "_").replace(" ", "_")
        # Keep only alnum and underscore
        s = "".join(ch for ch in s if (ch.isalnum() or ch == "_"))
        # Collapse multiple underscores
        while "__" in s:
            s = s.replace("__", "_")
        if s == "":
            s = "col"
        return s

    mapping: Dict[str, str] = {}
    used: Dict[str, int] = {}
    for c in df.columns:
        base = to_safe(c)
        safe = base
        idx = 1
        while safe in used:
            idx += 1
            safe = f"{base}_{idx}"
        used[safe] = 1
        mapping[c] = safe
    new_df = df.copy()
    new_df.columns = [mapping[c] for c in df.columns]
    return new_df, mapping


def coerce_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    """Coerce specified columns to numeric, stripping non-numeric chars.
    Returns the same df (mutates in place for convenience).
    """
    for col in cols:
        if col in df.columns:
            # Convert to string, strip everything except digits, minus, and dot
            ser = df[col].astype(str)
            ser = ser.str.replace(r"[^0-9\.\-]", "", regex=True)
            df[col] = pd.to_numeric(ser, errors="coerce")
    return df


def coerce_datetime(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def safe_altair_chart(builder: Callable[[], Tuple[alt.Chart, pd.DataFrame]]):
    """Safely build and render an Altair chart. If anything fails, show a warning and the sanitized table."""
    try:
        chart, safe_df = builder()
        if chart is None:
            st.warning("Chart unavailable")
            if isinstance(safe_df, pd.DataFrame) and not safe_df.empty:
                st.dataframe(safe_df)
            return
        try:
            st.altair_chart(chart, use_container_width=True)
        except Exception:
            st.warning("Chart unavailable")
            if isinstance(safe_df, pd.DataFrame) and not safe_df.empty:
                st.dataframe(safe_df)
    except Exception:
        st.warning("Chart unavailable")
        # If builder itself fails without providing data, nothing further to show.


# -----------------------------
# App renderer
# -----------------------------

def render_app():
    # Guard page config to avoid resetting on reruns/imports
    if "_page_config_set" not in st.session_state:
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_set"] = True

    # Avoid row limit issues in Altair
    try:
        alt.data_transformers.disable_max_rows()
    except Exception:
        pass

    st.title("AI Report")

    # Summary section
    summaries = REPORT.get("summary", []) or []
    if summaries:
        st.subheader("Summary")
        for item in summaries:
            st.markdown(f"- {item}")

    # Tables section
    tables = REPORT.get("tables", []) or []
    if tables:
        st.subheader("Tables")
        for t in tables:
            name = t.get("name", "Table")
            cols = t.get("columns", []) or []
            rows = t.get("rows", []) or []
            try:
                df = pd.DataFrame(rows, columns=cols)
            except Exception:
                # Fallback: try to coerce even if malformed
                df = pd.DataFrame(rows)
                if cols and len(cols) == df.shape[1]:
                    df.columns = cols
            st.markdown(f"**{name}**")
            st.dataframe(df)

    # Helper to find a DataFrame that contains all required columns
    def find_df_with_columns(required_cols: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, str]]:
        for t in tables:
            cols = t.get("columns", []) or []
            if all(rc in cols for rc in required_cols):
                df = pd.DataFrame(t.get("rows", []), columns=cols)
                safe_df, mapping = sanitize_columns(df)
                return df, safe_df, mapping
        # If none found, return empty
        empty = pd.DataFrame()
        return empty, empty, {}

    # Charts section
    charts = REPORT.get("charts", []) or []
    if charts:
        st.subheader("Charts")

    for ch in charts:
        ch_id = ch.get("id", "chart")
        ch_type = (ch.get("type") or "").lower()
        spec = ch.get("spec", {}) or {}
        st.markdown(f"**{ch_id.replace('_', ' ').title()}**")

        # Bar chart
        if ch_type == "bar":
            x_key = spec.get("xKey")
            y_key = spec.get("yKey")
            if not x_key or not y_key:
                st.warning("Chart unavailable")
                continue

            orig_df, safe_df, mapping = find_df_with_columns([x_key, y_key])
            if safe_df.empty:
                st.warning("Chart unavailable")
                continue

            x_safe = mapping.get(x_key)
            y_safe = mapping.get(y_key)

            def build_bar():
                df_local = safe_df.copy()
                # Coerce numeric for y
                coerce_numeric(df_local, [y_safe])
                # Ensure there is at least one non-null row for x and y
                valid = df_local[[x_safe, y_safe]].dropna()
                valid = valid[valid[y_safe].notna()]
                if valid.empty:
                    return None, df_local
                # Build chart
                chart = (
                    alt.Chart(valid)
                    .mark_bar()
                    .encode(
                        x=alt.X(x_safe, type="nominal"),
                        y=alt.Y(y_safe, type="quantitative"),
                        color=alt.value("#1f77b4"),
                        tooltip=[c for c in valid.columns if c in {x_safe, y_safe}]
                    )
                    .properties(height=400)
                )
                return chart, valid

            safe_altair_chart(build_bar)

        # Grouped bar: render as two separate bar charts side-by-side to avoid complex encodings
        elif ch_type == "groupedbar":
            x_key = spec.get("xKey")
            series = spec.get("series", []) or []
            y_keys = [s.get("yKey") for s in series if s.get("yKey")] 
            # Fallback if none specified
            if not x_key or not y_keys:
                st.warning("Chart unavailable")
                continue

            # Attempt to find a table that has all required columns
            orig_df, safe_df, mapping = find_df_with_columns([x_key] + y_keys)
            if safe_df.empty:
                st.warning("Chart unavailable")
                continue

            x_safe = mapping.get(x_key)

            # Prepare two side-by-side charts (or as many as series provided, max 3 columns)
            n = len(y_keys)
            cols = st.columns(min(n, 3)) if n > 1 else [st]

            for i, yk in enumerate(y_keys):
                y_safe = mapping.get(yk)

                def make_builder(y_col_safe=y_safe):
                    def _builder():
                        df_local = safe_df.copy()
                        coerce_numeric(df_local, [y_col_safe])
                        valid = df_local[[x_safe, y_col_safe]].dropna()
                        valid = valid[valid[y_col_safe].notna()]
                        if valid.empty:
                            return None, df_local
                        chart = (
                            alt.Chart(valid)
                            .mark_bar()
                            .encode(
                                x=alt.X(x_safe, type="nominal"),
                                y=alt.Y(y_col_safe, type="quantitative"),
                                color=alt.value("#1f77b4" if i % 2 == 0 else "#ff7f0e"),
                                tooltip=[c for c in valid.columns if c in {x_safe, y_col_safe}],
                            )
                            .properties(height=360)
                        )
                        return chart, valid
                    return _builder

                target = cols[i % len(cols)]
                with target:
                    st.caption(f"{yk}")
                    safe_altair_chart(make_builder())

        # Area chart (not present but supported defensively)
        elif ch_type == "area":
            x_key = spec.get("xKey")
            y_key = spec.get("yKey")
            if not x_key or not y_key:
                st.warning("Chart unavailable")
                continue

            orig_df, safe_df, mapping = find_df_with_columns([x_key, y_key])
            if safe_df.empty:
                st.warning("Chart unavailable")
                continue

            x_safe = mapping.get(x_key)
            y_safe = mapping.get(y_key)

            def build_area():
                df_local = safe_df.copy()
                # Try coerce x to datetime; if all NaT, treat as nominal later
                coerce_datetime(df_local, [x_safe])
                coerce_numeric(df_local, [y_safe])
                # Prefer temporal if any valid datetimes exist, else nominal
                x_is_temporal = df_local[x_safe].notna().any() and pd.api.types.is_datetime64_any_dtype(df_local[x_safe])
                valid = df_local[[x_safe, y_safe]].dropna()
                if valid.empty:
                    return None, df_local
                x_enc = alt.X(x_safe, type="temporal" if x_is_temporal else "nominal")
                chart = (
                    alt.Chart(valid)
                    .mark_area(opacity=0.7)
                    .encode(
                        x=x_enc,
                        y=alt.Y(y_safe, type="quantitative"),
                        tooltip=[c for c in valid.columns if c in {x_safe, y_safe}],
                    )
                    .properties(height=400)
                )
                return chart, valid

            safe_altair_chart(build_area)

        # Line chart (not present but supported defensively)
        elif ch_type == "line":
            x_key = spec.get("xKey")
            y_key = spec.get("yKey")
            if not x_key or not y_key:
                st.warning("Chart unavailable")
                continue

            orig_df, safe_df, mapping = find_df_with_columns([x_key, y_key])
            if safe_df.empty:
                st.warning("Chart unavailable")
                continue

            x_safe = mapping.get(x_key)
            y_safe = mapping.get(y_key)

            def build_line():
                df_local = safe_df.copy()
                coerce_datetime(df_local, [x_safe])
                coerce_numeric(df_local, [y_safe])
                x_is_temporal = df_local[x_safe].notna().any() and pd.api.types.is_datetime64_any_dtype(df_local[x_safe])
                valid = df_local[[x_safe, y_safe]].dropna()
                if valid.empty:
                    return None, df_local
                x_enc = alt.X(x_safe, type="temporal" if x_is_temporal else "nominal")
                chart = (
                    alt.Chart(valid)
                    .mark_line(point=True)
                    .encode(
                        x=x_enc,
                        y=alt.Y(y_safe, type="quantitative"),
                        tooltip=[c for c in valid.columns if c in {x_safe, y_safe}],
                    )
                    .properties(height=400)
                )
                return chart, valid

            safe_altair_chart(build_line)

        # Pie-like (arc) chart support (not present but supported defensively)
        elif ch_type == "pie":
            dim_key = spec.get("categoryKey") or spec.get("xKey")
            value_key = spec.get("valueKey") or spec.get("yKey")
            if not dim_key or not value_key:
                st.warning("Chart unavailable")
                continue

            orig_df, safe_df, mapping = find_df_with_columns([dim_key, value_key])
            if safe_df.empty:
                st.warning("Chart unavailable")
                continue

            dim_safe = mapping.get(dim_key)
            val_safe = mapping.get(value_key)

            def build_pie():
                df_local = safe_df.copy()
                coerce_numeric(df_local, [val_safe])
                valid = df_local[[dim_safe, val_safe]].dropna()
                valid = valid[valid[val_safe].notna()]
                if valid.empty:
                    return None, df_local
                chart = (
                    alt.Chart(valid)
                    .mark_arc()
                    .encode(
                        theta=alt.Theta(field=val_safe, type="quantitative"),
                        color=alt.Color(field=dim_safe, type="nominal"),
                        tooltip=[dim_safe, val_safe],
                    )
                    .properties(height=400)
                )
                return chart, valid

            safe_altair_chart(build_pie)

        else:
            st.warning("Chart type not supported in this app")


# Note: No top-level execution. Only define render_app().
