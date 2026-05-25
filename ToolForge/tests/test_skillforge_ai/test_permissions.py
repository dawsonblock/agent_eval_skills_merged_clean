"""
Tests for skillforge_ai.permissions — PermissionBroker, classify, check.
"""

from __future__ import annotations
# mypy: disable-error-code=import-untyped

import pytest

from skillforge_ai.models import RiskLevel  # type: ignore[import-untyped]
from skillforge_ai.permissions import (
    ApprovalRequiredError,
    PermissionBroker,
    PermissionDeniedError,
)  # type: ignore[import-untyped]


class TestClassify:
    def test_safe_action(self):
        broker = PermissionBroker(interactive=False)
        assert broker.classify("read_local_files") == RiskLevel.SAFE

    def test_approval_required_action(self):
        broker = PermissionBroker(interactive=False)
        assert (
            broker.classify("run_shell_commands")
            == RiskLevel.APPROVAL_REQUIRED
        )

    def test_blocked_action(self):
        broker = PermissionBroker(interactive=False)
        assert broker.classify("execute_untrusted_code") == RiskLevel.BLOCKED

    def test_unknown_action_defaults_to_approval_required(self):
        broker = PermissionBroker(interactive=False)
        # Unknown actions default to APPROVAL_REQUIRED for safety
        assert (
            broker.classify("some_unknown_action")
            == RiskLevel.APPROVAL_REQUIRED
        )


class TestCheck:
    def test_safe_passes_without_approval(self):
        broker = PermissionBroker(interactive=False)
        # Should not raise
        broker.check("read_local_files", None)

    def test_blocked_raises_denied(self):
        broker = PermissionBroker(interactive=False)
        with pytest.raises(PermissionDeniedError):
            broker.check("execute_untrusted_code", None)

    def test_approval_required_with_auto_approve(self):
        broker = PermissionBroker(interactive=False, auto_approve=True)
        # Should not raise
        broker.check("run_shell_commands", None)

    def test_approval_required_non_interactive_raises(self):
        broker = PermissionBroker(interactive=False, auto_approve=False)
        with pytest.raises(ApprovalRequiredError):
            broker.check("run_shell_commands", None)


class TestIsSafe:
    def test_safe_action(self):
        broker = PermissionBroker()
        assert broker.is_safe("read_local_files") is True

    def test_blocked_action_not_safe(self):
        broker = PermissionBroker()
        assert broker.is_safe("execute_untrusted_code") is False


class TestIsBlocked:
    def test_blocked(self):
        broker = PermissionBroker()
        assert broker.is_blocked("execute_untrusted_code") is True

    def test_safe_not_blocked(self):
        broker = PermissionBroker()
        assert broker.is_blocked("read_local_files") is False


class TestSafeActionsList:
    def test_returns_frozenset_or_set(self):
        broker = PermissionBroker()
        safe = broker.safe_actions()
        assert isinstance(safe, frozenset)
        assert "read_local_files" in safe

    def test_approval_required_list(self):
        broker = PermissionBroker()
        approval = broker.approval_required_actions()
        assert isinstance(approval, frozenset)
        assert "run_shell_commands" in approval


def test_safe_file_skill_allowed():
    broker = PermissionBroker(interactive=False)
    broker.check("write_within_skills", None)
    broker.check("write_within_skillforge", None)


def test_network_requires_approval():
    broker = PermissionBroker(interactive=False, auto_approve=False)
    with pytest.raises(ApprovalRequiredError):
        broker.check("access_network", None)


def test_shell_requires_approval():
    broker = PermissionBroker(interactive=False, auto_approve=False)
    with pytest.raises(ApprovalRequiredError):
        broker.check("run_shell_commands", None)


def test_delete_outside_workspace_blocked():
    broker = PermissionBroker(interactive=False)
    with pytest.raises(PermissionDeniedError):
        broker.check("delete_outside_workspace", None)


def test_unknown_permission_fails_closed():
    broker = PermissionBroker(interactive=False, auto_approve=False)
    with pytest.raises(ApprovalRequiredError):
        broker.check("totally_new_permission", None)
