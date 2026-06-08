import re
from dataclasses import dataclass


@dataclass
class Fragment:
    title: str          # Texto del encabezado
    section_path: str   # Ruta completa: "Guía > Instalación > Requisitos"
    content: str        # Cuerpo del fragmento (sin el encabezado)
    source: str         # URL o ruta del archivo origen
    level: int          # Nivel del encabezado (1, 2 o 3)


def fragment_markdown(content: str, source: str) -> list[Fragment]:
    """
    Divide un documento Markdown en fragmentos por encabezados (h1, h2, h3).
    Cada fragmento conserva su ruta de sección para mantener contexto.
    """
    heading_pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(content))

    if not matches:
        return [Fragment(
            title="Documento",
            section_path="Documento",
            content=content.strip(),
            source=source,
            level=1,
        )]

    fragments: list[Fragment] = []
    breadcrumb: dict[int, str] = {}

    for i, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()

        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start:end].strip()

        breadcrumb[level] = title
        for lvl in [l for l in breadcrumb if l > level]:
            del breadcrumb[lvl]

        section_path = " > ".join(breadcrumb[l] for l in sorted(breadcrumb))

        if body:
            fragments.append(Fragment(
                title=title,
                section_path=section_path,
                content=body,
                source=source,
                level=level,
            ))

    return fragments
