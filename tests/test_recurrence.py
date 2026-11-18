import unittest
from datetime import date, datetime, time, timezone
from unittest.mock import patch

from icalendar import Calendar

import app as calpine

SERIES = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//calpine//test//EN
BEGIN:VEVENT
UID:series-1
DTSTAMP:20260101T000000Z
DTSTART:20261001T140000Z
DTEND:20261001T150000Z
SUMMARY:Standup
LOCATION:Room 1
RRULE:FREQ=WEEKLY;BYDAY=MO,WE
END:VEVENT
END:VCALENDAR
"""

ALL_DAY_SERIES = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//calpine//test//EN
BEGIN:VEVENT
UID:allday-1
DTSTAMP:20260101T000000Z
DTSTART;VALUE=DATE:20261001
SUMMARY:Holiday
RRULE:FREQ=DAILY
END:VEVENT
END:VCALENDAR
"""


def series_calendar(data=SERIES):
    return Calendar.from_ical(data)


def master(data=SERIES):
    return calpine.find_component(series_calendar(data), "series-1")


def rule_of(component):
    return component.get("RRULE")


def first(value):
    return value[0] if isinstance(value, list) else value


class FakeResource:
    def __init__(self, data=SERIES):
        self.data = data
        self.saved = False
        self.deleted = False

    def save(self):
        self.saved = True

    def delete(self):
        self.deleted = True


class FakeCalendar:
    def __init__(self):
        self.saved = None

    def save_event(self, data):
        self.saved = data


class RecurrenceValueTests(unittest.TestCase):
    def test_parsed_rule_reports_frequency_and_until(self):
        item = Calendar.from_ical(
            SERIES.replace("RRULE:FREQ=WEEKLY;BYDAY=MO,WE", "RRULE:FREQ=WEEKLY;UNTIL=20261231T235959Z")
        ).walk("VEVENT")[0]
        self.assertEqual(calpine.recurrence_values(item), ("weekly", "2026-12-31"))

    def test_built_rule_reports_frequency_and_until(self):
        from icalendar import Event

        item = Event()
        item.add("DTSTART", datetime(2026, 10, 1, 10, tzinfo=calpine.SERVER_TIMEZONE))
        item.add("RRULE", {"FREQ": "DAILY", "UNTIL": date(2026, 12, 31)})
        self.assertEqual(calpine.recurrence_values(item), ("daily", "2026-12-31"))

    def test_event_json_accepts_parsed_rrule(self):
        item = Calendar.from_ical(
            SERIES.replace("RRULE:FREQ=WEEKLY;BYDAY=MO,WE", "RRULE:FREQ=WEEKLY;UNTIL=20261231T235959Z")
        ).walk("VEVENT")[0]
        payload = calpine.event_json(item)
        self.assertEqual(payload["frequency"], "weekly")
        self.assertEqual(payload["until"], "2026-12-31")


class SetRecurrenceTests(unittest.TestCase):
    def test_untouched_rule_is_preserved(self):
        item = master()
        calpine.set_recurrence(item, None, None, False)
        self.assertEqual(rule_of(item).to_ical(), b"FREQ=WEEKLY;BYDAY=MO,WE")

    def test_until_only_preserves_other_parts(self):
        item = master()
        calpine.set_recurrence(item, None, "2027-01-15", True)
        rule = rule_of(item)
        self.assertEqual(first(rule.get("FREQ")), "WEEKLY")
        self.assertEqual(first(rule.get("BYDAY")), "MO")
        expected = datetime.combine(date(2027, 1, 15), time(23, 59, 59), tzinfo=calpine.SERVER_TIMEZONE)
        self.assertEqual(first(rule.get("UNTIL")), expected.astimezone(timezone.utc))

    def test_until_on_count_rule_drops_count(self):
        item = master()
        rule = rule_of(item)
        rule["COUNT"] = 10
        item["RRULE"] = rule
        calpine.set_recurrence(item, None, "2027-01-15", True)
        self.assertIsNone(rule_of(item).get("COUNT"))
        self.assertIsNotNone(rule_of(item).get("UNTIL"))

    def test_frequency_change_keeps_interval_and_count(self):
        item = master()
        rule = rule_of(item)
        rule["COUNT"] = 10
        rule["INTERVAL"] = 2
        item["RRULE"] = rule
        calpine.set_recurrence(item, "daily", None, False)
        rule = rule_of(item)
        self.assertEqual(first(rule.get("FREQ")), "DAILY")
        self.assertEqual(first(rule.get("COUNT")), 10)
        self.assertEqual(first(rule.get("INTERVAL")), 2)
        self.assertIsNone(rule.get("BYDAY"))

    def test_none_removes_rule(self):
        item = master()
        calpine.set_recurrence(item, "none", None, False)
        self.assertIsNone(rule_of(item))

    def test_until_only_survives_serialization(self):
        item = Calendar.from_ical(
            SERIES.replace("RRULE:FREQ=WEEKLY;BYDAY=MO,WE", "RRULE:FREQ=WEEKLY;BYDAY=MO,WE;COUNT=10")
        ).walk("VEVENT")[0]
        calpine.set_recurrence(item, None, "2027-01-15", True)
        rule = Calendar.from_ical(item.to_ical()).walk("VEVENT")[0].get("RRULE")
        self.assertEqual(first(rule.get("BYDAY")), "MO")
        self.assertIsNone(rule.get("COUNT"))
        self.assertEqual(first(rule.get("FREQ")), "WEEKLY")
        self.assertIsNotNone(rule.get("UNTIL"))

    def test_until_can_be_cleared(self):
        item = master()
        calpine.set_recurrence(item, None, "2027-01-15", True)
        calpine.set_recurrence(item, None, "", True)
        self.assertIsNone(rule_of(item).get("UNTIL"))
        self.assertEqual(first(rule_of(item).get("FREQ")), "WEEKLY")

    def test_recurrence_can_be_added_to_single_event(self):
        item = Calendar.from_ical(SERIES.replace("RRULE:FREQ=WEEKLY;BYDAY=MO,WE\n", "")).walk("VEVENT")[0]
        self.assertIsNone(rule_of(item))
        calpine.set_recurrence(item, "daily", "2027-01-31", True)
        rule = rule_of(item)
        self.assertEqual(first(rule.get("FREQ")), "DAILY")
        expected = datetime.combine(date(2027, 1, 31), time(23, 59, 59), tzinfo=calpine.SERVER_TIMEZONE)
        self.assertEqual(first(rule.get("UNTIL")), expected.astimezone(timezone.utc))

    def test_all_day_until_is_a_date(self):
        item = series_calendar(ALL_DAY_SERIES).walk("VEVENT")[0]
        calpine.set_recurrence(item, None, "2026-12-31", True)
        self.assertEqual(first(rule_of(item).get("UNTIL")), date(2026, 12, 31))


class FindComponentTests(unittest.TestCase):
    def test_matches_recurrence_id_by_instant(self):
        data = SERIES.replace(
            "END:VCALENDAR",
            "BEGIN:VEVENT\nUID:series-1\nDTSTAMP:20260101T000000Z\n"
            "RECURRENCE-ID:20261005T140000Z\nDTSTART:20261005T160000Z\n"
            "DTEND:20261005T170000Z\nSUMMARY:Moved\nEND:VEVENT\nEND:VCALENDAR",
        )
        item = calpine.find_component(series_calendar(data), "series-1|2026-10-05T10:00:00-04:00")
        self.assertIsNotNone(item)
        self.assertEqual(str(item.get("SUMMARY")), "Moved")


class EndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = calpine.app.test_client()

    def put_series(self, data, resource=None, cal=None, event_id="series-1"):
        resource = resource or FakeResource()
        cal = cal or series_calendar()
        with patch.object(calpine, "calendar", return_value=object()), patch.object(
            calpine, "find_series", return_value=(resource, cal, "series-1")
        ):
            response = self.client.put(f"/api/events/{event_id}", json=data)
        return response, resource

    def test_series_title_edit_leaves_rule_and_anchor_alone(self):
        response, resource = self.put_series(
            {
                "title": "Renamed",
                "location": "Room 1",
                "start": "2026-10-01T14:00:00+00:00",
                "end": "2026-10-01T15:00:00+00:00",
                "allDay": False,
                "scope": "series",
            }
        )
        self.assertEqual(response.status_code, 200)
        item = Calendar.from_ical(resource.data).walk("VEVENT")[0]
        self.assertEqual(str(item.get("SUMMARY")), "Renamed")
        self.assertEqual(rule_of(item).to_ical(), b"FREQ=WEEKLY;BYDAY=MO,WE")
        self.assertEqual(item.decoded("DTSTART"), datetime(2026, 10, 1, 14, tzinfo=timezone.utc))
        self.assertEqual(response.json["frequency"], "weekly")

    def test_series_can_clear_recurrence(self):
        response, resource = self.put_series(
            {
                "title": "Standup",
                "location": "Room 1",
                "start": "2026-10-01T14:00:00+00:00",
                "end": "2026-10-01T15:00:00+00:00",
                "allDay": False,
                "scope": "series",
                "frequency": "none",
                "until": "",
            }
        )
        self.assertEqual(response.status_code, 200)
        item = Calendar.from_ical(resource.data).walk("VEVENT")[0]
        self.assertIsNone(rule_of(item))

    def test_invalid_frequency_is_rejected(self):
        response, resource = self.put_series(
            {
                "title": "Standup",
                "location": "Room 1",
                "start": "2026-10-01T14:00:00+00:00",
                "allDay": False,
                "scope": "series",
                "frequency": "hourly",
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(resource.saved)

    def test_occurrence_edit_keeps_master_rule(self):
        response, resource = self.put_series(
            {
                "title": "Moved",
                "location": "Room 1",
                "start": "2026-10-05T16:00:00+00:00",
                "end": "2026-10-05T17:00:00+00:00",
                "allDay": False,
                "scope": "occurrence",
                "recurrenceId": "2026-10-05T14:00:00+00:00",
            },
            cal=series_calendar(),
            event_id="series-1|2026-10-05T14:00:00+00:00",
        )
        self.assertEqual(response.status_code, 200)
        parsed = Calendar.from_ical(resource.data)
        master_item = calpine.find_component(parsed, "series-1")
        self.assertEqual(rule_of(master_item).to_ical(), b"FREQ=WEEKLY;BYDAY=MO,WE")
        override = calpine.find_component(parsed, "series-1|2026-10-05T14:00:00+00:00")
        self.assertIsNotNone(override)
        self.assertEqual(str(override.get("SUMMARY")), "Moved")

    def test_series_endpoint_returns_404_when_missing(self):
        with patch.object(calpine, "calendar", return_value=object()), patch.object(
            calpine, "find_series", return_value=(None, None, "missing")
        ):
            response = self.client.get("/api/series/missing")
        self.assertEqual(response.status_code, 404)

    def test_series_endpoint_returns_normalized_rule(self):
        resource = FakeResource(
            SERIES.replace("RRULE:FREQ=WEEKLY;BYDAY=MO,WE", "RRULE:FREQ=WEEKLY;UNTIL=20261231T235959Z")
        )
        cal = series_calendar(resource.data)
        with patch.object(calpine, "calendar", return_value=object()), patch.object(
            calpine, "find_series", return_value=(resource, cal, "series-1")
        ):
            response = self.client.get("/api/series/series-1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["frequency"], "weekly")
        self.assertEqual(response.json["until"], "2026-12-31")
        self.assertEqual(response.json["title"], "Standup")


if __name__ == "__main__":
    unittest.main()
