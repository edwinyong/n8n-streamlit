import streamlit as st
import pandas as pd
import altair as alt
import json
import re
from typing import Any, Dict, List

# Attempt to import the provided chat widget. If unavailable, provide a safe fallback.
try:
    from chat_widget import render_chat_widget  # Must include per spec
except Exception:
    def render_chat_widget(title: str, system_hint: str, context: Any, sidebar: bool = True):
        # Minimal fallback so the app doesn't crash if chat_widget isn't present.
        container = st.sidebar if sidebar else st
        container.header(title)
        container.info("AI chat is unavailable because 'chat_widget' module is missing.")


# ---- Embedded Report JSON ----
# The app embeds the provided JSON report so it can render without external files.
report: Dict[str, Any] = {
    "valid": True,
    "issues": [
        {
            "code": "pii_omitted",
            "severity": "info",
            "message": "PII columns (user_mobile, user_name) have been omitted from tables and charts."
        },
        {
            "code": "truncated_rows",
            "severity": "info",
            "message": "Only first 200 rows are shown in the table for brevity."
        }
    ],
    "summary": [
        "A total of 36,831 users are included in the performance report.",
        "Total sales across all users: RM1,843,315.89, with 94,087 units sold and 52,029 receipts issued.",
        "Average sales per user: RM50.05; average units sold per user: 2.55.",
        "Most users have low or zero activity, as indicated by a mean of 1.41 receipts per user."
    ],
    "tables": [
        {
            "name": "User Performance (Sample)",
            "columns": ["user_id", "Total Receipts", "Total Sales", "Total Sold Unit"],
            "rows": [
                ["79bedb76-6991-44a7-b01c-2ef568bb09cd", "0", "RM0.00", "0"],
                ["c876a017-9e3c-4ce5-a045-f4187fa0dfde", "0", "RM0.00", "0"],
                ["f6931e33-99eb-4163-a01f-09b58ce75848", "2", "RM110.88", "6"],
                ["e0211655-f2bb-4a61-81b0-457afdd796eb", "1", "RM41.09", "4"],
                ["82729809-dbbe-4eab-8d86-be1600bfdce6", "0", "RM0.00", "0"],
                ["544cc34d-fa81-4c41-9bbc-62e0a638813a", "0", "RM0.00", "0"],
                ["c31c72cf-0792-4a25-b873-ddbc73d8d105", "0", "RM0.00", "0"],
                ["c336e647-7ad0-4b8b-b511-009933ed4b48", "0", "RM0.00", "0"],
                ["789cab0c-619f-4abe-8b93-fd019777e45f", "1", "RM14.90", "2"],
                ["1f516b32-a6da-4963-be46-e9c2a83a3ae5", "0", "RM0.00", "0"]
            ]
        }
    ],
    "charts": [
        {
            "id": "main",
            "type": "kpi",
            "spec": {
                "xKey": "Metric",
                "yKey": "Value",
                "series": [
                    {"name": "Total Sales (RM)", "yKey": "Total Sales"},
                    {"name": "Total Sold Units", "yKey": "Total Sold Unit"},
                    {"name": "Total Receipts", "yKey": "Total Receipts"}
                ]
            }
        }
    ],
    "echo": {
        "intent": "table",
        "used": {
            "tables": ["user performance"],
            "columns": ["user_id", "user_mobile", "Total Receipts", "Total Sales", "Total Sold Unit"]
        },
        "stats": {"elapsed": 0},
        "sql_present": False
    }
}


# ---- Helpers ----

def extract_overall_kpis_from_summary(summary_lines: List[str]) -> Dict[str, float]:
    """Extract overall KPI values from the summary free-text.

    Returns keys:
    - "Total Sales (RM)": float
    - "Total Sold Units": float
    - "Total Receipts": float
    - "Total Users": float (optional extra)
    """
    text = " ".join(summary_lines)

    def to_number(s: str) -> float:
        return float(s.replace(",", ""))

    kpis: Dict[str, float] = {}

    m_sales = re.search(r"Total sales[^:]*:\s*RM([0-9,]+(?:\.[0-9]{1,2})?)", text, flags=re.I)
    if m_sales:
        kpis["Total Sales (RM)"] = to_number(m_sales.group(1))

    m_units = re.search(r"with\s*([0-9,]+)\s*units\s*sold", text, flags=re.I)
    if m_units:
        kpis["Total Sold Units"] = to_number(m_units.group(1))

    m_receipts = re.search(r"and\s*([0-9,]+)\s*receipts\s*issued", text, flags=re.I)
    if m_receipts:
        kpis["Total Receipts"] = to_number(m_receipts.group(1))

    m_users = re.search(r"A total of\s*([0-9,]+)\s*users", text, flags=re.I)
    if m_users:
        kpis["Total Users"] = to_number(m_users.group(1))

    return kpis


def format_number(value: float, currency: bool = False) -> str:
    if currency:
        return f"RM{value:,.2f}"
    # For large integers, show with thousands separator
    if abs(value - int(value)) < 1e-6:
        return f"{int(value):,}"
    return f"{value:,}"


def render_kpi_chart(chart_spec: Dict[str, Any], summary_lines: List[str]):
    """Render a KPI-style chart using Altair bars based on summary-derived totals."""
    series = chart_spec.get("spec", {}).get("series", [])
    kpis = extract_overall_kpis_from_summary(summary_lines)

    data_rows = []
    for s in series:
        label = s.get("name") or s.get("yKey") or "Metric"
        # Determine if this metric should be shown as currency
        is_currency = "sales" in label.lower() and "rm" in label.lower()
        val = kpis.get(label)
        # If exact label not found (due to label variations), try mapping by common aliases
        if val is None:
            alias_map = {
                "Total Sales (RM)": kpis.get("Total Sales (RM)"),
                "Total Sales": kpis.get("Total Sales (RM)"),
                "Total Sold Unit": kpis.get("Total Sold Units"),
                "Total Sold Units": kpis.get("Total Sold Units"),
                "Total Receipts": kpis.get("Total Receipts"),
            }
            val = alias_map.get(label)
        if val is not None:
            data_rows.append({
                "Metric": label,
                "Value": float(val),
                "ValueLabel": format_number(float(val), currency=is_currency)
            })

    if not data_rows:
        st.warning("No KPI data could be extracted from the summary to render the chart.")
        return

    df = pd.DataFrame(data_rows)

    base = alt.Chart(df).encode(
        x=alt.X("Metric:N", sort=None, axis=alt.Axis(title="Metric")),
        y=alt.Y("Value:Q", axis=alt.Axis(title="Value")),
        tooltip=[alt.Tooltip("Metric:N"), alt.Tooltip("ValueLabel:N", title="Value")]
    )

    bars = base.mark_bar(size=40, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        color=alt.Color("Metric:N", legend=None)
    )

    texts = base.mark_text(align="center", baseline="bottom", dy=-2).encode(
        text="ValueLabel:N",
        color=alt.value("#333")
    )

    chart = (bars + texts).properties(height=320)
    st.altair_chart(chart, use_container_width=True)


# ---- Streamlit App ----
st.set_page_config(page_title="Performance Report Dashboard", page_icon="📊", layout="wide")

st.title("Performance Report")

# Chat widget (sidebar)
render_chat_widget(
    title="💬 AI Analyst",
    system_hint="You are a data analyst AI. Use context when helpful.",
    context=report,
    sidebar=True,
)

# Issues / Notices
if report.get("issues"):
    for issue in report["issues"]:
        sev = (issue.get("severity") or "info").lower()
        msg = issue.get("message") or ""
        if sev == "error":
            st.error(msg)
        elif sev == "warning":
            st.warning(msg)
        else:
            st.info(msg)

# Summary
st.subheader("Summary")
if report.get("summary"):
    for line in report["summary"]:
        st.markdown(f"- {line}")
else:
    st.write("No summary available.")

# Tables
tables = report.get("tables", [])
if tables:
    st.subheader("Tables")
    for tbl in tables:
        name = tbl.get("name") or "Table"
        cols = tbl.get("columns") or []
        rows = tbl.get("rows") or []
        df = pd.DataFrame(rows, columns=cols)
        st.markdown(f"**{name}**")
        st.dataframe(df, use_container_width=True)
else:
    st.write("No tables provided.")

# Charts
charts = report.get("charts", [])
if charts:
    st.subheader("Charts")
    for ch in charts:
        ch_type = (ch.get("type") or "").lower()
        ch_id = ch.get("id") or "chart"
        with st.container():
            st.markdown(f"**Chart: {ch_id} ({ch_type})**")
            if ch_type == "kpi":
                render_kpi_chart(ch, report.get("summary", []))
            else:
                st.info(f"Chart type '{ch_type}' is not recognized. Rendering is skipped.")
else:
    st.write("No charts provided.")

# Raw JSON (for transparency/debug)
with st.expander("View raw report JSON"):
    st.code(json.dumps(report, indent=2), language="json")
