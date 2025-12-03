import streamlit as st
from auth import login, signup

st.set_page_config(page_title="Login | Signup", layout="centered")

# ----------------- Initialize session -----------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user" not in st.session_state:
    st.session_state["user"] = None

# ----------------- Redirect if already logged in -----------------
if st.session_state["authenticated"]:
    st.experimental_set_query_params()  # clear query params
    st.experimental_rerun()  # refresh page to redirect
    st.stop()

st.title("🔑 Welcome to YouTube Analytics Dashboard")

tab1, tab2 = st.tabs(["Login", "Signup"])

with tab1:
    st.subheader("Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login"):
        success, msg = login(email, password)
        if success:
            st.session_state["authenticated"] = True
            st.session_state["user"] = email
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

with tab2:
    st.subheader("Signup")
    new_email = st.text_input("Email", key="signup_email")
    new_password = st.text_input("Password", type="password", key="signup_password")
    if st.button("Signup"):
        success, msg = signup(new_email, new_password)
        if success:
            st.success(msg)
        else:
            st.error(msg)
