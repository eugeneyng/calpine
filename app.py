import logging
import os
from datetime import date, datetime, timezone
from urllib.parse import urlparse
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import caldav
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from icalendar import Calendar, Event, Timezone

load_dotenv()
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TZ_NAME = os.getenv("TZ", "UTC")
try:
    SERVER_TIMEZONE = ZoneInfo(TZ_NAME)
except ZoneInfoNotFoundError as error:
    raise RuntimeError(f"TZ must be a valid IANA timezone, got {TZ_NAME!r}") from error

CALDAV_URL = os.getenv("CALDAV_URL") or "http://localhost:5232/"
CALDAV_USERNAME = os.getenv("CALDAV_USERNAME") or ""
CALDAV_PASSWORD = os.getenv("CALDAV_PASSWORD") or ""


def add_server_timezone(cal):
    has_timed_event = any(
        isinstance(value.dt, datetime) and value.dt.tzinfo == SERVER_TIMEZONE
        for component in cal.walk("VEVENT")
        for name in ("DTSTART", "DTEND", "RECURRENCE-ID")
        for value in [component.get(name)]
        if value is not None and hasattr(value, "dt")
    )
    has_timezone = any(str(component.get("TZID")) == TZ_NAME for component in cal.walk("VTIMEZONE"))
    if has_timed_event and not has_timezone:
        cal.add_component(Timezone.from_tzinfo(SERVER_TIMEZONE, tzid=TZ_NAME, last_date=date(2100, 1, 1)))


def parse_date(value, all_day=False):
    if all_day:
        return date.fromisoformat(value[:10])
    value = value.replace("Z", "+00:00")
    parsed = date.fromisoformat(value) if "T" not in value else datetime.fromisoformat(value)
    if isinstance(parsed, datetime):
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=SERVER_TIMEZONE)
        return parsed.astimezone(SERVER_TIMEZONE)
    return parsed


def is_all_day(component):
    start = component.decoded("DTSTART") if component.get("DTSTART") else None
    return isinstance(start, date) and not isinstance(start, datetime)


if not urlparse(CALDAV_URL).scheme or not urlparse(CALDAV_URL).netloc:
    raise RuntimeError("CALDAV_URL must include a scheme and host, e.g. http://localhost:5232/")


_calendar = None


def calendar():
    """The CalDAV calendar, resolved once per process.

    Resolving it runs principal discovery and a calendar PROPFIND. Doing that
    on every request added two round-trips to every edit.
    """
    global _calendar
    if _calendar is None:
        client = caldav.DAVClient(
            url=CALDAV_URL,
            username=CALDAV_USERNAME,
            password=CALDAV_PASSWORD,
            # The server sits behind a proxy that gzips responses and weakens
            # their ETags to W/"...".  caldav echoes that ETag in If-Match, and
            # RFC 9110 requires a strong validator there, so Radicale rejects
            # every PUT with 412.  Ask for an uncompressed response so the
            # server returns a strong ETag that the conditional PUT accepts.
            headers={"Accept-Encoding": "identity"},
        )
        calendars = client.principal().calendars()
        if not calendars:
            raise RuntimeError("No CalDAV calendar found")
        _calendar = calendars[0]
    return _calendar


def uid(component):
    return str(component.get("UID"))


def recurrence_id(component):
    value = component.get("RECURRENCE-ID")
    return value.dt.isoformat() if value else None


def event_id(component):
    return uid(component) + (f"|{recurrence_id(component)}" if recurrence_id(component) else "")


def _has_master(ical, series_id):
    # A resource holding only RECURRENCE-ID overrides has no master to edit.
    return any(uid(item) == series_id and not item.get("RECURRENCE-ID") for item in ical.walk("VEVENT"))


def _series_resource_by_href(cal, series_id):
    """GET the series resource straight from its href, or None if it isn't there.

    A series is a single calendar object resource, and Radicale and Baikal both
    name it "<uid>.ics", so this asks for exactly one event instead of the whole
    calendar. A UID-filtered query looks like the better tool but isn't: servers
    without a UID index load every item to evaluate the text-match anyway.
    """
    try:
        resource = caldav.Event(cal.client, url=cal.url.join(f"{series_id}.ics"), parent=cal)
        resource.load()
    except caldav.error.NotFoundError:
        return None
    if not _has_master(Calendar.from_ical(resource.data), series_id):
        return None
    return resource


def find_series(cal, event_id):
    """Fetch the single resource that holds this series.

    This used to walk every event in the calendar and parse each one to match a
    UID, so every edit transferred and parsed the whole calendar. Servers that
    don't name resources after the UID fall back to that walk.
    """
    series_id = event_id.split("|", 1)[0]
    resource = _series_resource_by_href(cal, series_id)
    if resource is not None:
        return resource, Calendar.from_ical(resource.data), series_id
    for candidate in cal.events():
        ical = Calendar.from_ical(candidate.data)
        if _has_master(ical, series_id):
            return candidate, ical, series_id
    return None, None, series_id


def find_component(ical, event_id):
    series_id, _, instance = event_id.partition("|")
    for item in ical.walk("VEVENT"):
        if uid(item) == series_id and ((not instance and not item.get("RECURRENCE-ID")) or recurrence_id(item) == instance):
            return item
    return None


def event_json(component):
    start = component.decoded("DTSTART")
    end = component.decoded("DTEND") if component.get("DTEND") else None
    rule = component.get("RRULE")
    frequency = str(rule.get("FREQ", "none")).lower() if rule else "none"
    until = rule.get("UNTIL") if rule else None
    until = until.isoformat()[:10] if until else ""
    recurring = bool(rule or component.get("RECURRENCE-ID"))
    return {
        "id": event_id(component),
        "seriesId": uid(component),
        "recurrenceId": recurrence_id(component),
        "recurring": recurring,
        "frequency": frequency,
        "until": until,
        "title": str(component.get("SUMMARY", "")),
        "location": str(component.get("LOCATION", "")),
        "start": start.isoformat(),
        "end": end.isoformat() if end else None,
        "allDay": is_all_day(component),
    }


def add_recurrence(item, frequency, until):
    if frequency and frequency != "none":
        rule = {"FREQ": frequency.upper()}
        if until:
            rule["UNTIL"] = parse_date(until)
        item.add("RRULE", rule)


def set_property(item, name, value):
    """Rewrite a property in place.

    Assigning straight into an existing property keeps its old parameters and never
    re-serialises to iCalendar basic format -- a datetime assigned onto a DTSTART that
    still carries VALUE=DATE emits `DTSTART:2026-10-22 00:00:00+01:00`, which CalDAV
    servers reject. Dropping the property first lets icalendar re-derive the type.
    """
    if name in item:
        del item[name]
    if value is not None:
        item.add(name, value)


def update_values(item, data):
    all_day = bool(data.get("allDay"))
    set_property(item, "SUMMARY", data.get("title", ""))
    set_property(item, "LOCATION", data.get("location") or None)
    set_property(item, "DTSTART", parse_date(data["start"], all_day))
    if data.get("end"):
        set_property(item, "DTEND", parse_date(data["end"], all_day))
        # RFC 5545 3.6.3: DTEND and DURATION must not both appear.
        set_property(item, "DURATION", None)
    else:
        set_property(item, "DTEND", None)


@app.get("/")
def index():
    return send_from_directory(app.root_path, "index.html")


@app.get("/api/timezone")
def get_timezone():
    return jsonify(timezone=TZ_NAME)


@app.get("/api/events")
def get_events():
    try:
        start = parse_date(request.args["start"])
        end = parse_date(request.args["end"])
        result = []
        for resource in calendar().search(start=start, end=end, event=True, expand=True, split_expanded=True):
            ical = Calendar.from_ical(resource.data)
            result.extend(event_json(item) for item in ical.walk("VEVENT"))
        return jsonify(result)
    except Exception as error:
        logger.exception("Could not load events")
        return jsonify(error=str(error)), 500


@app.post("/api/events")
def create_event():
    try:
        data = request.json or {}
        item = Event()
        item.add("UID", data.get("id") or str(uuid4()))
        item.add("SUMMARY", data["title"])
        if data.get("location"):
            item.add("LOCATION", data["location"])
        all_day = bool(data.get("allDay"))
        item.add("DTSTART", parse_date(data["start"], all_day))
        if data.get("end"):
            item.add("DTEND", parse_date(data["end"], all_day))
        add_recurrence(item, data.get("frequency"), data.get("until"))
        item.add("DTSTAMP", datetime.now(timezone.utc))
        cal = Calendar()
        cal.add_component(item)
        add_server_timezone(cal)
        calendar().save_event(cal.to_ical())
        return jsonify(event_json(item)), 201
    except Exception as error:
        return jsonify(error=str(error)), 500


@app.put("/api/events/<path:event_id>")
def update_event(event_id):
    try:
        data = request.json or {}
        resource, cal, series_id = find_series(calendar(), event_id)
        if not resource:
            return jsonify(error="Event not found"), 404
        target = find_component(cal, event_id)
        scope = data.get("scope", "series")
        if "|" in event_id and scope == "occurrence":
            master = find_component(cal, series_id)
            # RFC 5545 3.8.4.4: DTSTART's value type must not change across an override.
            # Checked whether the override already exists or is being created.
            if master is not None and bool(data.get("allDay")) != is_all_day(master):
                return jsonify(error="An occurrence cannot change between all-day and timed"), 400
            if target is None:
                target = Event()
                target.add("UID", series_id)
                target.add("RECURRENCE-ID", parse_date(data["recurrenceId"]))
                target.add("DTSTAMP", datetime.now(timezone.utc))
                cal.add_component(target)
            update_values(target, data)
        else:
            target = find_component(cal, series_id)
            update_values(target, data)
            if "frequency" in data:
                if "RRULE" in target:
                    del target["RRULE"]
                add_recurrence(target, data.get("frequency"), data.get("until"))
        add_server_timezone(cal)
        resource.data = cal.to_ical()
        resource.save()
        return jsonify(event_json(target))
    except Exception as error:
        logger.exception("Could not update event")
        return jsonify(error=str(error)), 500


@app.delete("/api/events/<path:event_id>")
def delete_event(event_id):
    try:
        resource, cal, series_id = find_series(calendar(), event_id)
        if not resource:
            return jsonify(error="Event not found"), 404
        scope = request.args.get("scope", "series")
        if "|" in event_id and scope == "occurrence":
            target = find_component(cal, event_id)
            if target and target.get("RECURRENCE-ID"):
                cal.subcomponents.remove(target)
            else:
                master = find_component(cal, series_id)
                value = parse_date(event_id.split("|", 1)[1])
                master.add("EXDATE", value)
        else:
            resource.delete()
            return jsonify(status="success")
        resource.data = cal.to_ical()
        resource.save()
        return jsonify(status="success")
    except Exception as error:
        logger.exception("Could not delete event")
        return jsonify(error=str(error)), 500


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", host="0.0.0.0", port=5000)
