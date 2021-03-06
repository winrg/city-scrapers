# -*- coding: utf-8 -*-
import re
from datetime import datetime

import dateutil
import dateutil.parser
from legistar.events import LegistarEventsScraper

from city_scrapers.constants import BOARD
from city_scrapers.spider import Spider


class DetWaterSewageDepartmentSpider(Spider):
    name = 'det_water_sewage_department'
    agency_name = 'Detroit Water and Sewage Department'
    timezone = 'America/Detroit'
    start_urls = ['https://dwsd.legistar.com']
    allowed_domains = ['dwsd.legistar.com']

    def _make_legistar_call(self, since=None):
        les = LegistarEventsScraper()
        les.EVENTSPAGE = 'https://dwsd.legistar.com/Calendar.aspx'
        les.BASE_URL = 'https://dwsd.legistar.com'
        if not since:
            since = datetime.today().year
        return les.events(since=since)

    def parse(self, response):
        """
        `parse` should always `yield` a dict that follows the Event Schema
        <https://city-bureau.gitbooks.io/documenters-event-aggregator/event-schema.html>.
        Change the `_parse_id`, `_parse_name`, etc methods to fit your scraping
        needs.
        """
        events = self._make_legistar_call()
        return self._parse_events(events)

    def _parse_events(self, events):
        for item in events:
            item = item[0]
            data = {
                '_type': 'event',
                'name': item['Name'],
                'event_description': '',
                'classification': BOARD,
                'start': self._parse_start(item),
                'end': {
                    'date': None,
                    'time': None,
                    'note': ''
                },
                'all_day': False,
                'location': self._parse_location(item),
                'sources': self._parse_sources(item),
                'documents': self._parse_documents(item)
            }
            data['status'] = self._generate_status(data, item['Meeting Location'])
            data['id'] = self._generate_id(data)

            yield data

    def _parse_documents(self, item):
        """
        Parse meeting minutes and agenda if available.
        """
        documents = []
        for doc in ['Agenda', 'Minutes', 'Video']:
            if isinstance(item.get(doc), dict) and item[doc].get('url'):
                documents.append({'url': item[doc]['url'], 'note': doc})
        return documents

    @staticmethod
    def _get_doc(item, dockey):
        doc = item[dockey]
        if isinstance(doc, dict):
            return {'url': doc['url'], 'note': dockey}
        return None

    def _parse_location(self, item):
        """
        Parse location
        """
        address = item.get('Meeting Location', None)
        if address:
            address = re.sub(
                r'\s+',
                ' ',
                re.sub(r'(\n)|(--em--)|(--em)|(em--)', ' ', address),
            ).strip()

        if 'water board' in address.lower():
            addr_split = address.split(', ')
            water_board_address = '735 Randolph St Detroit, MI 48226'
            if 'room' in addr_split[0].lower():
                address = '{} {}'.format(addr_split[0], water_board_address)
            else:
                address = water_board_address
            return {
                'name': 'Water Board Building',
                'address': address,
                'neighborhood': '',
            }
        return {
            'name': '',
            'address': address,
            'neighborhood': '',
        }

    def _parse_start(self, item):
        """
        Parse start date and time.
        """
        time = item.get('Meeting Time', '')
        date = item.get('Meeting Date', '')
        note = ''
        time_string = '{0} {1}'.format(date, time)
        dt, other_text = dateutil.parser.parse(time_string, fuzzy_with_tokens=True)
        if other_text:
            note = ' '.join([s.strip() for s in other_text if s.strip()])
        return {'date': dt.date(), 'time': dt.time(), 'note': note}

    def _parse_sources(self, item):
        """
        Parse sources.
        """
        try:
            url = item['Name']['url']
        except Exception:
            url = 'https://dwsd.legistar.com/Calendar.aspx'
        return [{'url': url, 'note': ''}]
