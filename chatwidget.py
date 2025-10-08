# chat_widget.py
import time
import requests
import streamlit as st
from typing import Any, Dict, List, Optional

DEFAULT_WEBHOOK = "https://d-target-sb.d-rive.click/webhook/ai-data-analysis-v2"
SESSION_HISTORY_KEY = "chat_history"
SESSION_OPEN_KEY = "chat_open"

def _post_with_retry(
    url: str,
    json_body: Dict[str, Any],
    timeout: float = 30,
    retries: int = 2,
    backoff: float = 1.5,
):
    """Send POST request with simple retry/backoff."""
    err = None
    for attempt in range(retries + 1):
        try:
            r = requests.post(url, json=json_body, timeout=timeout)
            if 200 <= r.status_code < 300:
                return r
            err = RuntimeError(f"HTTP {r.status_code}: {r.text}")
        except Exception as e:
            err = e
        time.sleep(backoff ** (attempt + 1))
    raise err if err else RuntimeError("Unknown request error")


def _init_state(default_open: bool):
    if SESSION_HISTORY_KEY not in st.session_state:
        st.session_state[SESSION_HISTORY_KEY]: List[Dict[str, str]] = []
    if SESSION_OPEN_KEY not in st.session_state:
        st.session_state[SESSION_OPEN_KEY] = default_open


def _badge(label: str, live: bool = True):
    """Small status badge using native Streamlit text & emojis."""
    dot = "🟢" if live else "🔵"
    st.caption(f"{dot} {label}")


def render_chat_widget_modern(
    *,
    webhook_url: str = DEFAULT_WEBHOOK,
    title: str = "TDG Assistant",
    subtitle: str = "Agent chat",
    status: str = "Live",
    live: bool = True,
    system_hint: str = "You are a helpful assistant for CRM, loyalty, data, and engineering tasks.",
    context: Optional[Dict[str, Any]] = None,
    default_open: bool = False,
    show_on_sidebar_toggle: bool = False,
    clear_button: bool = True,
):
    """
    Modern, card-styled chat widget with a toggle to show/hide.

    - Pure Streamlit (no custom HTML).
    - Uses st.container(border=True) to render a card-like block.
    - Toggle open/close via a button.
    - Persists history in st.session_state.
    """
    _init_state(default_open)

    # Optional extra toggle in sidebar
    if show_on_sidebar_toggle:
        with st.sidebar:
            st.toggle("Open chat", key=SESSION_OPEN_KEY)

    # Header row (top of the page) with open/close button
    head_left, head_mid, head_right = st.columns([1, 6, 2])
    with head_left:
        st.button(
            "💬 Open chat" if not st.session_state[SESSION_OPEN_KEY] else "➖ Hide chat",
            key="chat_toggle_btn",
            use_container_width=True,
            on_click=lambda: st.session_state.update({SESSION_OPEN_KEY: not st.session_state[SESSION_OPEN_KEY]})
        )
    with head_mid:
        st.write("")  # spacer
    with head_right:
        pass

    if not st.session_state[SESSION_OPEN_KEY]:
        return  # collapsed; nothing else to render

    # Card container (modern look using Streamlit's bordered container)
    with st.container(border=True):
        # Header bar
        top = st.columns([0.6, 5, 1])
        with top[0]:
            # Icon box
            st.markdown("### ✨")
        with top[1]:
            st.subheader(title, anchor=False)
            row = st.columns([3, 3])
            with row[0]:
                st.caption(subtitle)
            with row[1]:
                _badge(status, live=live)
        with top[2]:
            st.button("⚙️", help="Agent settings", use_container_width=True)

        st.divider()

        # Messages
        history: List[Dict[str, str]] = st.session_state[SESSION_HISTORY_KEY]
        if not history:
            st.info("Say hello to start the conversation.")

        for i, msg in enumerate(history):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            with st.chat_message(role):
                st.markdown(content)

        st.divider()

        # Input row
        input_cols = st.columns([6, 1, 1])
        with input_cols[0]:
            prompt = st.chat_input("Type a message…")
        with input_cols[1]:
            send_clicked = st.button("Send", use_container_width=True, disabled=True, help="Use the chat box to send")
        with input_cols[2]:
            if clear_button and st.button("Clear", type="secondary", use_container_width=True):
                st.session_state[SESSION_HISTORY_KEY] = []
                st.rerun()

        # Handle message send
        if prompt:
            # Add user message
            st.session_state[SESSION_HISTORY_KEY].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Prepare payload
            payload: Dict[str, Any] = {
                "message": prompt,
                "history": st.session_state[SESSION_HISTORY_KEY],
                "system": system_hint,
                "source": "streamlit",
            }
            if context:
                payload["context"] = context

            # Call webhook
            with st.chat_message("assistant"):
                placeholder = st.empty()
                with st.spinner("Thinking…"):
                    try:
                        resp = _post_with_retry(webhook_url, payload, timeout=60)
                        try:
                            data = resp.json()
                        except Exception:
                            data = {"reply": resp.text}

                        reply_txt = (
                            data.get("reply")
                            or data.get("message")
                            or data.get("text")
                            or "(No reply)"
                        )

                        placeholder.markdown(reply_txt)

                        # Optional suggestions
                        if isinstance(data.get("suggestions"), list) and data["suggestions"]:
                            st.caption("Try:")
                            for s in data["suggestions"][:5]:
                                st.code(s)

                    except Exception as e:
                        reply_txt = f"Error: {e}"
                        placeholder.error(reply_txt)

            # Persist assistant reply
            st.session_state[SESSION_HISTORY_KEY].append({"role": "assistant", "content": reply_txt})
