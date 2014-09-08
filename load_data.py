import datetime
import json
import os
import sys
from hashlib import md5

import requests


CACHE_PATH = 'data/'


class BusTracker(object):
    api_url = 'http://ws.mybustracker.co.uk/'

    def __init__(self, api_key):
        self.api_key = api_key
        self._services = None

    @property
    def services(self):
        # Yeah, this is I/O on attribute access, don't do this
        if self._services is None:
            self._services = self.get_services()

        return self._services

    @property
    def key(self):
        time_string = datetime.datetime.utcnow().strftime("%Y%m%d%H")
        return md5(self.api_key + time_string).hexdigest()

    def get(self, service):
        routes = self.get_routes(service)
        self.services[service]['routes'] = routes
        return self.services[service]

    def get_services(self):
        services = {}
        service_data = get_cached('services.json', self.request_services)
        for service in service_data['services']:
            services[service['mnemo']] = service

        return services

    def get_stops(self):
        stops_data = get_cached('stops.json', self.request_stops)
        return stops_data['busStops']

    def get_destinations(self):
        destinations = {}
        dest_data = get_cached('destinations.json', self.request_destinations)
        for dest in dest_data['dests']:
            destinations[dest['ref']] = dest

        return destinations

    def get_routes(self, service):
        return get_cached(
            "%s_route.json" % (service),
            self.request_routes,
            service
        )

    def get_timetables(self, service, stop, destination=None, day=0, time=None):
        # We care about the timetable weekday, not offset from today
        # This is somewhat wrong, since day to day times might be different,
        # but that doesn't really matter much in this case
        weekday = (datetime.date.today() + datetime.timedelta(days=day)).weekday()

        filename = "_".join(map(str, [
            service,
            "timetable",
            stop,
            destination,
            weekday,
            time
        ]))

        timetable = get_cached(
            "%s.json" % filename,
            self.request_timetables,
            service, stop, destination, day, time
        )

        return timetable

    def request_services(self):
        return self.call_api('getServices')

    def request_stops(self):
        return self.call_api('getBusStops')

    def request_destinations(self):
        return self.call_api('getDests')

    def request_service_points(self, service):
        service_ref = self.services[service]['ref']
        return self.call_api('getServicePoints', {'ref': service_ref})

    def request_routes(self, service):
        base_url = 'http://lothianbuses.com/tt/parse.php?service='
        return requests.get(base_url + service).json()

    def request_timetables(self, service, stop, destination=None, day=0, time=None):
        service_ref = self.services[service]['ref']
        return self.call_api('getBusTimes', {
            'stopId': stop,
            'refService': service_ref,
            'refDest': destination,
            'time': time,
            'day': day,
            'nb': 10,
        })

    def request_journey(self, stop, journey):
        return self.call_api('getJourneyTimes', {
            'stopId': stop,
            'journeyId': journey,
        })

    def call_api(self, function, params=None):
        if params is None:
            params = {}
        else:
            params = params.copy()

        params.update({
            'module': 'json',
            'key': self.key,
            'function': function,
        })
        return requests.get(self.api_url, params=params).json()


def is_cached(filename):
    return os.path.exists(CACHE_PATH + filename)


def save_data(data, filename):
    with open(CACHE_PATH + filename, 'w') as file:
        json.dump(data, file)


def read_data(filename):
    with open(CACHE_PATH + filename, 'r') as file:
        return json.load(file)


def get_cached(filename, request_method, *args, **kwargs):
    cache_filename = filename
    if not is_cached(cache_filename):
        data = request_method(*args, **kwargs)
        save_data(data, cache_filename)
    else:
        data = read_data(cache_filename)

    return data


if __name__ == '__main__':
    api_key = sys.argv[1]
    print BusTracker(api_key=api_key).get("38")
