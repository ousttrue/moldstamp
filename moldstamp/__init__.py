import sys
import pathlib
import argparse
from . import generator
from . import server

VERSION = [0, 1]


def main():
    parser = argparse.ArgumentParser(description='A static site generator')
    sub = parser.add_subparsers()

    gen_parser = sub.add_parser('gen')
    gen_parser.set_defaults(action='gen')

    generator.setup_parser(gen_parser)

    server_parser = sub.add_parser('server')
    server_parser.set_defaults(action='server')

    server.setup_parser(server_parser)

    args = parser.parse_args()

    try:
        action = args.action
    except AttributeError:
        parser.print_help()
        sys.exit()

    if action == 'gen':
        src = pathlib.Path(args.src).resolve()
        dst = pathlib.Path(args.dst).resolve()
        generator.execute(src, dst)

    elif action == 'server':
        src = pathlib.Path(args.src).resolve()
        server.execute(src, args.port)

    else:
        raise RuntimeError()


if __name__ == '__main__':
    main()
