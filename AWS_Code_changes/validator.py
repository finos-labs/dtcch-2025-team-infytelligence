# validator.py
import json
from typing import Dict, Any
from datetime import datetime


class Validator:
    def validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        We only require 'CAEvent' to not be 'N/A'.
        'RecordDate' is now optional, so no validation error if 'N/A'.
        """
        errors = {}

        # Only require CAEvent
        required_fields = ["CAEvent"]

        # If you want to require more fields, add them here,
        # but do NOT add "RecordDate" if you don't want the error.

        for field in required_fields:
            if field not in data or data[field] == "N/A":
                errors[field] = "Required field missing"

        # We still check any field that ends with 'Date' for valid format,
        # but won't fail if it's 'N/A'.
        for key, val in data.items():
            if key.lower().endswith("date") and val != "N/A":
                try:
                    datetime.strptime(val, "%Y-%m-%d")
                except ValueError:
                    errors[key] = f"Invalid date format: {val}"

        if errors:
            raise ValueError(
                json.dumps({"validation_errors": errors}, indent=2))

        return data " and "{
  "stock_split": {
    "keywords": [
      "forward split",
      "reverse split",
      "stock split"
    ]
  },
  "merger": {
    "keywords": [
      "agreement and plan of merger",
      "merger transaction",
      "merger agreement"
    ]
  }
} 