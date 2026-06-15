from ServidorMCP.app import mcp

# Importar tools para registrarlos en la instancia mcp
import ServidorMCP.tools.github    # noqa: F401
import ServidorMCP.tools.docs      # noqa: F401
import ServidorMCP.tools.semantic  # noqa: F401

__all__ = ["mcp"]
