from __future__ import unicode_literals  # we are using json anyway.

import argparse
import cmd
import code
import errno
import json
import logging
import os
import signal
import sys
import tempfile

try:
    import daemon
    from daemon.pidfile import TimeoutPIDLockFile
    from daemon.runner import is_pidfile_stale
    import lockfile
    import pwd
    HAS_DAEMON = True
except ImportError:
    HAS_DAEMON = False

from mtj.eve.tracker.runner import BaseRunner, FlaskRunner


class Options(object):

    default_config = {
        'logging': {
            'level': 'WARNING',
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
            'time_format': '%Y-%m-%d %H:%M:%S',
            'path': None,
        },

        'implementations': {
            # will be initialized first.
            'IEvelinkCache': {
                'class': 'mtj.eve.tracker.evelink.EvelinkSqliteCache',
                'args': [':memory:'],
                'kwargs': {},
            },
            # optional
            'IAPIHelper': {
                'class': 'mtj.eve.tracker.evelink.Helper',
            },
            # required
            'IAPIKeyManager': {
                'class': 'mtj.eve.tracker.manager.APIKeyManager',
                'args': [],
                'kwargs': {
                    'api_keys': {},
                },
            },
            # required
            'ITrackerBackend': {
                'class': 'mtj.eve.tracker.backend.sql.SQLAlchemyBackend',
                'args': [],
                'kwargs': {
                    'backend_url': 'sqlite:///:memory:',
                },
            },
            # optional.
            'ITowerManager': {
                'class': 'mtj.eve.tracker.manager.TowerManager',
                'args': [],
                'kwargs': {},
            },
        },

        'data': {
            'evedb_url': None,
        },
        'daemon': {
            'effective_user': None,
            'pidfile': 'mtj_daemon.pid',
            'working_directory': None,
        },
        'flask': {
            'host': '127.0.0.1',
            'port': 8000,
            'secret': 'defaultsecretkeypleasechangeme',
        },
        'mtj.eve.tracker.runner.FlaskRunner': {
            'json_prefix': None,
            'admin_key': None
        },
    }

    _schema = {
        'logging': {
            'level': basestring,
            'format': basestring,
            'time_format': basestring,
            'path': basestring,
        },
        'implementations': {
            'IEvelinkCache': {
                'class': basestring,
                'args': list,
                'kwargs': dict,
            },
            'IAPIHelper': {
                'class': basestring,
                'args': list,
                'kwargs': dict,
            },
            'IAPIKeyManager': {
                'class': basestring,
                'args': list,
                'kwargs': dict,
            },
            'ITrackerBackend': {
                'class': basestring,
                'args': list,
                'kwargs': dict,
            },
            'ITowerManager': {
                'class': basestring,
                'args': list,
                'kwargs': dict,
            },
        },
        'data': {
            'evedb_url': basestring,
        },
        'daemon': {
            'effective_user': basestring,
            'pidfile': basestring,
            'working_directory': basestring,
        },
        'flask': {
            'host': basestring,
            'port': int,
            'secret': basestring,
        },
        'mtj.eve.tracker.runner.FlaskRunner': {
            'json_prefix': basestring,
            'admin_key': basestring,
        },
    }

    def __init__(self):
        self.config = {}
        self.config.update(self.default_config)

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

    def make_runner(self, config):
        """
        Return an instantiated and configured runner instance.
        """

        runner = self.runner_factory()
        runner.configure(config=config)
        return runner

    def run(self, config):
        """
        Run the thing right away.
        """

        runner = self.make_runner(config)
        runner.initialize()
        runner.run(app=self.app)

    def get_daemon_config(self):
        return self.options.config.get('daemon')

    def make_pid_file(self, timeout=0):
        return TimeoutPIDLockFile(self.get_daemon_config().get('pidfile'),
            timeout)

    def do_start(self, arg):
        """
        start the daemon (not implemented).
        """

        if not HAS_DAEMON:
            print("The package python-daemon is not available, please use fg.")
            return

        # As the python-daemon implementation will close all file
        # handlers by default, we have to defer the opening of all file
        # handlers that may end up being referenced after the fork to
        # prevent hilariously bad things from happening, like writing
        # the logs into a database file.
        logs = []

        def get_uid_gid(username):
            # Get the uid/gid from username to drop into post-startup
            if not username:
                return None, None
            try:
                pwrec = pwd.getpwnam(username)
            except KeyError:
                try:
                    pwrec = pwd.getpwuid(int(username))
                except (KeyError, ValueError):
                    logs.append((logging.WARNING,
                        'Invalid or unknown daemon.effective_user: `%r`',
                        username))
                    return None, None
            if os.geteuid() == 0:
                logs.append((logging.INFO,
                    'Found daemon.effective_user: %s (uid=%d).',
                    pwrec[0], pwrec[2]))
                return pwrec[2], pwrec[3]
            if os.geteuid() == pwrec[2]:
                logs.append((logging.INFO,
                    'Already running as daemon.effective_user: %s (uid=%d).',
                    pwrec[0], pwrec[2]))
                return None, None
            logs.append((logging.WARNING,
                'Process owner is not root; daemon.effective_user ignored.'))

        def make_daemon_context():
            config_daemon = self.get_daemon_config()
            pidfile = self.make_pid_file()
            uid, gid = get_uid_gid(config_daemon.get('effective_user'))
            working_dir = config_daemon.get('working_directory')

            if working_dir is None:
                print('ERROR: working directory undefined; aborting.')
                return

            # need to figure out relative paths to pid?

            return daemon.DaemonContext(**{
                'pidfile': pidfile,
                'uid': uid,
                'gid': gid,
                'stdin': sys.stdin,
                'stdout': sys.stdout,
                'stderr': sys.stderr,
            })

        dcontext = make_daemon_context()
        if not dcontext:
            print("ERROR: Fail to construct daemon context.")
            return

        pid = dcontext.pidfile.read_pid()
        if pid:
            if is_pidfile_stale(dcontext.pidfile):
                print("Removing stale pid file.")
                dcontext.pidfile.break_lock()
            else:
                print("Daemon already running (pid=%d)." % pid)
                return

        try:
            print("Starting daemon; check logs for status.")
            dcontext.open()
        except (lockfile.LockTimeout, lockfile.AlreadyLocked):
            print("ERROR: Failed to acquire pid lock file.")

        # Elsie's homeworld opened.

        logger = logging.getLogger('mtj.eve.tracker.ctrl')
        runner = self.make_runner(self.options.config)
        # Log the deferred logs.
        for log in logs:
            logger.log(*log)

        logger.info("Daemon running (pid=%d).", dcontext.pidfile.read_pid())

        try:
            runner.initialize()
            runner.run(app=self.app)
        except SystemExit as e:
            logger.info('%s', e)
        except:
            logger.exception("Unexpected error broke the runner.")

    def do_stop(self, arg):
        """
        stop the daemon (not implemented).
        """

        pidfile = self.make_pid_file()
        pid = pidfile.read_pid()
        if not pid:
            print("Daemon not running.")
            return
        if is_pidfile_stale(pidfile):
            print("Removing stale pid file.")
            pidfile.break_lock()
            return

        try:
            os.kill(pid, signal.SIGTERM)
            try:
                pidfile.acquire(5)
            except lockfile.LockTimeout:
                print("Daemon still running (pid=%d)." % pid)
            else:
                pidfile.release()
                print("Daemon process terminated.")
        except OSError as e:
            print("Error terminating daemon (pid=%d)." % pid)

    def do_restart(self, arg):
        self.do_stop(arg)
        self.do_start(arg)

    def do_status(self, arg):
        pidfile = self.make_pid_file()
        pid = pidfile.read_pid()
        if not pid:
            print("Daemon not running.")
            return
        if not is_pidfile_stale(pidfile):
            print("Daemon running (pid=%d)." % pid)

    def do_fg(self, arg):
        """
        run this in the foreground.
        """

        # local foreground options.
        options = self.options.__class__()
        options.update(self.options.config)
        options.update({'logging': {'level': 'INFO', 'path': '',}})

        self.run(options.config)

    def do_import(self, arg):
        # local foreground options.
        # XXX this needs DRYing...
        options = self.options.__class__()
        options.update(self.options.config)

        if arg:
            print('Notice: `%s` will be notified of update.' % arg)

        runner = self.runner_factory()
        runner.configure(config=options.config)
        runner.initialize()

        import requests
        import zope.component
        from mtj.eve.tracker import interfaces
        manager = zope.component.getUtility(interfaces.ITowerManager)
        manager.importAll()

        if arg:
            p = options.config['mtj.eve.tracker.runner.FlaskRunner']
            print(requests.post(arg, data='{"key": "%(admin_key)s"}' % p
                ).content)

    def do_debug(self, arg):
        """
        start the python debugger with the environment instantiated.
        """

        # local foreground options.
        options = self.options.__class__()
        options.update(self.options.config)
        options.update({'logging': {'level': 'INFO', 'path': '',}})

        runner = self.runner_factory()
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
            b'runner': runner,
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
            print("usage: read_config <filename>")
            return

        try:
            fd = open(arg)
            try:
                self.options.load_config(fd)
            except TypeError as e:
                print('invalid config file `%s`, %s' % (arg, str(e)))
            except ValueError as e:
                print('invalid config file `%s`, %s' % (arg, str(e)))
            fd.close()
        except IOError:
            print('cannot load config from file `%s`' % arg)

    def do_write_config(self, arg):
        """write the config file.

        usage: write_config <filename>
        """

        if not arg:
            print("usage: write_config <filename>")
            return

        if os.path.exists(arg):
            print('`%s` already exists' % arg)
            return

        try:
            td = tempfile.TemporaryFile()
            self.options.dump_config(td)
            # TODO maybe set the daemon working dir to the target dir if
            # it's undefined.
            td.seek(0)
            try:
                fd = open(arg, 'w')
                fd.write(td.read())
                fd.close()
            finally:
                td.close()
        except IOError:
            print('cannot write config to file `%s`' % arg)
        except TypeError as e:
            print('configuration cannot be written, %s' % str(e))

    def do_EOF(self, arg):
        print('')
        return 1


def get_argparsers():
    parser = argparse.ArgumentParser(description='Runner for mtj.pos.tracker.')
    parser.add_argument('--config', '-c', dest='config_file', required=False,
        help='The configuration file')

    sp = parser.add_subparsers(dest='command')
    sp_start = sp.add_parser(r'start', help='Starts %(prog)s daemon')
    sp_stop = sp.add_parser(r'stop', help='Stops %(prog)s daemon')
    sp_restart = sp.add_parser(r'restart', help='Restarts %(prog)s daemon')
    sp_status = sp.add_parser(r'status', help='Get daemon status')
    sp_fg = sp.add_parser(r'fg', help='Run %(prog)s in foreground')
    sp_import = sp.add_parser(r'import', help='Imports API data')
    sp_debug = sp.add_parser(r'debug', help='Open a debug python shell')
    sp_console = sp.add_parser(r'console', help='Console mode (default)')

    sp_import.add_argument('--update', '-u', dest='cmdarg', required=False,
        help='After API update, send a reload request to a running instance. '
             'optionally specify the target.',
        default='', nargs='?')

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
        cmdarg = getattr(parsed_args, 'cmdarg', '')
        if not cmdarg and parsed_args.command == 'import':
            p = {}
            p.update(c.options.config['mtj.eve.tracker.runner.FlaskRunner'])
            p.update(c.options.config['flask'])
            cmdarg = 'http://%(host)s:%(port)s%(json_prefix)s/reload' % p
        return c.onecmd(parsed_args.command + ' ' + cmdarg)
    else:  # interactive mode
        try:
            import readline
        except ImportError:
            pass
        c.cmdloop()

if __name__ == "__main__":
    main()
