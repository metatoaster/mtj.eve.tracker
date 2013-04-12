from __future__ import unicode_literals  # we are using json anyway.

import argparse
import cmd
import code
import json
import os
import sys
import tempfile

from mtj.eve.tracker.runner import BaseRunner, FlaskRunner


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
            'evedb_url': None,
            'backend_url': 'sqlite:///:memory:',
        },
        'api': {
            'source': 'config',
            'api_keys': {},
        },
        'flask': {
            'host': '127.0.0.1',
            'port': 8000,
            'json_prefix': None,
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
            'evedb_url': basestring,
            'backend_url': basestring,
        },
        'api': {
            'source': ('config', 'backend'),
            'api_keys': dict,
        },
        'flask': {
            'host': basestring,
            'port': int,
            'json_prefix': basestring,
        },
    }

    def __init__(self):
        self.config = {}
        self.config.update(Options.default_config)

    def load_config(self, stream):
        config = json.load(stream)
        self.update(config)

    def dump_config(self, stream):
        json.dump(self.config, stream, indent=4)

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

            if isinstance(_schema[k], tuple):
                if v in _schema[k]:
                    target[k] = v


class TrackerCmd(cmd.Cmd):

    def __init__(self, options, app=None, runner_factory=None):
        if isinstance(options, Options):
            self.options = options
        else:
            # Assume this is a dict.
            self.options = Options()
            self.options.update(options)

        self.prompt = 'mtj.tracker.ctrl> '
        cmd.Cmd.__init__(self)

        if runner_factory is None:
            runner_factory = FlaskRunner

        self.app = app
        self.runner_factory = runner_factory

    def run(self, config):
        """
        Run this thing.
        """

        runner = self.runner_factory()
        runner.configure(config=config)
        runner.initialize()
        runner.run(app=self.app)

    def do_start(self, arg):
        """
        start the daemon (not implemented).
        """

        print "daemon mode not implemented."

    def do_stop(self, arg):
        """
        stop the daemon (not implemented).
        """

        print "can't stop what's not implemented"

    def do_fg(self, arg):
        """
        run this in the foreground.
        """

        # local foreground options.
        options = Options()
        options.update(self.options.config)
        options.update({'logging': {'level': 'INFO', 'path': '',}})

        self.run(options.config)

    def do_debug(self, arg):
        """
        start the python debugger with the environment instantiated.
        """

        # local foreground options.
        options = Options()
        options.update(self.options.config)
        options.update({'logging': {'level': 'INFO', 'path': '',}})

        runner = BaseRunner()
        runner.configure(config=options.config)
        runner.initialize()

        import zope.component
        from mtj.eve.tracker import interfaces
        manager = zope.component.getUtility(interfaces.ITowerManager)
        backend = zope.component.getUtility(interfaces.ITrackerBackend)

        try:
            import readline
        except ImportError:
            pass

        console = code.InteractiveConsole(locals={
            b'backend': backend,
            b'manager': manager,
        })
        result = console.interact('')

    def do_read_config(self, arg):
        """
        read the configuration file

        usage: read_config <filename>
        """

        if not arg:
            print "usage: read_config <filename>"
            return

        try:
            fd = open(arg)
            try:
                self.options.load_config(fd)
            except TypeError as e:
                print 'invalid config file `%s`, %s' % (arg, str(e))
            except ValueError as e:
                print 'invalid config file `%s`, %s' % (arg, str(e))
            fd.close()
        except IOError:
            print 'cannot load config from file `%s`' % arg

    def do_write_config(self, arg):
        """write the config file.

        usage: write_config <filename>
        """

        if not arg:
            print "usage: write_config <filename>"
            return

        if os.path.exists(arg):
            print '`%s` already exists' % arg
            return

        try:
            td = tempfile.TemporaryFile()
            self.options.dump_config(td)
            td.seek(0)
            try:
                fd = open(arg, 'w')
                fd.write(td.read())
                fd.close()
            finally:
                td.close()
        except IOError:
            print 'cannot write config to file `%s`' % arg
        except TypeError as e:
            print 'configuration cannot be written, %s' % str(e)

    def do_EOF(self, arg):
        print
        return 1


def get_argparsers():
    parser = argparse.ArgumentParser(description='Runner for mtj.pos.tracker.')
    parser.add_argument('--config', '-c', dest='config_file', required=False,
        help='The configuration file')

    sp = parser.add_subparsers(dest='command')
    sp_start = sp.add_parser(r'start', help='Starts %(prog)s daemon')
    sp_stop = sp.add_parser(r'stop', help='Stops %(prog)s daemon')
    sp_restart = sp.add_parser(r'restart', help='Restarts %(prog)s daemon')
    sp_fg = sp.add_parser(r'fg', help='Run %(prog)s in foreground')
    sp_debug = sp.add_parser(r'debug', help='Open a debug python shell')
    sp_console = sp.add_parser(r'console', help='Console mode (default)')

    return parser, sp


def main(args=None, options=None, app=None, runner_factory=None,
        cmdclass=TrackerCmd):
    if args is None:
        args = sys.argv[1:]

    if options is None:
        options = Options()

    _default = 'console'

    parser, sp = get_argparsers()

    # workaround for an apparent lack of optional subparser
    if not set.intersection(set(args), set(sp.choices.keys())):
        args.append(_default)

    parsed_args = parser.parse_args(args)

    c = cmdclass(options, app=app, runner_factory=runner_factory)

    if parsed_args.config_file:
        c.do_read_config(parsed_args.config_file)

    if parsed_args.command and parsed_args.command != _default:
        return c.onecmd(parsed_args.command)
    else:  # interactive mode
        try:
            import readline
        except ImportError:
            pass
        c.cmdloop()

if __name__ == "__main__":
    main()
