import streamlit as st
from auth import login, signup

st.set_page_config(page_title="Login | Signup", layout="centered")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
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
                st.switch_page("pages/Project.py")  # ✅ Redirect to dashboard
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
else:
    st.switch_page("pages/Project.py")
