import os
from PyPDF2 import PdfReader
import json
import streamlit as st
import requests
import re
import pandas as pd
from streamlit_pdf_viewer import pdf_viewer
import base64
import pyperclip
from langchain_aws import ChatBedrock

# Initialize session state
if 'email_content' not in st.session_state:
    st.session_state.email_content = ""
if 'copied' not in st.session_state:
    st.session_state.copied = False
if 'email_type' not in st.session_state:
    st.session_state.email_type = "CA Event Email"
if 'file_path' not in st.session_state:
    st.session_state.file_path = ""



def read_pdf(file_path):
    content = ""
    with open(file_path, 'rb') as file:
        reader = PdfReader(file)
        for page in reader.pages:
            content += page.extract_text()
    return content

def convert_pdfs_to_json(directory):
    pdf_dict = {}
    for filename in os.listdir(directory):
        if filename.endswith('.pdf'):
            file_path = os.path.join(directory, filename)
            pdf_content = read_pdf(file_path)
            pdf_dict[filename] = pdf_content
    return pdf_dict

def prompt(partialCallJson):
   return f""" Objective: Extract and categorize entities from json containing corporate action documents related to partial call redemption event.
Ensure precision in identifying and structuring the extracted data.
 
Entities to extract:
 
    1.AccruedInterest / AccruedDividend:
    -Extract the accrued interest or dividend value, either per share or cumulative, and calculate the total based on shares/bonds outstanding if provided per share.
    -Value will be in USD $
    - If field is not available, mention as "Not Available"
    
    2.BaseCusip:
    -Extract the first 6 digits of the CUSIP
    -if multiple CUSIPs are provided, list all base CUSIPs
    - If field is not available, mention as "Not Available"
    
    3.Class: Use each unique CUSIP as a class
    -if no CUSIP is provided, format the class based on the document's %rate, security type, and maturity date (MM/YYYY).
    - If field is not available, mention as "Not Available"
    
    4.ConditionalPaymentApplicableFlag:
    -Mark as 'Yes' if terms/keywords like 'contingent payment' or 'conditional payment' are found in the document
    -otherwise, mark as 'No'.
    
    
    5.ContactE-mail:
    -Extract the contact email for the Trustee, Agent, or Paying Agent mentioned in the document.
    - If field is not available, mention as "Not Available"
    
    6.ContactPhoneNumber: Extract the phone number for the Trustee, Agent, or Paying Agent mentioned in the document.
    - If field is not available, mention as "Not Available"
      
    7.Currency:
    -Extract the currency of the redemption. This can be derived from redemption amount, accrued interest, premium amount.
    - If field is not available, mention as "Not Available"
    
    8.CUSIP:
    -Search for the 'CUSIP' keyword in the document and record the 9-digit alphanumeric identifier
    -if multiple CUSIPs are provided, list all, including those for 144a and RegS registrations.
    - If field is not available, mention as "Not Available"
    
    9.CAEvent:
    - Mention the event type as 'Partial Call'.
    
    10.CAEventCategory:
    - Whenever the CA Event is "Partial Call", the CA event Category should automatically be populated as 'Redemptions'.
    
    11.IssuerName:
    -Extract the company name from terms/keywords like 'issuer', 'issuing entity', or 'name of registrant' if not provided explicitly as 'issuer name' or similar.
    - If field is not available, mention as "Not Available"
    
    12.SecuritySymbol:
    -Search for the keyword 'ticker' and extract the identification code; if found with the exchange name (e.g., NYSE: WMT), extract only the ticker symbol.
    - If field is not available, mention as "Not Available"
    
    13.Maturity:
    -Extract the maturity date (MM/DD/YYYY format) from terms/keyword like 'stated maturity,' 'final payment date,' or 'principal payment date'; if not provided, leave blank.
    - If field is not available, mention as "Not Available"
    
    14.OutstandingNumberOfSecurities:
    -Extract the numeric count of outstanding securities at redemption. Only include numbers without currency symbols (e.g., ignore "$1,000,000"). If unavailable, output "Not Available".
    
    15.Premium/ CashRate:
    -Extract the premium value provided as part of the call; leave blank if no numerical value is provided.
    - If field is not available, mention as "Not Available"
    
    16.Price:
    -Extract the redemption price, either as a percentage (e.g., 100%) or a USD value (e.g., $25.00 per share), using keywords like 'redeemed at a price of' or 'redemption price'.
    - If field is not available, mention as "Not Available"
    
    17.PublicationDate / DatedDate / RecordDate:
    -Extract the publication, dated, or record date (e.g., 'announcement date')
    - if not provided, set this date to 30 days before the redemption date.
    - If field is not available, mention as "Not Available"
    
    18.Rate:
    -Extract the original notes rate in percentage format (e.g., 5%)
    - If field is not available, mention as "Not Available"
    
    19.RedemptionAmount:
    -Extract the total redemption amount as a numerical value
    -if not explicitly provided, calculate it by multiplying the offering price by the outstanding number of securities, excluding any accrued interest.
    - If field is not available, mention as "Not Available"
    
    20.RedemptionDate:
    -Extract the redemption date in MM/DD/YYYY format, found as a key value or in context like 'called for full redemption on July 22, 2024' or 'will be redeemed in full on August 30, 2010'.
    - If field is not available, mention as "Not Available"
    
    21.SubIssueType:
    -Determine the sub-issue type: label as 'Preferred Stock' if mentioned, 'Municipal Bonds' for school districts, municipalities, or states, 'Warrant' if warrants are redeemed, or 'Corporate Bond' if a company name (e.g., Walt Disney, Apple) appears. If not available, output "Not Available".
    
    22.Trustee/Agent/PayingAgent:
    -Extract the trustee, agent, or paying agent information, which may appear as 'paying agent', 'trustee', or 'agent', often in table format or phrases like 'addressed to corporate trust office' or 'by mail addressed to'.
    - If field is not available, mention as "Not Available"
    
    Additional Instructions for extracting:
    1. Text Extraction: Ensure the text is parsed from the pdf document accurately.
    2. Search Strategy: Utilize keyword search to locate relevant sections.
    3. Formatting: Follow the specified output formats strictly,especially for dates and currency values.
    4. Handling missing data: If any entity is not found, return "Not Available" for that entity in the output.
    5. If you find more than one value for an entity, combine them. Example: 'contactnumber: 1234567890, 0987654321'. Follow this for all the entities.
    6. Include all the field listed here (BaseCusip,Class,ConditionalPaymentApplicableFlag,ContactE-mail,ContactPhoneNumber,Currency,CUSIP,CAEvent,CAEventCategory,IssuerName,SecuritySymbol,Maturity,OutstandingNumberOfSecurities,Premium/ CashRate,Price,PublicationDate / DatedDate / RecordDate,Rate,RedemptionAmount,RedemptionDate,SubIssueType,Trustee/Agent/PayingAgent
       ). If the data is not present for any of the fields, Mention it as 'Not Avilable'.
    
    Input: A json {partialCallJson} contains document names (keys) and the content inside the PDFs (values)
    Output: extracted entities in json format.

    #Note: Add extracted values only when found. Do not add anything on your own. Include all the field is mentioned above.
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
if 'email_type' not in st.session_state:
    st.session_state.email_type = "CA Event Email"
if 'email_content' not in st.session_state:
    st.session_state.email_content = ""

def show(fileName):
    st.subheader("3. Partial Call Processing")
    folder_path = os.path.join("Classified_PDFs", "Partial Call")
    
    if os.path.exists(folder_path):
        # st.success("Partial Call folder exists")
        st.session_state.file_path = os.path.join(folder_path, fileName)
        # st.write(f"File path: {st.session_state.file_path}")
        # if os.path.isfile(st.session_state.file_path):
        #     st.success(f"The file {fileName} is available.")
        # else:
        #     st.error(f"The file {fileName} is not available.")
        
        # Convert PDFs to JSON
        pdf_data = read_pdf(st.session_state.file_path)
        
        # Display JSON data
        if pdf_data:
            fullCallPrompt = prompt(pdf_data)

            
            llm = ChatBedrock(
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            model_kwargs=dict(temperature=0),
            )
            messages =[{
                "role": "user",
                "content": f"""{fullCallPrompt}"""   
        }
            ] 
            ai_msg = llm.invoke(messages)
            json_part = re.search(r'\{.*\}', ai_msg.content, re.DOTALL).group()
 
            # Parse the extracted JSON string
            documents_data = json.loads(json_part)
            # st.json(documents_data)
            finalData =  pd.read_json(json.dumps(documents_data), orient='index')
            
            # Convert JSON to DataFrame
            finalData = pd.DataFrame(list(documents_data.items()), columns=['Attribute Name', 'Extracted Value'])
            st.session_state.response_partialCall = finalData
            # Divide the layout into two columns
            container_pdf, container_chat = st.columns([2, 1])

            # Display the PDF in the first column
            with container_pdf:
                try:
                    with open(st.session_state.file_path, "rb") as pdf_file:
                        binary_data = pdf_file.read()
                        base64_pdf = base64.b64encode(binary_data).decode('utf-8')
                        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
                        st.markdown(pdf_display, unsafe_allow_html=True)
                except FileNotFoundError:
                    st.error(f"File not found: {st.session_state.file_path}")

            # Display the DataFrame in the second column
            with container_chat:
                full_call_attributes = pd.read_csv("./Data/attributeList.csv")
                # Convert to lower case and remove special characters
                full_call_attributes['Attribute Name'] = full_call_attributes['Attribute Name'].str.lower().str.replace('[^a-z0-9]', '', regex=True)
                finalData['Attribute Name'] = finalData['Attribute Name'].str.lower().str.replace('[^a-z0-9]', '', regex=True)
                
                if 'edited_data_partialCall' not in st.session_state:
                    st.session_state.edited_data_partialCall = pd.merge(full_call_attributes, st.session_state.response_partialCall, on='Attribute Name')
                # Reset index and adjust to start from 1
                st.session_state.edited_data_partialCall.reset_index(drop=True, inplace=True)
                st.session_state.edited_data_partialCall.index += 1  # This changes the index to start at 1
                # Create form for data editing
                with st.form("data_editor_form"):
                    edited_df = st.data_editor(
                        st.session_state.edited_data_partialCall,
                        key='data_editor',
                        column_config={
                            'Attribute Name': {'editable': False},
                            'Attribute Type': {'editable': False},
                            'Extracted Value': {'editable': False}
                        },
                        disabled=False,
                        height=500
                    )
                    
                    submit_button = st.form_submit_button("Save Changes")
                    
                    if submit_button:
                        st.session_state.edited_data = edited_df
                        st.success("Changes saved successfully!")
                not_available_df = edited_df[edited_df['Extracted Value'] == "Not Available"]

            
            st.write("")
            issuer_name_value = edited_df.loc[edited_df['Attribute Name'] == "issuername", "Extracted Value"].values[0]

            sub_issue_type_value = edited_df.loc[edited_df['Attribute Name'] == "subissuetype", "Extracted Value"].values[0]

            attribute_names = not_available_df['Attribute Name']
            attribute_names_list = attribute_names.tolist()
            
            email_content = generate_email(issuer_name_value, sub_issue_type_value, 'Call', attribute_names_list)
            if len(not_available_df)!=0:
                st.session_state.email_content = email_content
                st.subheader("4. Missing Data Communication Email")
                base64_text = st.text_area('',email_content,height=300)

                # Add a button to copy the text
                if st.button('Copy '):
                    pyperclip.copy(base64_text)
                    st.success('Text copied successfully!')


            # with open("C:/Users/yashvant.sridharan/myenv/Data/report.png", "rb") as img_file:
            #     img_bytes = img_file.read()


            # st.download_button(
            #     label="Download Report",
            #     data=img_bytes,
            #     file_name="report.png",
            #     mime="image/png",
            # )
            

            if len(not_available_df)==0:
                st.subheader("Notification Document")
                # Specify the path to your PDF document
                reportPath = "./Data/Notifications_Template.pdf"

                # Read the PDF document from the specified path
                try:
                    with open(reportPath, 'rb') as pdf_file:
                        binary_data = pdf_file.read()

                    # Encode the binary data to base64
                    base64_pdf = base64.b64encode(binary_data).decode('utf-8')

                    # Create the HTML iframe to display the PDF document
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'

                    # Display the iframe in Streamlit
                    st.markdown(pdf_display, unsafe_allow_html=True)
                except FileNotFoundError:
                    st.error(f"The file at {reportPath} was not found. Please check the path and try again.")
            
        else:
            st.warning("No PDF files found in the folder")
    else:
        st.error("Full Call folder does not exist")
