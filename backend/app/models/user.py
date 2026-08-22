from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: str
    display_name: str | None = None
