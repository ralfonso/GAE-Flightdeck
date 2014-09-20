#!/usr/bin/env python

from gevent import monkey
monkey.patch_all()
monkey.patch_sys(stdin=True, stdout=False, stderr=False)
import gevent
from gevent.queue import Queue
import getopt
import signal
import sys
from socketio.namespace import BaseNamespace
from socketio.mixins import BroadcastMixin

from .formatter import process_log
from .web_server import make_server


DEFAULT_CONFIG = {'host': '127.0.0.1',
                  'port': 51324}


q = Queue()


def producer():
    while True:
        line = sys.stdin.readline()
        process_log(line, q.put)


class LogNamespace(BaseNamespace, BroadcastMixin):
    def recv_connect(self):
        def sendlogs():
            while True:
                val = q.get(True)
                self.emit('log', {'line': val})

        self.spawn(sendlogs)


def usage():

    print 'usage: gaeflightdeck.py [--host HOST] [--port PORT]'


def merge_options_with_config(config, argv):

    try:
        opts, args = getopt.getopt(argv, '', ('host=', 'port=', ))
    except getopt.GetoptError, e:
        usage()
        sys.exit(2)

    # remove the leading -- from the options and create dict
    clean_opts = {k.lstrip('--'): v for k, v in opts}

    # if port is present, make sure it's an int and
    # valid port number
    if 'port' in clean_opts:
        try:
            clean_opts['port'] = int(clean_opts['port'])
            if clean_opts['port'] < 0x1 or clean_opts['port'] > 0xffff:
                raise ValueError
        except ValueError:
            print 'Error: port must be integer [%d-%d]' % (0x1, 0xffff)
            usage()
            sys.exit(2)

    # merge with the existing config
    config.update(clean_opts)
    return config


def main():
    gevent.signal(signal.SIGQUIT, gevent.kill)

    config = DEFAULT_CONFIG
    config['namespaces'] = {'/logs': LogNamespace}
    config = merge_options_with_config(config, sys.argv[1:])

    server = make_server(config)

    greenlets = [
        gevent.spawn(producer)
    ]

    try:
        server.start()
        print 'Log webserver running on http://%s:%d' % (config['host'],
                                                         config['port'],)
        gevent.joinall(greenlets)
    except KeyboardInterrupt:
        print "Exiting..."


if __name__ == '__main__':
    main()
