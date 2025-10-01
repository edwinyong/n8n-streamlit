import json
import io
from typing import Any, Dict, List, Optional, Tuple, Union

import streamlit as st
import pandas as pd
import altair as alt


# --------------------------------------------------------------------------------------
# AI Report Viewer
# - Displays summary (markdown)
# - Renders tables with st.dataframe
# - Renders charts with Altair (pie, bar, line, area, scatter, histogram, boxplot)
# - Accepts JSON via file upload or paste; includes a demo report you can load
# --------------------------------------------------------------------------------------

st.set_page_config(page_title="AI Report Viewer", layout="wide")
st.title("AI Report Viewer")
st.caption("Load a JSON report and this app will render its summary, tables, and charts.")

# --------------------------------------------------------------------------------------
# Demo JSON Report (fully provided, no placeholders)
# --------------------------------------------------------------------------------------
DEMO_REPORT: Dict[str, Any] = {
    "summary": (
        "# Quarterly Sales Report\n\n"
        "This report summarizes regional performance and monthly revenue trends.\n\n"
        "- North and East regions led total sales.\n\n"
        "- Units distribution shows balanced contribution across regions.\n\n"
        "- Revenue shows steady month-over-month growth.\n"
    ),
    "tables": [
        {
            "name": "Sales by Region",
            "data": [
                {"Region": "North", "Sales": 120000, "Units": 340},
                {"Region": "South", "Sales": 95000, "Units": 290},
                {"Region": "East", "Sales": 110000, "Units": 310},
                {"Region": "West", "Sales": 102000, "Units": 300},
            ],
        },
        {
            "name": "Monthly Trend",
            "data": {
                "columns": ["Month", "Revenue", "Orders"],
                "rows": [
                    ["Jan", 20000, 120],
                    ["Feb", 22000, 130],
                    ["Mar", 25000, 140],
                    ["Apr", 24000, 135],
                    ["May", 27000, 150],
                    ["Jun", 30000, 160],
                ],
            },
        },
    ],
    "charts": [
        {
            "type": "bar",
            "title": "Revenue by Region",
            "dataset": "Sales by Region",
            "encoding": {
                "x": {"field": "Region", "type": "nominal"},
                "y": {"field": "Sales", "type": "quantitative"},
                "color": {"field": "Region", "type": "nominal"},
                "tooltip": ["Region", "Sales", "Units"],
            },
        },
        {
            "type": "pie",
            "title": "Units Share by Region",
            "dataset": "Sales by Region",
            "encoding": {
                "theta": {"field": "Units", "type": "quantitative"},
                "color": {"field": "Region", "type": "nominal"},
                "tooltip": ["Region", "Units"],
            },
        },
        {
            "type": "line",
            "title": "Monthly Revenue Trend",
            "dataset": "Monthly Trend",
            "encoding": {
                "x": {"field": "Month", "type": "ordinal"},
                "y": {"field": "Revenue", "type": "quantitative"},
                "tooltip": ["Month", "Revenue", "Orders"],
            },
        },
    ],
}


# --------------------------------------------------------------------------------------
# Utilities: JSON loading and normalization
# --------------------------------------------------------------------------------------

def _try_json_loads(text: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
    try:
        return json.loads(text)
    except Exception:
        return None


def load_json_from_file(uploaded) -> Optional[Union[Dict[str, Any], List[Any]]]:
    if uploaded is None:
        return None
    try:
        content = uploaded.read()
        # Try utf-8 first; fallback to Latin-1
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                text = content.decode(enc)
                obj = _try_json_loads(text)
                if obj is not None:
                    return obj
            except Exception:
                continue
    except Exception:
        return None
    return None


def to_dataframe(data_obj: Any) -> Optional[pd.DataFrame]:
    """Attempt to convert various JSON shapes into a pandas DataFrame.
    Supported patterns:
    - list of dicts
    - dict with {columns: [...], rows: [...]} or {columns: [...], data: [...]} or {data: [...], columns: [...]} or {data: list-of-dicts}
    - dict of arrays (keys as columns)
    - list of lists when accompanied by 'columns' at the same level is handled elsewhere
    Returns None on failure.
    """
    try:
        # Direct list of dicts
        if isinstance(data_obj, list):
            if len(data_obj) == 0:
                return pd.DataFrame()
            if isinstance(data_obj[0], dict):
                return pd.DataFrame(data_obj)
            else:
                # List of lists without column names – create generic columns
                max_len = max((len(r) if isinstance(r, (list, tuple)) else 1) for r in data_obj)
                rows = [r if isinstance(r, (list, tuple)) else [r] for r in data_obj]
                rows = [list(r) + [None] * (max_len - len(r)) for r in rows]
                cols = [f"col_{i+1}" for i in range(max_len)]
                return pd.DataFrame(rows, columns=cols)

        if isinstance(data_obj, dict):
            # Common nested patterns
            if "columns" in data_obj and "rows" in data_obj:
                return pd.DataFrame(data_obj["rows"], columns=data_obj["columns"]) 
            if "columns" in data_obj and "data" in data_obj and isinstance(data_obj["data"], list):
                # data can be list of lists
                if len(data_obj["data"]) > 0 and isinstance(data_obj["data"][0], (list, tuple)):
                    return pd.DataFrame(data_obj["data"], columns=data_obj["columns"]) 
            if "data" in data_obj and isinstance(data_obj["data"], list):
                # list of dicts in data
                if len(data_obj["data"]) == 0:
                    return pd.DataFrame()
                if isinstance(data_obj["data"][0], dict):
                    return pd.DataFrame(data_obj["data"]) 
                # list of lists without explicit columns -> generic columns
                max_len = max((len(r) if isinstance(r, (list, tuple)) else 1) for r in data_obj["data"])
                rows = [r if isinstance(r, (list, tuple)) else [r] for r in data_obj["data"]]
                rows = [list(r) + [None] * (max_len - len(r)) for r in rows]
                cols = [f"col_{i+1}" for i in range(max_len)]
                return pd.DataFrame(rows, columns=cols)
            # dict of arrays
            if all(isinstance(v, (list, tuple)) for v in data_obj.values()):
                return pd.DataFrame(data_obj)

            # Try last-resort constructor
            return pd.DataFrame(data_obj)

        # Fallback: try reading as CSV string if looks like CSV
        if isinstance(data_obj, str) and ("," in data_obj or "\n" in data_obj):
            try:
                return pd.read_csv(io.StringIO(data_obj))
            except Exception:
                pass
    except Exception:
        return None
    return None


def normalize_table_entry(table_obj: Any) -> Tuple[str, Optional[pd.DataFrame]]:
    """Extract a (name, DataFrame) from a table object.
    Accepts variations like:
    - {name/title, data: list-of-dicts}
    - {name/title, data: {columns, rows}}
    - {name/title, columns: [...], rows/data: [...]}
    - {name/title missing} -> fall back to "Table N"
    """
    name = None
    df: Optional[pd.DataFrame] = None

    if isinstance(table_obj, dict):
        name = table_obj.get("name") or table_obj.get("title") or table_obj.get("id")
        # Direct columns/rows at top-level
        if "columns" in table_obj and ("rows" in table_obj or "data" in table_obj):
            rows_key = "rows" if "rows" in table_obj else "data"
            try:
                df = pd.DataFrame(table_obj[rows_key], columns=table_obj["columns"])
            except Exception:
                df = to_dataframe(table_obj.get(rows_key))
        elif "data" in table_obj:
            df = to_dataframe(table_obj["data"])
        else:
            # Try to turn the whole dict into a DF
            df = to_dataframe(table_obj)

    elif isinstance(table_obj, list):
        df = to_dataframe(table_obj)

    if name is None:
        name = "Table"
    return name, df


def coerce_encoding(enc_val: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    if isinstance(enc_val, str):
        return {"field": enc_val}
    if isinstance(enc_val, dict):
        return dict(enc_val)
    return {}


def infer_field_types(df: pd.DataFrame) -> Dict[str, str]:
    types: Dict[str, str] = {}
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            types[c] = "quantitative"
        elif pd.api.types.is_datetime64_any_dtype(df[c]):
            types[c] = "temporal"
        else:
            types[c] = "nominal"
    return types


def infer_encodings(df: pd.DataFrame, chart_type: str) -> Dict[str, Any]:
    inferred = {}
    col_types = infer_field_types(df)
    numeric_cols = [c for c, t in col_types.items() if t == "quantitative"]
    temporal_cols = [c for c, t in col_types.items() if t == "temporal"]
    nominal_cols = [c for c, t in col_types.items() if t == "nominal"]

    if chart_type in ("pie", "donut"):
        theta_field = numeric_cols[0] if numeric_cols else None
        color_field = (nominal_cols or numeric_cols or list(df.columns))
        return {
            "theta": {"field": theta_field or df.columns[0]},
            "color": {"field": color_field[0]},
            "tooltip": list(df.columns),
        }

    if chart_type in ("bar", "area", "line"):
        # Prefer temporal for x if available
        if temporal_cols:
            x_field = temporal_cols[0]
            y_field = numeric_cols[0] if numeric_cols else None
        else:
            x_field = (nominal_cols or list(df.columns))[0]
            y_field = numeric_cols[0] if numeric_cols else None
        if y_field is None and len(df.columns) > 1:
            y_field = df.columns[1]
        return {
            "x": {"field": x_field},
            "y": {"field": y_field or df.columns[0]},
            "tooltip": list(df.columns),
        }

    if chart_type == "scatter":
        if len(numeric_cols) >= 2:
            x_field, y_field = numeric_cols[:2]
        else:
            # Fallback to first two columns
            x_field, y_field = df.columns[:2]
        enc = {"x": {"field": x_field}, "y": {"field": y_field}, "tooltip": list(df.columns)}
        if nominal_cols:
            enc["color"] = {"field": nominal_cols[0]}
        return enc

    if chart_type == "histogram":
        field = numeric_cols[0] if numeric_cols else df.columns[0]
        return {
            "x": {"field": field, "bin": True},
            "y": {"aggregate": "count"},
            "tooltip": [field],
        }

    if chart_type == "boxplot":
        field = numeric_cols[0] if numeric_cols else df.columns[0]
        cat = (nominal_cols or temporal_cols or [df.columns[0]])[0]
        return {"x": {"field": cat}, "y": {"field": field}, "tooltip": list(df.columns)}

    # Default
    return {"x": {"field": df.columns[0]}, "y": {"field": df.columns[1] if len(df.columns) > 1 else df.columns[0]}, "tooltip": list(df.columns)}


def build_chart_from_spec(df: pd.DataFrame, chart_spec: Dict[str, Any]) -> Optional[alt.Chart]:
    try:
        chart_type = (chart_spec.get("type") or "bar").lower()
        enc_spec = chart_spec.get("encoding") or {}
        width = chart_spec.get("width")
        height = chart_spec.get("height")
        title = chart_spec.get("title")
        orientation = chart_spec.get("orientation")  # e.g., 'horizontal'

        # Coerce encodings and apply type inference defaults
        encodings: Dict[str, Any] = {}
        if enc_spec:
            for k, v in enc_spec.items():
                if isinstance(v, list):
                    # Tooltips as list of fields
                    if k == "tooltip":
                        encodings[k] = [coerce_encoding(item).get("field", item) for item in v]
                    else:
                        # Uncommon, but handle generically
                        encodings[k] = v
                else:
                    encodings[k] = coerce_encoding(v)
        else:
            encodings = infer_encodings(df, chart_type)

        # Fill in missing types from data
        inferred_types = infer_field_types(df)
        def _attach_type(enc: Dict[str, Any]) -> Dict[str, Any]:
            enc = dict(enc)
            if "field" in enc and "type" not in enc:
                field = enc["field"]
                if field in inferred_types:
                    enc["type"] = inferred_types[field]
            return enc

        # Normalize enc types
        for key in ["x", "y", "theta", "color", "size", "shape", "opacity"]:
            if key in encodings and isinstance(encodings[key], dict):
                encodings[key] = _attach_type(encodings[key])

        # Build altair chart
        base = alt.Chart(df)

        # Choose mark based on type
        mark_kwargs = {}
        if chart_type == "bar":
            mark = base.mark_bar()
            if orientation == "horizontal":
                # Swap encodings
                x_enc = encodings.get("x")
                y_enc = encodings.get("y")
                if x_enc and y_enc:
                    encodings["x"], encodings["y"] = y_enc, x_enc
        elif chart_type == "line":
            mark = base.mark_line(point=True)
        elif chart_type == "area":
            mark = base.mark_area()
        elif chart_type == "scatter":
            mark = base.mark_point()
        elif chart_type in ("pie", "donut"):
            inner_radius = chart_spec.get("innerRadius", 0) if chart_type == "donut" else chart_spec.get("innerRadius", 0)
            mark = base.mark_arc(innerRadius=inner_radius)
            # If theta missing, infer
            if "theta" not in encodings:
                encodings.update(infer_encodings(df, "pie"))
        elif chart_type == "histogram":
            mark = base.mark_bar()
            # Ensure x is binned and y is count()
            if "x" in encodings:
                encodings["x"]["bin"] = True
            else:
                encodings["x"] = {"field": df.columns[0], "type": infer_field_types(df)[df.columns[0]], "bin": True}
            encodings["y"] = {"aggregate": "count"}
        elif chart_type == "boxplot":
            # Use built-in boxplot mark
            x_enc = encodings.get("x")
            y_enc = encodings.get("y")
            if not x_enc or not y_enc:
                encodings.update(infer_encodings(df, "boxplot"))
            chart = alt.Chart(df).mark_boxplot()
            chart = chart.encode(
                x=alt.X(**encodings.get("x", {})),
                y=alt.Y(**encodings.get("y", {})),
                color=alt.Color(**encodings.get("color", {})) if isinstance(encodings.get("color"), dict) else None,
                tooltip=encodings.get("tooltip", list(df.columns)),
            )
            if title:
                chart = chart.properties(title=title)
            if width:
                chart = chart.properties(width=width)
            if height:
                chart = chart.properties(height=height)
            return chart
        else:
            # Default to bar
            mark = base.mark_bar()

        # Compose encodings
        encoded = mark.encode(
            x=alt.X(**encodings.get("x", {})) if isinstance(encodings.get("x"), dict) else None,
            y=alt.Y(**encodings.get("y", {})) if isinstance(encodings.get("y"), dict) else None,
            theta=alt.Theta(**encodings.get("theta", {})) if isinstance(encodings.get("theta"), dict) else None,
            color=alt.Color(**encodings.get("color", {})) if isinstance(encodings.get("color"), dict) else None,
            size=alt.Size(**encodings.get("size", {})) if isinstance(encodings.get("size"), dict) else None,
            opacity=alt.Opacity(**encodings.get("opacity", {})) if isinstance(encodings.get("opacity"), dict) else None,
            tooltip=encodings.get("tooltip", list(df.columns)),
        )

        if title:
            encoded = encoded.properties(title=title)
        if width:
            encoded = encoded.properties(width=width)
        if height:
            encoded = encoded.properties(height=height)

        return encoded
    except Exception as e:
        st.warning(f"Could not render chart: {e}")
        return None


def extract_dataset_df(chart_obj: Dict[str, Any], table_map: Dict[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
    # Priority: explicit data -> dataset reference -> None
    data_obj = chart_obj.get("data")
    if data_obj is not None:
        return to_dataframe(data_obj)

    dataset_name = chart_obj.get("dataset") or chart_obj.get("table") or chart_obj.get("source")
    if dataset_name and dataset_name in table_map:
        return table_map[dataset_name]

    # If none specified but there's exactly one table, use it
    if len(table_map) == 1:
        return list(table_map.values())[0]

    return None


# --------------------------------------------------------------------------------------
# Sidebar: Load report JSON
# --------------------------------------------------------------------------------------
with st.sidebar:
    st.header("Report Input")
    uploaded = st.file_uploader("Upload JSON report", type=["json"])
    pasted_text = st.text_area("Or paste JSON here", height=200, placeholder="{\n  \"summary\": \"...\",\n  \"tables\": [ ... ],\n  \"charts\": [ ... ]\n}")
    use_demo = st.toggle("Load demo report", value=False, help="Loads a complete example report included with this app.")

    raw_obj: Optional[Union[Dict[str, Any], List[Any]]] = None
    if use_demo:
        raw_obj = DEMO_REPORT
    elif uploaded is not None:
        raw_obj = load_json_from_file(uploaded)
        if raw_obj is None:
            st.error("Could not parse the uploaded JSON file.")
    elif pasted_text.strip():
        raw_obj = _try_json_loads(pasted_text)
        if raw_obj is None:
            st.error("Could not parse the pasted JSON text.")

    show_raw = st.checkbox("Show raw JSON", value=False)


# --------------------------------------------------------------------------------------
# Main rendering
# --------------------------------------------------------------------------------------
if raw_obj is None:
    st.info("Upload or paste a JSON report, or enable 'Load demo report' in the sidebar.")
else:
    # Normalize top-level report structure
    if isinstance(raw_obj, list):
        report: Dict[str, Any] = {"summary": "", "tables": raw_obj, "charts": []}
    elif isinstance(raw_obj, dict):
        report = raw_obj
    else:
        report = {"summary": str(raw_obj), "tables": [], "charts": []}

    if show_raw:
        st.subheader("Raw JSON")
        st.json(report)

    # Summary (markdown)
    summary = report.get("summary")
    if isinstance(summary, list):
        st.markdown("\n\n".join(str(s) for s in summary))
    elif isinstance(summary, str):
        st.markdown(summary)
    elif summary is not None:
        st.markdown(str(summary))

    # Tables
    tables = report.get("tables") or []
    table_map: Dict[str, pd.DataFrame] = {}

    if isinstance(tables, dict):
        # dict of named tables
        for k, v in tables.items():
            name, df = normalize_table_entry({"name": k, "data": v})
            if df is not None:
                st.subheader(name)
                st.dataframe(df, use_container_width=True)
                table_map[name] = df
    elif isinstance(tables, list):
        for idx, t in enumerate(tables, start=1):
            name, df = normalize_table_entry(t)
            # Disambiguate duplicate names
            base_name = name
            if name in table_map:
                i = 2
                while f"{base_name} ({i})" in table_map:
                    i += 1
                name = f"{base_name} ({i})"
            if df is not None:
                st.subheader(name)
                st.dataframe(df, use_container_width=True)
                table_map[name] = df
    else:
        # Attempt to make a table from whatever is present
        df = to_dataframe(tables)
        if df is not None:
            st.subheader("Table")
            st.dataframe(df, use_container_width=True)
            table_map["Table"] = df

    # Charts
    charts = report.get("charts") or []
    if isinstance(charts, list) and len(charts) > 0:
        st.header("Charts")
        for i, ch in enumerate(charts, start=1):
            if not isinstance(ch, dict):
                st.warning(f"Chart #{i} is not a valid object; skipping.")
                continue
            title = ch.get("title") or ch.get("name") or f"Chart {i}"
            df = extract_dataset_df(ch, table_map)
            if df is None or df.empty:
                st.warning(f"{title}: No data available for this chart.")
                continue
            chart = build_chart_from_spec(df, ch)
            if chart is None:
                st.warning(f"{title}: Could not build chart.")
                continue
            st.subheader(title)
            st.altair_chart(chart, use_container_width=True)
    elif isinstance(charts, dict) and charts:
        st.header("Charts")
        for key, ch in charts.items():
            ch_spec = ch if isinstance(ch, dict) else {"type": "bar", "data": ch}
            title = ch_spec.get("title") or key
            df = extract_dataset_df(ch_spec, table_map)
            if df is None or df.empty:
                st.warning(f"{title}: No data available for this chart.")
                continue
            chart = build_chart_from_spec(df, ch_spec)
            if chart is None:
                st.warning(f"{title}: Could not build chart.")
                continue
            st.subheader(title)
            st.altair_chart(chart, use_container_width=True)

    # Download original JSON
    try:
        st.download_button(
            label="Download current report JSON",
            data=json.dumps(report, ensure_ascii=False, indent=2),
            file_name="report.json",
            mime="application/json",
        )
    except Exception:
        pass

# Footer
st.caption("Built with Streamlit, Altair, and Pandas.")
