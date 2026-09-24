import logging
import os
from datetime import date, datetime, timezone
from urllib.parse import urlparse
from uuid import uuid4

import caldav
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from icalendar import Calendar, Event

load_dotenv()
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CALDAV_URL = os.getenv("CALDAV_URL") or "http://localhost:5232/"
CALDAV_USERNAME = os.getenv("CALDAV_USERNAME") or ""
CALDAV_PASSWORD = os.getenv("CALDAV_PASSWORD") or ""

if not urlparse(CALDAV_URL).scheme or not urlparse(CALDAV_URL).netloc:
    raise RuntimeError("CALDAV_URL must include a scheme and host, e.g. http://localhost:5232/")


def calendar():
    client = caldav.DAVClient(
        url=CALDAV_URL,
        username=CALDAV_USERNAME,
        password=CALDAV_PASSWORD,
    )
    calendars = client.principal().calendars()
    if not calendars:
        raise RuntimeError("No CalDAV calendar found")
    return calendars[0]


def parse_date(value):
    value = value.replace("Z", "+00:00")
    return date.fromisoformat(value) if "T" not in value else datetime.fromisoformat(value)


def uid(component):
    return str(component.get("UID"))


def recurrence_id(component):
    value = component.get("RECURRENCE-ID")
    return value.dt.isoformat() if value else None


def event_id(component):
    return uid(component) + (f"|{recurrence_id(component)}" if recurrence_id(component) else "")


def find_series(cal, event_id):
    series_id = event_id.split("|", 1)[0]
    for resource in cal.events():
        ical = Calendar.from_ical(resource.data)
        if any(uid(item) == series_id and not item.get("RECURRENCE-ID") for item in ical.walk("VEVENT")):
            return resource, ical, series_id
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
        "start": start.isoformat(),
        "end": end.isoformat() if end else None,
        "allDay": isinstance(start, date) and not isinstance(start, datetime),
    }


def add_recurrence(item, frequency, until):
    if frequency and frequency != "none":
        rule = {"FREQ": frequency.upper()}
        if until:
            rule["UNTIL"] = parse_date(until)
        item.add("RRULE", rule)


def update_values(item, data):
    item["SUMMARY"] = data["title"]
    item["DTSTART"] = parse_date(data["start"])
    if data.get("end"):
        item["DTEND"] = parse_date(data["end"])
    elif "DTEND" in item:
        del item["DTEND"]


@app.get("/")
def index():
    return send_from_directory(app.root_path, "index.html")


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
        item.add("DTSTART", parse_date(data["start"]))
        if data.get("end"):
            item.add("DTEND", parse_date(data["end"]))
        add_recurrence(item, data.get("frequency"), data.get("until"))
        item.add("DTSTAMP", datetime.now(timezone.utc))
        cal = Calendar()
        cal.add_component(item)
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
            if target is None:
                target = Event()
                target.add("UID", series_id)
                target.add("RECURRENCE-ID", parse_date(data["recurrenceId"]))
                cal.add_component(target)
            update_values(target, data)
        else:
            target = find_component(cal, series_id)
            update_values(target, data)
            if "frequency" in data:
                if "RRULE" in target:
                    del target["RRULE"]
                add_recurrence(target, data.get("frequency"), data.get("until"))
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
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=5000)
