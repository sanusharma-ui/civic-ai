import asyncio
import json
import logging
import hashlib
from pathlib import Path

from app.core.database import upsert_chunk, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

def generate_id(domain: str, title: str) -> str:
    # Use a hash to prevent duplicates on multiple runs
    unique_string = f"{domain}:{title}"
    return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

async def seed_data():
    logger.info("Initializing database...")
    await init_db()
    
    count = 0
    for domain_dir in DATA_DIR.iterdir():
        if not domain_dir.is_dir():
            continue
            
        domain = domain_dir.name
        logger.info(f"Processing domain: {domain}")
        
        for json_file in domain_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                for item in data:
                    title = item.get("title", "Untitled")
                    content = item.get("content", "")
                    section = item.get("section", "")
                    tags = item.get("tags", [])
                    
                    chunk_id = generate_id(domain, title)
                    
                    await upsert_chunk(
                        id=chunk_id,
                        domain=domain,
                        title=title,
                        content=content,
                        source=json_file.name,
                        metadata={"section": section, "tags": tags}
                    )
                    count += 1
                logger.info(f"  - Loaded {json_file.name}")
            except Exception as e:
                logger.error(f"Error processing {json_file}: {e}")
                
    logger.info(f"Successfully seeded {count} chunks into the database!")

if __name__ == "__main__":
    asyncio.run(seed_data())
