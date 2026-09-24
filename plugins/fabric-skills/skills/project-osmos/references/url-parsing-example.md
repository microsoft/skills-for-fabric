# URL parser example

Use this inline parser in the agent's intake step; no separate script is required.
Apply the URL intake policy linked directly from `SKILL.md`.

## Path regexes

```python
import re
from urllib.parse import urlsplit

UUID_RE = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
WORKSPACE_PATH_RE = re.compile(rf"^/groups/(?P<ws>{UUID_RE})(?:/|$)", re.I)
LAKEHOUSE_PATH_RE = re.compile(
    rf"^/groups/(?P<ws>{UUID_RE})/lakehouses/(?P<lh>{UUID_RE})(?:/|$)", re.I
)
```

## Supported host check

```python
SUPPORTED_HOSTS = {
    "app.fabric.microsoft.com",
    "app.powerbi.com",
}
```

## Parser

```python
def parse_fabric_url(url: str):
    value = url.strip()
    if any(character.isspace() or character == "\\" for character in value):
        return None
    normalized = value if re.match(r"^[a-z][a-z0-9+.-]*://", value, re.I) else f"https://{value}"
    try:
        parts = urlsplit(normalized)
        port = parts.port
    except ValueError:
        return None
    if parts.scheme not in {"http", "https"} or parts.username is not None:
        return None
    host = parts.netloc.lower()
    if parts.hostname in {"app.fabric.microsoft.com", "app.powerbi.com"}:
        if parts.scheme != "https" or port not in {None, 443}:
            return None
        host = parts.hostname
    workspace_match = WORKSPACE_PATH_RE.match(parts.path)
    if not workspace_match:
        return None
    lakehouse_match = LAKEHOUSE_PATH_RE.match(parts.path)
    lakehouse_prefix = f"/groups/{workspace_match.group('ws')}/lakehouses/".lower()
    if parts.path.lower().startswith(lakehouse_prefix) and not lakehouse_match:
        return None
    if host not in SUPPORTED_HOSTS:
        return None
```

## Parser return

```python
    return {
        "workspace_id": workspace_match.group("ws"),
        "lakehouse_id": lakehouse_match.group("lh") if lakehouse_match else None,
        "host":         host,
    }
```
