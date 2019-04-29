import sys
import argparse
from . import generator
from . import server

VERSION = [0, 1]


def main():
    # setup
    parser = argparse.ArgumentParser(description='A static site generator')
    sub = parser.add_subparsers()

    gen_parser = sub.add_parser('gen')
    gen_parser.set_defaults(action='gen')
    generator.setup_parser(gen_parser)

    server_parser = sub.add_parser('server')
    server_parser.set_defaults(action='server')
    server.setup_parser(server_parser)

    # run
    args = parser.parse_args()
    try:
        action = args.action
    except AttributeError:
        parser.print_help()
        sys.exit()
    if action == 'gen':
        generator.execute(args)

    elif action == 'server':
        server.execute(args)

    else:
        raise RuntimeError()


if __name__ == '__main__':
    main()
