import unittest
from pathlib import Path
from calendar_bot.update_calendar import process_discussion, delete_discussion
from calendar_bot.utils import load_events_from_calendar_file


class TestCalendarBot(unittest.TestCase):
    """Test suite for calendar bot functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that are shared across tests."""
        cls.data_dir = Path("testdata")
        
        # Create discussion body in the new format
        cls.discussion_body = """### Event Name

😃 ADSV Happy Hour

### Event Description

Join us for the ADSV happy hour this Friday, hosted by the XXX Lab.
Some more information blah blah blah.
Blah.

### Start Time

2024-11-30 17:00:00

### End Time

2024-11-30 21:00:00

### Location

SV Lobby"""

    def setUp(self):
        """Set up for each test."""
        # Clean up before each test
        calendar_path = self.data_dir / "adsv_events_public.ics"
        if calendar_path.exists():
            calendar_path.unlink()

    def test_add_event(self):
        """Test adding a new event."""
        event, was_updated = process_discussion("test_add", self.discussion_body, self.data_dir)
        
        self.assertTrue(was_updated)
        self.assertEqual(event.name, "😃 ADSV Happy Hour")
        self.assertEqual(event.location, "SV Lobby")
        
        # Verify files were created
        self.assertTrue((self.data_dir / "adsv_events_public.ics").exists())
        self.assertTrue((self.data_dir / "individual_events/ghdiscussion_test_add.ics").exists())

    def test_update_unchanged_event(self):
        """Test that unchanged event is not re-saved."""
        # Create event
        process_discussion("test_unchanged", self.discussion_body, self.data_dir)
        
        # Try to update with same content
        event, was_updated = process_discussion("test_unchanged", self.discussion_body, self.data_dir)
        
        self.assertFalse(was_updated)

    def test_update_changed_event(self):
        """Test updating an existing event with changes."""
        # Create event
        process_discussion("test_changed", self.discussion_body, self.data_dir)
        
        # Update with modified content
        modified_body = self.discussion_body.replace("ADSV Happy Hour", "ADSV Holiday Party")
        event, was_updated = process_discussion("test_changed", modified_body, self.data_dir)
        
        self.assertTrue(was_updated)
        self.assertEqual(event.name, "😃 ADSV Holiday Party")

    def test_fullday_event(self):
        """Test creating an all-day event."""
        fullday_body = self.discussion_body.replace(
            "2024-11-30 17:00:00\n\n### End Time\n\n2024-11-30 21:00:00",
            "2024-11-28\n\n### End Time\n\n2024-11-30",
        )
        
        event, was_updated = process_discussion("test_fullday", fullday_body, self.data_dir)
        
        self.assertTrue(was_updated)
        self.assertTrue(event.all_day)

    def test_delete_event(self):
        """Test deleting an event."""
        # Create event
        process_discussion("test_delete", self.discussion_body, self.data_dir)
        
        event_file = self.data_dir / "individual_events/ghdiscussion_test_delete.ics"
        self.assertTrue(event_file.exists())
        
        # Delete event
        removed = delete_discussion("test_delete", self.data_dir)
        
        self.assertTrue(removed)
        self.assertFalse(event_file.exists())
        
        # Verify it's removed from calendar
        events = load_events_from_calendar_file(self.data_dir / "adsv_events_public.ics")
        event_uids = [e.uid for e in events]
        self.assertNotIn("ghdiscussion_test_delete", event_uids)

    def test_delete_nonexistent_event(self):
        """Test deleting a non-existent event."""
        removed = delete_discussion("test_nonexistent", self.data_dir)
        self.assertFalse(removed)

    def test_multiple_events(self):
        """Test managing multiple events."""
        # Create two events
        process_discussion("test_multi_1", self.discussion_body, self.data_dir)
        process_discussion("test_multi_2", self.discussion_body, self.data_dir)
        
        # Verify both exist
        events = load_events_from_calendar_file(self.data_dir / "adsv_events_public.ics")
        self.assertEqual(len(events), 2)
        
        # Delete one
        delete_discussion("test_multi_1", self.data_dir)
        
        # Verify only one remains
        events = load_events_from_calendar_file(self.data_dir / "adsv_events_public.ics")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].uid, "ghdiscussion_test_multi_2")


if __name__ == "__main__":
    unittest.main()
