import streamlit as st
from streamlit_app import render_app
from chat_widget import render_chat_widget_modern

st.set_page_config(page_title="TDG Assistant", layout="wide")

# Main content
render_app()

# Modern chat widget (toggle to show/hide)
render_chat_widget_modern(
    webhook_url="https://d-target-sb.d-rive.click/webhook/ai-data-analysis-v3",
    title="✨ TDG Assistant",
    subtitle="Agent chat",
    status="Live",
    live=True,
    system_hint="You are a helpful assistant for CRM, loyalty, data, and engineering tasks.",
    context={"app": "TDG Streamlit"},
    default_open=False,            # closed by default; click 'Open chat' to show
    show_on_sidebar_toggle=False,  # set True if you want an extra sidebar toggle
    clear_button=True,
)
