import os
import json
import re
from io import BytesIO
from typing import Dict, TypedDict, Annotated, Sequence
from PyPDF2 import PdfReader
import google.generativeai as genai
from langgraph.graph import Graph, StateGraph
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
import requests
from langchain_aws import ChatBedrock


# Function to read PDF content
def read_pdf(file_path): 
    content = "" 
    with open(file_path, 'rb') as file: 
        reader = PdfReader(file) 
        for page in reader.pages: 
            content += page.extract_text()
    return content

# Function to read PDF content from file-like object
def read_pdf_from_file(file): 
    content = "" 
    reader = PdfReader(file) 
    for page in reader.pages: 
        content += page.extract_text()
    return content

# Function to convert PDFs to JSON
def convert_pdfs_to_json(files):
    pdf_dict = {}
    for filename, file in files.items():
        pdf_content = read_pdf_from_file(file)
        pdf_dict[filename] = pdf_content
    return pdf_dict

# Function to save data to JSON file
def save_to_json(data, output_file):
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# Function to clean text
def clean_text(text):
    # Remove lines with a low proportion of alphabetic characters
    lines = text.split('\n')
    cleaned_lines = lines #[line for line in lines if len(line) > 0 and len(re.findall(r'[A-Za-z]', line)) / len(line) > 0.5]
    cleaned_text = ' '.join(cleaned_lines)
    
    # Replace newline characters with spaces
    cleaned_text = cleaned_text.replace('\n', ' ')
    
    return cleaned_text

# Function to clean JSON data
def clean_json(data):
    if isinstance(data, dict):
        return {key: clean_json(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [clean_json(item) for item in data]
    elif isinstance(data, str):
        return clean_text(data)
    else:
        return data


def create_prompt(classify):
     return f'''Objective:
 
            Classify each corporate action document from a given json document into one of the following categories:
            
            1. Merger – Documents related to mergers, acquisitions, consolidations, or takeovers.
            
            2. Full Call – Documents indicating the full redemption or recall of bonds, notes, or preferred stock.
            
            3. Partial Call – Documents indicating the partial redemption of bonds, notes, or preferred stock.
             
            Classification Criteria:
            
            • Merger
            
            • Keywords: (Merger, Acquisition, Takeover, Buyout, Consolidation, Absorption, Amalgamation, Business Combination, Strategic Acquisition, Stock-for-Stock Transaction, All-Cash Deal, Tender Offer, Exchange Offer, Asset Purchase, Share Exchange, Company Integration, Corporate Restructuring, Subsidiary Merger, Parent-Subsidiary Merger, Reverse Merger, Shareholder Approval, Anti-Trust Filing, Deal Valuation, Due Diligence, Voting Rights, Synergies, Regulatory Approval, Transaction Closure, Share Exchange Ratio, Ownership Transfer, Controlling Stake, Board Resolution, Acquisition Consideration, Majority Stake, Minority Stake Purchase, Hostile Takeover, Friendly Merger, Target Company, Bidding War, Regulatory Compliance, Post-Merger Integration, Acquisition Premium)
            
            • Full Call
            
            • Keywords: (Full Call, Callable Bond, Redemption Notice, Early Redemption, Prepayment, Repurchase, Mandatory Call, Bond Recall, Security Buyback, Call Price, Final Payment Date, Maturity Date, Par Value, Call Option, Debt Repayment, Call Event, Fixed Income Redemption, Issuer Redemption, Forced Redemption, Interest Payment Termination, Final Settlement, Capital Return, Bondholder Notification, CUSIP, ISIN, Record Date, Payment Date, Face Value, Bondholder Consent, Investor Notification, Debt Reduction Strategy, Refinancing, Regulatory Filing, Trustee Notification, Final Interest Payment, Final Redemption Price, Principal Repayment, Securities Recall, Debt Clearance, Liquidation Notice, Investor Compensation, Bond Expiry, Mandatory Full Call, Corporate Action Notice, Entire Principal Repayment, Full Call Execution)
            
            • Partial Call
            
            • Keywords: (Partial Call, Partial Redemption, Callable Bond, Early Partial Redemption, Repurchase of Securities, Selective Redemption, Partial Buyback, Call Price, Redemption Amount, Par Value, Call Event, Scheduled Partial Call, Issuer Option, Bondholder Notification, Debt Reduction, Pro-Rata Redemption, Redemption in Tranches, Lottery Redemption, ISIN, CUSIP, Record Date, Payment Date, Bondholder Payment, Interest Adjustment, Retained Bonds, Remaining Principal, Fractional Repayment, Debt Restructuring, Market Conditions, Voluntary Redemption, Repayment in Installments, Regulatory Compliance, Partial Debt Clearance, Fixed Income Securities Buyback, Issuer-Initiated Redemption, Callable Instrument, Principal Reduction, Early Retirement of Debt, Capital Adjustment, Outstanding Balance Reduction)
           
            
            
            Task:
            
            
            
            Classify each document from the json document into one of the four categories and provide:
            
            • A confidence score (0-100%) based on the presence and frequency of relevant keywords, phrases, and contextual understanding.
            
            • A justification explaining why that confidence score was assigned.
            
            
            
            Input: A JSON {classify} contains document names (keys) and the content inside the PDFs (values)
            
            
            Output: A structured JSON file listing the classification of the document with confidence scores and justification.
            
            
            
            Example Output: 
            
            {{
            
            "documents": [
                
            
                {{
            
                "file_name": "document_1.pdf",
            
                "document_type": "Full Call",
                
                "issuer": "Microsoft Corporation",
            
                "confidence_score": 92,
            
                "justification": "The document contains multiple instances of 'Full Call', 'Redemption Notice', 'Final Payment Date', and 'Issuer Redemption'. The presence of a clear redemption schedule and security identifiers (ISIN, CUSIP) further supports classification."
            
                }},
            
                {{
            
                "file_name": "document_2.docx",
            
                "document_type": "Merger",
                
                "issuer": "Apple Inc",
            
                "confidence_score": 85,
            
                "justification": "Several references to 'Acquisition', 'Share Exchange', and 'Strategic Acquisition' indicate an M&A transaction. However, some terms overlap with Exchange Offer documents, slightly reducing confidence."
            
                }},
            
            ]
            
            }}
            
            Additional Notes:
            
            • Documents with a confidence score below 50% should be flagged as "Unknown" and recommended for manual review.
            
            • The confidence score is calculated based on:
            
            • Number of category-specific keywords found.
            
            • Presence of relevant document structures (e.g., schedules, security identifiers).
            
            • issuer - Extract the company name from terms/keywords like 'issuer', 'issuing entity', or 'name of registrant' if not provided explicitly as 'issuer name' or similar.
            
            • Contextual relevance of terms.
            
            • The justification should clearly explain why the classification was made, referencing key terms or patterns.
            
            • Handle different file formats (PDF, DOCX, TXT, etc.) appropriately.

            • Give the output in JSON format. Dont include anything other than the output in JSON format.
            
            '''


def process_pdfs(files):
    # Convert PDFs to JSON
    pdf_data = convert_pdfs_to_json(files)
    
    
    

    # Clean the JSON data
    cleaned_pdf_data = clean_json(pdf_data)
    
    

    cleaned_pdf_data = json.dumps(cleaned_pdf_data,indent=2)
    print('Cleaned json :',cleaned_pdf_data)
    classify = create_prompt(cleaned_pdf_data)
    print('classify:',classify)
    llm = ChatBedrock(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    model_kwargs=dict(temperature=0),
    )
    messages =[{
           "role": "user",
           "content": f"""{classify}"""   
  }
    ] 
    ai_msg = llm.invoke(messages)
    json_part = re.search(r'\{.*\}', ai_msg.content, re.DOTALL).group()
 
# Parse the extracted JSON string
    documents_data = json.loads(json_part)

    return documents_data




