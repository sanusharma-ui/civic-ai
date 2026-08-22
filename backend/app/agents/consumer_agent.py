"""
Consumer Rights Agent — Consumer Protection specialist.

This module houses the Consumer Rights agent class with:
- Domain-specific capability metadata
- Example questions for the UI
- Jurisdiction helper (which commission based on claim amount)
- Legal notice / complaint letter builder (direct, bypasses LLM)
"""

from __future__ import annotations

from datetime import date
from typing import Any


class ConsumerAgent:
    """
    Specialised agent for India's Consumer Protection Act, 2019.

    The actual LLM orchestration happens in AgentService.
    This class provides metadata and stateless helper methods
    that can be used independently of the LLM loop.
    """

    agent_id = "consumer"
    name = "Consumer Rights Agent"
    description = (
        "Helps citizens understand consumer rights under the Consumer Protection "
        "Act, 2019, identify the fastest resolution path, and prepare complete "
        "legal notices and consumer complaint filings."
    )
    knowledge_domain = "consumer"
    version = "2.0"

    capabilities: list[str] = [
        "Explain consumer rights and relevant laws",
        "Identify the correct consumer commission (DCDRC/SCDRC/NCDRC) by claim amount",
        "Draft legal notices to sellers and service providers",
        "Guide through e-Daakhil online filing process",
        "Explain escalation ladder (NCH → legal notice → consumer court)",
        "Advise on e-commerce, banking, insurance, telecom, and real estate disputes",
        "Explain product liability and remedies under CPA 2019",
    ]

    example_questions: list[str] = [
        "I bought a defective phone from Amazon — what can I do?",
        "My builder has delayed possession for 3 years — how do I complain?",
        "The bank charged me incorrectly — how do I get a refund?",
        "How do I file a consumer complaint online?",
        "The airline cancelled my flight and won't refund — what are my rights?",
        "I was given a fake product by a local store — where do I complain?",
    ]

    # ------------------------------------------------------------------
    # Jurisdiction helper
    # ------------------------------------------------------------------

    @staticmethod
    def get_commission(claim_amount: float) -> dict[str, str]:
        """
        Determine the correct consumer commission by claim amount (₹).

        Returns a dict with 'commission', 'jurisdiction', 'website'.
        """
        if claim_amount <= 5_000_000:  # ≤ ₹50 lakh (actually ₹1 crore per CPA 2019)
            return {
                "commission": "District Consumer Disputes Redressal Commission (DCDRC)",
                "jurisdiction": "Claims up to ₹1 crore",
                "website": "edaakhil.nic.in",
                "note": "File in the district where you reside or where the seller has an office.",
            }
        if claim_amount <= 100_000_000:  # ≤ ₹10 crore
            return {
                "commission": "State Consumer Disputes Redressal Commission (SCDRC)",
                "jurisdiction": "Claims between ₹1 crore and ₹10 crore",
                "website": "edaakhil.nic.in",
                "note": "File at the state capital.",
            }
        return {
            "commission": "National Consumer Disputes Redressal Commission (NCDRC)",
            "jurisdiction": "Claims above ₹10 crore",
            "website": "ncdrc.nic.in and edaakhil.nic.in",
            "note": "NCDRC is located in New Delhi.",
        }

    # ------------------------------------------------------------------
    # Legal notice builder
    # ------------------------------------------------------------------

    @staticmethod
    def build_legal_notice(
        *,
        seller_name: str,
        product_service: str,
        complaint_description: str,
        demand: str,
        complainant_name: str = "[Your Full Name]",
        complainant_address: str = "[Your Complete Address]",
        seller_address: str = "[Registered Office Address of Seller]",
        purchase_date: str = "[Date of Purchase]",
        amount: str = "[Amount Paid]",
        order_reference: str = "",
        previous_attempts: str = "",
    ) -> str:
        """
        Generate a ready-to-use legal notice / consumer complaint letter.

        This is a direct helper — bypasses the LLM.
        Useful for testing and pre-built templates.
        """
        today = date.today().strftime("%d %B %Y")
        order_line = f"\n   Invoice / Order No.: {order_reference}" if order_reference else ""
        attempt_block = (
            f"\n\n4. I previously contacted your customer support — {previous_attempts} — "
            "but the matter remains unresolved."
            if previous_attempts
            else ""
        )

        return f"""{today}

To,
The Manager / Head — Customer Relations,
{seller_name},
{seller_address}

Subject: Legal Notice under the Consumer Protection Act, 2019 — {product_service}

Dear Sir/Madam,

I, {complainant_name}, residing at {complainant_address}, write to bring to your attention the following and to demand prompt redressal:

FACTS:
1. On {purchase_date}, I purchased {product_service} from {seller_name}{order_line}, for a total consideration of {amount}.

2. The said product / service was found to be defective / deficient:
   {complaint_description}

3. On account of the above, I have suffered loss, inconvenience, and mental agony.{attempt_block}

DEMAND:
I hereby demand the following within 15 (fifteen) days of receipt of this notice:
   {demand}

Should you fail to comply, I shall initiate appropriate legal proceedings before the Consumer Commission under the Consumer Protection Act, 2019, without further notice to you. All costs shall be at your account.

Yours faithfully,

{complainant_name}
{complainant_address}
Date: {today}

Note: Send via Registered Post AD and retain postal receipt."""

    @staticmethod
    def validate_complaint(data: dict[str, Any]) -> list[str]:
        """
        Check a consumer complaint for completeness.

        Returns a list of missing fields. Empty list = ready to draft.
        """
        issues: list[str] = []

        if not data.get("seller_name"):
            issues.append("Seller / company name not provided")
        if not data.get("product_service"):
            issues.append("Product or service description not provided")
        if not data.get("complaint_description"):
            issues.append("Nature of defect / deficiency not described")
        if not data.get("demand"):
            issues.append("What you are demanding (refund/replacement/compensation) not specified")

        return issues


consumer_agent = ConsumerAgent()
