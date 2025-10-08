# Streamlit Frontend
# Developed by: Shahab Salik

import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')

st.set_page_config(page_title="AI-Native DBMS", layout="wide")

st.title("AI-Native Database Management")
st.markdown("**Team Metavoid** | Natural Language Database Interface")

# User input
user_input = st.text_area("Enter your command in natural language:", 
                          placeholder="e.g., 'show all users' or 'add user name: John email: john@test.com'",
                          height=100)

col1, col2 = st.columns([1, 4])

with col1:
    execute_btn = st.button("Execute", type="primary")

with col2:
    if st.button("View Audit Logs"):
        st.session_state.show_logs = True

# Execute query
if execute_btn and user_input:
    with st.spinner("Processing..."):
        try:
            response = requests.post(
                f"{BACKEND_URL}/query",
                json={"text": user_input},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    st.success(data['message'])
                    if data['data']:
                        st.dataframe(data['data'])
                else:
                    st.error(data['message'])
            else:
                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
        except Exception as e:
            st.error(f"Connection error: {str(e)}")

# Show audit logs
if st.session_state.get('show_logs', False):
    st.divider()
    st.subheader("Audit Logs")
    try:
        response = requests.get(f"{BACKEND_URL}/audit-logs", timeout=10)
        if response.status_code == 200:
            logs = response.json()['logs']
            st.dataframe(logs, use_container_width=True)
        else:
            st.error("Failed to fetch logs")
    except Exception as e:
        st.error(f"Error: {str(e)}")
    
    if st.button("Hide Logs"):
        st.session_state.show_logs = False
        st.rerun()

# Examples
with st.expander("Example Commands"):
    st.code("show all users")
    st.code("add user name: Alice email: alice@example.com")
    st.code("update user id: 1 name: Bob email: bob@example.com")
