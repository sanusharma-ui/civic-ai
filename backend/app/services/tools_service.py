"""
Agent Tools Service.

Defines all tools available to the RTI and Consumer agents as:
  1. Python async functions that actually execute the tool logic.
  2. Groq-compatible JSON schema definitions for the tool-calling API.

The ToolRunner class ties these together, executing tool calls returned
by the LLM and returning structured observations.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool schemas (Groq / OpenAI tool-calling format)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": (
                "Search the knowledge base for verified information about RTI "
                "procedures, consumer rights, government departments, laws, "
                "timelines, fees, or appeal processes. "
                "Always call this before answering factual questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Specific search query (e.g. 'RTI fee central government', 'consumer complaint time limit')",
                    },
                    "domain": {
                        "type": "string",
                        "enum": ["rti", "consumer", "general"],
                        "description": "Knowledge domain to search",
                    },
                },
                "required": ["query", "domain"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_department_info",
            "description": (
                "Get information about a specific government department, "
                "public authority, or consumer redressal body including "
                "contact details, jurisdiction, and how to approach them."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "department": {
                        "type": "string",
                        "description": "Name of the department or authority (e.g. 'EPFO', 'NCDRC', 'CIC', 'Food Department Delhi')",
                    },
                    "state": {
                        "type": "string",
                        "description": "Indian state name, or 'central' for Central Government. Optional.",
                    },
                },
                "required": ["department"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_clarification",
            "description": (
                "Request specific missing information from the citizen that is "
                "required to give a complete and accurate response. "
                "Use when you cannot proceed without knowing: the state, "
                "department, purchase date, amount, seller name, or nature of dispute. "
                "Ask only the most important missing piece."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The single most important clarifying question to ask the citizen.",
                    },
                    "context": {
                        "type": "string",
                        "description": "Brief explanation of why this information is needed.",
                    },
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_rti_application",
            "description": (
                "Generate a complete, properly formatted RTI application "
                "ready for submission. Use when you have all required facts: "
                "applicant name (or placeholder), department/public authority, "
                "state (or central), and the specific information being requested."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "applicant_name": {
                        "type": "string",
                        "description": "Full name of the applicant (use '[Your Name]' if not provided)",
                    },
                    "applicant_address": {
                        "type": "string",
                        "description": "Full address of the applicant",
                    },
                    "department": {
                        "type": "string",
                        "description": "Name of the public authority / department",
                    },
                    "department_address": {
                        "type": "string",
                        "description": "Address of the department (if known)",
                    },
                    "information_sought": {
                        "type": "string",
                        "description": "Clear, specific description of the information being requested",
                    },
                    "reference_details": {
                        "type": "string",
                        "description": "Any reference numbers, dates, or case details relevant to the request. Optional.",
                    },
                    "government_level": {
                        "type": "string",
                        "enum": ["central", "state"],
                        "description": "Whether this is a Central or State Government authority",
                    },
                },
                "required": [
                    "department",
                    "information_sought",
                    "government_level",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_complaint_letter",
            "description": (
                "Generate a complete legal notice / consumer complaint letter "
                "ready to be sent to the seller or service provider. "
                "Use when you have: product/service details, purchase date, "
                "amount, nature of defect/deficiency, and what the citizen wants."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "complainant_name": {
                        "type": "string",
                        "description": "Name of the complainant",
                    },
                    "complainant_address": {
                        "type": "string",
                        "description": "Address of the complainant",
                    },
                    "seller_name": {
                        "type": "string",
                        "description": "Name of the seller, company, or service provider",
                    },
                    "seller_address": {
                        "type": "string",
                        "description": "Registered address of the seller",
                    },
                    "product_service": {
                        "type": "string",
                        "description": "Name of the product or service purchased",
                    },
                    "purchase_date": {
                        "type": "string",
                        "description": "Date of purchase",
                    },
                    "amount": {
                        "type": "string",
                        "description": "Amount paid (include currency symbol)",
                    },
                    "order_reference": {
                        "type": "string",
                        "description": "Order number, bill number, or transaction ID. Optional.",
                    },
                    "complaint_description": {
                        "type": "string",
                        "description": "Clear description of the defect or deficiency",
                    },
                    "previous_attempts": {
                        "type": "string",
                        "description": "What the citizen already tried to resolve (customer care calls, emails, etc.). Optional.",
                    },
                    "demand": {
                        "type": "string",
                        "description": "What the citizen is demanding (refund, replacement, compensation, etc.)",
                    },
                },
                "required": [
                    "seller_name",
                    "product_service",
                    "complaint_description",
                    "demand",
                ],
            },
        },
    },
]

# Map tool name → schema for quick lookup
TOOL_SCHEMA_MAP: dict[str, dict] = {
    t["function"]["name"]: t for t in TOOL_SCHEMAS
}


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


async def _tool_search_knowledge(
    query: str,
    domain: str,
    *,
    retrieval_service: Any,
    agent: Any,
) -> str:
    """Execute a knowledge search and return a formatted context string."""
    try:
        docs = await retrieval_service.retrieve(
            agent=agent,
            query=query,
        )
        if not docs:
            return (
                f"No specific knowledge found for query: '{query}' in domain '{domain}'. "
                "Please use your trained knowledge about Indian RTI/Consumer law, "
                "and clearly note that you are doing so."
            )
        return retrieval_service.format_context(docs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("search_knowledge failed: %s", exc)
        return f"Knowledge search encountered an error: {exc}. Use your trained knowledge and note the source."


async def _tool_get_department_info(
    department: str,
    state: str | None = None,
) -> str:
    """Return static department / authority info."""
    # Normalise
    dept_lower = department.lower()
    info_map = {
        "epfo": (
            "EPFO — Employees' Provident Fund Organisation\n"
            "Type: Central Government (Ministry of Labour and Employment)\n"
            "RTI Portal: rtionline.gov.in → Ministry of Labour and Employment\n"
            "PIO: Regional PF Commissioner of your nearest EPFO Regional Office\n"
            "Contact: 1800-118-005 (toll-free) | epfindia.gov.in\n"
            "For RTI: Select 'Employees Provident Fund Organisation' on rtionline.gov.in"
        ),
        "cic": (
            "CIC — Central Information Commission\n"
            "Type: Central Government statutory body\n"
            "Second Appeal / Complaints for Central Government RTIs\n"
            "Website: cic.gov.in | Online filing: rtionline.gov.in\n"
            "Address: Central Information Commission, Club Building, Old JNU Campus, New Delhi 110067"
        ),
        "ncdrc": (
            "NCDRC — National Consumer Disputes Redressal Commission\n"
            "Jurisdiction: Consumer claims ABOVE ₹10 crore\n"
            "Website: ncdrc.nic.in | e-Daakhil: edaakhil.nic.in\n"
            "Address: Janpath Bhawan, A Wing, 5th Floor, Janpath, New Delhi 110001\n"
            "Helpline: 011-23712199"
        ),
        "nch": (
            "NCH — National Consumer Helpline\n"
            "Toll-free: 1800-11-4000 (Mon–Sat, 8 AM–8 PM)\n"
            "SMS: 8800001915\n"
            "Website: consumerhelpline.gov.in\n"
            "Purpose: Register and track consumer grievances; works with 1000+ companies."
        ),
        "ccpa": (
            "CCPA — Central Consumer Protection Authority\n"
            "Type: Central Government regulatory authority (CPA 2019)\n"
            "Purpose: Addresses unfair trade practices and misleading ads affecting class of consumers\n"
            "Website: ccpa-india.nic.in\n"
            "Complaint: File via consumerhelpline.gov.in"
        ),
    }

    for key, info in info_map.items():
        if key in dept_lower:
            return info

    # Generic response
    state_note = f" in {state}" if state else ""
    return (
        f"Specific information for '{department}'{state_note} is not in the local knowledge base. "
        "Suggestions:\n"
        f"1. Search '{department} PIO address' or '{department} consumer grievance' on Google.\n"
        "2. Visit the department's official website and look for 'RTI' or 'Grievance' section.\n"
        "3. For Central Government: use rtionline.gov.in and search by ministry name.\n"
        "4. For State Government: search '[State] RTI online portal'."
    )


async def _tool_ask_clarification(question: str, context: str | None = None) -> str:
    """Return a structured clarification request."""
    return json.dumps(
        {
            "clarification_needed": True,
            "question": question,
            "context": context or "",
        }
    )


async def _tool_draft_rti_application(
    department: str,
    information_sought: str,
    government_level: str,
    applicant_name: str = "[Your Full Name]",
    applicant_address: str = "[Your Complete Address]",
    department_address: str = "",
    reference_details: str = "",
) -> str:
    """Generate a complete RTI application text."""
    today = date.today().strftime("%d %B %Y")
    fee_note = "₹10/-" if government_level == "central" else "₹10/- (or as applicable in your state)"
    dept_addr_line = f"\n{department_address}" if department_address else ""
    ref_block = f"\n\nReference Details:\n{reference_details}" if reference_details else ""

    draft = f"""To,
The Public Information Officer,
{department},{dept_addr_line}

Subject: Application under the Right to Information Act, 2005

Respected Sir/Madam,

I, {applicant_name}, a citizen of India, residing at {applicant_address}, hereby request the following information under Section 6(1) of the Right to Information Act, 2005:

Information Sought:
{information_sought}{ref_block}

I am enclosing a fee of {fee_note} by way of Indian Postal Order / Demand Draft / online payment (via rtionline.gov.in) as required under the Act.

Please provide the above information within the prescribed time limit of 30 days as mandated under Section 7(1) of the RTI Act, 2005.

If the requested information is not available with your office, kindly transfer this application to the concerned Public Information Officer under Section 6(3) of the RTI Act, 2005, within 5 days of receipt, and intimate me accordingly.

Thanking you,

Yours faithfully,

{applicant_name}
{applicant_address}
Date: {today}"""

    return draft


async def _tool_draft_complaint_letter(
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
    """Generate a complete legal notice / consumer complaint letter."""
    today = date.today().strftime("%d %B %Y")
    order_line = f"\n   Invoice / Order No.: {order_reference}" if order_reference else ""
    attempt_block = (
        f"\n\n4. I previously contacted your customer support — {previous_attempts} — "
        "but the matter remains unresolved."
        if previous_attempts
        else ""
    )
    para_num = 5 if previous_attempts else 4

    draft = f"""{today}

To,
The Manager / Head — Customer Relations,
{seller_name},
{seller_address}

Subject: Legal Notice under the Consumer Protection Act, 2019 — {product_service}

Dear Sir/Madam,

I, {complainant_name}, residing at {complainant_address}, write to bring to your attention the following facts and to demand prompt redressal:

FACTS:
1. On {purchase_date}, I purchased {product_service} from {seller_name}{order_line}, for a total consideration of {amount}.

2. The said product / service was found to be defective / deficient in the following manner:
   {complaint_description}

3. On account of the above defect / deficiency, I have suffered loss, inconvenience, and mental agony.{attempt_block}

DEMAND:
In light of the above, I hereby demand the following within 15 (fifteen) days of receipt of this notice:
   {demand}

Should you fail to comply within the stipulated period, I shall be constrained to initiate appropriate legal proceedings before the District Consumer Disputes Redressal Commission under the Consumer Protection Act, 2019, and also approach the National Consumer Helpline (1800-11-4000), without any further notice to you. All costs and consequences of such proceedings shall be to your account.

Yours faithfully,

{complainant_name}
{complainant_address}
Contact: [Your Phone Number]
Email: [Your Email Address]

Note: Send this notice via Registered Post AD and retain the postal receipt as proof of delivery."""

    return draft


# ---------------------------------------------------------------------------
# Tool Runner
# ---------------------------------------------------------------------------


class ToolRunner:
    """
    Executes tool calls returned by the LLM and returns observations.

    Each tool call result is returned as a string observation that is
    injected back into the conversation as a "tool" role message.
    """

    def __init__(self, retrieval_service: Any, agent: Any) -> None:
        self._retrieval = retrieval_service
        self._agent = agent

    async def run(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> str:
        """Dispatch a tool call by name and return the string observation."""
        logger.info("Tool call: %s(%s)", tool_name, list(tool_args.keys()))

        try:
            if tool_name == "search_knowledge":
                return await _tool_search_knowledge(
                    query=tool_args["query"],
                    domain=tool_args.get("domain", self._agent.knowledge_domain),
                    retrieval_service=self._retrieval,
                    agent=self._agent,
                )

            if tool_name == "get_department_info":
                return await _tool_get_department_info(
                    department=tool_args["department"],
                    state=tool_args.get("state"),
                )

            if tool_name == "ask_clarification":
                return await _tool_ask_clarification(
                    question=tool_args["question"],
                    context=tool_args.get("context"),
                )

            if tool_name == "draft_rti_application":
                return await _tool_draft_rti_application(**tool_args)

            if tool_name == "draft_complaint_letter":
                return await _tool_draft_complaint_letter(**tool_args)

            return f"Unknown tool '{tool_name}'. Available tools: {list(TOOL_SCHEMA_MAP.keys())}"

        except Exception as exc:  # noqa: BLE001
            logger.error("Tool %s raised: %s", tool_name, exc)
            return f"Tool '{tool_name}' encountered an error: {exc}"
