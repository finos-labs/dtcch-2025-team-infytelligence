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

if 'copy_clicked' not in st.session_state:
    st.session_state.copy_clicked = False

# Initialize session state
if 'response_merger' not in st.session_state:
    st.session_state.response_merger = ""
    
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

def prompt(merger):
 return f""" 
           Objective: Extract and categorize entities from Markdown text containing corporate action documents related to a merger event. Ensure precision in identifying and structuring the extracted data.

Entities to extract:

1. CAEvent:
   - Look for phrases like "Agreement and Plan of Merger," "Merger Agreement," or similar terms indicating a merger event.
   - If any of the above phrases are found, classify the event as a "Merger."

2. CASubEvent:
   - Represents whether the merger is a stock-for-stock, Cash, or a Cash and Securities.
   - Look for: "In the Merger," "At the effective time," "Under the terms of the agreement," post that document defines the event sub-type.

3. AcquiringCompany:
   - Look for: Company A (acquiring company) "with and into" Company B (Target Company).
   - Identify the company mentioned as the acquirer or the entity that will survive the merger.
   - If field is not available, mention as "Not Available"

4. TargetCompany:
   - Look for: Company A (acquiring company) "with and into" Company B (Target Company).
   - Identify the company mentioned as the target or the entity that will be merged into the acquiring company.
   - If field is not available, mention as "Not Available"

5. AnnouncementDate:
   - The announcement date refers to the day when the companies involved in the merger or acquisition make the formal public announcement of the deal.
   - Look for phrases like "announcement date," "date of the announcement," or similar terms.
   - If field is not available, mention as "Not Available"

6. RecordDate:
   - The record date is the date used to determine which shareholders are eligible to receive the merger consideration, such as cash or shares in the acquirer.
   - Look for phrases like "record date," "date of record," or similar terms.
   - If field is not available, mention as "Not Available"

7. EffectiveDate:
   - The effective date is the date when the merger or acquisition is formally and legally consummated, and the deal is effective under the terms agreed upon in the merger agreement.
   - Look for phrases like "effective date," "date of effectiveness," or similar terms.
   - If field is not available, mention as "Not Available"

8. PaymentDate:
   - The payment date is the date when the consideration (e.g., cash, stock, or other forms of payment) is actually paid or delivered to the shareholders of the target company.
   - Look for phrases like "payment date," "date of payment," or similar terms.
   - If field is not available, mention as "Not Available"

9. ExchangeRatio:
   - Securities and Cash & Securities Transaction - how many shares of the acquiring company (acquirer) a target company's shareholder will receive for each share of the target company they hold.
   - Look for phrases like "exchange ratio," "conversion ratio," or similar terms.
   - If field is not available, mention as "Not Available"

10. CashAmount:
    - Transactions in Cash - Value per share for the target company.
    - Look for phrases like "cash amount," "cash consideration," or similar terms.
    - If field is not available, mention as "Not Available"

11. DealValue:
    - The deal value in the context of a merger refers to the total value of the transaction being undertaken between the two companies involved, typically expressed in monetary terms.
    - Look for phrases like "deal value," "total consideration," or similar terms.
    - If field is not available, mention as "Not Available"

12. Additions / Premiums:
    - Any Right as per the CVR agreement.
    - Look for phrases like "contingent value right," "CVR," or similar terms.
    - Mention only the CVR Count. Example: '1 CVR'
    - If field is not available, mention as "Not Available" 

13. TargetCompanyOwnershipDistributionPostTransaction:
    - Details how ownership of the combined entity will be split and how much will the target company own?
    - Scenario:  Shareholders: Expected to own ~31% of the combined company. So it'll be 31%.
    - Mention the percentage only.
    - If field is not available, mention as "Not Available"

14. CombinedPrimaryExchange:
    - Exchange where the company is traded.
    - Look for phrases like "primary exchange," "stock exchange," or similar terms.
    - If field is not available, mention as "Not Available"

15. VotingRequired:
    - Shareholders are usually given the option to vote at a specially convened meeting or through a proxy vote, where they can vote in favor, against, or abstain from the merger.
    - Look for phrases like "voting required," "shareholder vote," or similar terms.
    - If field is not available, mention as "Not Available"

16. Currency:
    - Represents the currency of Merger. This will be derived from merger/acquisition amount or anywhere in the document which has currency symbol.
    - If field is not available, mention as "Not Available"

17. CUSIP/ ISIN/ RIC/ SEDOL: 
    - CUSIP is a 9-digit alphanumerical identifier and ISIN is a 12-digit alphanumerical identifier, uniquely assigned to each issue/class/tranche. There may be multiple CUSIPs/ ISINs. Search for "CUSIP", "ISIN" keyword in the documents. If for 1 CUSIP/ ISIN is provided for 1 issue, mention it; if multiple list them all.
    - If field is not available, mention as "Not Available"
    
Additional Instructions for extracting:

1. Text Extraction: Ensure the text is parsed from the document accurately.
2. Search Strategy: Utilize keyword search to locate relevant sections.
3. Formatting: Follow the specified output formats strictly, especially for dates and currency values.
4. Handling missing data: If any entity is not found, return "Not Available" for that entity in the output.
5. If you find more than one value for an entity, combine them. Example: 'contactnumber: 1234567890, 0987654321'. Follow this for all the entities.
6. Include all the field listed here (,CAEvent,CASubEvent,AcquiringCompany,TargetCompany,AnnouncementDate,RecordDate,EffectiveDate,PaymentDate,ExchangeRatio,CashAmount,DealValue,Additions / Premiums,TargetCompanyOwnershipDistributionPostTransaction,CombinedPrimaryExchange,VotingRequired,Currency,CUSIP/ ISIN/ RIC/ SEDOL
    ). If the data is not present for any of the fields, Mention it as 'Not Avilable'.

Input: A Markdown text {merger}
Output: Extracted entities in JSON format.

Note: Add extracted values only when found. Do not add anything on your own. Include all the fields mentioned above.
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
    st.title("3. Merger Processing")
    folder_path = os.path.join("Classified_PDFs", "Merger")
    
    if os.path.exists(folder_path):
        # st.success("Merger folder exists")
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
            print("this is the prompt of merger",fullCallPrompt)
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
            st.session_state.response_merger = finalData
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
                full_call_attributes = pd.read_csv(r'C:\Users\yashvant.sridharan\myenv\Data\meregrAttribute.csv')
                # Convert to lower case and remove special characters
                full_call_attributes['Attribute Name'] = full_call_attributes['Attribute Name'].str.lower().str.replace('[^a-z0-9]', '', regex=True)
                finalData['Attribute Name'] = finalData['Attribute Name'].str.lower().str.replace('[^a-z0-9]', '', regex=True)

                # Initialize data outside widget area
                if 'edited_data_merger' not in st.session_state:
                    st.session_state.edited_data_merger = pd.merge(full_call_attributes, st.session_state.response_merger, on='Attribute Name')

                # Create form for data editing
                with st.form("data_editor_form"):
                    edited_df = st.data_editor(
                        st.session_state.edited_data_merger,
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
                
                # st.dataframe(merged_df)
                
                not_available_df = edited_df[edited_df['Extracted Value'] == "Not Available"]

            
                
            st.write("")
            issuer_name_value = edited_df.loc[edited_df['Attribute Name'] == "acquiringcompany", "Extracted Value"].values[0]

            sub_issue_type_value = edited_df.loc[edited_df['Attribute Name'] == "casubevent", "Extracted Value"].values[0]

            attribute_names = not_available_df['Attribute Name']
            attribute_names_list = attribute_names.tolist()
            
            email_content = generate_email(issuer_name_value, sub_issue_type_value, 'Merger', attribute_names_list)
            if len(not_available_df)!=0:
                
                st.session_state.email_content = email_content
                st.subheader("4. Missing Data Communication Email")
                # st.text_area("", email_content, height=300)
                # Create a text area for Base64 input
                base64_text = st.text_area('',email_content,height=300)

                # Add a button to copy the text
                if st.button('Copy '):
                    pyperclip.copy(base64_text)
                    st.success('Text copied successfully!')

                

            if len(not_available_df)==0:
                st.subheader("Notification Document")
                # Specify the path to your PDF document
                reportPath = 'C:/Users/yashvant.sridharan/myenv/Data/Notifications_Template.pdf'

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
