# app.py - Streamlit Version of Order Analytics App

import os
import json
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import base64
import hmac

# --- Config ---
DATA_PATH = os.environ.get('DATA_PATH', './data')
USERS_FILE = os.environ.get('USERS_FILE', './users.json')

# --- Page Config ---
st.set_page_config(
    page_title="Order Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- Authentication Functions ---
def check_password():
    """Returns `True` if the user had the correct password."""
    if "authentication_status" not in st.session_state:
        # First run, initialize
        st.session_state.authentication_status = False
        
    if st.session_state.authentication_status:
        return True
    
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            users = json.load(f)
            correct_username = users.get('username', 'admin')
            correct_password = users.get('password', 'admin')
    else:
        correct_username = 'admin'
        correct_password = 'admin'
        
    # Create login form
    with st.form("Login"):
        st.markdown("## Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if username == correct_username and password == correct_password:
                st.session_state.authentication_status = True
                return True
            else:
                st.error("Invalid username or password")
                return False
        return False
    
# --- Auth check ---
if os.environ.get('AUTH_REQUIRED', 'True').lower() == 'true':
    if not check_password():
        st.stop()  # Stop execution if authentication fails

# --- App Logic ---
def load_data(file_path):
    """Load and preprocess data from CSV file"""
    try:
        df = pd.read_csv(file_path)
        # Ensure date columns are properly formatted
        if 'datePayment' in df.columns:
            df['date'] = pd.to_datetime(df['datePayment']).dt.date
        return df
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return pd.DataFrame()

def filter_data(df, selected_events=None):
    """Filter data based on selected events"""
    if selected_events and len(selected_events) > 0:
        return df[df['eventId'].isin(selected_events)]
    return df

def display_summary_stats(df):
    """Display summary statistics"""
    total_orders = len(df)
    total_amount = df['amount'].sum()
    avg_amount = df['amount'].mean()
    confirmed = df[df['stateId'] == 4]
    confirmed_pct = (len(confirmed) / total_orders) * 100 if total_orders > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Orders", f"{total_orders}")
    with col2:
        st.metric("Total Amount", f"${total_amount:.2f}")
    with col3:
        st.metric("Avg Order Amount", f"${avg_amount:.2f}")
    with col4:
        st.metric("Confirmed Orders", f"{len(confirmed)} ({confirmed_pct:.1f}%)")

def create_charts(df):
    """Create and display charts"""
    # Row 1 - Pie Chart and Line Chart
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart
        state_counts = df['stateId'].value_counts().reset_index()
        state_counts.columns = ['state', 'count']
        pie = px.pie(
            state_counts, values='count', names='state', 
            title='Order States', template='plotly_white'
        )
        st.plotly_chart(pie, use_container_width=True)
    
    with col2:
        # Line chart
        line = px.line(
            df.groupby('date')['amount'].sum().reset_index(), 
            x='date', y='amount',
            title='Total Amount by Date', template='plotly_white'
        )
        st.plotly_chart(line, use_container_width=True)
    
    # Row 2 - Bar Chart and Histogram
    col1, col2 = st.columns(2)
    
    with col1:
        # Avg by Event
        avg_event = px.bar(
            df.groupby('eventId')['amount'].mean().reset_index(),
            x='eventId', y='amount', 
            title='Avg Order Value by Event', template='plotly_white'
        )
        st.plotly_chart(avg_event, use_container_width=True)
    
    with col2:
        # Histogram
        hist = px.histogram(
            df, x='amount', nbins=30, 
            title='Order Amount Distribution', template='plotly_white'
        )
        st.plotly_chart(hist, use_container_width=True)

def display_confirmed_orders(df):
    """Display table of confirmed orders"""
    confirmed = df[df['stateId'] == 4]
    if not confirmed.empty:
        st.subheader("Confirmed Orders (State ID = 4)")
        st.dataframe(
            confirmed.drop(columns=['paymentResult'], errors='ignore'),
            use_container_width=True
        )
    else:
        st.info("No confirmed orders found in the selected data.")

# --- Main App ---
def main():
    st.title("Order Analytics Dashboard")
    
    # Sidebar for file selection and filtering
    with st.sidebar:
        st.header("Data Selection")
        
        # File selection
        csv_files = [f for f in os.listdir(DATA_PATH) if f.endswith('.csv')]
        if not csv_files:
            st.warning(f"No CSV files found in {DATA_PATH}")
            return
            
        selected_file = st.selectbox(
            "Select CSV File:",
            options=csv_files,
            format_func=lambda x: x
        )
        
        file_path = os.path.join(DATA_PATH, selected_file) if selected_file else None
        
        # Load data
        if file_path and os.path.exists(file_path):
            df = load_data(file_path)
            
            if not df.empty:
                # Event filtering
                event_ids = sorted(df['eventId'].unique())
                selected_events = st.multiselect(
                    "Filter by Event ID:",
                    options=event_ids,
                    format_func=lambda x: f"Event {x}"
                )
                
                # Apply filters
                filtered_df = filter_data(df, selected_events)
                
                if st.button("Analyze Data", type="primary"):
                    if filtered_df.empty:
                        st.warning("No data found for the selected filters.")
                        return
                        
                    # Main content area
                    display_summary_stats(filtered_df)
                    st.divider()
                    create_charts(filtered_df)
                    st.divider()
                    display_confirmed_orders(filtered_df)
            else:
                st.error("Selected file contains no data or is not properly formatted.")
        else:
            st.info("Please select a CSV file to analyze.")

# --- Run the app ---
if __name__ == "__main__":
    # Create data directory if it doesn't exist
    os.makedirs(DATA_PATH, exist_ok=True)
    main()