from datetime import datetime
import pandas as pd
import altair as alt
import streamlit as st

# Embedded report data (provided JSON)
REPORT = {
    "valid": True,
    "issues": [],
    "summary": [
        "Totals 2025-05-02 to 2025-08-01 — purchases: 8726; total sales: 348298.84000000014; total units: 14195; buyers: 3258"
    ],
    "tables": [
        {
            "name": "Overall Totals (2025-05-02 to 2025-08-01)",
            "columns": ["purchases", "total_sales", "total_units", "buyers"],
            "rows": [["8726", 348298.84000000014, "14195", "3258"]]
        }
    ],
    "charts": [
        {
            "id": "totals_bar",
            "type": "bar",
            "spec": {
                "xKey": "metric",
                "yKey": "value",
                "series": [{"name": "value", "yKey": "value"}]
            }
        }
    ],
    "echo": {
        "intent": "comparison_totals",
        "used": {
            "tables": ["`Haleon_Rewards_User_Performance_110925_SKUs`"],
            "columns": ["Upload_Date", "receiptid", "Total Sales Amount", "Total_Purchase_Units", "comuserid"]
        },
        "stats": {"elapsed": 0.015886698},
        "sql_present": True
    }
}


# -------------------- Utilities --------------------

def sanitize_columns(df: pd.DataFrame):
    """Return a copy of df with safe snake_case columns and a mapping of original->safe.
    Ensures only [A-Za-z0-9_] and uniqueness.
    """
    def to_safe(col: str) -> str:
        s = str(col).strip().lower()
        # replace spaces and dashes with underscores
        s = s.replace("-", "_").replace(" ", "_")
        # keep only [A-Za-z0-9_]
        out = []
        for ch in s:
            if (
                ("a" <= ch <= "z") or ("0" <= ch <= "9") or ch == "_"
            ):
                out.append(ch)
        s = "".join(out)
        # collapse multiple underscores
        while "__" in s:
            s = s.replace("__", "_")
        s = s.strip("_")
        if not s:
            s = "col"
        return s

    mapping = {}
    seen = {}
    safe_cols = []
    for c in df.columns:
        base = to_safe(c)
        name = base
        idx = 1
        while name in seen:
            idx += 1
            name = f"{base}_{idx}"
        seen[name] = True
        mapping[c] = name
        safe_cols.append(name)
    df_copy = df.copy()
    df_copy.columns = safe_cols
    return df_copy, mapping


def coerce_numeric(df: pd.DataFrame, cols):
    """Coerce specified columns to numeric, stripping non-numeric characters (e.g., currency symbols, commas, letters)."""
    if not isinstance(cols, (list, tuple, pd.Index)):
        cols = [cols]
    for c in cols:
        if c in df.columns:
            # Convert to string and strip non-numeric except minus and dot
            df[c] = (
                df[c]
                .astype(str)
                .str.replace(r"[^0-9.\-]", "", regex=True)
                .replace({"": pd.NA, "-": pd.NA, ".": pd.NA})
            )
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def coerce_datetime(df: pd.DataFrame, cols):
    """Coerce specified columns to datetime with errors coerced to NaT."""
    if not isinstance(cols, (list, tuple, pd.Index)):
        cols = [cols]
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def safe_altair_chart(builder_callable, fallback_df: pd.DataFrame):
    """Build and render an Altair chart safely. On failure, warn and show the sanitized table."""
    try:
        chart = builder_callable()
        if chart is None:
            raise ValueError("Chart builder returned None")
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.warning("Chart unavailable. Showing underlying data instead.")
        st.dataframe(fallback_df)


# -------------------- App Renderer --------------------

def render_app():
    # Guard to avoid re-setting in multi-import contexts
    if "_page_config_set" not in st.session_state:
        st.set_page_config(page_title="AI Report", layout="wide")
        st.session_state["_page_config_set"] = True

    # Disable Altair's row limit to avoid issues with larger data
    try:
        alt.data_transformers.disable_max_rows()
    except Exception:
        pass

    st.title("AI Report")

    # Summary section
    if REPORT.get("summary"):
        st.subheader("Summary")
        for item in REPORT["summary"]:
            st.markdown(f"- {item}")

    # Tables section
    st.subheader("Tables")
    dataframes = []
    for idx, table in enumerate(REPORT.get("tables", [])):
        name = table.get("name") or f"Table {idx+1}"
        cols = table.get("columns", [])
        rows = table.get("rows", [])
        try:
            df = pd.DataFrame(rows, columns=cols)
        except Exception:
            # Fallback: create from rows without columns
            df = pd.DataFrame(rows)
        st.markdown(f"**{name}**")
        st.dataframe(df)
        dataframes.append(df)

    # Helper to build a bar/line/area chart based on x and y
    def build_simple_chart(df_in: pd.DataFrame, chart_type: str, x_field: str, y_field: str, color_field: str | None = None, tooltip_fields=None):
        df_sanitized, mapping = sanitize_columns(df_in)
        # Ensure columns exist
        if x_field not in df_sanitized.columns or y_field not in df_sanitized.columns:
            raise ValueError("Required chart fields are missing")
        # Coerce types: x may be datetime, y must be numeric
        # Attempt datetime coercion for x; if all NaT, treat as nominal
        df_work = df_sanitized.copy()
        df_work = coerce_datetime(df_work, [x_field])
        df_work = coerce_numeric(df_work, [y_field])
        # Filter rows with valid x and y
        good = df_work[[x_field, y_field]].dropna(how="any")
        if good.empty:
            raise ValueError("No valid data to plot after coercion")
        # Determine x type: temporal if any datetime; otherwise nominal
        x_is_temporal = pd.api.types.is_datetime64_any_dtype(df_work[x_field]) and df_work[x_field].notna().any()
        x_encoding = alt.X(f"{x_field}:{'T' if x_is_temporal else 'N'}", title=x_field)
        y_encoding = alt.Y(f"{y_field}:Q", title=y_field)
        enc = {
            "x": x_encoding,
            "y": y_encoding,
        }
        if color_field and color_field in df_work.columns:
            enc["color"] = alt.Color(f"{color_field}:N")
        if tooltip_fields:
            safe_tips = [f"{c}:Q" if c == y_field else (f"{c}:T" if (c == x_field and x_is_temporal) else f"{c}:N") for c in tooltip_fields if c in df_work.columns]
            if safe_tips:
                enc["tooltip"] = safe_tips
        base = alt.Chart(df_work)
        if chart_type == "bar":
            chart = base.mark_bar()
        elif chart_type == "line":
            chart = base.mark_line(point=False)
        elif chart_type == "area":
            chart = base.mark_area()
        else:
            raise ValueError("Unsupported chart type for simple builder")
        return chart.encode(**enc)

    # Charts section
    if REPORT.get("charts"):
        st.subheader("Charts")

    # Use the first table as the primary data source for charts if available
    primary_df = dataframes[0] if dataframes else pd.DataFrame()

    for chart_def in REPORT.get("charts", []):
        chart_id = chart_def.get("id", "chart")
        chart_type = (chart_def.get("type") or "").lower()
        spec = chart_def.get("spec", {})
        st.markdown(f"**{chart_id}**")

        # Prepare data for charting
        src_df = primary_df.copy()
        if src_df.empty:
            st.warning("No data available for chart.")
            continue

        # Sanitize once for fallback display if needed
        sanitized_df, _ = sanitize_columns(src_df)

        # Strategy: If spec expects 'metric'/'value' but these fields don't exist,
        # create a melted long-form DataFrame with those columns.
        x_key = spec.get("xKey")
        y_key = spec.get("yKey")

        working_df = src_df.copy()
        if x_key == "metric" and y_key == "value":
            # Melt all columns into metric/value from a sanitized copy
            df_s, _m = sanitize_columns(working_df)
            # Build long form using all columns
            long_df = df_s.melt(value_vars=list(df_s.columns), var_name="metric", value_name="value")
            # Coerce numeric for value
            long_df = coerce_numeric(long_df, ["value"])
            # Remove rows where value is NaN after coercion
            long_df = long_df.dropna(subset=["value"])
            working_df = long_df
            # Ensure the keys align for the builder below
            x_key = "metric"
            y_key = "value"
            sanitized_df, _ = sanitize_columns(working_df)
        else:
            # Sanitize and keep as-is
            sanitized_df, _ = sanitize_columns(working_df)

        # Build and render chart safely
        def builder():
            if chart_type == "pie":
                # Pie via mark_arc with theta = sum(value)
                if x_key not in sanitized_df.columns and "category" in sanitized_df.columns:
                    # fallback to a generic category if provided
                    x_field = "category"
                else:
                    x_field = x_key if x_key in sanitized_df.columns else None
                y_field = y_key if y_key in sanitized_df.columns else None
                if not x_field or not y_field:
                    raise ValueError("Required fields for pie chart are missing")
                dfw = sanitized_df.copy()
                dfw = coerce_numeric(dfw, [y_field])
                dfw = dfw.dropna(subset=[x_field, y_field])
                if dfw.empty:
                    raise ValueError("No valid data for pie chart")
                base = alt.Chart(dfw)
                chart = base.mark_arc().encode(
                    theta=alt.Theta(f"{y_field}:Q", stack=True),
                    color=alt.Color(f"{x_field}:N"),
                    tooltip=[f"{x_field}:N", f"{y_field}:Q"],
                )
                return chart
            else:
                # bar/line/area
                tooltip_fields = []
                if x_key in sanitized_df.columns:
                    tooltip_fields.append(x_key)
                if y_key in sanitized_df.columns:
                    tooltip_fields.append(y_key)
                return build_simple_chart(sanitized_df, chart_type, x_key, y_key, None, tooltip_fields)

        safe_altair_chart(builder, sanitized_df)


# Note: No code executes on import. Use:
# from streamlit_app import render_app
# render_app()
