import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


INDEX_DIR: str = os.getenv("INDEX_DIR", ".docs_index")

SCRAPER_USER_AGENT: str = os.getenv(
    "SCRAPER_USER_AGENT",
    "tesis-mcp-bot/1.0 (+https://github.com/tesis-mcp)",
)

SCRAPE_CONCURRENCY: int = int(os.getenv("SCRAPE_CONCURRENCY", "5"))

SCRAPE_DELAY: float = float(os.getenv("SCRAPE_DELAY", "0.3"))

SCRAPE_MAX_PAGES: int = int(os.getenv("SCRAPE_MAX_PAGES", "50"))
