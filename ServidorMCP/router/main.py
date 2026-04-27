import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

from ServidorMCP.router.github_tools import register as register_github
from ServidorMCP.router.documentacion_tools import register as register_documentacion

load_dotenv()

mcp = FastMCP("MCP-ania")

register_github(mcp)
register_documentacion(mcp)

if __name__ == "__main__":
    mcp.run()
