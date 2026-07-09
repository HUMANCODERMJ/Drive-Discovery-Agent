"""Drive search tool wrapper for LangChain agents."""

from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from config import get_settings
from services.drive_client import get_drive_service, list_files


class DriveSearchInput(BaseModel):
    """Input schema for Drive search queries."""

    q: str = Field(description="Google Drive API q parameter string")


class DriveSearchTool(BaseTool):
    """Search for files in Google Drive using a q parameter string."""

    name: str = "drive_search"
    description: str = (
        "Search for files in Google Drive using a q parameter string. "
        "Returns a list of matching files with name, type, modified date, and link."
    )
    args_schema: type[BaseModel] = DriveSearchInput

    def _run(self, *args: Any, **kwargs: Any) -> list[dict]:
        _ = kwargs.pop("run_manager", None)
        q = ""
        if args:
            first_arg = args[0]
            if isinstance(first_arg, dict):
                q = str(first_arg.get("q", ""))
            else:
                q = str(first_arg)
        else:
            q = str(kwargs.get("q", ""))

        settings = get_settings()
        service = get_drive_service(settings)
        files = list_files(service, settings.drive_folder_id, q=q)
        return [
            {
                "id": file_item.get("id", ""),
                "name": file_item.get("name", ""),
                "mimeType": file_item.get("mimeType", ""),
                "modifiedTime": file_item.get("modifiedTime", ""),
                "webViewLink": file_item.get("webViewLink", ""),
            }
            for file_item in files
        ]

    async def _arun(self, *args: Any, **kwargs: Any) -> list[dict]:
        _ = kwargs.pop("run_manager", None)
        return self._run(*args, **kwargs)


drive_search_tool = DriveSearchTool()