from typing import Literal
import httpx
from ServidorMCP.models.GitHubModels.ArchivoArbol import ArchivoArbol
from ServidorMCP.models.GitHubModels.ArchivoDiff import ArchivoDiff
from ServidorMCP.models.GitHubModels.Commit import Commit
from ServidorMCP.models.GitHubModels.DiferenciaCommits import DiferenciaCommits
from ServidorMCP.models.GitHubModels.EstructuraProyecto import EstructuraProyecto
from ServidorMCP.models.GitHubModels.PullRequest import PullRequest


class GitHubClient:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_pull_requests(
        self,
        owner: str,
        repo: str,
        estado: Literal["open", "closed", "all"] = "open",
        cantidad: int = 30,
    ) -> list[PullRequest]:
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls"
        params = {"state": estado, "per_page": min(cantidad, 100)}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers, params=params)
            response.raise_for_status()
            datos = response.json()

        pull_requests = []
        for pr in datos:
            # El endpoint /pulls no incluye stats; se obtienen del endpoint individual
            pr_detail = await self._get_pr_detail(owner, repo, pr["number"])
            pull_requests.append(
                PullRequest(
                    numero=pr["number"],
                    titulo=pr["title"],
                    estado=pr["state"],
                    autor=pr["user"]["login"],
                    rama_origen=pr["head"]["ref"],
                    rama_destino=pr["base"]["ref"],
                    fecha_creacion=pr["created_at"],
                    fecha_actualizacion=pr["updated_at"],
                    fecha_merge=pr.get("merged_at"),
                    commits=pr_detail.get("commits", 0),
                    archivos_cambiados=pr_detail.get("changed_files", 0),
                    adiciones=pr_detail.get("additions", 0),
                    eliminaciones=pr_detail.get("deletions", 0),
                    url=pr["html_url"],
                )
            )
        return pull_requests

    async def _get_pr_detail(self, owner: str, repo: str, numero: int) -> dict:
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{numero}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()
            return response.json()

    async def get_estructura_proyecto(
        self,
        owner: str,
        repo: str,
        ref: str = "HEAD",
    ) -> EstructuraProyecto:
        """
        Extrae la estructura de archivos y directorios del proyecto
        en un commit específico.

        Args:
            owner: Propietario del repositorio.
            repo: Nombre del repositorio.
            ref: SHA del commit, nombre de rama o tag. Por defecto 'HEAD'.

        Returns:
            EstructuraProyecto con metadatos del commit y árbol completo de entradas.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            # 1. Obtener el commit para extraer el SHA del árbol y metadatos
            r_commit = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/commits/{ref}",
                headers=self._headers,
            )
            r_commit.raise_for_status()
            datos_commit = r_commit.json()

            tree_sha = datos_commit["commit"]["tree"]["sha"]

            # 2. Obtener el árbol completo de forma recursiva
            r_tree = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/git/trees/{tree_sha}",
                headers=self._headers,
                params={"recursive": "1"},
            )
            r_tree.raise_for_status()
            datos_tree = r_tree.json()

        entradas = [
            ArchivoArbol(
                ruta=item["path"],
                tipo=item["type"],
                sha=item["sha"],
                tamanio=item.get("size"),
            )
            for item in datos_tree.get("tree", [])
        ]

        archivos = sum(1 for e in entradas if e.tipo == "blob")
        directorios = sum(1 for e in entradas if e.tipo == "tree")

        commit_sha = datos_commit["sha"]
        return EstructuraProyecto(
            commit_sha=commit_sha,
            commit_sha_corto=commit_sha[:7],
            mensaje_commit=datos_commit["commit"]["message"].split("\n")[0],
            autor=datos_commit["commit"]["author"]["name"],
            fecha=datos_commit["commit"]["author"]["date"],
            total_archivos=archivos,
            total_directorios=directorios,
            entradas=entradas,
        )

    async def get_archivo(
        self,
        owner: str,
        repo: str,
        ruta: str,
        ref: str = "HEAD",
    ) -> dict:
        """
        Descarga el contenido de cualquier archivo de texto desde GitHub.

        Returns:
            Dict con: contenido (str), ruta, sha, tamanio, html_url, encoding.
        """
        import base64

        url = f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{ruta}"
        params = {} if ref == "HEAD" else {"ref": ref}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers, params=params)
            response.raise_for_status()
            datos = response.json()

        if datos.get("type") != "file":
            raise ValueError(f"La ruta '{ruta}' no corresponde a un archivo.")

        encoding = datos.get("encoding", "base64")
        if encoding == "base64":
            try:
                contenido = base64.b64decode(datos["content"]).decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError(
                    f"El archivo '{ruta}' es binario y no puede representarse como texto."
                )
        else:
            contenido = datos.get("content", "")

        return {
            "ruta": datos["path"],
            "sha": datos["sha"],
            "tamanio": datos["size"],
            "html_url": datos["html_url"],
            "contenido": contenido,
        }

    async def get_archivo_markdown(
        self,
        owner: str,
        repo: str,
        ruta: str,
    ) -> tuple[str, str]:
        """
        Descarga el contenido de un archivo Markdown desde GitHub.

        Returns:
            Tupla (contenido: str, url: str).
        """
        import base64

        url = f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{ruta}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()
            datos = response.json()

        if datos.get("type") != "file":
            raise ValueError(f"La ruta '{ruta}' no corresponde a un archivo.")
        if not ruta.lower().endswith((".md", ".markdown")):
            raise ValueError(f"El archivo '{ruta}' no es Markdown.")

        contenido = base64.b64decode(datos["content"]).decode("utf-8")
        return contenido, datos["html_url"]

    async def get_diferencia_commits(
        self,
        owner: str,
        repo: str,
        base: str,
        head: str,
        incluir_patch: bool = True,
    ) -> DiferenciaCommits:
        """
        Compara dos commits (o ramas/tags) y devuelve los archivos cambiados
        junto con el diff unificado de cada uno.

        Args:
            owner: Propietario del repositorio.
            repo: Nombre del repositorio.
            base: SHA, rama o tag del commit base (más antiguo).
            head: SHA, rama o tag del commit destino (más reciente).
            incluir_patch: Si True incluye el patch (diff) de cada archivo.

        Returns:
            DiferenciaCommits con los commits intermedios, estadísticas globales
            y la lista de archivos modificados con su diff.
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/compare/{base}...{head}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()
            datos = response.json()

        commits_intermedios = [
            Commit(
                sha=c["sha"],
                sha_corto=c["sha"][:7],
                mensaje=c["commit"]["message"].split("\n")[0],
                autor=c["commit"]["author"]["name"],
                email_autor=c["commit"]["author"]["email"],
                fecha=c["commit"]["author"]["date"],
                url=c["html_url"],
            )
            for c in datos.get("commits", [])
        ]

        archivos = [
            ArchivoDiff(
                ruta=f["filename"],
                estado=f["status"],
                adiciones=f["additions"],
                eliminaciones=f["deletions"],
                cambios=f["changes"],
                patch=f.get("patch") if incluir_patch else None,
            )
            for f in datos.get("files", [])
        ]

        base_commit = datos["base_commit"]["sha"]
        head_commit = datos["merge_base_commit"]["sha"] if "merge_base_commit" in datos else datos["commits"][-1]["sha"] if datos.get("commits") else head

        return DiferenciaCommits(
            base_sha=base_commit,
            base_sha_corto=base_commit[:7],
            head_sha=datos["commits"][-1]["sha"] if datos.get("commits") else head,
            head_sha_corto=(datos["commits"][-1]["sha"] if datos.get("commits") else head)[:7],
            commits_intermedios=commits_intermedios,
            total_commits=datos.get("total_commits", len(commits_intermedios)),
            adiciones_total=sum(f.adiciones for f in archivos),
            eliminaciones_total=sum(f.eliminaciones for f in archivos),
            archivos_cambiados=archivos,
        )

    async def get_commits(
        self,
        owner: str,
        repo: str,
        rama: str,
        cantidad: int = 30,
        desde: str | None = None,
        hasta: str | None = None,
    ) -> list[Commit]:
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits"
        params: dict = {"per_page": min(cantidad, 100)}
        if rama.strip():
            params["sha"] = rama
        if desde:
            params["since"] = desde
        if hasta:
            params["until"] = hasta

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers, params=params)
            response.raise_for_status()
            datos = response.json()

        return [
            Commit(
                sha=c["sha"],
                sha_corto=c["sha"][:7],
                mensaje=c["commit"]["message"].split("\n")[0],  # solo la primera línea
                autor=c["commit"]["author"]["name"],
                email_autor=c["commit"]["author"]["email"],
                fecha=c["commit"]["author"]["date"],
                url=c["html_url"],
            )
            for c in datos
        ]
