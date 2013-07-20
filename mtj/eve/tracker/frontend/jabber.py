import random
import time
from collections import OrderedDict

import requests

from mtj.jibber.bot import Command


class LogiCommand(Command):

    def __init__(self, *a, **kw):
        self.tower_root = kw.pop('tracker_tower_root')
        self.overview = kw.pop('tracker_overview')
        self.backdoor = kw.pop('tracker_backdoor')

    def low_fuel(self, msg, match):
        try:
            r = requests.get(self.overview, headers={
                    'Authorization': 'Backdoor %s' % self.backdoor,
                }, verify=False)
            data = r.json()
            if 'error' in data:
                raise ValueError
        except:
            return 'Failed to retrieve results from <%s>' % (target)

        lines = []
        lines.append('<p>')
        lines.append('The following towers are low on fuel:<br/>')
        by_region = OrderedDict()
        for p in data.get('online'):
            region = p['regionName'] 
            if region not in by_region:
                by_region[region] = []
            p['typeNameShort'] = p['typeName'].replace('Control Tower Small',
                'Small').replace('Control Tower Medium', 'Medium').replace(
                'Control Tower', 'Large')
            by_region[region].append(p)

        for region, towers in by_region.iteritems():
            lines.append(region + ' towers<br/>')
            for tower in towers:
                tower['auditLabel'] = tower['auditLabel'] or \
                    '[unlabeled:%s]' % tower['id']
                tower['href'] = '%s%s' % (self.tower_root, tower['id'])
                lines.append('    <a href="%(href)s">%(auditLabel)s</a>; '
                    'Location: '
                    '%(celestialName)s; Type: %(typeNameShort)s; '
                    'Time Remaining: %(timeRemainingFormatted)s<br/>' % tower)

        lines.append('</p>')
        return '\n'.join(lines)

    def reinforced(self, msg, match):
        try:
            r = requests.get(self.overview, headers={
                    'Authorization': 'Backdoor %s' % self.backdoor,
                }, verify=False)
            data = r.json()
            if 'error' in data:
                raise ValueError
        except:
            return

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
