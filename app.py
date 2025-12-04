import streamlit as st
import re
from auth import login, signup

st.set_page_config(page_title="Login | Signup", layout="centered")

# ----------------- Initialize session -----------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user" not in st.session_state:
    st.session_state["user"] = None


# ----------------- Email Validation -----------------
def is_valid_email(email: str) -> (bool, str):
    """Allow only specific email domains."""

    # Basic email format check
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(pattern, email):
        return False, "Invalid email format."

    ALLOWED_DOMAINS = {
        "gmail.com",
        "outlook.com",
        "yahoo.com",
        "hotmail.com",
        "protonmail.com"
    }

    domain = email.split("@")[-1].lower()

    if domain not in ALLOWED_DOMAINS:
        return False, f"Email domain '{domain}' is not allowed. Allowed domains: {', '.join(ALLOWED_DOMAINS)}"

    return True, ""


# ----------------- Password Validation -----------------
def is_strong_password(password: str) -> (bool, str):
    """Check password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character."
    return True, ""


# ----------------- Redirect if logged in -----------------
if st.session_state["authenticated"]:
    st.query_params.clear()
    st.rerun()
    st.stop()

st.title("🔑 Welcome to YouTube Analytics Dashboard")

tab1, tab2 = st.tabs(["Login", "Signup"])


# ----------------- LOGIN TAB -----------------
with tab1:
    st.subheader("Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login"):
        # Empty fields
        if not email or not password:
            st.error("Please fill in all fields.")
        else:
            valid, msg = is_valid_email(email)
            if not valid:
                st.error(msg)
            else:
                success, msg = login(email, password)
                if success:
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = email
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


# ----------------- SIGNUP TAB -----------------
with tab2:
    st.subheader("Signup")
    new_email = st.text_input("Email", key="signup_email")
    new_password = st.text_input("Password", type="password", key="signup_password")

    if st.button("Signup"):
        # Empty fields
        if not new_email or not new_password:
            st.error("Please fill in all fields.")
        else:
            valid, msg = is_valid_email(new_email)
            if not valid:
                st.error(msg)
            else:
                strong, msg_pw = is_strong_password(new_password)
                if not strong:
                    st.error(msg_pw)
                else:
                    success, msg = signup(new_email, new_password)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
