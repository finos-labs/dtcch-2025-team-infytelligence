import os
from PyPDF2 import PdfReader
import json
import streamlit as st
import re
import pandas as pd
from streamlit_pdf_viewer import pdf_viewer
import base64
import pyperclip
from langchain_aws import ChatBedrock

st.set_page_config(layout="wide")

# Initialize session state
if "email_content" not in st.session_state:
    st.session_state.email_content = ""
if "copied" not in st.session_state:
    st.session_state.copied = False
if "email_type" not in st.session_state:
    st.session_state.email_type = "CA Event Email"
if "file_path" not in st.session_state:
    st.session_state.file_path = ""


def read_pdf(file_path):
    content = ""
    with open(file_path, "rb") as file:
        reader = PdfReader(file)
        for page in reader.pages:
            content += page.extract_text()
    return content


def convert_pdfs_to_json(directory):
    pdf_dict = {}
    for filename in os.listdir(directory):
        if filename.endswith(".pdf"):
            file_path = os.path.join(directory, filename)
            pdf_content = read_pdf(file_path)
            pdf_dict[filename] = pdf_content
    return pdf_dict


def prompt(fullCallJson):
    return f""" Objective: Extract and categorize entities from json containing corporate action documents related to full call redemption event.
    Ensure precision in identifying and structuring the extracted data.
    
    Entities to extract:
    
    1.AccruedInterest / AccruedDividend:
    -Extract the accrued interest or dividend value, either per share or cumulative, and calculate the total based on shares/bonds outstanding if provided per share.
    -Value will be in USD $
    
    2.BaseCusip:
    -Extract the first 6 digits of the CUSIP
    -if multiple CUSIPs are provided, list all base CUSIPs
    
    3.Class: Use each unique CUSIP as a class
    -if no CUSIP is provided, format the class based on the document's %rate, security type, and maturity date (MM/YYYY).

    
    4.ConditionalPaymentApplicableFlag:
    -Mark as 'Yes' if terms/keywords like 'contingent payment' or 'conditional payment' are found in the document
    -otherwise, mark as 'No'.
    
    
    5.ContactE-mail:
    -Extract the contact email for the Trustee, Agent, or Paying Agent mentioned in the document.
    
    6.ContactPhoneNumber: Extract the phone number for the Trustee, Agent, or Paying Agent mentioned in the document.
    
    7.Currency:
    -Extract the currency of the redemption. This can be derived from redemption amount, accrued interest, premium amount.

    
    8.CUSIP:
    -Search for the 'CUSIP' keyword in the document and record the 9-digit alphanumeric identifier
    -if multiple CUSIPs are provided, list all, including those for 144a and RegS registrations.
    
    9.IssuerName:
    -Extract the company name from terms/keywords like 'issuer', 'issuing entity', or 'name of registrant' if not provided explicitly as 'issuer name' or similar.
    
    10.SecuritySymbol:
    -Search for the keyword 'ticker' and extract the identification code; if found with the exchange name (e.g., NYSE: WMT), extract only the ticker symbol.
    
    11.Matrix:
    -Extract the maturity date (MM/DD/YYYY format) from terms/keyword like 'stated maturity,' 'final payment date,' or 'principal payment date'; if not provided, leave blank.
    
    12.OutstandingNumberOfSecurities:
    -Extract the number of outstanding securities at the time of redemption in numeric format
    
    13.Premium/ CashRate:
    -Extract the premium value provided as part of the call; leave blank if no numerical value is provided.
    
    14.Price:
    -Extract the redemption price, either as a percentage (e.g., 100%) or a USD value (e.g., $25.00 per share), using keywords like 'redeemed at a price of' or 'redemption price'.
    
    15.PublicationDate / DatedDate / RecordDate:
    -Extract the publication, dated, or record date (e.g., 'announcement date')
    - if not provided, set this date to 30 days before the redemption date.
    
    16.Rate:
    -Extract the original notes rate in percentage format (e.g., 5%)
    
    17.RedemptionAmount:
    -Extract the total redemption amount as a numerical value
    -if not explicitly provided, calculate it by multiplying the offering price by the outstanding number of securities, excluding any accrued interest.
    
    18.RedemptionDate:
    -Extract the redemption date in MM/DD/YYYY format, found as a key value or in context like 'called for full redemption on July 22, 2024' or 'will be redeemed in full on August 30, 2010'.
    
    19.SubIssueType:
    -Identify the sub-issue type based on the document: mark as 'Preferred Stock' if mentioned, 'Municipal Bonds' for school districts, municipalities, or states, and 'Corporate Bond' if a company name (e.g., Walt Disney, Apple) is mentioned.
    
    20.Trustee/Agent/PayingAgent:
    -Extract the trustee, agent, or paying agent information, which may appear as 'paying agent', 'trustee', or 'agent', often in table format or phrases like 'addressed to corporate trust office' or 'by mail addressed to'.
    
    Additional Instructions for extracting:
    1. Text Extraction: Ensure the text is parsed from the pdf document accurately.
    2. Search Strategy: Utilize keyword search to locate relevant sections.
    3.Formatting: Follow the specified output formats strictly,especially for dates and currency values.
    4.Handling missing data: If any entity is not found, return "Not Available" for that entity in the output.
    5. If you find more than one value for an entity, combine them. Example: 'contactnumber: 1234567890, 0987654321'. Follow this for all the entities.
    
    Input: A json {fullCallJson} contains document names (keys) and the content inside the PDFs (values)
    Output: extracted entities in json format.

    #Note: Add extracted values only when found. Do not add anything on your own. Include all the fields mentioned above.
    """


def generate_email(issuer_name, security_details, event_type, missing_data):
    missing_data_list = "\n- ".join(missing_data)
    email_template = f"""
Hi <Issuer Agent/Paying Agent>,

Issue summary:

Issuer: {issuer_name}
Security Name: {security_details}
Event Type: {event_type}

Upon review, we have identified the following mandatory data points that are currently missing:

- {missing_data_list}

To ensure accurate processing and timely communication to stakeholders, please provide the missing details at your earliest convenience. 
Let us know if further clarification is needed. 

Regards,
DTC CA Operations Team
"""
    return email_template


def generate_reserch_email(issuer_name, event_type, missing_data):
    missing_data_list = "\n- ".join(missing_data)
    email_template = f"""
Dear <Issuer Agent/Paying Agent>,

We recently became aware of {event_type} involving {issuer_name} through public resources/news and would like to request further details for accurate and timely processing. Kindly provide the official documentation and confirm the following mandatory attributes:

-{missing_data_list}

Your prompt confirmation and any supporting documents would be greatly appreciated.

Regards,
DTC CA Operations Team				
					
"""
    return email_template


# Add at the beginning after imports
if "email_type" not in st.session_state:
    st.session_state.email_type = "CA Event Email"
if "email_content" not in st.session_state:
    st.session_state.email_content = ""


def show(fileName):
    st.title("Full Call Processing")
    folder_path = os.path.join("Classified_PDFs", "Full Call")

    if os.path.exists(folder_path):
        st.success("Full Call folder exists")
        st.session_state.file_path = os.path.join(folder_path, fileName)
        st.write(f"File path: {st.session_state.file_path}")
        if os.path.isfile(st.session_state.file_path):
            st.success(f"The file {fileName} is available.")
        else:
            st.error(f"The file {fileName} is not available.")

        # Convert PDFs to JSON
        pdf_data = read_pdf(st.session_state.file_path)

        # Display JSON data
        if pdf_data:
            fullCallPrompt = prompt(pdf_data)

            llm = ChatBedrock(
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
                model_kwargs=dict(temperature=0),
            )
            messages = [{"role": "user", "content": f"""{fullCallPrompt}"""}]
            ai_msg = llm.invoke(messages)
            json_part = re.search(r"\{.*\}", ai_msg.content, re.DOTALL).group()

            # Parse the extracted JSON string
            documents_data = json.loads(json_part)
            # st.json(documents_data)
            finalData = pd.read_json(json.dumps(documents_data), orient="index")

            # Convert JSON to DataFrame
            finalData = pd.DataFrame(
                list(documents_data.items()),
                columns=["Attribute Name", "Extracted Value"],
            )

            # Divide the layout into two columns
            container_pdf, container_chat = st.columns([2, 1])

            # Display the PDF in the first column
            with container_pdf:
                try:
                    with open(st.session_state.file_path, "rb") as pdf_file:
                        binary_data = pdf_file.read()
                        base64_pdf = base64.b64encode(binary_data).decode("utf-8")
                        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
                        st.markdown(pdf_display, unsafe_allow_html=True)
                except FileNotFoundError:
                    st.error(f"File not found: {st.session_state.file_path}")

            # Display the DataFrame in the second column
            with container_chat:
                full_call_attributes = pd.read_csv("./Data/attributeList.csv")
                # Convert to lower case and remove special characters
                full_call_attributes["Attribute Name"] = (
                    full_call_attributes["Attribute Name"]
                    .str.lower()
                    .str.replace("[^a-z0-9]", "", regex=True)
                )
                finalData["Attribute Name"] = (
                    finalData["Attribute Name"]
                    .str.lower()
                    .str.replace("[^a-z0-9]", "", regex=True)
                )

                merged_df = pd.merge(
                    full_call_attributes, finalData, on="Attribute Name"
                )
                # st.dataframe(merged_df)

                edited_df = st.data_editor(
                    merged_df,
                    column_config={
                        "Attribute Name": {"editable": False},
                        "Attribute Type": {"editable": False},
                        "Extracted Value": {"editable": False},
                    },
                )

                not_available_df = edited_df[
                    edited_df["Extracted Value"] == "Not Available"
                ]

            container1, container2 = st.columns([1, 1])

            with container1:

                st.write("")
                issuer_name_value = edited_df.loc[
                    edited_df["Attribute Name"] == "issuername", "Extracted Value"
                ].values[0]

                sub_issue_type_value = edited_df.loc[
                    edited_df["Attribute Name"] == "subissuetype", "Extracted Value"
                ].values[0]

                attribute_names = not_available_df["Attribute Name"]
                attribute_names_list = attribute_names.tolist()

                email_content = generate_email(
                    issuer_name_value,
                    sub_issue_type_value,
                    "Call",
                    attribute_names_list,
                )

                st.session_state.email_content = email_content
                st.subheader("CA Event Email Draft")

                base64_text = st.text_area("", email_content, height=300)

                # Add a button to copy the text
                if st.button("Copy "):
                    pyperclip.copy(base64_text)
                    st.success("Text copied successfully!")

            with container2:

                st.write("")
                issuer_name_value = edited_df.loc[
                    edited_df["Attribute Name"] == "issuername", "Extracted Value"
                ].values[0]

                sub_issue_type_value = edited_df.loc[
                    edited_df["Attribute Name"] == "subissuetype", "Extracted Value"
                ].values[0]

                attribute_names = not_available_df["Attribute Name"]
                attribute_names_list = attribute_names.tolist()

                email_content_2 = generate_reserch_email(
                    issuer_name_value, "Call", attribute_names_list
                )
                st.subheader("CA Research Email Draft")
                base64_text_2 = st.text_area("", email_content_2, height=300)

                # Add a button to copy the text
                if st.button("Copy"):
                    pyperclip.copy(base64_text_2)
                    st.success("Text copied successfully!")

            # with open("C:/Users/yashvant.sridharan/myenv/Data/report.png", "rb") as img_file:
            #     img_bytes = img_file.read()

            # st.download_button(
            #     label="Download Report",
            #     data=img_bytes,
            #     file_name="report.png",
            #     mime="image/png",
            # )
            st.subheader("Notification Document")
            if len(not_available_df) != 0:
                # Specify the path to your PDF document
                reportPath = "./Data/Notifications_Template.pdf"

                # Read the PDF document from the specified path
                try:
                    with open(reportPath, "rb") as pdf_file:
                        binary_data = pdf_file.read()

                    # Encode the binary data to base64
                    base64_pdf = base64.b64encode(binary_data).decode("utf-8")

                    # Create the HTML iframe to display the PDF document
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'

                    # Display the iframe in Streamlit
                    st.markdown(pdf_display, unsafe_allow_html=True)
                except FileNotFoundError:
                    st.error(
                        f"The file at {reportPath} was not found. Please check the path and try again."
                    )

        else:
            st.warning("No PDF files found in the folder")
    else:
        st.error("Full Call folder does not exist")
