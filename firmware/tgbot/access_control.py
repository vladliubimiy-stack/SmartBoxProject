"""Small helpers for fail-closed Telegram user access control."""


def parse_allowed_user_ids(value: str | None) -> frozenset[int]:
    if not value or not value.strip():
        raise ValueError("ALLOWED_TELEGRAM_USER_IDS must contain at least one numeric ID")

    user_ids = set()
    for item in value.split(","):
        item = item.strip()
        try:
            user_id = int(item)
        except ValueError as exc:
            raise ValueError("ALLOWED_TELEGRAM_USER_IDS must be comma-separated integers") from exc
        if user_id <= 0:
            raise ValueError("Telegram user IDs must be positive integers")
        user_ids.add(user_id)

    if not user_ids:
        raise ValueError("ALLOWED_TELEGRAM_USER_IDS must contain at least one numeric ID")
    return frozenset(user_ids)


def is_allowed_user(user_id: int | None, allowed_user_ids: frozenset[int]) -> bool:
    return user_id is not None and user_id in allowed_user_ids
