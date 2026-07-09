"""Tests for authentication and authorization logic."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.security import (
    Principal,
    require_roles,
    resolve_project_scope,
    resolve_project_scopes,
    _parse_project_scopes,
)


def _make_principal(role: str, project_scope: str | None = None) -> Principal:
    scopes = _parse_project_scopes(project_scope)
    return Principal(
        role=role,
        key_prefix="test",
        project_scope=project_scope,
        project_scopes=scopes,
    )


class TestRoleRequirement:
    def test_admin_passes_any_role(self):
        deps = require_roles("viewer")
        principal = _make_principal("admin")
        result = deps(principal)
        assert result.role == "admin"

    def test_matching_role_passes(self):
        deps = require_roles("analyst")
        principal = _make_principal("analyst")
        result = deps(principal)
        assert result.role == "analyst"

    def test_non_matching_role_fails(self):
        deps = require_roles("admin")
        principal = _make_principal("viewer")
        with pytest.raises(HTTPException) as exc:
            deps(principal)
        assert exc.value.status_code == 403

    def test_multiple_allowed_roles(self):
        deps = require_roles("viewer", "analyst")
        assert deps(_make_principal("viewer")).role == "viewer"
        assert deps(_make_principal("analyst")).role == "analyst"
        with pytest.raises(HTTPException):
            deps(_make_principal("ingest"))


class TestProjectScope:
    def test_admin_unrestricted(self):
        principal = _make_principal("admin")
        assert resolve_project_scope(principal, "myproject") == "myproject"
        assert resolve_project_scopes(principal, None) is None
        assert resolve_project_scopes(principal, "proj") == ["proj"]

    def test_scoped_access_allowed(self):
        principal = _make_principal("viewer", "project-a")
        assert resolve_project_scope(principal, "project-a") == "project-a"
        assert resolve_project_scopes(principal, "project-a") == ["project-a"]
        assert resolve_project_scopes(principal, None) == ["project-a"]

    def test_scoped_access_denied(self):
        principal = _make_principal("viewer", "project-a")
        with pytest.raises(HTTPException) as exc:
            resolve_project_scope(principal, "project-b")
        assert exc.value.status_code == 403

    def test_multiple_scopes(self):
        principal = _make_principal("analyst", "proj-a,proj-b")
        scopes = resolve_project_scopes(principal, None)
        assert set(scopes) == {"proj-a", "proj-b"}
        with pytest.raises(HTTPException):
            resolve_project_scope(principal, "proj-c")


class TestPrincipalRoleValidation:
    def test_invalid_role_raises(self):
        with pytest.raises(ValueError):
            require_roles("nonexistent_role")
