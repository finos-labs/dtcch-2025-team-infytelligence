import streamlit as st
import zipfile
import os
from io import BytesIO
from typing import Dict, TypedDict, Annotated, Sequence
from classificationAgent import process_pdfs
import time
import logging
import pandas as pd
import fullCall
import merger
import partialCall
from datetime import date
from chat import chat_interface

st.set_page_config(layout="wide")

st.markdown("""
<style>
       .top-right {
           position: absolute;
           right: 20px;
           font-size: 18px;
           font-weight: bold;
       }
</style>
<div class="top-right">Innovate DTCC: AI-Powered Hackathon</div>
""", unsafe_allow_html=True)


# Initialize session state
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'df' not in st.session_state:
    st.session_state.df = None
if 'search_id' not in st.session_state:
    st.session_state.search_id = 0
    
    
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('execution_log.txt')
    ]

st.markdown("<h1 style='text-align: center;'>AI-Powered Corporate Action Data Ingestion</h1>", unsafe_allow_html=True)

st.subheader("1. Upload CA event Documents")

st.markdown("""
    <style>
    .file-upload-container {
        display: flex;
        justify-content: center;
    }
    .file-upload-container > div {
        width: 50%; /* Adjust the width as needed */
    }
    </style>
    """, unsafe_allow_html=True)

# File upload section
st.markdown('<div class="file-upload-container">', unsafe_allow_html=True)
uploaded_files = st.file_uploader(
    "Choose one ZIP file or multiple PDF files",
    type=["zip", "pdf"],
    accept_multiple_files=True
)
st.markdown('</div>', unsafe_allow_html=True)

@st.cache_data
def process_files(uploaded_files):
    pdf_files = {}
    total_files = 0

    for uploaded_file in uploaded_files:
        try:
            if uploaded_file.type == "application/x-zip-compressed":
                with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                    for file_info in zip_ref.infolist():
                        if file_info.filename.endswith('.pdf'):
                            with zip_ref.open(file_info) as file:
                                pdf_files[file_info.filename] = BytesIO(file.read())
                                total_files += 1
            elif uploaded_file.type == "application/pdf":
                pdf_files[uploaded_file.name] = BytesIO(uploaded_file.read())
                total_files += 1
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {e}")

    if pdf_files:
        result = process_pdfs(pdf_files)
        return result, pdf_files, total_files
    return None, {}, 0

if uploaded_files:
    with st.spinner('Processing files...'):
        start_time = time.time()
        result, pdf_files, total_files = process_files(uploaded_files)
        st.session_state.processed_data = result

        if result:
            main_folder = "Classified_PDFs"
            os.makedirs(main_folder, exist_ok=True)

            table_data = []
            counter = 100
            today = date.today()

            for doc in result['documents']:
                counter += 1
                table_data.append([
                    f"{counter}",
                    "Issuer Document",
                    doc['file_name'],
                    doc['document_type'],
                    doc['issuer'],
                    today.strftime("%m/%d/%Y"),
                    "User"
                ])

            st.session_state.df = pd.DataFrame(
                table_data,
                columns=['Document ID', 'Trigger', 'File Name', 'CA Event', 'Issuer Name', 'Uploaded Date', 'Uploaded By']
            )

            st.success(f"Processed {total_files} files successfully!")
            st.subheader("CA Event Documents")
            st.dataframe(st.session_state.df, hide_index=True)

            end_time = time.time()
            logging.info(f"Execution time: {end_time - start_time:.2f} seconds")

            # Save files to folders
            categorized_files = {}
            for doc in result['documents']:
                doc_type = doc['document_type']
                if doc_type not in categorized_files:
                    categorized_files[doc_type] = []
                categorized_files[doc_type].append(doc['file_name'])

            for category, files in categorized_files.items():
                category_folder = os.path.join(main_folder, category)
                os.makedirs(category_folder, exist_ok=True)
                for file_name in files:
                    if file_name in pdf_files:
                        file_path = os.path.join(category_folder, file_name)
                        with open(file_path, 'wb') as f:
                            f.write(pdf_files[file_name].getbuffer())

# Initialize session states
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'last_search_id' not in st.session_state:
    st.session_state.last_search_id = None

@st.cache_data
def search_records(df, search_id):
    return df[df['Document ID'] == str(search_id)]

# Search section
if st.session_state.df is not None:
    st.subheader("2. Extract Document")
    
    search_container = st.container()
    results_container = st.container()
    
    with search_container:
        with st.form(key='search_form', clear_on_submit=False):
            col1, col2 = st.columns([3, 1])
            with col1:
                search_id = st.text_input(
                    "Enter Document ID to Extract:",
                    key='search_input'
                )
            with col2:
                st.write(" ")  # This line ensures the button aligns with the input box
                submit_button = st.form_submit_button(label='Extract')

            if submit_button and search_id != st.session_state.last_search_id:
                st.session_state.search_results = search_records(st.session_state.df, search_id)
                st.session_state.last_search_id = search_id

    with results_container:
        if st.session_state.search_results is not None:
            if not st.session_state.search_results.empty:
                st.success(f"Result for Document ID: {st.session_state.last_search_id}")
                st.dataframe(st.session_state.search_results, hide_index=True)
                
                # Save the search results
                search_results = st.session_state.search_results
                
                # Extract 'File Name' and 'CA Event'
                file_names = search_results['File Name'].tolist()
                ca_events = search_results['CA Event'].tolist()
                
                # Display the extracted information
                # st.write("File Names:", file_names[0])
                # st.write("CA Events:", ca_events[0])
                # Inject minimal CSS for scrollable container
                
                st.header("Chat with CorpAct Buddy")
                st.markdown("""
                <style>
                .scroll-container {
                    max-height: 400px;
                    overflow-y: auto;
                }
                </style>
                """, unsafe_allow_html=True)
                st.markdown("<div class='scroll-container'>", unsafe_allow_html=True)
                chat_interface()
                st.markdown("</div>", unsafe_allow_html=True)
                            
                # Perform actions based on 'CA Event'
                if ca_events[0] == "Full Call":
                    fullCall.show(file_names[0])
                elif ca_events[0] == "Partial Call":
                    partialCall.show(file_names[0])
                elif ca_events[0] == "Merger":
                    merger.show(file_names[0])
            
                    

            
                
            else:
                st.warning(f"No records found for Document ID: {st.session_state.last_search_id}")


    