"""
Capa 2 — Tools MCP expuestas vía FastMCP.

Importar este paquete registra todas las tools en la instancia `mcp`
(el decorador `@mcp.tool()` corre al importar cada submódulo). Por eso
`server.py` solo necesita `import ServidorMCP.tools`.
"""
from ServidorMCP.tools import docs, github, semantic  # noqa: F401

__all__ = ["github", "docs", "semantic"]
