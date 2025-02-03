# classifier.py
import json
import os
from dotenv import load_dotenv

load_dotenv()

class Classifier:
    def __init__(self):
        data_path = os.getenv("DATA_DICT_PATH", "data/data_dictionary.json")
        if not os.path.exists(data_path):
            print(f"Warning: data_dictionary not found at {data_path}")
            self.data_dict = {}
        else:
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
