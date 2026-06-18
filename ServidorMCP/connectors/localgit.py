import asyncio
import re
from pathlib import Path
from typing import Optional

from ServidorMCP.config import GITHUB_TOKEN
from ServidorMCP.connectors.github import GitHubConnector

# Separadores de bajo nivel para parsear la salida de `git log` sin ambigüedad:
# %x1f (unit separator) entre campos, %x1e (record separator) entre commits.
# Así un mensaje multilínea no rompe el parseo.
_FIELD = "\x1f"
_RECORD = "\x1e"
_LOG_FMT = f"%H{_FIELD}%B{_FIELD}%an{_FIELD}%ae{_FIELD}%aI{_RECORD}"

# Mapeo de los códigos de estado de git a los nombres que usa la API de GitHub,
# para que el esquema de salida sea idéntico entre conectores.
_STATUS_MAP = {
    "A": "added",
    "M": "modified",
    "D": "removed",
    "R": "renamed",
    "C": "copied",
    "T": "changed",
}


class LocalGitError(Exception):
    """Error al ejecutar git sobre un repositorio local."""


def parse_github_slug(remote_url: str) -> Optional[str]:
    """Extrae 'owner/repo' de una URL remota de GitHub (ssh o https)."""
    m = re.search(r"github\.com[:/]([^/]+)/(.+?)(?:\.git)?/?$", remote_url.strip())
    return f"{m.group(1)}/{m.group(2)}" if m else None


class LocalGitConnector:
    """Lee el historial de un repositorio git clonado localmente vía subprocess.

    Expone la misma interfaz que un repositorio remoto (get_commits,
    get_commit, get_pull_requests) pero leyendo directamente el `.git` local,
    sin pasar por la API de GitHub ni sufrir rate limits.
    """

    def __init__(self, path: str):
        self.path = str(Path(path).expanduser().resolve())

    async def _git(self, *args: str) -> str:
        """Ejecuta `git -C <path> <args>` y devuelve su stdout."""
        proc = await asyncio.create_subprocess_exec(
            "git",
            "-C",
            self.path,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate()
        if proc.returncode != 0:
            raise LocalGitError(err.decode("utf-8", "replace").strip())
        return out.decode("utf-8", "replace")

    async def remote_slug(self) -> Optional[str]:
        """Devuelve 'owner/repo' del remoto origin, o None si no aplica."""
        try:
            url = await self._git("remote", "get-url", "origin")
        except LocalGitError:
            return None
        return parse_github_slug(url)

    def _commit_url(self, slug: Optional[str], sha: str) -> str:
        return f"https://github.com/{slug}/commit/{sha}" if slug else ""

    async def get_commits(
        self,
        branch: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 30,
    ) -> list[dict]:
        """Extrae el historial de commits del repositorio local."""
        args = ["log", f"--pretty=format:{_LOG_FMT}", f"-n{limit}"]
        if since:
            args += ["--since", since]
        if until:
            args += ["--until", until]
        if branch:
            args.append(branch)

        out = await self._git(*args)
        slug = await self.remote_slug()

        commits: list[dict] = []
        for record in out.split(_RECORD):
            record = record.strip("\n")
            if not record:
                continue
            sha, message, author, email, date = record.split(_FIELD)
            commits.append(
                {
                    "sha": sha,
                    "sha_short": sha[:7],
                    "message": message.strip(),
                    "author": author,
                    "email": email,
                    "date": date,
                    "url": self._commit_url(slug, sha),
                }
            )
        return commits

    async def get_commit(self, sha: str) -> dict:
        """Extrae el detalle de un commit incluyendo los diffs por archivo."""
        # Metadatos (sin diff)
        meta = await self._git("show", "-s", f"--pretty=format:{_LOG_FMT}", sha)
        c_sha, message, author, email, date = meta.split(_RECORD)[0].strip("\n").split(_FIELD)

        # numstat: additions / deletions / filename por archivo
        numstat = await self._git("show", sha, "--no-color", "--format=", "--numstat")
        # name-status: status / filename por archivo
        namestatus = await self._git("show", sha, "--no-color", "--format=", "--name-status")
        # patch completo, lo repartimos por archivo
        patch = await self._git("show", sha, "--no-color", "--format=", "--patch")
        patches = self._split_patches(patch)
        status_by_file = self._parse_name_status(namestatus)

        slug = await self.remote_slug()
        files: list[dict] = []
        for line in numstat.splitlines():
            if not line.strip():
                continue
            cols = line.split("\t")
            if len(cols) < 3:
                continue
            add, dele, filename = cols[0], cols[1], cols[2]
            files.append(
                {
                    "filename": filename,
                    "status": status_by_file.get(filename, "modified"),
                    "additions": int(add) if add.isdigit() else 0,
                    "deletions": int(dele) if dele.isdigit() else 0,
                    "patch": patches.get(filename, "")[:1500],
                }
            )

        return {
            "sha": c_sha,
            "sha_short": c_sha[:7],
            "message": message.strip(),
            "author": author,
            "email": email,
            "date": date,
            "url": self._commit_url(slug, c_sha),
            "files": files,
        }

    async def get_pull_requests(self, state: str = "all", limit: int = 30) -> list[dict]:
        """Los PRs son un concepto de GitHub: se delega a la API usando el
        remoto del clon local. Falla si el repo no tiene remoto de GitHub."""
        slug = await self.remote_slug()
        if not slug:
            raise LocalGitError(
                "El repositorio local no tiene un remoto de GitHub; "
                "los pull requests solo existen en GitHub."
            )
        owner, name = slug.split("/", 1)
        gh = GitHubConnector(GITHUB_TOKEN)
        return await gh.get_pull_requests(owner=owner, repo=name, state=state, limit=limit)

    @staticmethod
    def _parse_name_status(text: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for line in text.splitlines():
            if not line.strip():
                continue
            cols = line.split("\t")
            code = cols[0][:1]
            # En renombrados/copias el destino es la última columna.
            filename = cols[-1]
            result[filename] = _STATUS_MAP.get(code, "modified")
        return result

    @staticmethod
    def _split_patches(patch_text: str) -> dict[str, str]:
        """Reparte el patch completo en un dict {filename: patch_de_ese_archivo}."""
        result: dict[str, str] = {}
        current: Optional[str] = None
        buf: list[str] = []
        for line in patch_text.splitlines(keepends=True):
            if line.startswith("diff --git "):
                if current is not None:
                    result[current] = "".join(buf)
                buf = [line]
                m = re.match(r"diff --git a/.+? b/(.+)", line)
                current = m.group(1).rstrip("\n") if m else None
            else:
                buf.append(line)
        if current is not None:
            result[current] = "".join(buf)
        return result
