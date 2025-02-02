# app.py
import os
import json
import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # Load Azure environment variables if needed

from azure_openai_llm import AzureOpenAIClient
from classifier import Classifier
from extractor import Extractor
from validator import Validator
from planner import Planner
from file_handler import FileHandler
from output_generator import ReportGenerator

def main():
    st.set_page_config(page_title="Corporate Action Processor (Review Flow)", layout="wide")
    st.title("Corporate Action Processor (Review Flow)")

    # 1) Initialize session state
    if "file_states" not in st.session_state:
        st.session_state.file_states = {}
    if "upload_processed" not in st.session_state:
        st.session_state.upload_processed = False

    # Initialize helper classes
    file_handler = FileHandler()
    azure_client = AzureOpenAIClient()
    llm = azure_client.get_llm()
    classifier = Classifier()
    extractor = Extractor(llm)
    validator = Validator()
    planner = Planner()

    # 2) Upload Section (Process Files button)
    with st.expander("Upload PDF/ZIP Files", expanded=True):
        uploaded_files = st.file_uploader(
            "Select PDFs or ZIPs (multiple allowed):",
            type=["pdf", "zip"],
            accept_multiple_files=True
        )

        if st.button("Process Files"):
            if uploaded_files:
                saved_paths = file_handler.save_uploaded_files(uploaded_files)

                # Add each new path to session state if not already present
                for path in saved_paths:
                    if path not in st.session_state.file_states:
                        # We'll add a new 'review_ready' field to control the review step
                        st.session_state.file_states[path] = {
                            "filename": os.path.basename(path),
                            "original_text": None,
                            "classification": "unknown",
                            "comment": "",
                            "extracted_data": {},
                            "review_ready": False,   # new flag
                            "validated": False,
                            "error": None,
                            "report_generated": False,
                            "report_path": "",
                            "show_details": False,
                            "plan_steps": []
                        }

                st.session_state.upload_processed = True
                st.success("Files processed successfully!")
            else:
                st.warning("No files selected to process.")

    # (Optional) Reset button
    if st.button("Reset Uploads"):
        st.session_state.file_states = {}
        st.session_state.upload_processed = False
        st.experimental_rerun()

    # 3) Display table/list of uploaded files
    st.header("Uploaded Files")
    if not st.session_state.file_states:
        st.info("No files uploaded yet (or after reset).")
        return  # Nothing else to show

    cols_header = st.columns([3, 2, 3, 2, 2])
    with cols_header[0]: st.write("**File Name**")
    with cols_header[1]: st.write("**Classification**")
    with cols_header[2]: st.write("**Comment**")
    with cols_header[3]: st.write("**Validation**")
    with cols_header[4]: st.write("**Actions**")

    # Loop through each saved file
    for fp, state in list(st.session_state.file_states.items()):
        row_cols = st.columns([3, 2, 3, 2, 2])

        with row_cols[0]:
            st.write(state["filename"])

        with row_cols[1]:
            st.write(state["classification"])

        with row_cols[2]:
            new_comment = st.text_input(
                label="Comment",
                value=state["comment"],
                key=f"comment_{fp}",
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
            if st.button("Toggle Details", key=f"toggle_{fp}"):
                state["show_details"] = not state["show_details"]

        state["comment"] = new_comment

        # 4) If user toggles details
        if state["show_details"]:
            st.markdown("---")
            with st.expander(f"Details for: {state['filename']}", expanded=True):
                left_col, right_col = st.columns([2, 4])
                with left_col:
                    # Classification override
                    override_class = st.selectbox(
                        "Reclassify Document Type",
                        ["dividend", "merger", "stock_split", "unknown", "other"],
                        index=["dividend", "merger", "stock_split", "unknown", "other"].index(
                            state["classification"]
                        ) if state["classification"] in ["dividend", "merger", "stock_split", "unknown", "other"] else 4,
                        key=f"override_class_{fp}"
                    )
                    if st.button("Re-classify", key=f"reclass_{fp}"):
                        state["classification"] = override_class
                        st.success(f"Re-classified to '{override_class}'")

                with right_col:
                    st.write("**Document Preview**")
                    prev_img = file_handler.get_preview_image(fp)
                    if prev_img:
                        st.image(prev_img, width=300)
                    else:
                        st.warning("Preview unavailable.")

                # Load PDF text if needed
                if state["original_text"] is None:
                    try:
                        pdf_text = file_handler.extract_text_from_pdf(fp)
                        state["original_text"] = pdf_text
                        if state["classification"] == "unknown":
                            auto_cls = classifier.classify_document(pdf_text)
                            state["classification"] = auto_cls
                        steps = planner.plan_workflow(state["classification"])
                        state["plan_steps"] = steps
                    except Exception as e:
                        state["error"] = f"Could not read PDF: {e}"
                        st.error(state["error"])
                        continue

                st.write("### Workflow Steps")
                if not state["plan_steps"]:
                    state["plan_steps"] = planner.plan_workflow(state["classification"])
                st.write(state["plan_steps"])

                st.subheader("Extracted Content & Validation")
                # If no data => "Extract Data" button
                if not state["extracted_data"]:
                    st.info("No extracted data yet. Click 'Extract Data' to parse fields.")
                    if st.button("Extract Data", key=f"extract_{fp}"):
                        try:
                            # Extract from LLM
                            extracted = extractor.extract_details(
                                state["original_text"],
                                state["classification"]
                            )
                            state["extracted_data"] = extracted
                            state["error"] = None
                            state["review_ready"] = False
                            st.success("Data extracted. Please click 'Review Data' next.")
                            # Force a re-run so the next UI state gets updated
                            st.experimental_rerun()
                        except Exception as verr:
                            state["error"] = str(verr)
                            st.error(f"Extraction failed: {verr}")
                else:
                    # We have extracted_data
                    if not state["review_ready"]:
                        st.info("Data extracted but not reviewed. Click 'Review Data' to proceed.")
                        if st.button("Review Data", key=f"review_{fp}"):
                            state["review_ready"] = True
                            st.experimental_rerun()
                    else:
                        # Show fields for editing => then Save & Update
                        st.write("Below are the extracted fields. Edit if needed, then Save & Update.")
                        updated_data = {}
                        for field, val in state["extracted_data"].items():
                            updated_data[field] = st.text_input(
                                field,
                                value=val,
                                key=f"{field}_{fp}"
                            )

                        # Save & Update => Validate
                        if st.button("Save & Update", key=f"save_{fp}"):
                            try:
                                validated_data = validator.validate_data(updated_data)
                                state["extracted_data"] = validated_data
                                state["validated"] = True
                                state["error"] = None
                                json_path = os.path.join(file_handler.output_dir, f"{state['filename']}_data.json")
                                with open(json_path, "w") as jf:
                                    json.dump(validated_data, jf, indent=2)
                                st.success(f"Data updated & validated. JSON saved at: {json_path}")
                            except Exception as e:
                                state["validated"] = False
                                state["error"] = str(e)
                                st.error(f"Validation error: {e}")

                        # Generate Report only if validated
                        if state["validated"] and state["extracted_data"]:
                            st.subheader("Generate Report")
                            if not state["report_generated"]:
                                if st.button("Generate Report", key=f"report_{fp}"):
                                    report_filename = f"Report_{state['filename']}.pdf"
                                    report_path = os.path.join(file_handler.output_dir, report_filename)
                                    try:
                                        ReportGenerator.generate_pdf_report(state["extracted_data"], report_path)
                                        state["report_generated"] = True
                                        state["report_path"] = report_path
                                        st.success(f"Report generated successfully! Find it at: {report_path}")
                                    except Exception as rep_err:
                                        st.error(f"Report generation failed: {rep_err}")
                            else:
                                st.info(f"Report already generated at: {state['report_path']}")

                # Show errors
                if state["error"]:
                    st.error(f"Error: {state['error']}")

            st.markdown("---")

if __name__ == "__main__":
    main() 