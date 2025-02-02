# classifier.py
import json
import os

class Classifier:
    def __init__(self):
        data_path = os.path.join("data", "data_dictionary.json")
        with open(data_path, "r") as f:
            self.data_dict = json.load(f)

    def classify_document(self, text: str) -> str:
        text_lower = text.lower()
        for category, cat_data in self.data_dict.items():
            if isinstance(cat_data, dict) and "keywords" in cat_data:
                keywords_list = cat_data["keywords"]
            elif isinstance(cat_data, list):
                keywords_list = cat_data
            else:
                keywords_list = []

            if any(kw.lower() in text_lower for kw in keywords_list):
                return category
        return "unknown" 