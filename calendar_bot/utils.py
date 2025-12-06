import ics
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from re import match


def make_event_from_github_discussion_body(
    event_uid: str, body: str, timezone_ianacode: str = "Europe/Zurich"
) -> ics.Event:
    """Parse a GitHub discussion form body into an iCalendar event.

    The body format is:
    ### Event Name

    value

    ### Event Description

    value

    etc.
    """
    try:
        tzinfo = ZoneInfo(timezone_ianacode)
    except Exception as e:
        raise EventFormParserError(
            f"Invalid timezone IANA code: {timezone_ianacode}"
        ) from e

    # Parse the form-style body
    fields = {}
    lines = body.strip().split("\n")

    current_field = None
    current_content = []

    for line in lines:
        if line.startswith("### "):
            # Save previous field if exists
            if current_field:
                fields[current_field] = "\n".join(current_content).strip()
            # Start new field
            current_field = line[4:].strip()
            current_content = []
        elif current_field and line.strip():
            current_content.append(line)

    # Save last field
    if current_field:
        fields[current_field] = "\n".join(current_content).strip()

    # Validate required fields
    required_fields = [
        "Event Name",
        "Event Description",
        "Start Time",
        "End Time",
        "Location",
    ]
    for field in required_fields:
        if field not in fields or not fields[field]:
            raise EventFormParserError(f"Missing required field: {field}")

    # Create event
    event = ics.Event(uid=event_uid)
    event.name = _parse_event_name(fields["Event Name"])
    event.description = _parse_event_description(fields["Event Description"])
    event.location = _parse_location(fields["Location"])

    # Parse times
    start_dt, start_is_all_day = _parse_time(fields["Start Time"])
    end_dt, end_is_all_day = _parse_time(fields["End Time"])

    if start_is_all_day != end_is_all_day:
        raise EventFormParserError(
            "Start and end times must both be either date-only or datetime format"
        )

    if start_is_all_day:
        event.begin = start_dt
        event.end = end_dt
        event.make_all_day()
    else:
        event.begin = start_dt.replace(tzinfo=tzinfo)
        event.end = end_dt.replace(tzinfo=tzinfo)

    return event


def are_events_identical(event1: ics.Event, event2: ics.Event) -> bool:
    """Check if two events have identical content (ignoring UID)."""
    return (
        event1.name == event2.name
        and event1.description == event2.description
        and event1.begin == event2.begin
        and event1.end == event2.end
        and event1.location == event2.location
    )


def load_events_from_calendar_file(filepath: Path) -> list[ics.Event]:
    """Load events from an iCalendar file."""
    if not filepath.exists():
        return []
    with open(filepath, "r") as f:
        calendar = ics.Calendar(f.read())
    return list(calendar.events)


def write_events_to_calendar(events: list[ics.Event], filepath: Path) -> None:
    """Write events to an iCalendar file."""
    calendar = ics.Calendar()
    for event in events:
        calendar.events.add(event)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        f.writelines(calendar.serialize_iter())


def _parse_event_name(name_str: str) -> str:
    """Parse and validate event name (must be single line)."""
    if "\n" in name_str:
        raise EventFormParserError("Event Name should be a single line.")
    return name_str


def _parse_event_description(desc_str: str) -> str:
    """Parse event description (can be multi-line)."""
    lines = desc_str.strip().split("\n")
    lines = [line for line in lines if not line.startswith("```")]
    return "\n".join(lines).strip()


def _parse_time(time_str: str) -> tuple[datetime, bool]:
    """Parse a single time string into datetime and all-day flag.

    Returns:
        tuple: (datetime, is_all_day)
    """
    time_str = time_str.strip()

    # Try full datetime format
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return dt, False
    except ValueError:
        pass

    # Try date-only format
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d")
        return dt, True
    except ValueError:
        pass

    raise EventFormParserError(
        f"Could not parse time '{time_str}'. Use format 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'"
    )


def _parse_location(loc_str: str) -> str:
    """Parse and validate location (must be single line)."""
    if "\n" in loc_str:
        raise EventFormParserError("Location should be a single line.")
    return loc_str


class EventFormParserError(Exception):
    """Exception raised when parsing GitHub discussion form fails."""

    def __init__(self, message: str):
        print(f"EventFormParserError: {message}", flush=True)
        super().__init__(message)
