import streamlit as st
import pandas as pd
import altair as alt

# -----------------------------
# Embedded report JSON payload
# -----------------------------
REPORT_DATA = {
    'valid': True,
    'issues': [],
    'summary': [
        'Monthly registered users peaked in February 2025 at 2,093, then generally declined through September.',
        'Total sales also peaked in February 2025 (181,249.13), followed by a gradual decrease, reaching the lowest in September (18,826.01).',
        'Both user registrations and sales show a downward trend from Q1 to Q3 2025.'
    ],
    'tables': [
        {
            'name': 'Table',
            'columns': ['month', 'registered_users', 'total_sales'],
            'rows': [
                ['2025-01-01', '1416', 119626.18999999885],
                ['2025-02-01', '2093', 181249.12999999718],
                ['2025-03-01', '1946', 162391.27999999782],
                ['2025-04-01', '1621', 122584.14999999863],
                ['2025-05-01', '1096', 110036.75999999886],
                ['2025-06-01', '1491', 138457.01999999848],
                ['2025-07-01', '1036', 101228.30999999943],
                ['2025-08-01', '762', 90910.37999999947],
                ['2025-09-01', '194', 18826.00999999998]
            ]
        }
    ],
    'charts': [
        {
            'id': 'trend1',
            'type': 'line',
            'spec': {
                'xKey': 'month',
                'yKey': 'registered_users',
                'series': [
                    {'name': 'Registered Users', 'yKey': 'registered_users'}
                ]
            }
        },
        {
            'id': 'trend2',
            'type': 'line',
            'spec': {
                'xKey': 'month',
                'yKey': 'total_sales',
                'series': [
                    {'name': 'Total Sales', 'yKey': 'total_sales'}
                ]
            }
        }
    ],
    'echo': {
        'intent': 'trend',
        'used': {
            'tables': ['`Haleon_Rewards_User_Performance_110925_SKUs`'],
            'columns': ['Upload_Date', 'comuserid', 'Total Sales Amount']
        },
        'stats': {'elapsed': 0.01229455},
        'sql_present': True
    }
}

# -----------------------------
# Helper functions
# -----------------------------

def build_dataframe(table_dict: dict) -> pd.DataFrame:
    df = pd.DataFrame(table_dict['rows'], columns=table_dict['columns'])
    # Convert date-like columns
    for col in df.columns:
        cl = col.lower()
        if cl in ['month', 'date'] or cl.endswith('date'):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass
    # Coerce numeric where applicable
    for col in df.columns:
        if col.lower() in ['registered_users', 'total_sales']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def make_line_chart(df: pd.DataFrame, x_key: str, y_key: str, title: str = None) -> alt.Chart:
    # Determine data types for encoding
    if pd.api.types.is_datetime64_any_dtype(df[x_key]):
        x_type = 'T'
    elif pd.api.types.is_numeric_dtype(df[x_key]):
        x_type = 'Q'
    else:
        x_type = 'N'

    y_type = 'Q' if pd.api.types.is_numeric_dtype(df[y_key]) else 'N'

    # Axis formatting
    y_axis = None
    y_title = title if title else y_key.replace('_', ' ').title()
    if y_type == 'Q':
        if y_key.lower() in ['total_sales', 'sales', 'amount', 'revenue']:
            y_axis = alt.Axis(format='$,.2f', title=y_title)
        elif pd.api.types.is_integer_dtype(df[y_key]):
            y_axis = alt.Axis(format=',d', title=y_title)
        else:
            y_axis = alt.Axis(format=',.2f', title=y_title)
    else:
        y_axis = alt.Axis(title=y_title)

    # Sort by x if temporal
    sort_df = df.sort_values(by=[x_key]) if x_type in ['T', 'Q'] else df.copy()

    tooltip = [
        alt.Tooltip(f'{x_key}:{x_type}', title=x_key.replace('_', ' ').title()),
        alt.Tooltip(f'{y_key}:{y_type}', title=y_title)
    ]

    chart = (
        alt.Chart(sort_df)
        .mark_line(point=True)
        .encode(
            x=alt.X(f'{x_key}:{x_type}', title=x_key.replace('_', ' ').title()),
            y=alt.Y(f'{y_key}:{y_type}', axis=y_axis),
            tooltip=tooltip,
            color=alt.value('#1f77b4')
        )
        .properties(height=320, title=y_title)
    )
    return chart


# -----------------------------
# Streamlit App
# -----------------------------
st.set_page_config(page_title='AI Report Dashboard', page_icon='📊', layout='wide')

st.title('AI Report Dashboard')

# Summary
if REPORT_DATA.get('summary'):
    st.header('Summary')
    for item in REPORT_DATA['summary']:
        st.markdown(f'- {item}')

# Tables
dfs = []
if REPORT_DATA.get('tables'):
    st.header('Tables')
    for idx, tbl in enumerate(REPORT_DATA['tables']):
        df_tbl = build_dataframe(tbl)
        dfs.append(df_tbl)
        st.subheader(tbl.get('name', f'Table {idx + 1}'))
        st.dataframe(df_tbl, use_container_width=True)

# Choose a primary DataFrame for charts (use first table by default)
base_df = dfs[0] if len(dfs) > 0 else pd.DataFrame()

# Charts
if REPORT_DATA.get('charts') and not base_df.empty:
    st.header('Charts')
    for chart_def in REPORT_DATA['charts']:
        ctype = chart_def.get('type', '').lower()
        spec = chart_def.get('spec', {})
        x_key = spec.get('xKey')
        y_key = spec.get('yKey')
        series_name = None
        series = spec.get('series') or []
        if isinstance(series, list) and len(series) > 0:
            series_name = series[0].get('name')

        if ctype == 'line' and x_key and y_key and x_key in base_df.columns and y_key in base_df.columns:
            chart = make_line_chart(base_df, x_key, y_key, title=series_name)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info(f"Chart '{chart_def.get('id', 'chart')}' could not be rendered due to missing fields or unsupported type.")

# Echo / Source details
if REPORT_DATA.get('echo'):
    with st.expander('Source details'):
        echo = REPORT_DATA['echo']
        st.write('Intent:', echo.get('intent'))
        used = echo.get('used') or {}
        if used:
            st.write('Used tables:', used.get('tables'))
            st.write('Used columns:', used.get('columns'))
        stats = echo.get('stats') or {}
        if stats:
            st.write('Stats:', stats)
        st.write('SQL present:', echo.get('sql_present'))

st.caption('Generated by AI Report App Builder')
