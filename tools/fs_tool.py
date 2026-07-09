"""LangChain BaseTool wrapper around the local filesystem search client."""

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from config import get_settings
from services.fs_client import search_local_files


class LocalSearchInput(BaseModel):
    """Input schema for LocalSearchTool."""

    name_contains: str = Field(default="", description="Substring to match against filenames.")
    extensions: list[str] = Field(
        default_factory=list,
        description="File extensions to filter by, e.g. ['.pdf', '.docx']. Empty = all types.",
    )
    modified_after: str = Field(
        default="",
        description="ISO date 'YYYY-MM-DD'. Only return files modified after this date.",
    )
    modified_before: str = Field(
        default="",
        description="ISO date 'YYYY-MM-DD'. Only return files modified before this date.",
    )


class LocalSearchTool(BaseTool):
    """Search the user-configured local directory for files matching given filters."""

    name: str = "local_search"
    description: str = (
        "Search for files in the user's local filesystem directory. "
        "Supports filtering by filename substring, file extension, and modified date range. "
        "Returns a list of matching files with name, path, type, modified date, and size."
    )
    args_schema: type[BaseModel] = LocalSearchInput

    def _run(
        self,
        name_contains: str = "",
        extensions: list[str] | None = None,
        modified_after: str = "",
        modified_before: str = "",
    ) -> list[dict]:
        settings = get_settings()

        root_dir: str = getattr(settings, "local_root_dir", "")
        if not root_dir:
            return []

        restricted_raw: str = getattr(settings, "restricted_dirs", "")

        try:
            return search_local_files(
                root_dir=root_dir,
                restricted_raw=restricted_raw,
                name_contains=name_contains,
                extensions=extensions or [],
                modified_after=modified_after,
                modified_before=modified_before,
            )
        except (ValueError, RuntimeError) as exc:
            raise RuntimeError(str(exc)) from exc

    async def _arun(
        self,
        name_contains: str = "",
        extensions: list[str] | None = None,
        modified_after: str = "",
        modified_before: str = "",
    ) -> list[dict]:
        return self._run(
            name_contains=name_contains,
            extensions=extensions,
            modified_after=modified_after,
            modified_before=modified_before,
        )


local_search_tool = LocalSearchTool()