from datetime import datetime


def month_diff(start: datetime | None, end: datetime | None) -> int | None:
    if not start or not end:
        return None
    return (end.year - start.year) * 12 + (end.month - start.month)
