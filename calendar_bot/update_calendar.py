import ics
from pathlib import Path

from .utils import (
    make_event_from_github_discussion_body,
    are_events_identical,
    load_events_from_calendar_file,
    write_events_to_calendar,
)


def process_discussion(
    discussion_number: str, body: str, data_dir: Path = Path("data/")
) -> tuple[ics.Event, bool]:
    """Process a GitHub discussion by creating or updating a calendar event.
    
    Returns:
        tuple: (event, was_updated) where was_updated is False if no changes were made
    """
    event_uid = f"ghdiscussion_{discussion_number}"
    new_event = make_event_from_github_discussion_body(event_uid, body)
    
    # Load existing events
    full_calendar_path = data_dir / "adsv_events_public.ics"
    all_events = load_events_from_calendar_file(full_calendar_path)
    
    # Find existing event with matching UID
    existing_event_idx = None
    for i, event in enumerate(all_events):
        if event.uid == event_uid:
            existing_event_idx = i
            break
    
    if existing_event_idx is not None:
        if are_events_identical(all_events[existing_event_idx], new_event):
            print("No changes detected; skipping update.")
            return new_event, False
        all_events[existing_event_idx] = new_event
        print("Event updated.")
    else:
        all_events.insert(0, new_event)
        print("Event added.")
    
    # Save files
    event_path = data_dir / f"individual_events/{event_uid}.ics"
    write_events_to_calendar([new_event], event_path)
    write_events_to_calendar(all_events, full_calendar_path)
    
    return new_event, True


def delete_discussion(discussion_number: str, data_dir: Path = Path("data/")) -> bool:
    """Delete a calendar event associated with a GitHub discussion.
    
    Returns:
        bool: True if event was found and removed, False otherwise
    """
    event_uid = f"ghdiscussion_{discussion_number}"
    event_path = data_dir / f"individual_events/{event_uid}.ics"
    full_calendar_path = data_dir / "adsv_events_public.ics"
    
    event_removed = False
    
    # Remove individual event file
    if event_path.exists():
        event_path.unlink()
        print(f"Removed individual event file: {event_path}")
        event_removed = True
    
    # Remove from main calendar
    if full_calendar_path.exists():
        all_events = load_events_from_calendar_file(full_calendar_path)
        filtered_events = [e for e in all_events if e.uid != event_uid]
        
        if len(filtered_events) < len(all_events):
            write_events_to_calendar(filtered_events, full_calendar_path)
            print(f"Removed event {event_uid} from main calendar.")
            event_removed = True
    
    if not event_removed:
        print(f"Event {event_uid} not found.")
    
    return event_removed


def main():
    """CLI entry point for calendar bot."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Process GitHub discussions to manage calendar events"
    )
    parser.add_argument("--discussion_number", required=True, help="GitHub discussion number")
    parser.add_argument("--body", help="Discussion body content (required unless --delete)")
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the event instead of creating/updating",
    )
    parser.add_argument(
        "--data_dir", type=Path, default=Path("data/"), help="Data directory path"
    )
    args = parser.parse_args()

    if args.delete:
        delete_discussion(args.discussion_number, args.data_dir)
    else:
        if args.body is None:
            parser.error("--body is required when not using --delete")
        process_discussion(args.discussion_number, args.body, args.data_dir)


if __name__ == "__main__":
    main()
