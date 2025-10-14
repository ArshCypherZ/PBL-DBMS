# Streamlit Frontend
# Developed by: Shahab Salik
import streamlit as st
import requests
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')

st.set_page_config(page_title="AI-Native DBMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'query'
if 'pending_query' not in st.session_state:
    st.session_state.pending_query = None
if 'show_confirmation' not in st.session_state:
    st.session_state.show_confirmation = False
if 'last_result' not in st.session_state:
    st.session_state.last_result = None

def login(username, password):
    try:
        response = requests.post(f"{BACKEND_URL}/auth/login", json={"username": username, "password": password}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            st.session_state.logged_in = True
            st.session_state.token = data['access_token']
            st.session_state.user_info = {'user_id': data['user_id'], 'username': data['username'], 'role': data['role'], 'email': data['email']}
            return True, "Login successful"
        return False, response.json().get('detail', 'Login failed')
    except Exception as e:
        return False, str(e)

def logout():
    st.session_state.logged_in = False
    st.session_state.token = None
    st.session_state.user_info = {}

def get_auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}

def execute_query(text, confirm=False):
    try:
        response = requests.post(f"{BACKEND_URL}/query", json={"text": text, "confirm": confirm}, headers=get_auth_headers(), timeout=30)
        if response.status_code == 200:
            return response.json()
        return {"success": False, "message": response.json().get('detail', 'Failed'), "data": [], "needs_confirmation": False}
    except Exception as e:
        return {"success": False, "message": str(e), "data": [], "needs_confirmation": False}

def get_profile():
    try:
        response = requests.get(f"{BACKEND_URL}/profile", headers=get_auth_headers(), timeout=10)
        if response.status_code == 200:
            return response.json()['profile']
    except:
        pass
    return {}

def get_audit_logs():
    try:
        response = requests.get(f"{BACKEND_URL}/audit-logs", headers=get_auth_headers(), timeout=10)
        if response.status_code == 200:
            return response.json()['logs']
    except:
        pass
    return []

def get_users():
    try:
        response = requests.get(f"{BACKEND_URL}/users", headers=get_auth_headers(), timeout=10)
        if response.status_code == 200:
            return response.json()['users']
    except:
        pass
    return []

def get_schema():
    try:
        response = requests.get(f"{BACKEND_URL}/schema", headers=get_auth_headers(), timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"tables": [], "columns": [], "procedures": []}

def show_login_page():
    st.title("University ERP System")
    st.markdown("AI-Native Database Management")
    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", type="primary", width='stretch')
            
            if submit and username and password:
                success, message = login(username, password)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        
        with st.expander("Demo Credentials"):
            st.markdown("Admin: admin / admin123")
            st.markdown("Student: student1 / user123")
            st.markdown("Faculty: faculty1 / user123")

def show_query_page():
    st.title("Query Interface")
    st.markdown(f"Welcome, {st.session_state.user_info['username']} ({st.session_state.user_info['role'].title()})")
    st.divider()
    
    if st.session_state.show_confirmation and st.session_state.pending_query:
        st.warning("Query Confirmation Required")
        
        st.markdown("**Original Query:**")
        st.info(st.session_state.pending_query['text'])
        
        st.markdown("**Generated SQL:**")
        st.code(st.session_state.pending_query.get('sql_query', ''), language='sql')
        
        if st.session_state.pending_query.get('explanation'):
            st.markdown("**Explanation:**")
            st.write(st.session_state.pending_query['explanation'])
        
        st.markdown("**Confirm execution?**")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Yes, Execute", type="primary", width='stretch'):
                with st.spinner("Executing..."):
                    result = execute_query(st.session_state.pending_query['text'], confirm=True)
                    st.session_state.last_result = result
                    st.session_state.pending_query = None
                    st.session_state.show_confirmation = False
                    st.rerun()
        
        with col2:
            if st.button("No, Cancel", width='stretch'):
                st.session_state.pending_query = None
                st.session_state.show_confirmation = False
                st.session_state.last_result = None
                st.rerun()
        
        st.divider()
    
    if st.session_state.last_result:
        result = st.session_state.last_result
        if result['success']:
            st.success(result['message'])
            if result['data']:
                st.dataframe(pd.DataFrame(result['data']), width='stretch')
        else:
            st.error(result['message'])
        st.session_state.last_result = None
    
    user_input = st.text_area("Enter your query:", 
                             placeholder="e.g., show all students in computer science",
                             height=100,
                             disabled=st.session_state.show_confirmation)
    
    if st.button("Execute Query", type="primary", disabled=st.session_state.show_confirmation):
        if user_input:
            with st.spinner("Processing..."):
                result = execute_query(user_input, confirm=False)
                
                if result.get('needs_confirmation'):
                    st.session_state.pending_query = {
                        'text': user_input,
                        'sql_query': result.get('sql_query', ''),
                        'explanation': result.get('explanation', '')
                    }
                    st.session_state.show_confirmation = True
                    st.rerun()
                elif result['success']:
                    st.success(result['message'])
                    if result['data']:
                        st.dataframe(pd.DataFrame(result['data']), width='stretch')
                else:
                    st.error(result['message'])

def show_profile_page():
    st.title("My Profile")
    st.divider()
    
    profile = get_profile()
    if profile:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Username", profile.get('username', ''))
            st.metric("Email", profile.get('email', ''))
        with col2:
            st.metric("Full Name", profile.get('full_name', ''))
            st.metric("Role", profile.get('role', '').title())
        
        if profile.get('additional_info'):
            st.info(profile['additional_info'])

def show_schema_page():
    st.title("Database Schema")
    st.divider()
    
    schema = get_schema()
    
    if schema['tables']:
        st.subheader("Tables")
        tables_df = pd.DataFrame(schema['tables'])
        st.dataframe(tables_df, width='stretch')
    
    if schema['columns']:
        st.subheader("Columns")
        columns_df = pd.DataFrame(schema['columns'])
        st.dataframe(columns_df, width='stretch', height=400)
    
    if schema.get('procedures'):
        st.subheader("Stored Procedures")
        procedures_df = pd.DataFrame(schema['procedures'])
        st.dataframe(procedures_df, width='stretch')

def show_audit_logs_page():
    if st.session_state.user_info['role'] != 'admin':
        st.error("Admin access required")
        return
    
    st.title("Audit Logs")
    st.divider()
    
    logs = get_audit_logs()
    if logs:
        st.dataframe(pd.DataFrame(logs), width='stretch', height=600)
    else:
        st.info("No logs found")

def show_users_page():
    if st.session_state.user_info['role'] != 'admin':
        st.error("Admin access required")
        return
    
    st.title("System Users")
    st.divider()
    
    users = get_users()
    if users:
        st.dataframe(pd.DataFrame(users), width='stretch')
    else:
        st.info("No users found")

def show_sidebar():
    with st.sidebar:
        st.markdown(f"**User:** {st.session_state.user_info['username']}")
        st.markdown(f"**Role:** {st.session_state.user_info['role'].title()}")
        st.divider()
        
        if st.button("Query", width='stretch'):
            st.session_state.current_page = 'query'
            st.rerun()
        
        if st.button("My Profile", width='stretch'):
            st.session_state.current_page = 'profile'
            st.rerun()
        
        if st.button("Schema", width='stretch'):
            st.session_state.current_page = 'schema'
            st.rerun()
        
        if st.session_state.user_info['role'] == 'admin':
            if st.button("Audit Logs", width='stretch'):
                st.session_state.current_page = 'logs'
                st.rerun()
            
            if st.button("Users", width='stretch'):
                st.session_state.current_page = 'users'
                st.rerun()
        
        st.divider()
        if st.button("Logout", width='stretch'):
            logout()
            st.rerun()

def main():
    if not st.session_state.logged_in:
        show_login_page()
    else:
        show_sidebar()
        
        if st.session_state.current_page == 'query':
            show_query_page()
        elif st.session_state.current_page == 'profile':
            show_profile_page()
        elif st.session_state.current_page == 'schema':
            show_schema_page()
        elif st.session_state.current_page == 'logs':
            show_audit_logs_page()
        elif st.session_state.current_page == 'users':
            show_users_page()

if __name__ == "__main__":
    main()
