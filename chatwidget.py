# chat_widget.py
import time
import json
import requests
import streamlit as st
from typing import Any, Dict, List, Optional

# default webhook
DEFAULT_WEBHOOK = "https://d-target-sb.d-rive.click/webhook/ai-data-analysis-streamlit"


def _post_with_retry(
    url: str, json_body: Dict[str, Any], timeout: float = 30, retries: int = 2, backoff: float = 1.5
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


def render_chat_widget(
    webhook_url: str = DEFAULT_WEBHOOK,
    *,
    title: str = "💬 Ask the AI",
    system_hint: str = "You are a helpful assistant.",
    context: Optional[Dict[str, Any]] = None,
    sidebar: bool = False,
):
    """
    Renders a chat widget in Streamlit that connects to an n8n webhook.

    Args:
        webhook_url: Target webhook URL (n8n).
        title: Header title.
        system_hint: Instruction sent with each payload.
        context: Optional dict with extra context (e.g., summary/tables).
        sidebar: Place chat in sidebar if True.
    """
    if "chat_history" not in st.session_state:
        st.session_state.chat_history: List[Dict[str, str]] = []

    container = st.sidebar if sidebar else st
    container.header(title)

    # render history
    for msg in st.session_state.chat_history:
        role = msg.get("role", "user")
        with container.chat_message(role):
            container.markdown(msg.get("content", ""))

    # chat input
    prompt = container.chat_input("Type your question…")
    if not prompt:
        return

    # append user message
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with container.chat_message("user"):
        container.markdown(prompt)

    # build payload
    payload: Dict[str, Any] = {
        "message": prompt,
        "history": st.session_state.chat_history,
        "system": system_hint,
        "source": "streamlit",
    }
    if context:
        payload["context"] = context

    # send request
    with container.chat_message("assistant"):
        placeholder = container.empty()
        with container.spinner("Thinking…"):
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

                # optional suggestions
                if isinstance(data.get("suggestions"), list):
                    container.caption("Try:")
                    for s in data["suggestions"][:5]:
                        container.code(s)

            except Exception as e:
                reply_txt = f"Error: {e}"
                placeholder.error(reply_txt)

    st.session_state.chat_history.append({"role": "assistant", "content": reply_txt})
