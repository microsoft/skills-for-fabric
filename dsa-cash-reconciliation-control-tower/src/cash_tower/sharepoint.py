from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote
from typing import Any, Callable

import msal
import requests

APPROVED_EXTENSIONS = {".xlsx", ".xlsm", ".csv"}
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
READ_SCOPE = ["Sites.Selected"]


class SharePointConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class SharePointSettings:
    tenant_id: str
    client_id: str
    site_id: str
    drive_id: str
    root_folder: str

    @classmethod
    def from_environment(cls) -> "SharePointSettings":
        names = {
            "tenant_id": "MS_TENANT_ID",
            "client_id": "MS_CLIENT_ID",
            "site_id": "SHAREPOINT_SITE_ID",
            "drive_id": "SHAREPOINT_DRIVE_ID",
            "root_folder": "SHAREPOINT_ROOT_FOLDER",
        }
        values = {field: os.getenv(environment_name, "").strip()
                  for field, environment_name in names.items()}
        missing = [environment_name for field, environment_name in names.items() if not values[field]]
        if missing:
            raise SharePointConfigurationError(
                "SharePoint integration is not configured. Set: " + ", ".join(missing)
            )
        return cls(**values)


class GraphSharePointClient:
    """Read-only delegated Graph client; never issues a SharePoint write request."""

    def __init__(
        self,
        settings: SharePointSettings,
        token_provider: Callable[[], str] | None = None,
        session: requests.Session | None = None,
    ):
        self.settings = settings
        self.session = session or requests.Session()
        self.token_provider = token_provider or self._interactive_token

    def _interactive_token(self) -> str:
        authority = f"https://login.microsoftonline.com/{self.settings.tenant_id}"
        app = msal.PublicClientApplication(
            self.settings.client_id, authority=authority,
            token_cache=msal.SerializableTokenCache(),
        )
        result = app.acquire_token_interactive(scopes=READ_SCOPE)
        if "access_token" not in result:
            error = result.get("error_description") or result.get("error") or "Unknown authentication failure"
            raise RuntimeError(f"Microsoft Graph delegated authentication failed: {error}")
        return result["access_token"]

    def _get(self, url: str) -> dict[str, Any]:
        response = self.session.get(
            url, headers={"Authorization": f"Bearer {self.token_provider()}"},
            timeout=(10, 90),
        )
        response.raise_for_status()
        return response.json()

    def list_files(
        self, source_folders: dict[str, str],
        period_start: date | None = None, period_end: date | None = None,
    ) -> list[dict[str, Any]]:
        found = []
        for source, folder in source_folders.items():
            if source in {"Adjustments", "Configuration", "Output"}:
                continue
            path = "/".join(part for part in (self.settings.root_folder, folder) if part)
            escaped = quote(path, safe="/")
            endpoint = f"{GRAPH_BASE}/drives/{quote(self.settings.drive_id, safe='')}/root:/{escaped}:/children"
            found.extend(self._walk_folder(endpoint, source, period_start, period_end))
        return found

    def _walk_folder(
        self, endpoint: str, source: str, period_start: date | None, period_end: date | None
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        url: str | None = endpoint
        while url:
            payload = self._get(url)
            for item in payload.get("value", []):
                if "folder" in item:
                    child = f"{GRAPH_BASE}/drives/{quote(self.settings.drive_id, safe='')}/items/{quote(item['id'], safe='')}/children"
                    results.extend(self._walk_folder(child, source, period_start, period_end))
                    continue
                if "file" not in item or Path(item.get("name", "")).suffix.lower() not in APPROVED_EXTENSIONS:
                    continue
                if not self._within_metadata_period(item, period_start, period_end):
                    continue
                results.append({
                    "source": source,
                    "name": item["name"],
                    "item_id": item["id"],
                    "web_url": item.get("webUrl"),
                    "size": item.get("size"),
                    "created_at": item.get("createdDateTime"),
                    "modified_at": item.get("lastModifiedDateTime"),
                    "e_tag": item.get("eTag"),
                    "parent_path": item.get("parentReference", {}).get("path"),
                    "download_url": item.get("@microsoft.graph.downloadUrl"),
                })
            url = payload.get("@odata.nextLink")
        return results

    @staticmethod
    def _within_metadata_period(
        item: dict[str, Any], period_start: date | None, period_end: date | None
    ) -> bool:
        if period_start is None and period_end is None:
            return True
        modified = item.get("lastModifiedDateTime")
        if not modified:
            return False
        modified_date = datetime.fromisoformat(modified.replace("Z", "+00:00")).date()
        return (period_start is None or modified_date >= period_start) and (
            period_end is None or modified_date <= period_end
        )

    def download_file(self, metadata: dict[str, Any], destination: str | Path) -> dict[str, Any]:
        if Path(metadata["name"]).suffix.lower() not in APPROVED_EXTENSIONS:
            raise ValueError(f"Refusing to download unapproved file type: {metadata['name']!r}")
        destination_path = Path(destination)
        download_url = metadata.get("download_url")
        if not download_url:
            url = (f"{GRAPH_BASE}/drives/{quote(self.settings.drive_id, safe='')}/items/"
                   f"{quote(metadata['item_id'], safe='')}/content")
            response = self.session.get(
                url,
                headers={"Authorization": f"Bearer {self.token_provider()}"},
                timeout=(10, 180),
            )
        else:
            url = download_url
            response = self.session.get(url, timeout=(10, 180))
        response.raise_for_status()
        content = response.content
        digest = hashlib.sha256(content).hexdigest()
        final_path = destination_path / digest[:12] / Path(metadata["name"]).name
        final_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_out = {
            key: value for key, value in metadata.items()
            if key != "download_url"
        }
        metadata_out.update({"sha256": digest, "local_path": str(final_path)})
        final_path.write_bytes(content)
        return metadata_out

    def read_delta(
        self, repository: Any, delta_key: str = "sharepoint_delta_url"
    ) -> list[dict[str, Any]]:
        """Persist the Graph deltaLink for a later incremental poll."""
        previous = repository.get_state(delta_key)
        if previous:
            url = previous
        else:
            url = (f"{GRAPH_BASE}/drives/{quote(self.settings.drive_id, safe='')}"
                   "/root/delta")
        changes = []
        while url:
            payload = self._get(url)
            changes.extend(payload.get("value", []))
            next_link = payload.get("@odata.nextLink")
            delta_link = payload.get("@odata.deltaLink")
            if delta_link:
                repository.set_state(delta_key, delta_link)
            url = next_link
        return changes
