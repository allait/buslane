import datetime
import json
import itertools
import os
import sys

from collections import defaultdict
from hashlib import md5
from time import sleep

import requests
from lxml.html import fromstring


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

    def get_all(self):
        routes = []
        for service in self.services:
            service_routes = self.get(service)
            self.services[service]['routes'] = service_routes
            routes.extend(service_routes)

        return routes

    def get(self, service):
        try:
            routes = self.get_routes(service)
        except ValueError:
            return []

        for route in routes:
            start, stop = get_route_endpoints(route)
            times = self.get_full_timetable(service, start['code'], stop['code'])

            route['buses'] = times

        return drop_duplicates(routes)

    def get_services(self):
        services = {}
        service_data = get_cached('getServices.json', self.request_services)
        for service in service_data['services']:
            services[service['mnemo']] = service

        return services

    def get_routes(self, service):
        return get_cached(
            "%s_route.json" % (service),
            self.request_routes,
            service
        )

    def get_full_timetable(self, service, start, stop):
        time = 0
        times = []
        errors = 0
        # Would you look at that, a while loop in python
        while (time < 2400):
            timetable = self.get_timetables(service, start, stop, "%04d" % time)
            if timetable:
                if (int(timetable[0]['start']) < time) and (errors < 3):
                    errors += 1
                    drop_cache("_".join([service, start, stop, "%04d" % time, 'timetable.html']))
                elif errors >= 3:
                    time += 200
                else:
                    errors = 0
                    times.extend(timetable)
                    time = int(timetable[-1]['start'])
            else:
                time += 200

        return times

    def get_timetables(self, *args):
        response = get_cached(
            "_".join(args + ("timetable.html",)),
            self.request_timetables,
            *args
        )

        doc = fromstring(response)
        rows = [
            elem.xpath('./td//text()') for elem in doc.xpath('//table[@class="timetable"][2]/tr')
        ]
        if not rows:
            return rows

        start_times, stop_times = rows[0][1:], rows[-1][1:]

        return [{"start": s, "stop": e} for s, e in zip(start_times, stop_times)]

    def request_services(self):
        return self.call_api('getServices')

    def request_routes(self, service):
        base_url = 'http://lothianbuses.com/tt/parse.php?service='
        return requests.get(base_url + service).json()

    def request_timetables(self, service, start, stop, time=None):
        base_url = 'http://lothianbuses.com/plan-a-journey/timetables/'

        return requests.get(base_url + service, params={
            's': start,
            'e': stop,
            'b': time,
            'sid': service,
            'p': 120,  # time range in minutes
            'd[]': 0,  # monday to friday
            'self': '',
        }).text

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


# Cache utils

def is_cached(filename):
    return os.path.exists(CACHE_PATH + filename)


def save_data(data, filename):
    with open(CACHE_PATH + filename, 'w') as f:
        if filename.endswith('.json'):
            json.dump(data, f)
        else:
            f.write(data)


def read_data(filename):
    with open(CACHE_PATH + filename, 'r') as f:
        if filename.endswith('.json'):
            return json.load(f)
        else:
            return f.read()


def drop_cache(filename):
    os.remove(CACHE_PATH + filename)


def get_cached(filename, request_method, *args, **kwargs):
    cache_filename = filename
    if not is_cached(cache_filename):
        # plan-a-journey pages start returning wrong times if
        # there requests are coming without delay.
        # Also, it's good to be nice
        sleep(5)
        data = request_method(*args, **kwargs)
        save_data(data, cache_filename)
    else:
        data = read_data(cache_filename)

    return data


# Route utils

def drop_duplicates(routes):
    """Removes duplicate bus times from service routes.

    Some routes are a part of a larger service route, which means that
    some buses are added multiple times. In order to remove these duplicates
    we find the longest route for each start and stop time.

    """

    stop_routes = defaultdict(list), defaultdict(list)

    for index, kind in ((0, 'start'), (1, 'stop')):
        stop_routes = defaultdict(list)
        for route in routes:
            stop = get_route_endpoints(route)[index]
            stop_routes[stop['code']].append(route)

        for route_list in stop_routes.values():
            if len(route_list) <= 1:
                continue
            for r1, r2 in itertools.combinations(route_list, 2):
                if is_subroute(r1, r2):
                    parent, subroute = r2, r1
                elif is_subroute(r2, r1):
                    parent, subroute = r1, r2
                else:
                    continue
                subroute['buses'] = unique_times(subroute['buses'], parent['buses'], kind)

    return routes


def unique_times(subroute_buses, route_buses, time_key):
    """Removes entries from subroute_buses which exist in route_buses.

    Returns a new list with duplicates removed.
    Uses entry[time_key] for comparison.

    """

    route_times = set(bus[time_key] for bus in route_buses)
    return [bus for bus in subroute_buses if bus[time_key] not in route_times]


def get_route_endpoints(route):
    stops = get_route_stops(route)
    return stops[0], stops[-1]


def get_route_stops(route):
    return filter(lambda x: 'code' in x, route['points'])


def is_subroute(rA, rB):
    """Returns True if rA is a subroute of rB.

    Route A is considered a subroute if it's start and end stops are
    also stops of route B.

    """

    rA_stops = set(s['code'] for s in get_route_endpoints(rA))
    rB_stops = set(s['code'] for s in get_route_stops(rB))

    return rA_stops.issubset(rB_stops)


def compress_routes(routes):
    """Drops non-essential data to reduce route file size."""

    remaining_routes = []

    for route in routes:
        # Don't keep routes without any scheduled buses
        if not route['buses']:
            continue
        # Remove all points data except stop coordinates
        route['points'] = [{'lat': p['lat'], 'lng': p['lng']} for p in route['points']]

        remaining_routes.append(route)

    return remaining_routes


if __name__ == '__main__':
    api_key = sys.argv[1]

    bustracker = BusTracker(api_key=api_key)

    all_routes = bustracker.get_all()

    active_services = []
    for service in bustracker.services.values():
        service_routes = compress_routes(service['routes'])
        if service_routes:
            save_data(service_routes, '%s.json' % service['mnemo'])
            active_services.append({'name': service['name'], 'mnemo': service['mnemo']})

    active_services.sort(key=lambda x: int(x['mnemo']) if x['mnemo'].isdigit() else x['mnemo'])

    save_data(compress_routes(all_routes), 'all.json')
    save_data(active_services, 'services.json')
