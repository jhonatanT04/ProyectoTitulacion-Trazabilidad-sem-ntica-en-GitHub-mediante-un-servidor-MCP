"""
Núcleo de la lógica de aplicación, independiente del transporte MCP.

- `retrieval`: orquesta la recuperación (embeddings ↔ fallback TF-IDF).
- `prompt_builder`: construye los prompts enviados al LLM.
"""
from ServidorMCP.core.prompt_builder import SYSTEM_PROMPT, build_explain_prompt
from ServidorMCP.core.retrieval import embed_index, retrieve

__all__ = [
    "embed_index",
    "retrieve",
    "SYSTEM_PROMPT",
    "build_explain_prompt",
]
