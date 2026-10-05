from datetime import date
from pathlib import Path

from cash_tower.pipeline import run_reconciliation
from cash_tower.repository import SQLiteRepository
from cash_tower.synthetic import generate_synthetic_files

PROJECT_ROOT = Path(__file__).resolve().parents[1]
config = PROJECT_ROOT / "config" / "synthetic_column_mappings.yaml"
files = generate_synthetic_files(PROJECT_ROOT / "data" / "synthetic")
repository = SQLiteRepository(PROJECT_ROOT / "data" / "reconciliation.sqlite")
result = run_reconciliation(
    files, config, repository, date(2026, 9, 1), date(2026, 9, 30)
)
print(f"Run {result['run_id']}: {result['status']}")
print(f"Rows: {result['controls']['input_rows']}; bridge passed: {result['controls']['bridge_passed']}")
for source in result["controls"]["sources"]:
    print(f"{source['source']}: {source['input_rows']} rows; bridge {source['bridge_row_difference']} rows / {source['bridge_dollar_difference']} dollars")
