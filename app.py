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


def find_event(cal, event_id):
    for resource in cal.events():
        ical = Calendar.from_ical(resource.data)
        if any(str(item.get("UID")) == event_id for item in ical.walk("VEVENT")):
            return resource, ical
    return None, None


def event_json(component):
    start = component.decoded("DTSTART")
    end = component.decoded("DTEND") if component.get("DTEND") else None
    return {
        "id": str(component.get("UID")),
        "title": str(component.get("SUMMARY", "")),
        "start": start.isoformat(),
        "end": end.isoformat() if end else None,
        "allDay": isinstance(start, date) and not isinstance(start, datetime),
    }


@app.get("/")
def index():
    return send_from_directory(app.root_path, "index.html")


@app.get("/api/events")
def get_events():
    try:
        start = parse_date(request.args["start"])
        end = parse_date(request.args["end"])
        result = []
        for resource in calendar().search(start=start, end=end, event=True, expand=True):
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
        item.add("DTSTAMP", datetime.now(timezone.utc))
        cal = Calendar()
        cal.add_component(item)
        calendar().save_event(cal.to_ical())
        return jsonify(event_json(item)), 201
    except Exception as error:
        return jsonify(error=str(error)), 500


@app.put("/api/events/<event_id>")
def update_event(event_id):
    try:
        data = request.json or {}
        resource, cal = find_event(calendar(), event_id)
        if not resource:
            return jsonify(error="Event not found"), 404
        item = next(item for item in cal.walk("VEVENT") if str(item.get("UID")) == event_id)
        item["SUMMARY"] = data["title"]
        item["DTSTART"] = parse_date(data["start"])
        if data.get("end"):
            item["DTEND"] = parse_date(data["end"])
        elif "DTEND" in item:
            del item["DTEND"]
        resource.data = cal.to_ical()
        resource.save()
        return jsonify(event_json(item))
    except Exception as error:
        return jsonify(error=str(error)), 500


@app.delete("/api/events/<event_id>")
def delete_event(event_id):
    try:
        resource, _ = find_event(calendar(), event_id)
        if not resource:
            return jsonify(error="Event not found"), 404
        resource.delete()
        return jsonify(status="success")
    except Exception as error:
        return jsonify(error=str(error)), 500


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=5000)
