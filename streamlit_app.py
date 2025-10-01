import json
from typing import Any, Dict, List, Optional, Union

import altair as alt
import pandas as pd
import streamlit as st


# ---------------------------
# Utility functions
# ---------------------------

def _ensure_dataframe(data: Any) -> Optional[pd.DataFrame]:
    """Convert various data representations into a pandas DataFrame when possible."""
    if data is None:
        return None

    # If it's already a DataFrame
    if isinstance(data, pd.DataFrame):
        return data

    # If the data is a dict with 'values' key (Vega-Lite style)
    if isinstance(data, dict) and 'values' in data:
        try:
            return pd.DataFrame(data['values'])
        except Exception:
            return None

    # If it's a list of dicts or list of lists
    if isinstance(data, list):
        try:
            # If list of dicts or homogeneous dict-like
            if len(data) == 0:
                return pd.DataFrame([])
            if isinstance(data[0], dict):
                return pd.DataFrame(data)
            # If list of lists, we will try to build a DF directly
            return pd.DataFrame(data)
        except Exception:
            return None

    # If it's a plain dict (mapping of columns to lists)
    if isinstance(data, dict):
        try:
            return pd.DataFrame(data)
        except Exception:
            return None

    return None


def _encode_channel(channel_name: str, value: Any, dtype: Optional[str] = None, **kwargs):
    """Create an Altair encoding channel from value. Value can be a string (field name) or a dict of Vega-Lite field definition."""
    # Map channel name to Altair class constructors
    constructors = {
        'x': alt.X,
        'y': alt.Y,
        'x2': alt.X2,
        'y2': alt.Y2,
        'color': alt.Color,
        'size': alt.Size,
        'shape': alt.Shape,
        'theta': alt.Theta,
        'radius': alt.Radius,
        'opacity': alt.Opacity,
        'tooltip': alt.Tooltip,
        'order': alt.Order,
        'detail': alt.Detail,
        'column': alt.Column,
        'row': alt.Row,
    }
    ctor = constructors.get(channel_name)
    if ctor is None:
        return None

    try:
        if isinstance(value, dict):
            return ctor(**value)
        if dtype:
            return ctor(value, type=dtype, **kwargs)
        return ctor(value, **kwargs)
    except Exception:
        # Fallback: return None to skip this channel
        return None


def build_altair_chart(chart_def: Dict[str, Any]) -> Optional[alt.Chart]:
    """Build an Altair chart from a simple chart definition.

    Supported keys in chart_def:
      - type: one of ['bar','line','area','scatter','pie','tick','point']
      - title: str
      - data: list[dict] | dict(values=...) | pandas.DataFrame
      - width, height: int (optional)
      - mark: dict for custom mark options (optional)
      - x, y, x2, y2, theta, radius, color, size, opacity, tooltip, order, detail, column, row
        Each channel can be either a string field name, or a dict specifying a Vega-Lite fieldDef.
      - x_type, y_type, theta_type, radius_type, color_type, size_type ... (for simple type hints)
      - aggregate, stack, sort, timeUnit etc can be included as part of the channel dict if using dict style.
      - spec: full Vega-Lite JSON spec (optional). If provided, will try to render from spec. If both spec and data
        are provided, data will be injected into the spec if spec lacks data.
    """
    if not isinstance(chart_def, dict):
        return None

    # If a full Vega-Lite spec is provided
    spec = chart_def.get('spec')
    if isinstance(spec, dict):
        # Attempt to inject data if present externally
        data = chart_def.get('data')
        if data is not None:
            df = _ensure_dataframe(data)
            if df is not None:
                spec = dict(spec)  # shallow copy
                # Replace or provide inline values
                if 'data' not in spec or not isinstance(spec['data'], dict):
                    spec['data'] = {'values': df.to_dict(orient='records')}
                else:
                    spec['data'] = {'values': df.to_dict(orient='records')}
        try:
            return alt.Chart.from_dict(spec)
        except Exception:
            pass  # Fall through to manual build

    # Manual build
    df = _ensure_dataframe(chart_def.get('data'))
    if df is None:
        return None

    title = chart_def.get('title')
    width = chart_def.get('width')
    height = chart_def.get('height')

    base = alt.Chart(df, title=title)

    ctype = (chart_def.get('type') or '').lower()
    mark_kwargs = chart_def.get('mark', {}) if isinstance(chart_def.get('mark'), dict) else {}

    if ctype in ['bar', 'bar_chart', 'stacked_bar']:
        chart = base.mark_bar(**mark_kwargs)
    elif ctype in ['line', 'line_chart']:
        chart = base.mark_line(**mark_kwargs)
    elif ctype in ['area', 'area_chart']:
        chart = base.mark_area(**mark_kwargs)
    elif ctype in ['scatter', 'point']:
        chart = base.mark_circle(**mark_kwargs)
    elif ctype in ['pie']:
        # Pie charts use mark_arc and theta/color encodings
        chart = base.mark_arc(**mark_kwargs)
    elif ctype in ['tick']:
        chart = base.mark_tick(**mark_kwargs)
    else:
        # Default to bar if unknown
        chart = base.mark_bar(**mark_kwargs)

    # Build encodings
    encodings = {}
    channel_types = {
        'x': chart_def.get('x_type'),
        'y': chart_def.get('y_type'),
        'x2': chart_def.get('x2_type'),
        'y2': chart_def.get('y2_type'),
        'theta': chart_def.get('theta_type'),
        'radius': chart_def.get('radius_type'),
        'color': chart_def.get('color_type'),
        'size': chart_def.get('size_type'),
        'opacity': chart_def.get('opacity_type'),
        'order': chart_def.get('order_type'),
        'detail': chart_def.get('detail_type'),
        'tooltip': chart_def.get('tooltip_type'),
        'column': chart_def.get('column_type'),
        'row': chart_def.get('row_type'),
    }

    for channel in ['x','y','x2','y2','theta','radius','color','size','opacity','order','detail','tooltip','column','row']:
        val = chart_def.get(channel)
        if val is not None:
            enc = _encode_channel(channel, val, dtype=channel_types.get(channel))
            if enc is not None:
                encodings[channel] = enc

    if encodings:
        try:
            chart = chart.encode(**encodings)
        except Exception:
            # graceful fallback without encodings if something went wrong
            pass

    if width:
        chart = chart.properties(width=width)
    if height:
        chart = chart.properties(height=height)

    if chart_def.get('interactive', True):
        chart = chart.interactive()

    return chart


def render_summary(report: Dict[str, Any]):
    summary = report.get('summary')
    if summary:
        st.markdown("## Summary")
        if isinstance(summary, list):
            for para in summary:
                if isinstance(para, str):
                    st.markdown(para)
        elif isinstance(summary, str):
            st.markdown(summary)


def render_tables(tables: List[Dict[str, Any]]):
    for idx, tbl in enumerate(tables):
        title = tbl.get('title') or f"Table {idx+1}"
        data = tbl.get('data')
        df = _ensure_dataframe(data)
        st.markdown(f"### {title}")
        if df is not None:
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("Unable to render table: invalid data format.")


def render_charts(charts: List[Dict[str, Any]]):
    for idx, ch in enumerate(charts):
        title = ch.get('title')
        if title:
            st.markdown(f"### {title}")
        chart_obj = build_altair_chart(ch)
        if chart_obj is not None:
            st.altair_chart(chart_obj, use_container_width=True)
        else:
            st.warning("Unable to render chart: invalid specification or data.")


def render_sections(sections: List[Dict[str, Any]]):
    for i, sec in enumerate(sections):
        sec_title = sec.get('title') or f"Section {i+1}"
        st.markdown(f"## {sec_title}")
        if sec.get('summary'):
            if isinstance(sec['summary'], list):
                for para in sec['summary']:
                    if isinstance(para, str):
                        st.markdown(para)
            elif isinstance(sec['summary'], str):
                st.markdown(sec['summary'])

        if isinstance(sec.get('tables'), list) and sec['tables']:
            render_tables(sec['tables'])
        if isinstance(sec.get('charts'), list) and sec['charts']:
            render_charts(sec['charts'])


# ---------------------------
# Chat widget
# ---------------------------

def _summarize_context_for_ai(context: Dict[str, Any], limit_chars: int = 600) -> str:
    parts = []
    try:
        if context.get('summary'):
            if isinstance(context['summary'], str):
                parts.append(context['summary'])
            elif isinstance(context['summary'], list):
                parts.append(" ".join([p for p in context['summary'] if isinstance(p, str)]))
        # Add table titles
        tbls = context.get('tables') or []
        if isinstance(tbls, list) and tbls:
            parts.append("Tables: " + ", ".join([t.get('title','Table') for t in tbls if isinstance(t, dict)]))
        # Add chart titles
        chs = context.get('charts') or []
        if isinstance(chs, list) and chs:
            parts.append("Charts: " + ", ".join([c.get('title','Chart') for c in chs if isinstance(c, dict)]))
    except Exception:
        pass
    joined = " | ".join([p for p in parts if isinstance(p, str) and p.strip()])
    return (joined[:limit_chars] + ('…' if len(joined) > limit_chars else '')) if joined else "(no summary available)"


def _generate_ai_reply(user_msg: str, context: Dict[str, Any], system_hint: str) -> str:
    """A simple, local heuristic reply generator that references the context. No external AI calls."""
    user_lower = (user_msg or '').lower()
    ctx_summary = _summarize_context_for_ai(context)

    # Heuristic intents
    if any(k in user_lower for k in ['summary', 'summarize', 'overview']):
        return f"Here is a brief overview based on the report: {ctx_summary}"

    if any(k in user_lower for k in ['table', 'tables']):
        tables = context.get('tables') or []
        if isinstance(tables, list) and tables:
            names = [t.get('title','Table') for t in tables if isinstance(t, dict)]
            return f"The report contains {len(names)} table(s): " + ", ".join(names)
        return "I couldn't find any tables in the current report."

    if any(k in user_lower for k in ['chart', 'charts', 'plot', 'graph']):
        charts = context.get('charts') or []
        if isinstance(charts, list) and charts:
            names = [c.get('title','Chart') for c in charts if isinstance(c, dict)]
            return f"The report includes {len(names)} chart(s): " + ", ".join(names)
        return "I couldn't find any charts in the current report."

    if 'help' in user_lower or 'how' in user_lower:
        return (
            "You can ask me to summarize the report, list tables or charts, "
            "or explain specific fields. If you paste a JSON report, I'll use it as context."
        )

    # Default echo with context prompt
    return (
        f"You said: '{user_msg}'. Based on the report context, here's a quick note: {ctx_summary}"
    )


def render_chat_widget(title: str, system_hint: str, context: Dict[str, Any], sidebar: bool = True):
    """Render a minimal chat UI in the sidebar (right side not natively supported in Streamlit; sidebar is left by default).
    This widget is local-only and does not call external LLMs.
    """
    target = st.sidebar if sidebar else st

    with target:
        st.markdown(f"## {title}")
        with st.expander("Context (report) preview", expanded=False):
            try:
                st.json(context if context else {})
            except Exception:
                st.write("(invalid context)")

        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []  # list of {role, content}

        # Display history
        if st.session_state.chat_history:
            for msg in st.session_state.chat_history:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                prefix = '🧑' if role == 'user' else '🤖'
                st.markdown(f"{prefix} {content}")

        # Input form (kept simple to work inside sidebar)
        with st.form(key="ai_analyst_form", clear_on_submit=True):
            user_input = st.text_input("Ask about this report", value="")
            submitted = st.form_submit_button("Send")
        if submitted and user_input.strip():
            st.session_state.chat_history.append({"role": "user", "content": user_input.strip()})
            reply = _generate_ai_reply(user_input.strip(), context or {}, system_hint)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            st.experimental_rerun()


# ---------------------------
# Main app
# ---------------------------

def parse_report_json_text(text: str) -> Optional[Dict[str, Any]]:
    if not text or not text.strip():
        return None
    try:
        return json.loads(text)
    except Exception as e:
        st.error(f"Failed to parse JSON: {e}")
        return None


def main():
    st.set_page_config(page_title="AI Report Viewer", layout="wide", initial_sidebar_state="expanded")
    st.title("AI Report Viewer")
    st.caption("Load a JSON report to view its summary, tables, and charts. A local AI assistant is available in the sidebar.")

    # Report loader UI
    with st.expander("Load Report JSON", expanded=True):
        uploaded = st.file_uploader("Upload a JSON file", type=["json"]) 
        pasted_text = st.text_area("Or paste JSON here", value="", height=180)
        load_col1, load_col2 = st.columns([1,1])
        with load_col1:
            parse_btn = st.button("Parse JSON")
        with load_col2:
            clear_btn = st.button("Clear")

    report: Dict[str, Any] = {}
    if clear_btn:
        st.session_state.pop('loaded_report', None)

    # Prioritize explicit parse action to avoid accidental partial parses
    if parse_btn:
        parsed: Optional[Dict[str, Any]] = None
        if uploaded is not None:
            try:
                parsed = json.load(uploaded)
            except Exception as e:
                st.error(f"Failed to load uploaded JSON: {e}")
        if parsed is None and pasted_text.strip():
            parsed = parse_report_json_text(pasted_text)
        if parsed is not None:
            st.session_state['loaded_report'] = parsed

    # If nothing parsed this session, still attempt to parse pasted text for convenience
    if 'loaded_report' not in st.session_state and pasted_text.strip() and not parse_btn:
        tentative = parse_report_json_text(pasted_text)
        if tentative is not None:
            st.session_state['loaded_report'] = tentative

    if 'loaded_report' in st.session_state and isinstance(st.session_state['loaded_report'], dict):
        report = st.session_state['loaded_report']

    # Render the chat widget in sidebar with the report context
    render_chat_widget(
        title="💬 AI Analyst",
        system_hint="You are a data analyst AI. Use context when helpful.",
        context=report,
        sidebar=True,
    )

    # If no report, show instructions
    if not report:
        st.info("No report loaded yet. Upload a JSON file or paste JSON to render.")
        return

    # Render summary
    render_summary(report)

    # Render top-level tables and charts
    if isinstance(report.get('tables'), list) and report['tables']:
        st.markdown("## Tables")
        render_tables(report['tables'])

    if isinstance(report.get('charts'), list) and report['charts']:
        st.markdown("## Charts")
        render_charts(report['charts'])

    # Render sections if present
    if isinstance(report.get('sections'), list) and report['sections']:
        render_sections(report['sections'])

    # Raw JSON (optional view)
    with st.expander("Raw JSON", expanded=False):
        st.json(report)


if __name__ == "__main__":
    main()
