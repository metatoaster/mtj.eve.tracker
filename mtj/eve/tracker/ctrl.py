from __future__ import unicode_literals  # we are using json anyway.

import cmd
import json

from mtj.eve.tracker.runner import BaseRunner


class Options(object):

    default_config = {
        'logging': {
            'level': 'WARNING',
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
            'time_format': '%Y-%m-%d %H:%M:%S',
            'path': None,
        },
        'data': {
            'evelink_cache': ':memory:',
            'backend_url': 'sqlite:///:memory:',
        },
        'api': {
            'source': 'config',  # 'backend' is the other choice
            'api_keys': []
        },
    }

    _schema = {
        'logging': {
            'level': basestring,
            'format': basestring,
            'time_format': basestring,
            'path': basestring,
        },
        'data': {
            'evelink_cache': basestring,
            'backend_url': basestring,
        },
        'api': {
            'source': basestring,
            'api_keys': dict,
        },
    }

    def __init__(self):
        self.config = {}
        self.config.update(Options.default_config)

    def load_config(self, config_file):
        fd = open(config_file)
        config = json.load(fd)
        fd.close()
        self.update(config)

    def update(self, source, target=None, _schema=None):
        if not isinstance(source, dict):
            raise TypeError('source needs to be a dict')

        if target is None:
            target = self.config

        if _schema is None:
            _schema = self._schema

        for k, v in source.iteritems():
            if k not in _schema:
                continue

            if isinstance(_schema[k], dict):
                self.update(v, target[k], _schema[k])

            if isinstance(_schema[k], type):
                if isinstance(v, _schema[k]):
                    target[k] = v
