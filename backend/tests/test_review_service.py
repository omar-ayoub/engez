"""Tests for review_actions service layer — domain exceptions and business rules."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense
from app.services.review_actions import (
    approve,
    reject,
    correct,
    resubmit,
    _is_bulk_eligible,
    ReviewConflictError,
    ReviewNotFoundError,
    ReviewFieldNotAllowedError,
    ReviewNotRejectedError,
    ReviewNotAuthorizedError,
)


async def _create_pending_expense(db: AsyncSession, seed_data, **overrides) -> Expense:
    """Helper to create a pending expense for testing."""
    import uuid
    defaults = dict(
        id=str(uuid.uuid4()),
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        offline_id=str(uuid.uuid4()),
        amount=100.0,
        currency="EGP",
        status="pending",
        review_version=1,
        capture_mode="manual",
    )
    defaults.update(overrides)
    expense = Expense(**defaults)
    db.add(expense)
    await db.flush()
    return expense


async def test_approve_nonexistent_raises_not_found(db_session: AsyncSession, seed_data):
    with pytest.raises(ReviewNotFoundError):
        await approve(db_session, seed_data["company"].id, "nonexistent-id", seed_data["admin"].id, 1)


async def test_approve_stale_version_raises_conflict(db_session: AsyncSession, seed_data):
    expense = await _create_pending_expense(db_session, seed_data)
    await db_session.commit()

    with pytest.raises(ReviewConflictError) as exc_info:
        await approve(db_session, seed_data["company"].id, expense.id, seed_data["admin"].id, review_version=999)

    assert exc_info.value.current_version == 1
    assert exc_info.value.current_status == "pending"


async def test_reject_nonexistent_raises_not_found(db_session: AsyncSession, seed_data):
    with pytest.raises(ReviewNotFoundError):
        await reject(db_session, seed_data["company"].id, "nonexistent-id", seed_data["admin"].id, 1, "bad")


async def test_correct_disallowed_field_raises_error(db_session: AsyncSession, seed_data):
    expense = await _create_pending_expense(db_session, seed_data)
    await db_session.commit()

    with pytest.raises(ReviewFieldNotAllowedError) as exc_info:
        await correct(db_session, seed_data["company"].id, expense.id, seed_data["admin"].id, expense.review_version, "user_id", "hacked")

    assert exc_info.value.field_name == "user_id"


async def test_resubmit_non_rejected_raises_error(db_session: AsyncSession, seed_data):
    expense = await _create_pending_expense(db_session, seed_data)
    await db_session.commit()

    with pytest.raises(ReviewNotRejectedError):
        await resubmit(db_session, seed_data["company"].id, expense.id, seed_data["user"].id, "field_worker", expense.review_version)


async def test_resubmit_by_non_owner_raises_unauthorized(db_session: AsyncSession, seed_data):
    expense = await _create_pending_expense(db_session, seed_data, status="rejected")
    await db_session.commit()

    with pytest.raises(ReviewNotAuthorizedError):
        await resubmit(
            db_session, seed_data["company"].id, expense.id,
            "some-other-user", "field_worker", expense.review_version,
        )


def test_bulk_eligible_uses_config_threshold(seed_data):
    """Verify _is_bulk_eligible reads from settings, not hardcoded 0.8."""
    from unittest.mock import patch, MagicMock

    expense = MagicMock()
    expense.eta_verified = True
    expense.status = "pending"
    expense.ai_confidence = {"amount": 0.75, "vendor": 0.75}

    # At default threshold (0.8), 0.75 is below → not eligible
    assert _is_bulk_eligible(expense) is False

    # Lower the threshold to 0.7 → now eligible
    with patch("app.services.review_actions.settings") as mock_settings:
        mock_settings.BULK_APPROVE_CONFIDENCE_THRESHOLD = 0.7
        assert _is_bulk_eligible(expense) is True
