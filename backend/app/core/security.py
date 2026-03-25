from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class UserContext:
    user_id: UUID
    email: str | None = None
