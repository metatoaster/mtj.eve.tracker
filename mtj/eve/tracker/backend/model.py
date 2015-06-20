# miscelleneous shared models.

from collections import namedtuple

ApiTowerStatus = namedtuple('ApiTowerStatus',
    ['currentTime', 'api_error_count'])

ApiUsage = namedtuple('ApiUsage',
    ['start_ts', 'end_ts', 'state'])

api_usage_states = {
    -1: 'running',
    0: 'completed',
    1: 'error',
}
