import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime


def render_app() -> None:
    """Render the Streamlit application for user registrations and sales trends."""
    st.set_page_config(page_title="User & Sales Trends", layout="wide")

    st.title("User Registrations and Sales Trends")

    # Embedded report data (derived from the provided JSON)
    report = {
        "summary": [
            "Registered users peaked in February 2025 (2,093) and declined to 194 by September.",
            "Total sales were highest in February 2025 (181,249.13) and lowest in September (18,826.01).",
            "Both user registrations and sales show a downward trend after February.",
        ],
        "tables": [
            {
                "name": "Table",
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
                    ["2025-09-01", "194", 18826.00999999998],
                ],
            }
        ],
        "charts": [
            {
                "id": "main",
                "type": "line",
                "spec": {
                    "xKey": "month",
                    "yKey": "registered_users",
                    "series": [
                        {"name": "Registered Users", "yKey": "registered_users"},
                        {"name": "Total Sales", "yKey": "total_sales"},
                    ],
                },
            }
        ],
    }

    # Summaries
    st.subheader("Summary")
    for item in report.get("summary", []):
        st.markdown(f"- {item}")

    # Tables
    st.subheader("Data Table")
    table = report["tables"][0]
    df = pd.DataFrame(table["rows"], columns=table["columns"]).copy()

    # Type conversions
    df["month"] = pd.to_datetime(df["month"], errors="coerce")
    df["registered_users"] = pd.to_numeric(df["registered_users"], errors="coerce")
    df["total_sales"] = pd.to_numeric(df["total_sales"], errors="coerce")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "month": st.column_config.DateColumn("month", format="YYYY-MM"),
            "registered_users": st.column_config.NumberColumn(
                "registered_users", format=",.0f"
            ),
            "total_sales": st.column_config.NumberColumn(
                "total_sales", format="$,.2f"
            ),
        },
    )

    # Charts
    st.subheader("Charts")
    st.caption("Line chart showing monthly Registered Users and Total Sales (dual y-axes)")

    base = alt.Chart(df).encode(x=alt.X("month:T", title="Month"))

    line_users = base.mark_line(point=True, color="#1f77b4").encode(
        y=alt.Y(
            "registered_users:Q",
            axis=alt.Axis(title="Registered Users", format=",.0f"),
        ),
        tooltip=[
            alt.Tooltip("month:T", title="Month"),
            alt.Tooltip("registered_users:Q", title="Registered Users", format=",.0f"),
        ],
    )

    line_sales = base.mark_line(point=True, color="#d62728").encode(
        y=alt.Y(
            "total_sales:Q",
            axis=alt.Axis(title="Total Sales ($)", orient="right", format="$,.0f"),
        ),
        tooltip=[
            alt.Tooltip("month:T", title="Month"),
            alt.Tooltip("total_sales:Q", title="Total Sales", format="$,.2f"),
        ],
    )

    chart = (
        alt.layer(line_users, line_sales)
        .resolve_scale(y="independent")
        .properties(title="Monthly Registered Users and Total Sales", height=420)
    )

    st.altair_chart(chart, use_container_width=True)

    # Display the original chart spec for reference (optional but helpful)
    with st.expander("Chart specification (from report)"):
        st.json(report["charts"][0])
