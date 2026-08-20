import streamlit as st
import pandas as pd

st.title("Simple Data Entry Form")

with st.form("entry_form", clear_on_submit=True):
    name = st.text_input("Name")
    category = st.selectbox("Category", ["Option A", "Option B", "Option C"])
    notes = st.text_area("Notes")
    submitted = st.form_submit_button("Submit")

if submitted:
    st.success(f"Submitted: {name} | {category}")