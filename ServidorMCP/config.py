import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
# Modelo de embeddings para recuperación semántica de documentación.
# Si no hay OPENAI_API_KEY o la llamada falla, el índice cae a TF-IDF.
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# --- Indexación y scraping de documentación ---
# Carpeta donde se persisten los índices de documentación ya scrapeados.
INDEX_DIR: str = os.getenv("INDEX_DIR", ".docs_index")
# User-Agent identificable para el scraper (buena práctica ética/legal).
SCRAPER_USER_AGENT: str = os.getenv(
    "SCRAPER_USER_AGENT",
    "tesis-mcp-bot/1.0 (+https://github.com/tesis-mcp)",
)
# Nº máximo de peticiones HTTP simultáneas al scrapear un sitio.
SCRAPE_CONCURRENCY: int = int(os.getenv("SCRAPE_CONCURRENCY", "5"))
# Pausa (segundos) entre peticiones para no saturar el servidor remoto.
SCRAPE_DELAY: float = float(os.getenv("SCRAPE_DELAY", "0.3"))
# Tope de páginas a descargar por librería.
SCRAPE_MAX_PAGES: int = int(os.getenv("SCRAPE_MAX_PAGES", "50"))
