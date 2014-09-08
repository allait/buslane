import datetime
import json
import os
import sys
from time import sleep
from hashlib import md5

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
            routes.extend(self.get(service))

        return routes

    def get(self, service):
        routes = self.get_routes(service)
        timetables, bus_routes = [], []
        for route in routes:
            stops = filter(lambda x: 'code' in x, route['points'])
            start, stop = stops[0]['code'], stops[-1]['code']
            times = self.get_full_timetable(service, start, stop)

            # Some routes have duplicates: same start and destination stops
            # but slightly different service points along the way.
            # This leads to multiple buses starting at the same time.
            # Since there's no easy way to separate timetables between these subroutes,
            # we'll just drop routes with times we've seen before
            if times not in timetables:
                route['buses'] = map(rel_time, times)
                timetables.append(times)
                bus_routes.append(route)

        return bus_routes

    def get_services(self):
        services = {}
        service_data = get_cached('services.json', self.request_services)
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
        # Would you look at that, a while loop in python
        while (time < 2400):
            timetable = self.get_timetables(service, start, stop, "%04d" % time)
            if timetable:
                times.extend(timetable)
                if int(timetable[0]['start']) < time:
                    drop_cache("_".join([service, start, stop, "%04d" % time, 'timetable.html']))
                else:
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


def rel_time(bus_time):
    return dict([(k, ((int(v) / 100) * 60 + int(v) % 100)) for k, v in bus_time.items()])


if __name__ == '__main__':
    api_key = sys.argv[1]
    save_data(BusTracker(api_key=api_key).get_all(), 'all.json')
