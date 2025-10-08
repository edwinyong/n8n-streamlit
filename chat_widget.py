# chat_widget.py
import time
import datetime as _dt
import requests
import streamlit as st
from typing import Any, Dict, List, Optional

DEFAULT_WEBHOOK = "https://d-target-sb.d-rive.click/webhook/ai-data-analysis-v3"
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
    # --- NEW: preset composer ---
    enable_presets: bool = True,
    date_mode: str = "range",  # "range" or "single"
    presets: Optional[List[Dict[str, str]]] = None,
):
    """
    Modern, card-styled chat widget with a toggle to show/hide.
    Adds a preset composer with a date picker on the right (single/range).
    Pure Streamlit (no custom components). Backward compatible with older Streamlit.
    """
    _init_state(default_open)

        # ----- presets default -----
    if presets is None:
        presets = [
            {
                "label": "Weekly performance by brand",
                "template": (
                    "Generate weekly performance including buyers purchases total sales and total units grouped by Brand "
                    "using Upload_Date for the weekly bucket from the table Haleon_Rewards_User_Performance_110925_SKUs."
                ),
            },
            {
                "label": "Overall totals",
                "template": (
                    "Compute overall totals including purchases counted as distinct receiptid total sales as the sum of Total Sales Amount "
                    "total units as the sum of Total_Purchase_Units and buyers as the unique count of comuserid from the table Haleon_Rewards_User_Performance_110925_SKUs."
                ),
            },
            {
                "label": "Monthly sales and units by brand",
                "template": (
                    "Show monthly totals grouped by Brand using Upload_Date for the month bucket including purchases total sales total units and buyers "
                    "from the table Haleon_Rewards_User_Performance_110925_SKUs."
                ),
            },
            {
                "label": "Top 10 brands by total sales",
                "template": (
                    "Return the top 10 brands ordered by total sales calculated as the sum of Total Sales Amount "
                    "from the table Haleon_Rewards_User_Performance_110925_SKUs."
                ),
            },
        ]


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

    # Keys for composer state
    _today = _dt.date.today()
    preset_key = "chat_preset_label"
    composer_key = "chat_preset_text"
    date_key = "chat_preset_date"

    # Initialize composer defaults if missing
    if composer_key not in st.session_state:
        st.session_state[composer_key] = presets[0]["template"]
    if date_key not in st.session_state:
        if date_mode == "range":
            st.session_state[date_key] = (_today, _today)
        else:
            st.session_state[date_key] = _today

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

        # ---------- PRESET COMPOSER (left) + DATE PICKER (right) ----------
        if enable_presets:
            c_left, c_right = st.columns([3, 2], gap="large")
            with c_left:
                st.caption("Preset")
                def _apply_preset():
                    label = st.session_state.get(preset_key)
                    tmpl = next((p["template"] for p in presets if p["label"] == label), "")
                    st.session_state[composer_key] = tmpl

                st.selectbox(
                    "Choose a preset",
                    options=[p["label"] for p in presets],
                    key=preset_key,
                    index=0,
                    on_change=_apply_preset,
                )
                st.text_area(
                    "Message to send",
                    key=composer_key,
                    value=st.session_state[composer_key],
                    height=130,
                )
            with c_right:
                st.caption("Date filter")
                if date_mode == "range":
                    dr = st.date_input(
                        "Date range",
                        value=st.session_state[date_key],  # (start, end)
                        key=date_key,
                    )
                else:
                    dr = st.date_input(
                        "Date",
                        value=st.session_state[date_key],  # single date
                        key=date_key,
                    )

            # submit preset query
            submit_cols = st.columns([1, 6])
            with submit_cols[0]:
                send_preset = st.button("Apply & Ask", type="primary", use_container_width=True)
            with submit_cols[1]:
                st.caption("Fill message and optionally set date(s), then click send.")

            if send_preset:
                # Build message from preset + date(s) as plain sentences (no quotes/backticks)
                base_msg = (st.session_state.get(composer_key) or "").strip()
                if date_mode == "range":
                    try:
                        start, end = st.session_state.get(date_key, (_today, _today))
                    except Exception:
                        start, end = _today, _today
                    date_clause = f" This request is for the period from {start} to {end}."
                else:
                    the_date = st.session_state.get(date_key, _today)
                    date_clause = f" This request is for the date {the_date}."
                composed = (base_msg + date_clause).strip()

                # Echo and send via the same pipeline as chat input
                st.session_state[SESSION_HISTORY_KEY].append({"role": "user", "content": composed})
                _render_msg(st, "user", composed)

                # Payload
                payload: Dict[str, Any] = {
                    "message": composed,
                    "history": st.session_state[SESSION_HISTORY_KEY],
                    "system": system_hint,
                    "source": "streamlit",
                }
                if context is not None:
                    payload["context"] = context

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
                            for k in ("reply", "message", "text"):
                                v = data.get(k)
                                if isinstance(v, str) and v.strip():
                                    reply_txt = v.strip()
                                    break
                            if not reply_txt:
                                reply_txt = "(No reply)"

                            placeholder.markdown(reply_txt)

                            suggestions = data.get("suggestions")
                            if isinstance(suggestions, list) and suggestions:
                                st.caption("Try:")
                                for s in suggestions[:5]:
                                    if isinstance(s, str):
                                        st.code(s)
                        except Exception as e:
                            reply_txt = f"Error: {e}"
                            placeholder.error(reply_txt)

                st.session_state[SESSION_HISTORY_KEY].append({"role": "assistant", "content": reply_txt})

                # Cap history size
                if len(st.session_state[SESSION_HISTORY_KEY]) > max_history:
                    st.session_state[SESSION_HISTORY_KEY] = st.session_state[SESSION_HISTORY_KEY][-max_history:]

                # After sending preset, add a divider before message history
                st.divider()

        # ---------- MESSAGES ----------
        history = st.session_state.get(SESSION_HISTORY_KEY, [])
        if not history:
            st.info("Say hello to start the conversation.")

        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content") or ""
            _render_msg(st, role, content)

        st.divider()

        # ---------- FOLLOW-UP INPUT ----------
        prompt = _get_input(st, "Type a message…", key="chat_prompt")
        right_cols = st.columns([6, 1, 1])
        with right_cols[1]:
            st.button("Send", use_container_width=True, disabled=True, help="Use the input to send")
        with right_cols[2]:
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
                    for k in ("reply", "message", "text"):
                        v = data.get(k)
                        if isinstance(v, str) and v.strip():
                            reply_txt = v.strip()
                            break
                    if not reply_txt:
                        reply_txt = "(No reply)"

                    placeholder.markdown(reply_txt)

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
