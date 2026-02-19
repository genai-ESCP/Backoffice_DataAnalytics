import hashlib
import hmac
import time

import streamlit as st

AUTH_USER = "genai@escp.eu"
PBKDF2_ITERATIONS = 210000
SALT_HEX = "775e8070c10ed3b1d7d0665e34f0435a"
PASSWORD_HASH_HEX = "b7649b02e4159edc4c885d7d0b19ddfc973c143526fe6cdfac64acfcbfbe0573"

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 180


def _hash_password(password: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(SALT_HEX),
        PBKDF2_ITERATIONS,
    )
    return digest.hex()


def _verify_password(password: str) -> bool:
    submitted = _hash_password(password)
    return hmac.compare_digest(submitted, PASSWORD_HASH_HEX)


def is_authenticated() -> bool:
    return bool(st.session_state.get("auth_ok", False))


def logout() -> None:
    st.session_state["auth_ok"] = False
    st.session_state["auth_user"] = ""


def require_auth() -> None:
    if is_authenticated():
        return

    now = time.time()
    lock_until = float(st.session_state.get("auth_lock_until", 0.0))
    failed_attempts = int(st.session_state.get("auth_failed_attempts", 0))

    st.markdown("# Login")
    st.markdown(
        '<div class="small-muted">Authentication required to access this dashboard.</div>',
        unsafe_allow_html=True,
    )

    if lock_until > now:
        remaining = int(lock_until - now)
        st.error(f"Too many failed attempts. Try again in {remaining} seconds.")
        st.stop()

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Email", placeholder="JohnSmith@escp.eu")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        user_ok = username.strip().lower() == AUTH_USER
        pass_ok = _verify_password(password or "")
        if user_ok and pass_ok:
            st.session_state["auth_ok"] = True
            st.session_state["auth_user"] = AUTH_USER
            st.session_state["auth_failed_attempts"] = 0
            st.session_state["auth_lock_until"] = 0.0
            st.rerun()
        else:
            failed_attempts += 1
            st.session_state["auth_failed_attempts"] = failed_attempts
            if failed_attempts >= MAX_FAILED_ATTEMPTS:
                st.session_state["auth_lock_until"] = now + LOCKOUT_SECONDS
                st.error("Too many failed attempts. Login is temporarily locked.")
            else:
                left = MAX_FAILED_ATTEMPTS - failed_attempts
                st.error(f"Invalid credentials. Attempts left: {left}")

    st.stop()
