# Streamlit app generated from an AI JSON report
# Renders summary, tables, and charts (Altair) based on the provided JSON structure.

import streamlit as st
import pandas as pd
import altair as alt

# ---- Embedded report JSON (as a Python dict) ----
REPORT = {
    'valid': True,
    'issues': [],
    'summary': [
        'Sensodyne leads all brands with the highest total sales (808,739.14), unique buyers (11,944), and units sold (38,793).',
        'Scotts and Polident follow in total sales, with 493,057.30 and 392,956.06 respectively.',
        'Calsource has the lowest performance with only 8 unique buyers, 325.91 in sales, and 8 units sold.',
        'There is a significant sales and buyer concentration in the top three brands: Sensodyne, Scotts, and Polident.'
    ],
    'tables': [
        {
            'name': 'Table',
            'columns': ['Brand', 'unique_buyers', 'total_sales', 'total_units'],
            'rows': [
                ['Sensodyne', '11944', 808739.14000007, '38793'],
                ['Scotts', '5859', 493057.3000000183, '19098'],
                ['Polident', '3476', 392956.0600000011, '19056'],
                ['Caltrate', '2863', 371326.40000000445, '5134'],
                ['Centrum', '1523', 193685.1399999982, '2787'],
                ['Panaflex', '870', 37043.94000000076, '4285'],
                ['Panadol', '316', 29882.030000000028, '1951'],
                ['Parodontax', '415', 15701.869999999963, '796'],
                ['Eno', '301', 10154.350000000082, '2246'],
                ['Calsource', '8', 325.9099999999999, '8']
            ]
        }
    ],
    'charts': [
        {
            'id': 'brand_sales',
            'type': 'bar',
            'spec': {
                'xKey': 'Brand',
                'yKey': 'total_sales',
                'series': [
                    {'name': 'Total Sales', 'yKey': 'total_sales'}
                ]
            }
        },
        {
            'id': 'brand_buyers',
            'type': 'bar',
            'spec': {
                'xKey': 'Brand',
                'yKey': 'unique_buyers',
                'series': [
                    {'name': 'Unique Buyers', 'yKey': 'unique_buyers'}
                ]
            }
        },
        {
            'id': 'brand_units',
            'type': 'bar',
            'spec': {
                'xKey': 'Brand',
                'yKey': 'total_units',
                'series': [
                    {'name': 'Total Units', 'yKey': 'total_units'}
                ]
            }
        }
    ],
    'echo': {
        'intent': 'table',
        'used': {
            'tables': ['`Haleon_Rewards_User_Performance_110925_SKUs`'],
            'columns': ['Brand', 'comuserid', 'Total Sales Amount', 'Total_Purchase_Units']
        },
        'stats': {'elapsed': 0.020411109},
        'sql_present': True
    }
}

# ---- Helper functions ----
def coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    df2 = df.copy()
    for col in df2.columns:
        if df2[col].dtype == 'object':
            df2[col] = pd.to_numeric(df2[col], errors='ignore')
    return df2


def infer_num_format(series: pd.Series) -> str:
    # Returns a Vega-Lite format string appropriate for the data
    if pd.api.types.is_integer_dtype(series):
        return ',.0f'
    if pd.api.types.is_float_dtype(series):
        return ',.2f'
    # fallback
    return ''


def build_bar_chart(df: pd.DataFrame, x_key: str, y_key: str, title: str = '', color: str | None = None) -> alt.Chart:
    # Determine formatting
    y_fmt = infer_num_format(df[y_key]) if y_key in df.columns else ''

    x_enc = alt.X(x_key, sort='-y', title=x_key)
    if y_fmt:
        y_enc = alt.Y(y_key, axis=alt.Axis(format=y_fmt), title=y_key)
        tooltip = [alt.Tooltip(x_key, type='nominal'), alt.Tooltip(y_key, type='quantitative', format=y_fmt)]
    else:
        y_enc = alt.Y(y_key, title=y_key)
        tooltip = [x_key, y_key]

    mark = alt.MarkConfig()
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=x_enc,
            y=y_enc,
            color=alt.value(color) if color else alt.value('#1f77b4'),
            tooltip=tooltip,
        )
        .properties(title=title or f'{y_key} by {x_key}', width='container', height=420)
    )
    return chart


# ---- Streamlit App ----
st.set_page_config(page_title='AI Report: Brand Performance', layout='wide')
st.title('Brand Performance Report')

# Validity and issues
if not REPORT.get('valid', True):
    st.error('Report marked as invalid.')
if REPORT.get('issues'):
    with st.expander('Report Issues'):
        for i, issue in enumerate(REPORT['issues'], start=1):
            st.write(f'{i}. {issue}')

# Summary
st.header('Summary')
summary_items = REPORT.get('summary', [])
if summary_items:
    st.markdown('\n'.join([f'- {item}' for item in summary_items]))
else:
    st.info('No summary provided.')

# Tables
st.header('Tables')
raw_tables = REPORT.get('tables', [])

df_map: dict[str, pd.DataFrame] = {}
first_table_name = None

if raw_tables:
    for idx, t in enumerate(raw_tables):
        name = t.get('name', f'Table {idx+1}')
        cols = t.get('columns', [])
        rows = t.get('rows', [])
        df = pd.DataFrame(rows, columns=cols)
        df = coerce_numeric_columns(df)
        if first_table_name is None:
            first_table_name = name
        df_map[name] = df
        st.subheader(f'Table: {name}')
        st.dataframe(df, use_container_width=True)
else:
    st.info('No tables available in the report.')

# Charts
st.header('Charts')
charts = REPORT.get('charts', [])

# Choose a data source for charts: default to the first table
if not df_map:
    st.info('No data available for charts.')
else:
    if len(df_map) > 1:
        ds_name = st.selectbox('Select data source for charts', list(df_map.keys()), index=list(df_map.keys()).index(first_table_name))
    else:
        ds_name = first_table_name
    data_df = df_map[ds_name]

    for ch in charts:
        cid = ch.get('id', '')
        ctype = ch.get('type', 'bar')
        spec = ch.get('spec', {})
        x_key = spec.get('xKey')
        y_key = spec.get('yKey')
        series = spec.get('series', [])

        if ctype == 'bar':
            # Determine title
            series_name = ''
            if series and isinstance(series, list) and isinstance(series[0], dict):
                series_name = series[0].get('name', '')
                y_key = series[0].get('yKey', y_key)
            chart_title = f'{series_name} by {x_key}' if series_name else (cid or f'{y_key} by {x_key}')

            missing_cols = [c for c in [x_key, y_key] if c not in data_df.columns]
            if missing_cols:
                st.warning(f'Chart {cid or "(untitled)"} skipped: missing columns {missing_cols}.')
                continue

            chart = build_bar_chart(data_df, x_key, y_key, title=chart_title)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning(f'Unsupported chart type: {ctype}. Only bar charts are rendered.')

# Optional: echo metadata
with st.expander('Report Metadata (echo)'):
    st.json(REPORT.get('echo', {}))

st.caption('App generated from AI JSON report. Uses Streamlit, Pandas, and Altair.')
