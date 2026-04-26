import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from ServidorMCP.router.github_tools import register as register_github
from ServidorMCP.router.documentacion_tools import register as register_documentacion

load_dotenv()

mcp = FastMCP("ania-github")

register_github(mcp)
register_documentacion(mcp)

if __name__ == "__main__":
    mcp.run()
