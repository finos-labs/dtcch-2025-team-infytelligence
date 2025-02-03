# planner.py
class Planner:
    def plan_workflow(self, document_type: str) -> list:
        """
        Example workflow steps for doc type.
        """
        workflows = {
            "stock_split": [
                "Ingestion",
                "Validation",
                "Shareholder Notification",
                "Reporting"
            ],
            "merger": [
                "Ingestion",
                "Legal Review",
                "Stakeholder Approval",
                "Reporting"
            ],
            "dividend": [
                "Ingestion",
                "Validation",
                "Approval",
                "Reporting"
            ],
            "unknown": [
                "Review",
                "Reporting"
            ]
        }
        return workflows.get(document_type.lower(), ["Review", "Reporting"]) 