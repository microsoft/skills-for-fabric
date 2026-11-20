# Data Fetcher

Use this procedure only when the requested values are not already supplied.
For a supplied dataset or completed authorized read result, retain its evidence
and hand it directly to Narrative Format; do not fetch it again.

## Optional registered capabilities

If current Plan visual data is requested, inspect the host's available registered
read capabilities and their actual input schemas and output contracts. Choose
by capability and authorized scope, not by an assumed tool name.

The contract must establish the target and a read-only way to retrieve its data.
Use documented scope/selection discovery when required. Resolve exact identities
from verified host context, captured scope or a confirmed lookup choice. Never
guess IDs or infer sheet type from an editor name or tool prefix.

Follow the registered contract's scope-consumption, sequencing, selection and
pagination rules. Retain captured scope throughout the request; do not consume
it repeatedly between targets. Do not expand scope or change existing filters.
If no suitable tool is available, ask the user for the data or name the missing
capability. Do not invent tools, arguments, response fields or alternate queries.

## Retrieve and classify

Retain the requested answer format before retrieval. For JSON-only output, call
the tool silently and wait for its result; do not announce a fetch, continuation
or failure in prose. Your first visible text is the final JSON object -- write
nothing before or between reader calls. Format the eventual outcome using the
same JSON contract.

1. Send only arguments supported by the registered schema for the confirmed
   target. Reads must not edit the Plan, change selection or save an artifact.
2. Await documented completion. A task ID, running status or acknowledgement
   is not a completed dataset.
3. Interpret outcome using the real contract, including application-level
   failures. Failure and cancellation are not successful empty results.
4. Continue pagination only through its documented registered capability for
   the same target, passing exactly the `nextCursor` the previous page
   returned. When a page returns no `nextCursor` (null or absent), stop: never
   guess or reuse a cursor. Avoid duplicate rows and incompatible snapshots. If
   continuation is unavailable, disclose incomplete coverage.
5. Validate attribution to the requested source before narrating results.
   Missing or conflicting attribution blocks live numeric claims.

## Retain evidence

Keep each dataset together with its provided labels, raw and formatted values,
row order, units, filters, time scope, freshness, total/subtotal classifications
and coverage. Unknown metadata stays unknown; retrieval time is not refresh time.

Preserve signs, nulls and blanks. A blank member is not automatically a total,
and missing rows are not zero. Do not parse display-only values as quantities
without verified numeric meaning, format, locale and unit.

| Outcome | Handling |
|---|---|
| Successful, usable result | Hand attributed evidence and coverage to Narrative Format |
| Successful, empty result | State that no data was returned, not that its total is zero |
| Failed or cancelled result | Report the actual outcome; do not narrate stale values or restart automatically |
| Running or incomplete result | Await supported completion or explicitly report incomplete retrieval |
| Partial usable result | Qualify observations to received evidence; do not claim full coverage |

When the requested output includes a values map, unavailable evidence is `null`,
not `{}`. Reserve an empty map for a successful, completed empty result.

Do not fall back to REST, SQL, FabricIQ, saved definitions or independent
semantic-model queries for missing narrative values.
