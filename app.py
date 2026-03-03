from flask import Flask, render_template, request, jsonify
import caldav
from datetime import datetime, timedelta
from icalendar import Calendar, Event
import pytz

app = Flask(__name__)

# CalDAV configuration
CALDAV_URL = "http://localhost:5232/"  # Radicale default
CALDAV_USERNAME = "your_username"
CALDAV_PASSWORD = "your_password"

def get_caldav_client():
    client = caldav.DAVClient(
        url=CALDAV_URL,
        username=CALDAV_USERNAME,
        password=CALDAV_PASSWORD
    )
    return client

def get_calendar():
    client = get_caldav_client()
    principal = client.principal()
    calendars = principal.calendars()
    # Return first calendar or modify to select specific one
    return calendars[0] if calendars else None

@app.route('/')
def index():
    return render_template('calendar.html')

@app.route('/api/events', methods=['GET'])
def get_events():
    """Fetch events from CalDAV server"""
    try:
        calendar = get_calendar()
        if not calendar:
            return jsonify([])

        # Get date range from FullCalendar
        start = request.args.get('start')
        end = request.args.get('end')

        start_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(end.replace('Z', '+00:00'))

        # Fetch events from CalDAV
        events = calendar.date_search(start=start_date, end=end_date, expand=True)

        fullcalendar_events = []
        for event in events:
            ical = Calendar.from_ical(event.data)
            for component in ical.walk('VEVENT'):
                fullcalendar_events.append({
                    'id': str(component.get('UID')),
                    'title': str(component.get('SUMMARY', 'No Title')),
                    'start': component.get('DTSTART').dt.isoformat(),
                    'end': component.get('DTEND').dt.isoformat() if component.get('DTEND') else None,
                    'allDay': not isinstance(component.get('DTSTART').dt, datetime),
                    'url': event.url
                })

        return jsonify(fullcalendar_events)

    except Exception as e:
        print(f"Error fetching events: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/events', methods=['POST'])
def create_event():
    """Create new event on CalDAV server"""
    try:
        data = request.json
        calendar = get_calendar()

        cal = Calendar()
        event = Event()

        event.add('summary', data['title'])
        event.add('dtstart', datetime.fromisoformat(data['start'].replace('Z', '+00:00')))

        if data.get('end'):
            event.add('dtend', datetime.fromisoformat(data['end'].replace('Z', '+00:00')))

        event.add('uid', data.get('id', str(datetime.now().timestamp())))
        event.add('dtstamp', datetime.now(pytz.UTC))

        cal.add_component(event)

        calendar.save_event(cal.to_ical())

        return jsonify({'status': 'success'}), 201

    except Exception as e:
        print(f"Error creating event: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/events/<event_id>', methods=['PUT'])
def update_event(event_id):
    """Update existing event"""
    try:
        data = request.json
        calendar = get_calendar()

        # Find and update the event
        events = calendar.events()
        for event in events:
            ical = Calendar.from_ical(event.data)
            for component in ical.walk('VEVENT'):
                if str(component.get('UID')) == event_id:
                    component['SUMMARY'] = data['title']
                    component['DTSTART'].dt = datetime.fromisoformat(data['start'].replace('Z', '+00:00'))
                    if data.get('end'):
                        component['DTEND'].dt = datetime.fromisoformat(data['end'].replace('Z', '+00:00'))

                    event.data = ical.to_ical()
                    event.save()
                    return jsonify({'status': 'success'})

        return jsonify({'error': 'Event not found'}), 404

    except Exception as e:
        print(f"Error updating event: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/events/<event_id>', methods=['DELETE'])
def delete_event(event_id):
    """Delete event from CalDAV server"""
    try:
        calendar = get_calendar()
        events = calendar.events()

        for event in events:
            ical = Calendar.from_ical(event.data)
            for component in ical.walk('VEVENT'):
                if str(component.get('UID')) == event_id:
                    event.delete()
                    return jsonify({'status': 'success'})

        return jsonify({'error': 'Event not found'}), 404

    except Exception as e:
        print(f"Error deleting event: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
