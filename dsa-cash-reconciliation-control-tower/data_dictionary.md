# Data dictionary

| Field | Meaning |
|---|---|
| `run_id` | Unique reconciliation run identifier. |
| `source_record_id` | Unique identifier assigned to each retained input row. |
| `reconciliation_id` | Group key shared by rows connected by the exact-key matching waterfall. |
| `source` | `SnapPay`, `BluePay`, `BMO`, or `JDE`. |
| `transaction_id` | Exact normalized transaction identifier; treated as text. |
| `account_type` | Canonical payment/account type from SnapPay or its configured source. |
| `batch_number` | Exact normalized batch key used in GL comparison. |
| `backend_id` | Exact normalized backend reference. |
| `customer_reference` | Exact normalized bank/customer reference. |
| `amount` | Signed `Decimal` value; never converted to binary float in matching logic. |
| `transaction_date` | Normalized source transaction/posting date. |
| `settlement_date` | Normalized settlement date, when provided. |
| `status` | Algorithmic disposition from the requested classification list. |
| `algorithm_status` | Original immutable result, retained if a manual override exists. |
| `override_status` | Separately audited reviewed status, if present. |
| `match_rule` | Exact waterfall rule(s) that connected a record. |
| `fields_used` | Canonical exact-key and amount fields used by the matching rules. |
| `amount_variance` | Difference at the applicable grouped comparison (left total minus right total). |
| `lineage` | Per-source component rows with IDs, keys, amount, dates, file, worksheet, source row, and record ID. |
| `source_file` | Input workbook or CSV filename. |
| `source_worksheet` | Configured worksheet name or `CSV`. |
| `source_row` | Spreadsheet row index including header; first data row is row 2. |
| `file_hash` | SHA-256 of the input file bytes, used for duplicate prevention. |
| `raw_values` | Original row values, retained separately from normalized canonical values. |
| `quality_issues` | Blank required field, malformed date, or malformed amount issue(s). |
| `candidate_only` | `true` for a date-window suggestion; it is not a confirmed match. |
| `bridge_row_difference` | Source input row count minus ledger disposition row count. Must equal zero. |
| `bridge_dollar_difference` | Source input signed dollars minus categorized output signed dollars. Must equal zero. |
| `override_id` | Unique manual-override audit identifier. |
| `prior_status`, `revised_status` | Status before/after a manual override; the original algorithm result is not rewritten. |
| `reason`, `preparer`, `timestamp` | Required override explanation, preparer, and UTC audit timestamp. |
| `approver`, `supporting_reference` | Optional approval identity and evidence reference. |

See `config/column_mappings.yaml` for required/optional canonical fields and
clearly marked source-header examples. The included synthetic mappings use
synthetic names and must not be mistaken for a processor's actual schema.
