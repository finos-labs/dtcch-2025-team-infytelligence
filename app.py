import json
import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables from .env
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Ensure credentials are loaded correctly
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Supabase credentials. Make sure .env file is set up correctly!")
    st.stop()

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Function to fetch all events and parse JSON correctly
def fetch_events():
    response = supabase.table("events").select("*").execute()
    events = response.data if response.data else []
    
    # Ensure JSON is properly parsed
    for event in events:
        if isinstance(event["data"], str):  # If data is a JSON string, parse it
            event["data"] = json.loads(event["data"])
    
    return events

# Function to add an event
def add_event(event_id, event_data):
    formatted_data = {key: value for key, value in event_data.items() if key and value}
    response = supabase.table("events").insert({"id": event_id, "data": json.dumps(formatted_data)}).execute()
    return response

# Function to update an event
def update_event(event_id, new_data):
    formatted_data = {key: value for key, value in new_data.items() if key and value}
    response = supabase.table("events").update({"data": json.dumps(formatted_data)}).eq("id", event_id).execute()
    return response

# Function to delete an event
def delete_event(event_id):
    response = supabase.table("events").delete().eq("id", event_id).execute()
    return response

# Streamlit UI Title
st.markdown(
    "<h1 style='white-space: nowrap;'>Corporate Action Event Manager</h1>", 
    unsafe_allow_html=True
)


# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📜 View Events", "➕ Add Event", "✏️ Edit Event", "❌ Delete Event"])

# --- TAB 1: VIEW EVENTS ---
with tab1:
    st.subheader("📄 View CA Events")

    events = fetch_events()
    event_ids = [event["id"] for event in events]

    if event_ids:
        selected_event_id = st.selectbox("Select an Event", event_ids)

        event_to_view = next((event for event in events if event["id"] == selected_event_id), None)
        if event_to_view:
            data_dict = event_to_view["data"]

            st.write(f"### Event ID: {selected_event_id}")

            # Convert dictionary to DataFrame and display in table
            df = pd.DataFrame(list(data_dict.items()), columns=["Attribute", "Prompt"])
            st.data_editor(df, disabled=True, key="view_event")  # View-only table
    else:
        st.warning("No events found!")

# --- TAB 2: ADD NEW EVENT ---
with tab2:
    st.subheader("➕ Add New CA Event")

    new_event_id = st.text_input("Enter Event ID")

    st.write("### Event Attributes and Prompts")

    # Initialize session state for new event table with default empty row
    if "new_data_df" not in st.session_state:
        st.session_state.new_data_df = pd.DataFrame(columns=["Attribute", "Prompt"])
    
    # Editable table for adding data (default option allows adding rows dynamically)
    new_data_df = st.data_editor(st.session_state.new_data_df, num_rows="dynamic", key="new_event")

    if st.button("Add Event"):
        # Convert DataFrame to dictionary with correct JSON format
        parsed_data = {row["Attribute"]: row["Prompt"] for _, row in new_data_df.iterrows() if row["Attribute"]}

        if new_event_id and parsed_data:
            add_event(new_event_id, parsed_data)
            st.success(f"Event '{new_event_id}' added successfully!")

            # Reset session state only for new event entry
            st.session_state.new_data_df = pd.DataFrame(columns=["Attribute", "Prompt"])  
            st.rerun()  # Preserve scroll position
        else:
            st.error("Please enter a valid Event ID and at least one attribute.")

# --- TAB 3: EDIT EVENT ---
with tab3:
    st.subheader("✏️ Edit CS Event")
    
    events = fetch_events()
    edit_event_id = st.selectbox("Select Event to Edit", [event["id"] for event in events])

    if edit_event_id:
        event_to_edit = next((event for event in events if event["id"] == edit_event_id), None)
        if event_to_edit:
            data_dict = event_to_edit["data"]

            st.write("### Edit Attributes and Prompts")

            # Initialize session state for editing event table
            if "edit_data_df" not in st.session_state or st.session_state.edit_event_id != edit_event_id:
                st.session_state.edit_event_id = edit_event_id
                st.session_state.edit_data_df = pd.DataFrame(list(data_dict.items()), columns=["Attribute", "Prompt"])

            # Editable table for updating attributes (allows dynamic row addition)
            updated_data_df = st.data_editor(st.session_state.edit_data_df, num_rows="dynamic", key="edit_event")

            if st.button("Update Event"):
                # Convert edited DataFrame to dictionary with correct JSON format
                updated_data = {row["Attribute"]: row["Prompt"] for _, row in updated_data_df.iterrows() if row["Attribute"]}

                if updated_data:
                    update_event(edit_event_id, updated_data)
                    st.success(f"Event '{edit_event_id}' updated successfully!")
                    st.rerun()  # Preserve scroll position
                else:
                    st.error("Please enter at least one attribute.")

# --- TAB 4: DELETE EVENT ---
with tab4:
    st.subheader("❌ Delete CA Event")
    
    events = fetch_events()
    delete_event_id = st.selectbox("Select Event to Delete", [event["id"] for event in events])

    if st.button("Delete Event"):
        delete_event(delete_event_id)
        st.success(f"Event '{delete_event_id}' deleted successfully!")
        st.rerun()  # Preserve scroll position
