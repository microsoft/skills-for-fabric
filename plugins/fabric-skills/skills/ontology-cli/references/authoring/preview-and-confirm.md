# Preview & Confirm — Author-Time Design Review

> Before invoking `createItem` or `updateDefinition` (the LRO write), the agent **must** render a preview of what's about to be authored and obtain explicit user confirmation. This prevents schema drift, accidental property type changes, and unintended drops of bindings/relationships.

Two modes:

- **Greenfield** — creating a new ontology, or composing one from scratch → render a **proposal**.
- **Brownfield** — updating an existing ontology → render a **change set** vs. the `getDefinition` snapshot.

Both modes use the same emoji scheme and the same three layout tiers. ASCII boxes + emojis (no Mermaid, no ANSI) so the preview renders identically in any terminal, chat surface, or notebook.

---

## 1. Emoji legend (use these consistently)

| Emoji | Meaning            | Emoji | Meaning           |
| ----- | ------------------ | ----- | ----------------- |
| 🏢    | entity type        | ➕    | ADD (new)         |
| 🔑    | key / PK           | 🔧    | MOD (changed)     |
| 📈    | timeseries property| ➖    | DEL (removed)     |
| 🔗    | relationship       | ✅    | KEEP (unchanged)  |
| 🏬    | lakehouse source   | ⚠️    | risky change      |
| ⚡    | eventhouse source  | 📁    | group / folder    |

---

## 2. Tier selection (auto)

Pick the tier by **post-update entity count** (so a brownfield update with 4 existing + 26 new → Tier 3):

| Entities | Tier   | Layout                                                                  |
| -------- | ------ | ----------------------------------------------------------------------- |
| ≤ 5      | Tier 1 | ASCII boxes per entity + relationships rendered between boxes           |
| 6–15     | Tier 2 | Entity inventory table + adjacency-list relationships                   |
| 16+      | Tier 3 | Group summary + paginated inventory + adjacency list; details on demand |

---

## 3. Tier 1 — ≤ 5 entities (boxes)

```text
📁 Workspace : <ws-name>     Folder : <folder-name>
📊 Entities  : 2             🔗 Relations : 1            📌 Bindings : 3 (1 📈)

   ┌───────────────────────────┐                       ┌─────────────────────────────────┐
   │ 🏢 HUB                    │                       │ 🏢 AIRCRAFT                     │
   ├───────────────────────────┤                       ├─────────────────────────────────┤
   │ 🔑 HubId         string   │     🔗 operates       │ 🔑 TailNumber       string      │
   │    HubName       string   │   1 ───────────► *    │    Manufacturer     string      │
   │    City          string   │                       │ 📈 ObservedAt       datetime    │
   │                           │                       │ 📈 AltitudeFt       double      │
   │                           │                       │ 📈 GroundSpeedKts   double      │
   └───────────────────────────┘                       └─────────────────────────────────┘
   🏬 LH dbo.hubs                                      🏬 LH dbo.aircrafts (static)
                                                       ⚡ EH AircraftReadings (TS, ts=ObservedAt)

   🔗 operates  ➜  🏬 LH dbo.zava_hub_aircraft_link
       hub_id       →  Hub.HubId
       tail_number  →  Aircraft.TailNumber
```

**Box conventions:**

- One box per entity. Title = `🏢 <NAME>` in caps.
- Properties listed inside, one per line: `<emoji> <name>   <type>` aligned in two columns.
- `🔑` only on key properties (`entityIdParts`); `📈` only on timeseries properties.
- Below the box: `🏬 LH …` static binding line, then `⚡ EH …` timeseries binding line if present.
- Relationships: render between the two boxes when space permits. Otherwise list below all boxes:
  `🔗 <name>  ➜  🏬 LH <link-table>` then 2-space-indented key mappings.

---

## 4. Tier 2 — 6–15 entities (inventory + adjacency)

```text
🏢 ENTITY INVENTORY  (8 of 8)

   #  Entity         Key                Props  TS   Static binding         Timeseries binding
   ─  ─────────────  ─────────────────  ─────  ──   ─────────────────────  ────────────────────────
   1  Hub            🔑 HubId            4      —   🏬 dbo.hubs            —
   2  Aircraft       🔑 TailNumber       6      📈  🏬 dbo.aircrafts       ⚡ AircraftReadings
   3  Gate           🔑 GateId           3      —   🏬 dbo.gates           —
   4  Flight         🔑 FlightId         9      📈  🏬 dbo.flights         ⚡ FlightTelemetry
   5  Crew           🔑 CrewId           5      —   🏬 dbo.crew            —
   6  Passenger      🔑 PassengerId      7      —   🏬 dbo.passengers      —
   7  Booking        🔑 BookingId        6      —   🏬 dbo.bookings        —
   8  Maintenance    🔑 WorkOrderId      5      📈  🏬 dbo.maint_orders    ⚡ MaintEvents

🔗 RELATIONSHIPS (6)
   Hub        ─[ operates    ]─►  Aircraft        🏬 dbo.zava_hub_aircraft_link
   Aircraft   ─[ flies       ]─►  Flight          🏬 dbo.aircraft_flight_link
   Flight     ─[ departsFrom ]─►  Gate            🏬 dbo.flight_gate_link
   Flight     ─[ staffedBy   ]─►  Crew            🏬 dbo.flight_crew_link
   Passenger  ─[ bookedOn    ]─►  Booking         🏬 dbo.passenger_booking_link
   Maint      ─[ scheduledFor]─►  Aircraft        🏬 dbo.maint_aircraft_link
```

**Conventions:** prompt user with `show <name>` for full per-entity property list when they want it. Don't print property dumps for every entity at this tier — keeps the preview readable.

---

## 5. Tier 3 — 16+ entities (grouped, paginated, status-coded)

```text
📁 GROUPS
   Operations (8)   Customer (6)   Crew (5)   Maintenance (7)   Finance (4)   →  30 entities

🏢 INVENTORY  (showing 1–6 of 30 — "next" / "show <name>")

   S   #  Entity        Group        Key                Props  TS   Bindings
   ──  ─  ────────────  ───────────  ─────────────────  ─────  ──   ───────────────────────────────────
   ➕   9  Gate          Operations   🔑 GateId           3      —    🏬 dbo.gates                              (new)
   🔧   2  Aircraft      Operations   🔑 TailNumber       6      📈   🏬 dbo.aircrafts | ⚡ AircraftReadings    (+1 📈 prop)
   ✅   1  Hub           Operations   🔑 HubId            4      —    🏬 dbo.hubs                               (unchanged)
   ➖   4  Sector        Operations   🔑 SectorId         5      —    🏬 dbo.sectors                            (REMOVED)
   ➕  11  Part          Maintenance  🔑 PartNumber       4      —    🏬 dbo.parts                              (new)
   ➕  12  PartUsage     Maintenance  🔑 UsageId          5      📈   🏬 dbo.part_usage | ⚡ PartEvents          (new)
```

**Conventions:**

- The `S` (status) column is mandatory in brownfield previews and optional in greenfield (everything is `➕` so the column degenerates). For consistency, keep it in greenfield Tier 3 too.
- Group label comes from a user-supplied `group:` annotation in the spec, or from the entity's `namespace`. If neither is present, default group is `_ungrouped`.
- Pagination accepts `next`, `prev`, `page <n>`, `show <name>`, `all`.
- `all` may produce a very long output — warn the user before printing if `count > 50`.

---

## 6. Brownfield change-set (any tier)

The same diagram is rendered from the **proposed** tree, but every row carries a status emoji from the diff vs. `getDefinition`:

| Status | Meaning |
| ------ | ---------------------------------------------------------- |
| ➕     | added (new in this update)                                 |
| 🔧     | modified (existing element with changed definition)        |
| ✅     | kept (unchanged, but still in the envelope — see warning)  |
| ➖     | removed (will be deleted by this update)                   |

**`✅` rows are mandatory.** `updateDefinition` replaces the entire `parts[]` — anything not re-included in the envelope is dropped. Rendering `✅` rows reassures the user nothing is being silently removed.

### Per-property change rendering (Tier 1 box mode)

Inside an entity box, annotate the changed line directly:

```text
   │ 🔑 TailNumber       string                │
   │    Manufacturer     string                │
   │ 📈 ObservedAt       datetime              │
   │ 📈 AltitudeFt       double      🔧 was String  │
   │ 📈 GroundSpeedKts   double      ➕ added       │
```

### Risky-change callouts

Print the `⚠️ RISKY CHANGES` block **before** the affected-parts table, regardless of tier:

```text
⚠️  RISKY CHANGES
   🔧  valueType change   Aircraft.AltitudeFt   String → Double   (existing rows may fail to parse)
   🔧  key change         Aircraft.entityIdParts  TailNumber → AircraftId   (break-change for downstream)
   🔧  source change      Hub binding             dbo.hubs → dbo.hubs_v2    (verify intent)
   ➖  removal            Sector entity + 1 binding + 1 relationship   (confirm explicitly)
```

If **no** risky changes are detected, omit the section entirely (don't print "⚠️ RISKY CHANGES — none").

---

## 7. Affected parts list (always print)

After the diagram(s) and risky callouts, print a flat action list. One row per definition file, prefixed with status emoji:

```text
➕  .platform                                                          # displayName=ZavaAirlines_PreviewDemo
➕  definition.json
➕  EntityTypes/<HUB_ET>/definition.json
➕  EntityTypes/<HUB_ET>/DataBindings/<guid>.json                      # 🏬 LH dbo.hubs
🔧  EntityTypes/<AIRCRAFT_ET>/DataBindings/<existing-eh-guid>.json     # ⚡ EH AircraftReadings  +propertyBindings[GroundSpeedKts]
✅  EntityTypes/<HUB_ET>/DataBindings/<existing-guid>.json             # 🏬 LH dbo.hubs (carried forward)
➖  EntityTypes/<SECTOR_ET>/...                                        # entire entity tree
```

In greenfield mode this collapses to all `➕`. In brownfield mode every part in the proposed envelope shows up here with its diff status.

---

## 8. Confirmation prompt (mandatory)

The **final assistant message** must contain the complete preview at the selected
tier: the diagram or inventory, change details, risky-change callouts when present,
and the affected-parts list including every KEEP row. For Tier 1, retain the
unchanged entities and their properties, bindings, and relationships, not just the
new property. Reuse the generated preview text; a diagram printed by a tool or an
earlier message is not a substitute for the final preview.

Put explanations such as "no write was applied" before any user-requested
delegation or proposed-property lines. Repeat those lines together immediately
before the confirmation, with no intervening paragraph.

End the preview with **exactly one** of these single-line prompts:

- Greenfield: `Confirm and proceed with createItem? (yes / edit / cancel)`
- Brownfield: `Confirm and apply this change set with updateDefinition? (yes / edit / cancel)`

The selected prompt must be the final non-empty line, in plain text without
Markdown emphasis or backticks.

Do not auto-continue. Treat anything other than literal `yes` as `edit` (loop back to intent gathering) or `cancel` (discard envelope).

---

## 9. How to compute the diff

```bash
# Step A — fetch current state (after Step 3 of the workflow)
az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items/${ONTO_ID}/getDefinition" \
  --resource "https://api.fabric.microsoft.com" -o json > /tmp/onto.current.json
# (poll Location, then GET .../result — see COMMON-CLI.md § LRO)

# Step B — decode parts to a directory tree
mkdir -p /tmp/onto.current.tree
jq -r '.definition.parts[] | "\(.path)\t\(.payload)"' /tmp/onto.current.json |
while IFS=$'\t' read -r path b64; do
  mkdir -p "/tmp/onto.current.tree/$(dirname "$path")"
  printf '%s' "$b64" | base64 -d > "/tmp/onto.current.tree/$path"
done

# Step C — do the same for the proposed envelope (the agent already has it in memory)
# dump it under /tmp/onto.proposed.tree

# Step D — diff
diff -ruN /tmp/onto.current.tree /tmp/onto.proposed.tree
```

The agent parses this diff (or the in-memory equivalent) into the `➕ / 🔧 / ✅ / ➖` rows. Tier-3 status detection is at the part-level granularity (one entity's `definition.json` → one `🔧` if any field changed; bindings are tracked per-binding).

---

## 10. Agent contract

A skill consumer agent **must**:

1. Validate staged Kusto binding `itemId` values against the discovered parent Eventhouse IDs, then render the preview before any LRO write. Unresolved or mismatched IDs block confirmation. Greenfield → §3/§4/§5; brownfield → same tiers + §6 + §7.
2. Wait for explicit `yes` from the user.
3. On `edit`, regenerate the proposal from the user's revised intent — do **not** apply a partial update.
4. On `cancel`, leave the existing ontology untouched and discard the proposed envelope.
5. Persist the **post-write snapshot** alongside the spec so the next run's diff is reliable.

A skill consumer agent **must not**:

- Skip the preview because the change "looks small".
- Replace the final preview with a summary or a reference to earlier tool output.
- Compress `✅` rows out of the affected-parts list — replace-the-whole-tree semantics make every retained part user-visible.
- Auto-confirm in non-interactive mode without an explicit `--yes` flag from the caller.
