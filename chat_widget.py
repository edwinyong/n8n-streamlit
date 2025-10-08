# chat_widget.py
import time
import requests
import streamlit as st
from typing import Any, Dict, List, Optional

DEFAULT_WEBHOOK = "https://d-target-sb.d-rive.click/webhook/ai-data-analysis-v2"
SESSION_HISTORY_KEY = "chat_history"
SESSION_OPEN_KEY = "chat_open"

# ---------------------------
# Compatibility shims (old Streamlit)
# ---------------------------
_HAS_CHAT_MESSAGE = hasattr(st, "chat_message")
_HAS_CHAT_INPUT = hasattr(st, "chat_input")

def _render_msg(ui, role: str, content: str):
    role_norm = "assistant" if role == "assistant" else "user"
    if _HAS_CHAT_MESSAGE:
        with ui.chat_message(role_norm):
            ui.markdown(content)
    else:
        who = "Assistant" if role_norm == "assistant" else "You"
        ui.markdown(f"**{who}:** {content}")

def _get_input(ui, placeholder: str, key: str) -> Optional[str]:
    if _HAS_CHAT_INPUT:
        return ui.chat_input(placeholder, key=key)
    with ui.form(key=f"{key}__form", clear_on_submit=True):
        txt = ui.text_input(placeholder, key=f"{key}__txt")
        sent = ui.form_submit_button("Send")
    return txt.strip() if sent and isinstance(txt, str) and txt.strip() else None

# ---------------------------
# HTTP helper
# ---------------------------
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

# ---------------------------
# Session/state helpers
# ---------------------------
def _init_state(default_open: bool):
    # Ensure history is a list of {role, content}
    hist = st.session_state.get(SESSION_HISTORY_KEY)
    if not isinstance(hist, list):
        st.session_state[SESSION_HISTORY_KEY] = []
    else:
        st.session_state[SESSION_HISTORY_KEY] = [
            m for m in hist if isinstance(m, dict) and "role" in m and "content" in m
        ]
    if SESSION_OPEN_KEY not in st.session_state:
        st.session_state[SESSION_OPEN_KEY] = default_open

def _badge(label: str, live: bool = True):
    dot = "🟢" if live else "🔵"
    st.caption(f"{dot} {label}")

# ---------------------------
# Main widget
# ---------------------------
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
    max_history: int = 40,
):
    """
    Modern, card-styled chat widget with a toggle to show/hide.
    Pure Streamlit (no custom components). Backward compatible with older Streamlit.
    """
    _init_state(default_open)

    # Optional extra toggle in sidebar
    if show_on_sidebar_toggle:
        with st.sidebar:
            st.toggle("Open chat", key=SESSION_OPEN_KEY)

    # Top toggle button (circle, icon-only)
    left, mid, right = st.columns([1, 6, 2])
    with left:
        btn_label = "💬" if not st.session_state[SESSION_OPEN_KEY] else "➖"
        st.button(
            btn_label,
            key="chat_toggle_btn",
            help="Open/Hide chat",
            use_container_width=True,
            on_click=lambda: st.session_state.update(
                {SESSION_OPEN_KEY: not st.session_state[SESSION_OPEN_KEY]}
            ),
        )
    with mid:
        st.write("")  # spacer
    with right:
        pass

    # Collapsed → return early
    if not st.session_state[SESSION_OPEN_KEY]:
        return

    # Card container
    with st.container(border=True):
        # Header
        top = st.columns([0.6, 5, 1])
        with top[0]:
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

        # Messages (safe history access)
        history = st.session_state.get(SESSION_HISTORY_KEY, [])
        if not history:
            st.info("Say hello to start the conversation.")

        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content") or ""
            _render_msg(st, role, content)

        st.divider()

        # Input + Clear
        cols = st.columns([6, 1, 1])
        with cols[0]:
            prompt = _get_input(st, "Type a message…", key="chat_prompt")
        with cols[1]:
            st.button("Send", use_container_width=True, disabled=True, help="Use the input to send")
        with cols[2]:
            if clear_button and st.button("Clear", type="secondary", use_container_width=True):
                st.session_state[SESSION_HISTORY_KEY] = []
                st.rerun()

        if not prompt:
            # keep history cap
            if len(st.session_state[SESSION_HISTORY_KEY]) > max_history:
                st.session_state[SESSION_HISTORY_KEY] = st.session_state[SESSION_HISTORY_KEY][-max_history:]
            return

        # Append user message
        st.session_state[SESSION_HISTORY_KEY].append({"role": "user", "content": prompt})
        _render_msg(st, "user", prompt)

        # Payload
        payload: Dict[str, Any] = {
            "message": prompt,
            "history": st.session_state[SESSION_HISTORY_KEY],
            "system": system_hint,
            "source": "streamlit",
        }
        if context is not None:
            payload["context"] = context

        # Call webhook
        with (st.chat_message("assistant") if _HAS_CHAT_MESSAGE else st.container()):
            placeholder = st.empty()
            with st.spinner("Thinking…"):
                try:
                    resp = _post_with_retry(webhook_url, payload, timeout=60)
                    try:
                        data = resp.json()
                    except Exception:
                        data = {"reply": resp.text}

                    reply_txt = None
                    # Safely pick a string reply
                    for k in ("reply", "message", "text"):
                        v = data.get(k)
                        if isinstance(v, str) and v.strip():
                            reply_txt = v.strip()
                            break
                    if not reply_txt:
                        reply_txt = "(No reply)"

                    placeholder.markdown(reply_txt)

                    # Optional suggestions
                    suggestions = data.get("suggestions")
                    if isinstance(suggestions, list) and suggestions:
                        st.caption("Try:")
                        for s in suggestions[:5]:
                            if isinstance(s, str):
                                st.code(s)

                except Exception as e:
                    reply_txt = f"Error: {e}"
                    placeholder.error(reply_txt)

        # Persist assistant reply
        st.session_state[SESSION_HISTORY_KEY].append({"role": "assistant", "content": reply_txt})

        # Cap history size
        if len(st.session_state[SESSION_HISTORY_KEY]) > max_history:
            st.session_state[SESSION_HISTORY_KEY] = st.session_state[SESSION_HISTORY_KEY][-max_history:]
