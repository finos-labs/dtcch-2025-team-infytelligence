# app.py
import os
import json
import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # Load .env

from bedrock_llm import BedrockClient
from classifier import Classifier
from extractor import Extractor
from validator import Validator
from planner import Planner
from file_handler import FileHandler
from output_generator import ReportGenerator

def main():
    st.set_page_config(page_title="Corporate Action Processor (Review Flow)", layout="wide")
    st.title("Corporate Action Processor (Review Flow)")

    if "file_states" not in st.session_state:
        st.session_state.file_states = {}

    if "upload_processed" not in st.session_state:
        st.session_state.upload_processed = False

    # Instantiate classes
    llm_client = BedrockClient()
    file_handler = FileHandler()
    classifier = Classifier()
    extractor = Extractor(llm_client)
    validator = Validator()
    planner = Planner()

    # Section 1: Let user specify existing S3 keys
    st.header("1) Provide existing S3 PDF keys (Comma-separated)")
    s3_keys_input = st.text_input("S3 keys", "8k_stock_split.pdf, 8k_merger.pdf")
    if st.button("Load from S3"):
        s3_keys_list = [k.strip() for k in s3_keys_input.split(",") if k.strip()]
        for k in s3_keys_list:
            if k not in st.session_state.file_states:
                st.session_state.file_states[k] = {
                    "filename": os.path.basename(k),
                    "original_text": None,
                    "classification": "unknown",
                    "comment": "",
                    "extracted_data": {},
                    "review_ready": False,
                    "validated": False,
                    "error": None,
                    "report_generated": False,
                    "report_path": "",
                    "show_details": False,
                    "plan_steps": []
                }
        st.session_state.upload_processed = True
        st.success("Loaded references from S3 into session.")

    # Section 2: (Optional) Upload new PDFs
    st.header("2) (Optional) Upload New PDFs or ZIPs to S3")
    uploaded_files = st.file_uploader("Select PDFs or ZIPs", type=["pdf", "zip"], accept_multiple_files=True)
    if st.button("Process Uploads"):
        if uploaded_files:
            s3_keys = file_handler.save_uploaded_files(uploaded_files)
            for s3k in s3_keys:
                if s3k not in st.session_state.file_states:
                    st.session_state.file_states[s3k] = {
                        "filename": os.path.basename(s3k),
                        "original_text": None,
                        "classification": "unknown",
                        "comment": "",
                        "extracted_data": {},
                        "review_ready": False,
                        "validated": False,
                        "error": None,
                        "report_generated": False,
                        "report_path": "",
                        "show_details": False,
                        "plan_steps": []
                    }
            st.session_state.upload_processed = True
            st.success("Uploads processed & stored in S3!")
        else:
            st.warning("No files selected.")

    # Display table
    st.header("3) Processed S3 Files in Session")
    if not st.session_state.file_states:
        st.info("No files in session yet.")
        return

    cols_header = st.columns([3, 2, 3, 2, 2])
    with cols_header[0]: st.write("**File**")
    with cols_header[1]: st.write("**Classification**")
    with cols_header[2]: st.write("**Comment**")
    with cols_header[3]: st.write("**Validation**")
    with cols_header[4]: st.write("**Actions**")

    for s3_key, state in list(st.session_state.file_states.items()):
        row_cols = st.columns([3, 2, 3, 2, 2])
        with row_cols[0]:
            st.write(state["filename"])
        with row_cols[1]:
            st.write(state["classification"])
        with row_cols[2]:
            new_comment = st.text_input(
                label="Comment",
                value=state["comment"],
                key=f"comment_{s3_key}",
                label_visibility="collapsed"
            )
        with row_cols[3]:
            if state["error"]:
                st.error("Error")
            elif state["validated"]:
                st.success("Validated")
            else:
                st.write("—")
        with row_cols[4]:
            if st.button("Toggle Details", key=f"toggle_{s3_key}"):
                state["show_details"] = not state["show_details"]

        state["comment"] = new_comment

        # If toggled details
        if state["show_details"]:
            st.markdown("---")
            with st.expander(f"Details for: {state['filename']}", expanded=True):
                left_col, right_col = st.columns([2, 4])
                with left_col:
                    override_class = st.selectbox(
                        "Reclassify Document Type",
                        ["dividend", "merger", "stock_split", "unknown", "other"],
                        index=["dividend","merger","stock_split","unknown","other"].index(
                            state["classification"]
                        ) if state["classification"] in ["dividend","merger","stock_split","unknown","other"] else 4,
                        key=f"override_class_{s3_key}"
                    )
                    if st.button("Re-classify", key=f"reclass_{s3_key}"):
                        state["classification"] = override_class
                        st.success(f"Re-classified to '{override_class}'")

                with right_col:
                    st.write("**PDF Preview**")
                    img = file_handler.get_preview_image(s3_key)
                    if img:
                        st.image(img, width=300)
                    else:
                        st.warning("No preview available.")

                if state["original_text"] is None:
                    # Extract text
                    try:
                        pdf_text = file_handler.extract_text_from_pdf(s3_key)
                        state["original_text"] = pdf_text
                        if state["classification"] == "unknown":
                            auto_cls = classifier.classify_document(pdf_text)
                            state["classification"] = auto_cls
                        state["plan_steps"] = planner.plan_workflow(state["classification"])
                    except Exception as e:
                        state["error"] = f"Could not read PDF: {e}"
                        st.error(state["error"])
                        continue

                st.write("### Workflow Steps")
                if not state["plan_steps"]:
                    state["plan_steps"] = planner.plan_workflow(state["classification"])
                st.write(state["plan_steps"])

                st.subheader("Extracted Content & Validation")
                if not state["extracted_data"]:
                    st.info("No extracted data yet. Click 'Extract Data' to parse fields.")
                    if st.button("Extract Data", key=f"extract_{s3_key}"):
                        try:
                            extracted = extractor.extract_details(
                                state["original_text"],
                                state["classification"]
                            )
                            state["extracted_data"] = extracted
                            state["error"] = None
                            state["review_ready"] = False
                            st.success("Data extracted. Click 'Review Data' next.")
                            st.experimental_rerun()
                        except Exception as verr:
                            state["error"] = str(verr)
                            st.error(f"Extraction failed: {verr}")
                else:
                    if not state["review_ready"]:
                        st.info("Data extracted but not reviewed. Click 'Review Data' to proceed.")
                        if st.button("Review Data", key=f"review_{s3_key}"):
                            state["review_ready"] = True
                            st.experimental_rerun()
                    else:
                        # Show fields for editing => Save => Validate
                        updated_data = {}
                        for field, val in state["extracted_data"].items():
                            updated_data[field] = st.text_input(field, value=val, key=f"{field}_{s3_key}")

                        if st.button("Save & Update", key=f"save_{s3_key}"):
                            try:
                                validated = validator.validate_data(updated_data)
                                state["extracted_data"] = validated
                                state["validated"] = True
                                state["error"] = None
                                json_key = f"output/{state['filename']}_data.json"
                                file_handler.save_json_to_s3(validated, json_key)
                                st.success(f"Data validated. JSON saved to {json_key}")
                            except Exception as e:
                                state["validated"] = False
                                state["error"] = str(e)
                                st.error(f"Validation error: {e}")

                        # Generate Report
                        if state["validated"] and state["extracted_data"]:
                            st.subheader("Generate Report")
                            if not state["report_generated"]:
                                if st.button("Generate Report", key=f"report_{s3_key}"):
                                    report_filename = f"Report_{state['filename']}.pdf"
                                    local_pdf = os.path.join("/tmp", report_filename)
                                    try:
                                        ReportGenerator.generate_pdf_report(state["extracted_data"], local_pdf)
                                        s3_key_report = f"output/{report_filename}"
                                        file_handler.upload_file_to_s3(local_pdf, s3_key_report)
                                        state["report_generated"] = True
                                        state["report_path"] = s3_key_report
                                        st.success(f"Report generated! S3: {s3_key_report}")
                                    except Exception as rep_err:
                                        st.error(f"Report generation failed: {rep_err}")
                            else:
                                st.info(f"Report already generated at: {state['report_path']}")

                if state["error"]:
                    st.error(f"Error: {state['error']}")

            st.markdown("---")

if __name__ == "__main__":
    main()
