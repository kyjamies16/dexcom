from datetime import datetime


def format_display_datetime(current: datetime | None = None) -> str:
    """Return a short 'Mon 01 12:34 PM' string for the LED header."""
    current = current or datetime.now()
    formatted_date = current.strftime("%b %d")
    formatted_time = current.strftime("%I:%M %p")
    return f"{formatted_date} {formatted_time}"
