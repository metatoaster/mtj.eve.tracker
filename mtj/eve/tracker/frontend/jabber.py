import random
from time import time
from collections import OrderedDict
import logging

import requests
from requests import ConnectionError

try:
    # for requests will try to use this.
    from simplejson import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError

from mtj.jibber.bot import Command

logger = logging.getLogger(__name__)

_cache_length = 10


class TrackerError(ValueError):
    pass


class TrackerResponseError(TrackerError):
    pass


def handle_tracker_error(f):

    def run(inst, *a, **kw):
        try:
            return f(inst, *a, **kw)
        except TrackerError as e:
            if time() - _cache_length < inst.last_error_time:
                return ''
            inst.last_error_time = time()
            if inst.error_format_string:
                return inst.error_format_string % str(e)
            return str(e)

    return run


class LogiCommand(Command):

    def __init__(self, *a, **kw):
        self.tower_root = kw.pop('tracker_tower_root')
        self.overview = kw.pop('tracker_overview')
        self.backdoor = kw.pop('tracker_backdoor')
        self.error_format_string = kw.pop('error_format_string', '')

        self.cache = {}
        self.cache_time = 0

        self.last_error_time = 0

    def _overview(self):
        last_cache = time() - _cache_length
        if last_cache < self.cache_time:
            return self.cache
        if last_cache < self.last_error_time:
            raise TrackerError('Timeout still active from last error')

        try:
            r = requests.get(self.overview, headers={
                    'Authorization': 'Backdoor %s' % self.backdoor,
                }, verify=False)
            data = r.json()
        except ConnectionError:
            raise TrackerError('Error connecting to tracker.')
        except JSONDecodeError:
            raise TrackerError('Error parsing tracker response.')
        except:
            logger.exception('Exception raised')
            raise TrackerError('Error getting response from tracker. '
                               'Please check log files.')

        if 'error' in data:
            raise TrackerResponseError(data['error'])
        self.cache_time = time()
        self.cache = data

        return data

    @handle_tracker_error
    def low_fuel(self, **kw):

        def append_(by_region, p):
            region = p['regionName'] 
            if region not in by_region:
                by_region[region] = []
            p['typeNameShort'] = p['typeName'].replace('Control Tower Small',
                'Small').replace('Control Tower Medium', 'Medium').replace(
                'Control Tower', 'Large')
            by_region[region].append(p)

        def report_by_region(by_region):
            lines = []
            for region, towers in by_region.iteritems():
                lines.append(region + ' towers<br/>')
                for tower in towers:
                    tower['auditLabel'] = tower['auditLabel'] or \
                        '[unlabeled:%s]' % tower['id']
                    tower['href'] = '%s%s' % (self.tower_root, tower['id'])
                    lines.append('    <a href="%(href)s">%(auditLabel)s</a>; '
                        'Location: '
                        '%(celestialName)s; Type: %(typeNameShort)s; '
                        'Time Remaining: %(timeRemainingFormatted)s<br/>' %
                            tower
                    )
            return lines

        data = self._overview()
        lines = []
        by_region_normal = OrderedDict()
        by_region_dangerous = OrderedDict()
        for p in data.get('online'):
            if p["timeRemaining"] > 86400:
                append_(by_region_normal, p)
            else:
                append_(by_region_dangerous, p)

        if by_region_normal:
            lines.append('The following towers are low on fuel:<br/>')
            lines.extend(report_by_region(by_region_normal))

        if by_region_dangerous:
            lines.append(
                '<br/><strong style="font-weight:bold;color:#220000;">'
                'The following towers have CRITICALLY LOW fuel '
                'levels:<br/>')
            lines.extend(report_by_region(by_region_dangerous))
            lines.append('</strong>')

        if by_region_normal or by_region_dangerous:
            return '<p>%s</p>' % '\n'.join(lines)

        # otherwise return a blank string to not say anything.
        return ''

    @handle_tracker_error
    def ok_fuel(self, **kw):
        data = self._overview()
        safe = 'There are no towers with low fuel levels.'
        api_usage = data.get('api_usage', [])
        usage_str = 'Update status unknown.'
        if api_usage:
            # XXX only using the latest entry, so no support for
            # multiple keys
            usage = api_usage[-1]
            usage_str = 'Update %s since %s ago.' % (
                usage['state'],
                (usage['end_ts_delta'] or usage['start_ts_delta']),
            )
        if data.get('online'):
            return usage_str
        return safe + '\n' + usage_str

    @handle_tracker_error
    def reinforced(self, **kw):
        data = self._overview()
        if not data.get('reinforced'):
            return

        lines = []
        lines.append('<p>')
        lines.append('**** REINFORCED TOWER ALERT ****<br/>')
        by_region = OrderedDict()
        for p in data.get('reinforced'):
            p['auditLabel'] = p['auditLabel'] or '[unlabeled:%s]' % p['id']
            p['typeNameShort'] = p['typeName'].replace('Control Tower Small',
                'Small').replace('Control Tower Medium', 'Medium').replace(
                'Control Tower', 'Large')
            p['href'] = '%s%s' % (self.tower_root, p['id'])
            lines.append('<a href="%(href)s">%(typeNameShort)s</a>; '
                'Location: %(celestialName)s; '
                'Reinforced until: %(stateTimestampFormatted)s; '
                'Time Remaining: %(stateTimestampDeltaFormatted)s<br/>' % p)
        lines.append('</p>')

        return '\n'.join(lines)

    @handle_tracker_error
    def offlined(self, **kw):
        data = self._overview()
        if not data.get('offlined'):
            return

        lines = []
        lines.append('<p>')
        lines.append('**** UNINTENDED OFFLINED TOWER ALERT ****<br/>')
        by_region = OrderedDict()
        for p in data.get('offlined'):
            p['auditLabel'] = p['auditLabel'] or '[unlabeled:%s]' % p['id']
            p['typeNameShort'] = p['typeName'].replace('Control Tower Small',
                'Small').replace('Control Tower Medium', 'Medium').replace(
                'Control Tower', 'Large')
            p['href'] = '%s%s' % (self.tower_root, p['id'])
            lines.append('<a href="%(href)s">%(auditLabel)s</a>; '
                '%(typeNameShort)s; Location: %(celestialName)s; '
                '%(regionName)s<br />' % p)
        lines.append('</p>')

        return '\n'.join(lines)
