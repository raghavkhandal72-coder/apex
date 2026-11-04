from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Set


class EnterpriseRole(str, Enum):
    ADMIN = "ADMIN"
    SECURITY_LEAD = "SECURITY_LEAD"
    DEVELOPER = "DEVELOPER"
    AUDITOR = "AUDITOR"


ROLE_PERMISSIONS: Dict[EnterpriseRole, Set[str]] = {
    EnterpriseRole.ADMIN: {
        "battle", "audit", "relay", "heal", "engineer", "solve",
        "redteam", "benchmark", "diff", "pr", "serve", "mcp", "init-ci", "audit-verify"
    },
    EnterpriseRole.SECURITY_LEAD: {
        "audit", "redteam", "diff", "heal", "pr", "benchmark", "audit-verify"
    },
    EnterpriseRole.DEVELOPER: {
        "battle", "relay", "heal", "diff", "engineer", "solve"
    },
    EnterpriseRole.AUDITOR: {
        "audit-verify", "benchmark"
    },
}


@dataclass
class AuthUser:
    token: str
    user_id: str
    tenant_id: str
    role: EnterpriseRole


class RBACManager:
    """Enterprise Role-Based Access Control & Multi-Tenant Authentication."""

    def __init__(self):
        self._tokens: Dict[str, AuthUser] = {}
        self._load_default_enterprise_tokens()

    def _load_default_enterprise_tokens(self):
        # Default root enterprise admin token if set in environment
        root_token = os.getenv("APEX_ADMIN_TOKEN", "apex-admin-root-sec-key-999")
        self.register_token(
            token=root_token,
            user_id="root-admin@enterprise.internal",
            tenant_id="global-hq",
            role=EnterpriseRole.ADMIN,
        )

    def register_token(self, token: str, user_id: str, tenant_id: str, role: EnterpriseRole):
        self._tokens[token] = AuthUser(
            token=token,
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
        )

    def authenticate(self, token: Optional[str]) -> Optional[AuthUser]:
        if not token:
            return None
        return self._tokens.get(token)

    def authorize(self, token: Optional[str], action: str) -> bool:
        # If enterprise auth is disabled, allow
        if os.getenv("APEX_AUTH_REQUIRED", "false").lower() != "true":
            return True

        user = self.authenticate(token)
        if not user:
            return False

        allowed_actions = ROLE_PERMISSIONS.get(user.role, set())
        return action in allowed_actions
