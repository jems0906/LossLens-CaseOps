import hmac
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import ANALYST_TOKEN, REVIEWER_TOKEN


bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Actor:
    role: str
    actor_id: str


def current_actor(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Actor:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Bearer token required")
    token = credentials.credentials
    if hmac.compare_digest(token, REVIEWER_TOKEN):
        return Actor("reviewer", "synthetic-reviewer")
    if hmac.compare_digest(token, ANALYST_TOKEN):
        return Actor("analyst", "synthetic-analyst")
    raise HTTPException(status_code=401, detail="Invalid access token")


def reviewer_actor(actor: Actor = Depends(current_actor)) -> Actor:
    if actor.role != "reviewer":
        raise HTTPException(status_code=403, detail="Reviewer permission required")
    return actor