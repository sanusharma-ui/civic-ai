import asyncio
import sys
from pathlib import Path

# Allow running this script directly from backend/scripts.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.groq_service import groq_service


async def main() -> None:
    result = await groq_service.generate(
        messages=[
            {
                "role": "system",
                "content": "You are a concise assistant.",
            },
            {
                "role": "user",
                "content": "Reply with one short sentence.",
            },
        ]
    )
    print(result["content"])


if __name__ == "__main__":
    asyncio.run(main())
