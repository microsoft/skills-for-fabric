# Control framework

## Recognition and population

Each adapter-retained row enters the reconciliation population once per
source. Duplicate file bytes in the same run/reporting period abort that run,
avoiding both duplicate counting and a partial successful population. The
same file hash may be used for a different reporting period. Rows with malformed
or blank required values remain in the run; they are not silently discarded.
They are routed to `Unmatched / Research Required` unless a reject/reversal/
refund or duplicate identifier takes precedence. Out-of-period rows are
excluded by their source transaction/posting date and recorded in the run log.
Rows with no parseable transaction date are retained as quality exceptions so
their existence remains visible.

## Ordered rule controls

The engine uses exact transaction ID, exact backend/customer reference, and
exact batch number in sequence. Amounts are summed as signed Decimals and
compared against a non-negative, configured tolerance. One-to-one and grouped
totals are supported. The report records the rule, fields, amount variance,
source amounts, dates, and row-level provenance.

Date proximity is an advisory **candidate** only. Candidate rows do not merge
into a reconciliation ID, do not affect the match status, and are labeled
`candidate_only`. Timing differences require a confirmed exact reference and
amount within tolerance plus a later bank settlement inside the configured
date window. Date-only evidence cannot confirm a match.

## Dispositions

The classifications are `Fully Matched`, `Timing Difference`, `Missing from
BluePay`, `Missing from Bank`, `Missing from GL`, `Amount Mismatch`,
`Reject/Reversal/Refund`, `Duplicate Identifier`, and `Unmatched / Research
Required`. Reject/reversal/refund and duplicate classifications take
precedence over a match; amount mismatches precede timing/full-match results.
A group is fully matched only when SnapPay, BluePay, BMO, and JDE evidence is
present. A matched upstream component that lacks bank or GL evidence stays an
exception, not a partial success.

## Source-to-output completeness bridge

For each source, the engine calculates:

```text
input rows and signed dollars
    = fully matched
    + timing differences
    + rejects / reversals / refunds
    + unresolved exceptions
```

The bridge is checked independently for row counts and signed dollar amounts.
Missing ledger rows, extra rows, or non-zero dollar/count differences mark a
run `Critical`. The dashboard and workbook preserve the `Critical` status; a
failed bridge is never presented as complete. The bridge partitions every
source row exactly once; it does not claim that processor, bank, and GL dollar
populations should be equal to one another.

Per-source controls include input, valid, and quality-rejected rows; input
dollars; matched, timing, reject/reversal/refund, and unresolved rows/dollars;
duplicate identifier counts; amount mismatch counts; missing GL batches; and
row/dollar bridge differences.

## Manual review

An override must identify a reconciliation group, exact prior algorithm
status, revised status, reason, and preparer. Timestamp is captured in UTC;
approver and supporting reference are optional. The repository rejects
overrides with an incorrect prior status or missing required audit fields.
Overrides are append-only in a separate table and are included in reporting.
They never mutate source values or `algorithm_status`.

## Reconciliation evidence

The summary and controls are built from the same ledger/source detail that is
exported in Excel. `Control Totals` is broken out by source, and summary rows
carry the same per-source counts and amounts. Candidate-only rows are included
in the exception queue but not in confirmed ledger totals. Exports retain the
bridge result and bridge failures in `Run Log`.
