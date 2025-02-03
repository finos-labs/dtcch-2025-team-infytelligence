# extractor.py
import json
import re
from typing import Dict, Any

class Extractor:
    def __init__(self, llm):
        self.llm = llm

        # Different fields for each category
        self.FIELDS_BY_CATEGORY = {
            "stock_split": [
                {
                    "name": "CAEvent",
                    "description": (
                        "Look for language representing forward splits, reverse splits, or stock splits. "
                        "Output 'Stock Split' if found."
                    )
                },
                {
                    "name": "SubEvent",
                    "description": (
                        "Indicate if it is a 'forward split', 'reverse split', etc. If found in the doc."
                    )
                },
                {
                    "name": "CUSIP_ISIN_SEDOL",
                    "description": (
                        "A 9- or 12-digit alphanumeric security identifier. If multiple, record them all. "
                        "Look for 'CUSIP', 'ISIN', 'SEDOL'."
                    )
                },
                {
                    "name": "SecurityName",
                    "description": (
                        "Name of the security, e.g. 'Common Stock' or 'ETF'."
                    )
                },
                {
                    "name": "IssuerName",
                    "description": (
                        "Name of the company or issuer. E.g. 'Acme Corp'."
                    )
                },
                {
                    "name": "SplitEffectiveTradingDate",
                    "description": (
                        "Effective trading date when the split is recognized on an exchange. "
                        "Often found near 'split adjusted basis'."
                    )
                },
                {
                    "name": "RecordDate",
                    "description": (
                        "The record date when the company determines which shareholders are eligible. "
                        "Look for 'record date'."
                    )
                },
                {
                    "name": "SplitRatio",
                    "description": (
                        "The X-for-Y ratio describing the split. Output in the format 'Y-for-X', e.g. '2-for-1'."
                    )
                },
                {
                    "name": "NoOfSharesBeforeSplit",
                    "description": (
                        "Number of shares before the split. E.g. '100'."
                    )
                },
                {
                    "name": "NoOfSharesAfterSplit",
                    "description": (
                        "Number of shares after the split. E.g. '200'."
                    )
                },
                {
                    "name": "AnnouncementDate",
                    "description": (
                        "If mentioned, the date the split was announced. Format 'YYYY-MM-DD'."
                    )
                }
            ],
            "merger": [
                {
                    "name": "CAEvent",
                    "description": (
                        "Look for 'Agreement and Plan of Merger' or language describing a merger event. "
                        "Output 'Merger' if found."
                    )
                },
                {
                    "name": "SubEvent",
                    "description": (
                        "Whether the merger is stock-for-stock, cash transaction, or combination. "
                        "e.g. 'stock-for-stock'."
                    )
                },
                {
                    "name": "AcquiringCompany",
                    "description": (
                        "Look for 'Company A (acquiring)' or language indicating who is acquiring whom."
                    )
                },
                {
                    "name": "TargetCompany",
                    "description": (
                        "Look for 'Company B (target)' or who is being acquired."
                    )
                },
                {
                    "name": "AnnouncementDate",
                    "description": (
                        "Date the merger was publicly announced. Format 'YYYY-MM-DD'."
                    )
                },
                {
                    "name": "RecordDate",
                    "description": (
                        "Date when shareholders must hold shares to vote or receive merger benefits."
                    )
                },
                {
                    "name": "EffectiveDate",
                    "description": (
                        "The date the merger becomes legally effective. Format 'YYYY-MM-DD'."
                    )
                },
                {
                    "name": "PaymentDate",
                    "description": (
                        "If there's a cash/stock payout, the date shareholders receive it. Format 'YYYY-MM-DD'."
                    )
                },
                {
                    "name": "ExchangeRatio",
                    "description": (
                        "Number of acquiring-company shares given for each target-company share, e.g. '1.2-for-1'."
                    )
                },
                {
                    "name": "CashAmount",
                    "description": (
                        "Cash amount per share if part of the transaction is paid in cash."
                    )
                },
                {
                    "name": "DealValue",
                    "description": (
                        "Total value of the merger transaction if mentioned, e.g. '$5 billion'."
                    )
                }
            ],
            # If you have other categories (e.g., 'dividend'), add them here...
        }

    def extract_details(self, text: str, category: str) -> Dict[str, Any]:
        fields = self.FIELDS_BY_CATEGORY.get(category.lower(), [])
        if not fields:
            return {"error": f"No field definitions found for category '{category}'."}

        instructions = ""
        field_names = []
        for f in fields:
            instructions += f"- {f['name']}: {f['description']}\n"
            field_names.append(f['name'])

        prompt = f"""
You are a data extraction assistant. The document is classified as '{category}'.

Extract these fields exactly as named:
{instructions}

If a field is missing, use "N/A". Dates in YYYY-MM-DD.

Document Text:
{text}

Return ONLY valid JSON in this format:
{{
{', '.join([f'"{n}": "..."' for n in field_names])}
}}
"""

        raw_text = self.llm.predict(prompt)

        cleaned = re.sub(r"(?i)^\s*```json\s*|\s*```\s*$", "", raw_text.strip())

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            data = {f['name']: "N/A" for f in fields}

        # Ensure all fields are present
        for f in fields:
            if f['name'] not in data:
                data[f['name']] = "N/A"

        return data 