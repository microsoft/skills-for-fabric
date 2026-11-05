# Ontology MCP request files in PowerShell

Use the same absolute path to write, validate, and send a request. `Set-Location`
changes PowerShell's location, not the .NET process working directory: a relative
`[IO.File]::WriteAllText` path can write somewhere the CLI cannot read.

Prepare UTF-8-without-BOM JSON and re-read the exact file locally before any POST:

```powershell
$payloadPath = Join-Path $PWD 'ontology-tools-list-request.json'
[IO.File]::WriteAllText($payloadPath, '{"jsonrpc":"2.0","id":1,"method":"tools/list"}', [Text.UTF8Encoding]::new($false))
$null = Get-Content -LiteralPath $payloadPath -Raw -ErrorAction Stop |
    ConvertFrom-Json -ErrorAction Stop
```

Pass quoted `--body "@$payloadPath"` to `az rest`; unquoted `@` is PowerShell
splatting. Write, validate, and send in one invocation. Recreate path variables
and revalidate in fresh shells. Use a distinct file for each request.

Fix missing files, encoding, or invalid JSON locally, before contacting the
service. Do not send a discovery request to test whether payload preparation
worked. A failed discovery POST is still a real service call, not a local
argument-parser rejection.

See `consumption/examples.md`, indexed in `SKILL.md`, for headers, request scope,
and response capture without repeating a billed request.
