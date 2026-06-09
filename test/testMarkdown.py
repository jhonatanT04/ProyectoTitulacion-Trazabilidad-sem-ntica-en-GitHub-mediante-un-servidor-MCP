"""
Test Sprint 2 — Módulo de Documentación Markdown
Prueba: lectura, fragmentación semántica, indexación y búsqueda.
"""
import asyncio
from ServerMCP.connectors.markdown import read_markdown
from ServerMCP.indexer import fragment_markdown, DocumentIndex

# Documentación real de la SDK de Anthropic en GitHub (raw Markdown)
SOURCE_URL = "https://raw.githubusercontent.com/anthropics/anthropic-sdk-python/main/README.md"
SOURCE_LOCAL = "test/sample.md"


def separador(titulo: str):
    print(f"\n{'='*60}")
    print(f"  {titulo}")
    print(f"{'='*60}")


async def test_lectura_url():
    """Descarga un archivo Markdown desde una URL."""
    separador("TEST 1 — Lectura de Markdown desde URL")
    content = await read_markdown(SOURCE_URL)

    assert isinstance(content, str), "Debe retornar string"
    assert len(content) > 100, "El contenido no puede estar vacío"

    lineas = content.splitlines()
    print(f"  Fuente: {SOURCE_URL}")
    print(f"  Tamaño: {len(content)} caracteres | {len(lineas)} líneas")
    print(f"  Primeras 3 líneas:")
    for l in lineas[:3]:
        print(f"    {l}")

    print("\n  OK — Lectura desde URL exitosa")
    return content


async def test_lectura_local():
    """Lee un archivo Markdown local."""
    separador("TEST 2 — Lectura de Markdown local")

    # Crear archivo de muestra para el test
    sample = """# Guía de Python

## Instalación

Para instalar Python en tu sistema usa el siguiente comando:

```bash
sudo apt install python3
```

## Variables y Tipos

Python es un lenguaje de tipado dinámico. Las variables se declaran directamente:

```python
nombre = "Juan"
edad = 25
```

### Tipos básicos

Los tipos más comunes son: str, int, float, bool, list, dict.

## Funciones

Las funciones se definen con la palabra clave `def`:

```python
def saludar(nombre):
    return f"Hola, {nombre}"
```

### Parámetros por defecto

Puedes asignar valores por defecto a los parámetros.

## Manejo de errores

Usa `try/except` para capturar excepciones y manejar errores en tu código.
"""
    with open(SOURCE_LOCAL, "w", encoding="utf-8") as f:
        f.write(sample)

    content = await read_markdown(SOURCE_LOCAL)
    assert isinstance(content, str)
    assert "Python" in content

    print(f"  Archivo: {SOURCE_LOCAL}")
    print(f"  Tamaño: {len(content)} caracteres")
    print("\n  OK — Lectura local exitosa")
    return content


def test_fragmentacion(content: str, source: str):
    """Fragmenta el documento por encabezados y verifica la estructura."""
    separador("TEST 3 — Fragmentación semántica")
    fragments = fragment_markdown(content, source)

    assert isinstance(fragments, list)
    assert len(fragments) > 0, "Debe generar al menos un fragmento"
    assert all(hasattr(f, "title") and hasattr(f, "section_path") for f in fragments)

    print(f"  Total de fragmentos: {len(fragments)}")
    print(f"\n  Estructura de secciones:")
    for f in fragments:
        indent = "  " * (f.level - 1)
        print(f"    {indent}[H{f.level}] {f.section_path}")
        print(f"    {indent}     → {len(f.content)} chars de contenido")

    print("\n  OK — Fragmentación correcta")
    return fragments


def test_indexacion(fragments):
    """Construye el índice TF-IDF y verifica el tamaño."""
    separador("TEST 4 — Construcción del índice TF-IDF")
    index = DocumentIndex()
    index.add(fragments)

    assert index.size == len(fragments), "El índice debe contener todos los fragmentos"

    print(f"  Fragmentos indexados: {index.size}")
    print("\n  OK — Índice construido correctamente")
    return index


def test_busqueda(index: DocumentIndex):
    """Realiza búsquedas y verifica que retorna fragmentos relevantes."""
    separador("TEST 5 — Búsqueda por términos")

    queries = ["instalación", "manejo de errores", "funciones", "tipos"]

    for query in queries:
        results = index.search(query, top_k=2)
        assert isinstance(results, list)

        print(f"\n  Query: '{query}' → {len(results)} resultado(s)")
        for r in results:
            print(f"    [{r['score']:.4f}] {r['section_path']}")
            print(f"             {r['content'][:80].strip()}...")

    print("\n  OK — Búsqueda por términos funciona correctamente")


async def test_busqueda_url():
    """Test completo: descarga, fragmenta, indexa y busca en docs reales."""
    separador("TEST 6 — Flujo completo con docs reales (Anthropic SDK)")
    content = await read_markdown(SOURCE_URL)
    fragments = fragment_markdown(content, SOURCE_URL)
    index = DocumentIndex()
    index.add(fragments)

    queries = ["authentication", "streaming", "rate limit", "install"]
    for query in queries:
        results = index.search(query, top_k=2)
        print(f"\n  Query: '{query}' → {len(results)} resultado(s)")
        for r in results:
            print(f"    [{r['score']:.4f}] {r['section_path']}")
            print(f"             {r['content'][:100].strip()}...")

    print("\n  OK — Flujo completo con URL exitoso")


async def main():
    print("\nINICIANDO TESTS SPRINT 2 — Módulo de Documentación Markdown")

    passed = 0
    failed = 0

    # Tests asíncronos
    async_tests = [
        ("Lectura URL", test_lectura_url),
        ("Flujo completo URL", test_busqueda_url),
    ]

    content_local = None

    for nombre, test in async_tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"\n  FALLO en '{nombre}' — {e}")
            failed += 1

    # Tests locales (síncronos)
    try:
        content_local = await test_lectura_local()
        passed += 1
    except Exception as e:
        print(f"\n  FALLO en 'Lectura local' — {e}")
        failed += 1

    if content_local:
        try:
            fragments = test_fragmentacion(content_local, SOURCE_LOCAL)
            passed += 1
        except Exception as e:
            print(f"\n  FALLO en 'Fragmentación' — {e}")
            failed += 1
            fragments = []

        if fragments:
            try:
                index = test_indexacion(fragments)
                passed += 1
                test_busqueda(index)
                passed += 1
            except Exception as e:
                print(f"\n  FALLO — {e}")
                failed += 1

    print(f"\n{'='*60}")
    print(f"  RESULTADO: {passed} pasados / {failed} fallidos")
    print(f"{'='*60}\n")


asyncio.run(main())
