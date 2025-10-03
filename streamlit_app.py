import json
from typing import Any, Dict, List, Optional

import altair as alt
import pandas as pd
import streamlit as st


# ------------------------------
# Page setup
# ------------------------------
st.set_page_config(page_title='AI Report Dashboard', layout='wide')
st.title('AI Report Dashboard')


# ------------------------------
# Embedded report JSON (as provided)
# ------------------------------
report_json = r'''{"valid":true,"issues":[],"summary":["Registered users trend in 2025: Q1 (4,998), Q2 (3,826), Q3 (4,011), Q4 (4,210).","Sales trend in 2025: Q1 (461,543.37), Q2 (371,077.93), Q3 (384,099.01), Q4 (401,120.55).","Significant drop in both registered users and sales from Q1 to Q2.","Gradual recovery in Q3 and Q4, but no quarters surpass Q1's performance.","No abnormal spikes detected; Q1 is peak, followed by a dip and moderate recovery."],"tables":[{"name":"Table","columns":["quarter","registered_users","total_sales"],"rows":[["Q1","4998",461543.3700000002],["Q2","3826",371077.93],["Q3","4011",384099.01],["Q4","4210",401120.55]]}],"charts":[{"id":"main","type":"line","spec":{"xKey":"quarter","yKey":"registered_users","series":[{"name":"Registered Users","yKey":"registered_users"}]}},{"id":"sales","type":"line","spec":{"xKey":"quarter","yKey":"total_sales","series":[{"name":"Total Sales","yKey":"total_sales"}]}}],"echo":{"intent":"trend","used":{"tables":["`Haleon_Rewards_User_Performance_110925_list`"],"columns":["\"user_id\"","\"Total Sales Amount\"","\"Upload_Date\""]},"stats":{"elapsed":0.04843408},"sql_present":true}}'''

report: Dict[str, Any] = json.loads(report_json)


# ------------------------------
# Helpers
# ------------------------------
def coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    df2 = df.copy()
    for col in df2.columns:
        # Attempt to convert to numeric, leave as-is if not convertible
        df2[col] = pd.to_numeric(df2[col], errors='ignore')
    return df2


def alt_type_from_dtype(dtype) -> str:
    if pd.api.types.is_numeric_dtype(dtype):
        return 'Q'
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return 'T'
    return 'N'


def build_line_chart(df: pd.DataFrame, x_key: str, series: List[Dict[str, Any]], title: Optional[str] = None) -> alt.Chart:
    # Prepare data
    present_y_keys = [s.get('yKey') for s in series if s.get('yKey') in df.columns]
    label_map = {s.get('yKey'): s.get('name', s.get('yKey')) for s in series if s.get('yKey')}

    x_type = alt_type_from_dtype(df[x_key].dtype) if x_key in df.columns else 'N'

    if len(present_y_keys) <= 1:
        y_key = present_y_keys[0] if present_y_keys else None
        if y_key is None:
            return alt.Chart(pd.DataFrame({'msg': ['No data']})).mark_text().encode(text='msg:N')
        y_type = alt_type_from_dtype(df[y_key].dtype)
        base = alt.Chart(df)
        chart = base.mark_line(point=True).encode(
            x=alt.X(f'{x_key}:{x_type}', title=x_key),
            y=alt.Y(f'{y_key}:{y_type}', title=label_map.get(y_key, y_key)),
            tooltip=[x_key, y_key]
        )
        if title:
            chart = chart.properties(title=title)
        return chart

    # Multi-series: melt to long format
    use_cols = [x_key] + present_y_keys
    long_df = df[use_cols].melt(id_vars=[x_key], var_name='series', value_name='value')
    long_df['label'] = long_df['series'].map(lambda k: label_map.get(k, k))

    y_type = alt_type_from_dtype(long_df['value'].dtype)

    chart = alt.Chart(long_df).mark_line(point=True).encode(
        x=alt.X(f'{x_key}:{x_type}', title=x_key),
        y=alt.Y(f'value:{y_type}', title='Value'),
        color=alt.Color('label:N', title='Series'),
        tooltip=[x_key, 'label', 'value']
    )
    if title:
        chart = chart.properties(title=title)
    return chart


def build_bar_chart(df: pd.DataFrame, x_key: str, series: List[Dict[str, Any]], title: Optional[str] = None) -> alt.Chart:
    present_y_keys = [s.get('yKey') for s in series if s.get('yKey') in df.columns]
    label_map = {s.get('yKey'): s.get('name', s.get('yKey')) for s in series if s.get('yKey')}

    x_type = alt_type_from_dtype(df[x_key].dtype) if x_key in df.columns else 'N'

    if len(present_y_keys) <= 1:
        y_key = present_y_keys[0] if present_y_keys else None
        if y_key is None:
            return alt.Chart(pd.DataFrame({'msg': ['No data']})).mark_text().encode(text='msg:N')
        y_type = alt_type_from_dtype(df[y_key].dtype)
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X(f'{x_key}:{x_type}', title=x_key),
            y=alt.Y(f'{y_key}:{y_type}', title=label_map.get(y_key, y_key)),
            tooltip=[x_key, y_key]
        )
        if title:
            chart = chart.properties(title=title)
        return chart

    use_cols = [x_key] + present_y_keys
    long_df = df[use_cols].melt(id_vars=[x_key], var_name='series', value_name='value')
    long_df['label'] = long_df['series'].map(lambda k: label_map.get(k, k))

    y_type = alt_type_from_dtype(long_df['value'].dtype)

    chart = alt.Chart(long_df).mark_bar().encode(
        x=alt.X(f'{x_key}:{x_type}', title=x_key),
        y=alt.Y(f'value:{y_type}', title='Value'),
        color=alt.Color('label:N', title='Series'),
        tooltip=[x_key, 'label', 'value']
    )
    if title:
        chart = chart.properties(title=title)
    return chart


def build_area_chart(df: pd.DataFrame, x_key: str, series: List[Dict[str, Any]], title: Optional[str] = None) -> alt.Chart:
    present_y_keys = [s.get('yKey') for s in series if s.get('yKey') in df.columns]
    label_map = {s.get('yKey'): s.get('name', s.get('yKey')) for s in series if s.get('yKey')}
    x_type = alt_type_from_dtype(df[x_key].dtype) if x_key in df.columns else 'N'

    if len(present_y_keys) <= 1:
        y_key = present_y_keys[0] if present_y_keys else None
        if y_key is None:
            return alt.Chart(pd.DataFrame({'msg': ['No data']})).mark_text().encode(text='msg:N')
        y_type = alt_type_from_dtype(df[y_key].dtype)
        chart = alt.Chart(df).mark_area(point=True, line=True, opacity=0.6).encode(
            x=alt.X(f'{x_key}:{x_type}', title=x_key),
            y=alt.Y(f'{y_key}:{y_type}', title=label_map.get(y_key, y_key)),
            tooltip=[x_key, y_key]
        )
        if title:
            chart = chart.properties(title=title)
        return chart

    use_cols = [x_key] + present_y_keys
    long_df = df[use_cols].melt(id_vars=[x_key], var_name='series', value_name='value')
    long_df['label'] = long_df['series'].map(lambda k: label_map.get(k, k))
    y_type = alt_type_from_dtype(long_df['value'].dtype)
    chart = alt.Chart(long_df).mark_area(opacity=0.6).encode(
        x=alt.X(f'{x_key}:{x_type}', title=x_key),
        y=alt.Y(f'value:{y_type}', title='Value'),
        color=alt.Color('label:N', title='Series'),
        tooltip=[x_key, 'label', 'value']
    )
    if title:
        chart = chart.properties(title=title)
    return chart


def build_pie_chart(df: pd.DataFrame, category_key: str, value_key: str, title: Optional[str] = None) -> alt.Chart:
    # Pie charts are not part of this report, but supported for completeness.
    if category_key not in df.columns or value_key not in df.columns:
        return alt.Chart(pd.DataFrame({'msg': ['No data']})).mark_text().encode(text='msg:N')

    chart = alt.Chart(df).mark_arc().encode(
        theta=alt.Theta(field=value_key, type='quantitative'),
        color=alt.Color(field=category_key, type='nominal'),
        tooltip=[category_key, value_key]
    )
    if title:
        chart = chart.properties(title=title)
    return chart


def render_chart_from_spec(chart_spec: Dict[str, Any], df_source: pd.DataFrame) -> alt.Chart:
    ctype = (chart_spec or {}).get('type', 'line')
    spec = (chart_spec or {}).get('spec', {})
    x_key = spec.get('xKey')

    # Normalize series list
    series = spec.get('series', []) or []
    if not series and spec.get('yKey'):
        series = [{
            'name': spec.get('name', spec.get('yKey')),
            'yKey': spec.get('yKey')
        }]

    title = None
    # Attempt reasonable title
    if series:
        names = [s.get('name', s.get('yKey', '')) for s in series]
        title = ' & '.join([n for n in names if n])
        if x_key:
            title = f"{title} over {x_key}"

    if ctype == 'line':
        return build_line_chart(df_source, x_key, series, title)
    if ctype == 'bar':
        return build_bar_chart(df_source, x_key, series, title)
    if ctype == 'area':
        return build_area_chart(df_source, x_key, series, title)
    if ctype == 'pie':
        # For pie, expect xKey as category and first series yKey as value
        value_key = series[0].get('yKey') if series else None
        return build_pie_chart(df_source, x_key, value_key, title)

    # Fallback to line
    return build_line_chart(df_source, x_key, series, title)


# ------------------------------
# Render Summary
# ------------------------------
summary_points: List[str] = report.get('summary', [])
if summary_points:
    st.subheader('Summary')
    st.markdown('\n'.join([f'- {point}' for point in summary_points]))


# ------------------------------
# Render Tables
# ------------------------------
table_dfs: Dict[str, pd.DataFrame] = {}
all_tables = report.get('tables', []) or []
if all_tables:
    st.subheader('Tables')

for idx, table in enumerate(all_tables):
    name = table.get('name') or f'Table {idx + 1}'
    columns = table.get('columns', [])
    rows = table.get('rows', [])
    df = pd.DataFrame(rows, columns=columns)
    df = coerce_numeric_columns(df)
    table_dfs[name] = df

    st.markdown(f'**{name}**')
    st.dataframe(df, use_container_width=True)


# ------------------------------
# Render Charts with Altair
# ------------------------------
charts = report.get('charts', []) or []
if charts:
    st.subheader('Charts')

# Pick a default data source (first table)
default_df = next(iter(table_dfs.values())) if table_dfs else pd.DataFrame()

for chart_spec in charts:
    chart_id = chart_spec.get('id')
    # Render chart
    chart_obj = render_chart_from_spec(chart_spec, default_df)
    if chart_id:
        st.markdown(f'**Chart: {chart_id}**')
    st.altair_chart(chart_obj, use_container_width=True)


# ------------------------------
# Optional: Metadata
# ------------------------------
with st.expander('Report Metadata', expanded=False):
    st.write({
        'valid': report.get('valid'),
        'issues': report.get('issues'),
        'echo': report.get('echo')
    })
    st.caption('Raw JSON below:')
    st.code(report_json, language='json')
