"""
RTI Agent — Right to Information specialist.

This module houses the RTI agent class with:
- Domain-specific capability metadata
- Example questions for the UI
- Draft RTI application helper (used by tests / direct calls)
- Agent persona validation
"""

from __future__ import annotations

from datetime import date
from typing import Any


class RTIAgent:
    """
    Specialised agent for India's Right to Information Act, 2005.

    The actual LLM orchestration happens in AgentService.
    This class provides metadata and stateless helper methods
    that can be used independently of the LLM loop.
    """

    agent_id = "rti"
    name = "RTI Agent"
    description = (
        "Helps citizens understand the Right to Information Act, 2005, "
        "identify the correct public authority, and prepare complete, "
        "ready-to-submit RTI applications and appeals."
    )
    knowledge_domain = "rti"
    version = "2.0"

    capabilities: list[str] = [
        "Explain RTI procedures, timelines, and fees",
        "Identify the correct Public Information Officer (PIO)",
        "Draft RTI applications ready for submission",
        "Guide through First Appeal and Second Appeal (CIC/SIC) process",
        "Explain exemptions under Section 8",
        "Help track RTI status",
    ]

    example_questions: list[str] = [
        "How do I file an RTI to check my PF withdrawal status?",
        "My RTI was rejected — how do I file an appeal?",
        "What is the fee for filing an RTI with the central government?",
        "Can I file RTI online? How?",
        "Which department should I send my RTI to for a ration card issue?",
        "How long does the government have to reply to my RTI?",
    ]

    # ------------------------------------------------------------------
    # Stateless helpers
    # ------------------------------------------------------------------

    @staticmethod
    def build_application(
        *,
        department: str,
        information_sought: str,
        applicant_name: str = "[Your Full Name]",
        applicant_address: str = "[Your Complete Address]",
        department_address: str = "",
        reference_details: str = "",
        government_level: str = "central",
    ) -> str:
        """
        Generate a ready-to-use RTI application.

        This is a direct helper — bypasses the LLM.
        Useful for testing and pre-built templates.
        """
        today = date.today().strftime("%d %B %Y")
        fee = "₹10/-" if government_level == "central" else "₹10/- (or as applicable in your state)"
        dept_addr = f"\n{department_address}" if department_address else ""
        ref_block = f"\n\nReference Details:\n{reference_details}" if reference_details else ""

        return f"""To,
The Public Information Officer,
{department},{dept_addr}

Subject: Application under the Right to Information Act, 2005

Respected Sir/Madam,

I, {applicant_name}, a citizen of India, residing at {applicant_address}, hereby request the following information under Section 6(1) of the Right to Information Act, 2005:

Information Sought:
{information_sought}{ref_block}

I am enclosing a fee of {fee} by way of Indian Postal Order / Demand Draft / online payment as required under the Act.

Please provide the above information within the prescribed time limit of 30 days as mandated under Section 7(1) of the RTI Act, 2005.

If the requested information is not available with your office, kindly transfer this application to the concerned Public Information Officer under Section 6(3) of the RTI Act, 2005, within 5 days, and intimate me accordingly.

Thanking you,

Yours faithfully,

{applicant_name}
{applicant_address}
Date: {today}"""

    @staticmethod
    def validate_request(data: dict[str, Any]) -> list[str]:
        """
        Check an RTI request for completeness.

        Returns a list of missing / unclear fields.
        An empty list means the request is ready to draft.
        """
        issues: list[str] = []

        if not data.get("department"):
            issues.append("Target department / public authority not specified")
        if not data.get("information_sought"):
            issues.append("Specific information sought is not described")
        if not data.get("government_level"):
            issues.append("Government level (central / state) not specified")

        return issues


rti_agent = RTIAgent()
