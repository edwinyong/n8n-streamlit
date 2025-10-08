from datetime import datetime
import streamlit as st
import pandas as pd
import altair as alt


def render_app():
    """Render the Streamlit app for the provided report JSON content."""
    st.set_page_config(page_title="Brand Sales and User Overview", layout="wide")

    # -----------------------------
    # Source: Provided JSON content
    # -----------------------------
    summaries = [
        "Sensodyne leads with the highest total sales (808,739.14) and the largest registered user base (11,944), accounting for 35.6% of overall sales.",
        "Scotts and Polident follow, with total sales of 493,057.30 and 392,956.06, respectively.",
        "Caltrate and Centrum are mid-tier brands in both sales and registered users.",
        "Calsource has the lowest sales and user count among all brands.",
    ]

    table_columns = ["Brand", "registered_users", "total_sales", "total_units"]
    table_rows = [
        ["Sensodyne", "11944", 808739.14000007, "38793"],
        ["Scotts", 5859, 493057.3000000183, "19098"],
        ["Polident", 3476, 392956.0600000011, "19056"],
        ["Caltrate", 2863, 371326.40000000445, "5134"],
        ["Centrum", 1523, 193685.1399999982, "2787"],
        ["Panaflex", 870, 37043.94000000076, "4285"],
        ["Panadol", 316, 29882.030000000028, "1951"],
        ["Parodontax", 415, 15701.869999999963, "796"],
        ["Eno", 301, 10154.350000000082, "2246"],
        ["Calsource", 8, 325.9099999999999, "8"],
    ]

    # Create DataFrame
    df = pd.DataFrame(table_rows, columns=table_columns)

    # Ensure proper data types for numeric fields
    for col in ["registered_users", "total_sales", "total_units"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # -----------------------------
    # UI: Header and Summary
    # -----------------------------
    st.title("Brand Sales and Registered Users Overview")
    st.caption(f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    st.subheader("Key Insights")
    st.markdown("\n".join([f"- {s}" for s in summaries]))

    # -----------------------------
    # Data Table
    # -----------------------------
    st.subheader("Data Table")
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Brand": st.column_config.TextColumn("Brand"),
            "registered_users": st.column_config.NumberColumn("Registered Users", format="%d"),
            "total_sales": st.column_config.NumberColumn("Total Sales", format="$%.2f"),
            "total_units": st.column_config.NumberColumn("Total Units", format="%d"),
        },
    )

    # -----------------------------
    # Charts (Altair)
    # -----------------------------
    st.subheader("Charts")

    # Bar chart: Total Sales by Brand
    sales_chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("Brand:N", sort="-y", title="Brand"),
            y=alt.Y("total_sales:Q", title="Total Sales", axis=alt.Axis(format="$,.2f")),
            tooltip=[
                alt.Tooltip("Brand:N", title="Brand"),
                alt.Tooltip("total_sales:Q", title="Total Sales", format=",.2f"),
                alt.Tooltip("registered_users:Q", title="Registered Users", format=",d"),
                alt.Tooltip("total_units:Q", title="Total Units", format=",d"),
            ],
            color=alt.Color("Brand:N", legend=None),
        )
        .properties(title="Total Sales by Brand")
    )

    # Bar chart: Registered Users by Brand
    users_chart = (
        alt.Chart(df)
        .mark_bar(color="#4C78A8")
        .encode(
            x=alt.X("Brand:N", sort="-y", title="Brand"),
            y=alt.Y("registered_users:Q", title="Registered Users", axis=alt.Axis(format=",d")),
            tooltip=[
                alt.Tooltip("Brand:N", title="Brand"),
                alt.Tooltip("registered_users:Q", title="Registered Users", format=",d"),
                alt.Tooltip("total_sales:Q", title="Total Sales", format=",.2f"),
                alt.Tooltip("total_units:Q", title="Total Units", format=",d"),
            ],
        )
        .properties(title="Registered Users by Brand")
    )

    col1, col2 = st.columns(2)
    with col1:
        st.altair_chart(sales_chart, use_container_width=True)
    with col2:
        st.altair_chart(users_chart, use_container_width=True)


# Note: Do not execute render_app() on import. It will be called by the host application.
