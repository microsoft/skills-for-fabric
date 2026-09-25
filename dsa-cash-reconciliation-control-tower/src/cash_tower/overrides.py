from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from cash_tower.models import ManualOverride
from cash_tower.repository import ReconciliationRepository


def record_manual_override(
    repository: ReconciliationRepository,
    run_id: str,
    reconciliation_id: str,
    prior_status: str,
    revised_status: str,
    reason: str,
    preparer: str,
    approver: str | None = None,
    supporting_reference: str | None = None,
) -> ManualOverride:
    override = ManualOverride(
        override_id=str(uuid4()),
        reconciliation_id=reconciliation_id,
        prior_status=prior_status,
        revised_status=revised_status,
        reason=reason,
        preparer=preparer,
        timestamp=datetime.now(timezone.utc),
        approver=approver or None,
        supporting_reference=supporting_reference or None,
    )
    repository.add_override(run_id, override)
    return override
