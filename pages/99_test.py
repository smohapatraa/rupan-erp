import streamlit as st
from core import auth

st.title("Bootstrap Admin User")

st.write("Click the button below to create the first admin user.")
st.write("**Username:** `admin`")
st.write("**Password:** `admin123`")

if st.button("Create Admin User"):
    with st.spinner("Creating user..."):
        success = auth.create_user(
            username="admin",
            password="admin123",
            role="admin",
            created_by="SYSTEM"
        )
        if success:
            st.success("Admin user created successfully! You can now log in.")
        else:
            st.info("Admin user might already exist.")
