# Lakehouse Scheduling CLI — Live API Test Results

**Date**: 2026-06-18 20:45 IST  
**Workspace**: <TEST_WORKSPACE> (ID: <WORKSPACE_ID>)  
**Lakehouse**: <TEST_LAKEHOUSE> (ID: <LAKEHOUSE_ID>)

## Key Discovery: Correct Endpoint Format

**WRONG** (documented in initial skill version):
```
POST /v1/jobs/RefreshMaterializedLakeViews/schedules
```

**CORRECT** (validated via live testing):
```
POST /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules
```

**Pattern**: MLV refresh scheduling is **workspace + lakehouse scoped**, not a global job type.

## Test Results

### ✅ TEST 1: List Schedules (GET)
```powershell
GET /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules
```
- Status: **200 OK**
- Response: Empty list (no existing schedules)
- Conclusion: API works, returns `{value: []}` when no schedules exist

### ✅ TEST 2: Create Schedule (POST)
```powershell
POST /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules
```
- Status: **201 Created**
- Payload:
  ```json
  {
    "enabled": true,
    "configuration": {
      "startDateTime": "2026-06-18T20:45:00",
      "endDateTime": "2026-06-25T20:45:00",
      "localTimeZoneId": "UTC",
      "type": "Cron",
      "interval": 60
    }
  }
  ```
- Response:
  ```json
  {
    "id": "<SCHEDULE_ID>",
    "enabled": true,
    "createdDateTime": "2026-06-18T15:15:01.2333333",
    "configuration": {...},
    "owner": {
      "id": "3a5e2f0a-da7c-4f22-92d9-145d59583ff1",
      "type": "User"
    }
  }
  ```
- Conclusion: API works perfectly, returns schedule ID + owner info

### ✅ TEST 3: Delete Schedule (DELETE)
```powershell
DELETE /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules/{id}
```
- Status: **204 No Content**
- Schedule ID: `<SCHEDULE_ID>`
- Conclusion: API works, schedule deleted successfully

## Key Findings

1. **Endpoint Scope**: APIs are lakehouse-scoped, not global. Each lakehouse has its own set of schedules.
2. **Payload Structure**: Uses `configuration.type = "Cron"` + `interval` (in minutes), not `cronExpression` directly.
3. **Tool Choice**: `Invoke-RestMethod` works reliably. `az rest` has issues with Content-Type headers for POST.
4. **Owner Tracking**: API returns owner info (user ID + type) — useful for audit trails.
5. **Time Zone**: Supports `localTimeZoneId` (e.g., "UTC", "Central Standard Time").

## What This Means for the Skill

### Updates Needed

1. **Endpoint URLs** — Change from:
   ```
   /v1/jobs/RefreshMaterializedLakeViews/schedules
   ```
   To:
   ```
   /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules
   ```

2. **Payload Structure** — Use:
   ```json
   {
     "enabled": true,
     "configuration": {
       "type": "Cron",  // not "cronExpression"
       "interval": 60,  // minutes
       "startDateTime": "...",
       "endDateTime": "...",
       "localTimeZoneId": "UTC"
     }
   }
   ```

3. **Tool Recommendation** — Prefer `Invoke-RestMethod` or `curl` over `az rest` for POST operations (Content-Type header issue).

4. **Discovery Workflow** — User must provide:
   - Workspace name → find workspace ID
   - Lakehouse name → find lakehouse ID (within workspace)
   - MLV table names → cannot be discovered programmatically (GET /materializedLakeViews still returns 404)

## Updated API Coverage Matrix

| Operation | Endpoint | Status | Tested |
|-----------|----------|--------|--------|
| List schedules | GET `/workspaces/{ws}/lakehouses/{lh}/jobs/.../schedules` | ✅ Works | ✅ |
| Create schedule | POST `/workspaces/{ws}/lakehouses/{lh}/jobs/.../schedules` | ✅ Works | ✅ |
| Get schedule | GET `/workspaces/{ws}/lakehouses/{lh}/jobs/.../schedules/{id}` | ✅ Works (inferred) | ⏸ |
| Update schedule | PATCH `/workspaces/{ws}/lakehouses/{lh}/jobs/.../schedules/{id}` | ✅ Works (inferred) | ⏸ |
| Delete schedule | DELETE `/workspaces/{ws}/lakehouses/{lh}/jobs/.../schedules/{id}` | ✅ Works | ✅ |
| Trigger refresh | POST `/workspaces/{ws}/lakehouses/{lh}/jobs/.../instances` | ✅ Works (inferred) | ⏸ |
| List job history | GET `/workspaces/{ws}/lakehouses/{lh}/jobs/.../instances` | ✅ Works (inferred) | ⏸ |
| Get job status | GET `/jobs/instances/{id}` | ✅ Works (MS Learn documented) | ⏸ |
| Cancel job | POST `/jobs/instances/{id}/cancel` | ✅ Works (MS Learn documented) | ⏸ |

**Note**: "Inferred" means the endpoint pattern is consistent with what we tested + MS Learn docs confirm the pattern.

## Conclusion

**The skill is viable!** All core scheduling APIs work as expected. The only update needed is fixing the endpoint URLs to use the workspace + lakehouse scoped pattern.

**Next Steps**:
1. Update SKILL.md with correct endpoint URLs
2. Fix payload structure examples (use `interval` not `cronExpression`)
3. Update eval.yaml graders to check for workspace/lakehouse IDs in tool calls
4. Re-run tests with corrected endpoints
5. Submit PR

## Tool Choice Recommendation

For skill implementation, recommend **PowerShell `Invoke-RestMethod`** over `az rest`:
- `az rest` has Content-Type header issues for POST
- `Invoke-RestMethod` works reliably
- Better error handling with try/catch
- Returns parsed JSON directly

Example pattern for skill:
```powershell
$token = az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$response = Invoke-RestMethod `
    -Uri "https://api.fabric.microsoft.com/v1/workspaces/$wsId/lakehouses/$lhId/jobs/refreshMaterializedLakeViews/schedules" `
    -Method Post `
    -Body $payload `
    -Headers $headers
```
