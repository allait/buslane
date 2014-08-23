import itertools
import json
import os

import requests
from lxml.html import fromstring

SERVICES = [
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "14", "15",
    "15A", "16", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27",
    "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40",
    "41", "42", "43", "44", "44A", "45", "47", "49", "61", "63", "67", "69",
    "100", "113", "N3", "N11", "N16", "N22", "N25", "N26", "N30", "N31", "N34",
    "N37", "N44", "X12", "X25", "X26", "X29", "X31", "X37", "X44",
]

CACHE_PATH = 'data/'


class ServiceData(object):
    cache_extension = 'txt'

    def __init__(self, service):
        self.service = service

    def get(self):
        cache_filename = '%s_%s.%s' % (
            self.service, self.__class__.__name__.lower(), self.cache_extension
        )
        if not is_cached(cache_filename):
            data = self.request()
            save_data(data, cache_filename)
        else:
            data = read_data(cache_filename)

        return self.parse(data)

    def request(self):
        raise NotImplemented()

    def parse(self, data):
        return data


class Route(ServiceData):
    cache_extension = 'json'

    def request(self):
        base_url = 'http://lothianbuses.com/tt/parse.php?service='
        return requests.get(base_url + self.service).json()


class Timetable(ServiceData):
    cache_extension = 'html'

    def request(self):
        base_url = 'http://lothianbuses.com/plan-a-journey/timetables/'
        return requests.get(base_url + self.service).text

    def parse(self, response):
        doc = fromstring(response)
        rows = [elem.xpath('./td//text()') for elem in doc.xpath('//table/tr')]
        for row in rows:
            times = filter(lambda x: x.isdigit(), map(lambda x: x.strip(), row[1:]))
            if times:
                print [row[0]] + times
            else:
                print "\n"


def is_cached(filename):
    return os.path.exists(CACHE_PATH + filename)


def save_data(data, filename):
    with open(CACHE_PATH + filename, 'w') as file:
        json.dump(data, file)


def read_data(filename):
    with open(CACHE_PATH + filename, 'r') as file:
        return json.load(file)


def all_routes():
    service_routes = [Route(service).get() for service in SERVICES]
    routes = []
    for route in itertools.chain(*service_routes):
        # Remove everything except point coordinates
        route_data = {
            'points': [{'lat': p['lat'], 'lng': p['lng']} for p in route['points']]
        }
        routes.append(route_data)

    save_data(routes, 'all_route.json')
    return routes


if __name__ == '__main__':
    routes = Route("30").get()
    for off, route in enumerate(routes):
        # Placeholder times
        route['buses'] = [{'start': i + 5 * off, 'stop': i + 5 * off + 60} for i in range(0, 24 * 60, 15)]
    save_data(routes, '30t_route.json')
