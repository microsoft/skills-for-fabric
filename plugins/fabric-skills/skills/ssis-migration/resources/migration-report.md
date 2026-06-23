# Phase 8 — Migration report

Emit a summary after migration so reviewers see what was converted, what was parked,
and what needs manual work.

## Template

```markdown
# SSIS → Fabric Migration Report: <package>

**Date:** <utc>   **Source:** <package>.dtsx   **Target workspace:** <ws>
**Complexity:** Low | Medium | High   **Status:** Complete | Partial | Blocked

## Items created in Fabric
| Fabric item | Type | From SSIS | Notes |
|---|---|---|---|
| <name> | DataPipeline | <package> | N activities |
| <name> | Warehouse | 3 OLE DB DBs | schemas edl/stg/dat |
| <name> | Connection | <CM> | Entra ID |

## Activity mapping
| SSIS task | Fabric activity | Status |
|---|---|---|
| ... | Script / Copy / Lookup / IfCondition | migrated / parked |

## Parked / manual items
| Item | Reason | Recommended action |
|---|---|---|
| OPENQUERY(NETSUITEDB) | no linked servers | NetSuite connector + Copy |

## Validation
| Check | SSIS | Fabric | Match |
|---|---|---|---|
| FT row count | | | |
| SUM(AMOUNT) | | | |
| Watermark | | | |

## Effort / follow-ups
- <remaining manual tasks, owners, dates>
```

## FT_NS_GL pre-filled summary

- **Created:** 1 DataPipeline (Copy + 7 Script/Lookup + 1 IfCondition), 1 Warehouse
  (schemas `edl`/`stg`/`dat`), Connections for each DB + NetSuite.
- **Migrated cleanly:** all 8 Execute SQL tasks, the single data flow (as Copy),
  precedence + `@COUNT>0` branch (as Lookup + IfCondition).
- **Parked:** `OPENQUERY(NETSUITEDB)` extract → needs a NetSuite connection.
- **Script Tasks:** 0 (low risk).
- **Dropped:** disabled file tasks + their variables.
- **Source mapping reference:** `FT_NS_GL_STTM.xlsx` (column-level lineage).
```
