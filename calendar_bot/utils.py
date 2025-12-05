import ics
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from re import match


def make_event_from_github_issue_str(
    event_uid: str, issue_str: str, timezone_ianacode: str = "Europe/Zurich"
) -> ics.Event:
    """Parse a GitHub issue string into an iCalendar event."""
    try:
        tzinfo = ZoneInfo(timezone_ianacode)
    except Exception as e:
        raise GithubIssueParserError(
            f"Invalid timezone IANA code: {timezone_ianacode}"
        ) from e

    lines = [s.strip() for s in issue_str.splitlines()]
    event = ics.Event(uid=event_uid)

    for field in ["Event Name", "Event Description", "Time", "Location"]:
        try:
            start_line_idx = lines.index(f"### {field}")
        except ValueError as e:
            raise GithubIssueParserError(
                f"Header '### {field}' not found in the issue string."
            ) from e

        # Find first triple-backticked block after the header
        backticks_lines_idx = []
        for i in range(start_line_idx + 1, len(lines)):
            if lines[i].startswith("```"):
                backticks_lines_idx.append(i)
                if len(backticks_lines_idx) == 2:
                    break
        
        if len(backticks_lines_idx) < 2:
            raise GithubIssueParserError(
                f"Could not find complete code block for field '{field}'"
            )
        
        content_lines = lines[backticks_lines_idx[0] + 1 : backticks_lines_idx[1]]
        content = "\n".join(content_lines).strip()

        if field == "Event Name":
            event.name = _parse_event_name(content)
        elif field == "Event Description":
            event.description = content
        elif field == "Time":
            start_dt, end_dt, is_all_day = _parse_time(content)
            if is_all_day:
                event.begin = start_dt
                event.end = end_dt
                event.make_all_day()
            else:
                event.begin = start_dt.replace(tzinfo=tzinfo)
                event.end = end_dt.replace(tzinfo=tzinfo)
        elif field == "Location":
            event.location = _parse_location(content)

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
        raise GithubIssueParserError("Event Name should be a single line.")
    return name_str


def _parse_time(time_str: str) -> tuple[datetime, datetime, bool]:
    """Parse time string into start, end datetime and all-day flag."""
    time_match = match(r"^FROM (.+?) TO (.+?)$", time_str.upper())
    if not time_match:
        raise GithubIssueParserError(
            "Invalid time format: should be 'FROM <start> TO <end>'"
        )
    from_str, to_str = time_match.groups()

    # Try full datetime format
    try:
        start = datetime.strptime(from_str, "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(to_str, "%Y-%m-%d %H:%M:%S")
        return start, end, False
    except ValueError:
        pass

    # Try date-only format
    try:
        start = datetime.strptime(from_str, "%Y-%m-%d")
        end = datetime.strptime(to_str, "%Y-%m-%d")
        return start, end, True
    except ValueError:
        pass

    raise GithubIssueParserError(
        "Could not parse times. Use format 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'"
    )


def _parse_location(loc_str: str) -> str:
    """Parse and validate location (must be single line)."""
    if "\n" in loc_str:
        raise GithubIssueParserError("Location should be a single line.")
    return loc_str


class GithubIssueParserError(Exception):
    """Exception raised when parsing GitHub issue fails."""
    pass
