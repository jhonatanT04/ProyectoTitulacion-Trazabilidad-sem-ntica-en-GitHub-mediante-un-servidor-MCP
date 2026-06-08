from ServerMCP.app import mcp

# Importar tools para registrarlos en la instancia mcp
import ServerMCP.tools.github    # noqa: F401
import ServerMCP.tools.docs      # noqa: F401
import ServerMCP.tools.semantic  # noqa: F401

__all__ = ["mcp"]
