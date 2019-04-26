#!/usr/bin/env python

import sys
import argparse
import re
import toml
import pathlib
import shutil
import markdown2
from typing import List, Set
import jinja2
from pygments.formatters import HtmlFormatter

VERSION = [0, 1]

HERE = pathlib.Path(__file__).resolve().parent

SPLITTER = re.compile(r'^\+\+\+$', re.M)
TITLE_MATCH = re.compile(r'^\s+<li><a href="[^"]*">([^<]*)')
LINK_PATTERN = [(
    re.compile(
        r'((([A-Za-z]{3,9}:(?:\/\/)?)(?:[\-;:&=\+\$,\w]+@)?[A-Za-z0-9\.\-]+(:[0-9]+)?|(?:www\.|[\-;:&=\+\$,\w]+@)[A-Za-z0-9\.\-]+)((?:\/[\+~%\/\.\w\-_]*)?\??(?:[\-\+=&;%@\.\w_]*)#?(?:[\.\!\/\\\w]*))?)'  # noqa: E501
    ),
    r'\1')]


class Article:
    def __init__(self, path, frontmatter, content, toc, title: str) -> None:
        self.name = path.stem
        self.folder = path.parent
        self.src_path = self.folder / f'{self.name}.html'
        self.path = pathlib.Path(self.src_path.name)

        self.title = title
        self.datetime = frontmatter.get('date')
        self.date = self.datetime.strftime('%Y-%m-%d')
        self.content = content
        self.toc = toc
        self.tags = frontmatter.get('tags', [])

    def __str__(self) -> str:
        return f'<{self.title}>'


def convert(path: pathlib.Path, src: str) -> Article:
    '''
    convert markdown to html
    '''
    splitted = SPLITTER.split(src, 2)
    if len(splitted) == 3:
        frontmatter = toml.loads(splitted[1])
        body = splitted[2]
    else:
        frontmatter = {}
        body = src

    extras = {
        'fenced-code-blocks': None,
        'header-ids': None,
        'toc': {
            'depth': 4
        },
        'link-patterns': None,
        'tables': None,
        'footnotes': None,
    }
    md = markdown2.Markdown(extras=extras, link_patterns=LINK_PATTERN)
    converted = md.convert(body)

    # tocのtoplevelを削除する
    splitted = converted.toc_html.strip().split('\n')
    toc = '\n'.join([x[2:] for x in splitted[2:-1]])
    m = TITLE_MATCH.match(splitted[1])

    title = ''
    if m:
        title = m.group(1)
    return Article(path, frontmatter, converted, toc, title)


def generate(src: pathlib.Path, dst: pathlib.Path) -> None:
    '''
    ソースフォルダから目標フォルダにファイルを変換しながら移し替える
    '''

    articles: List[Article] = []
    assets: List[pathlib.Path] = []
    css_path = dst / 'default.css'

    used: Set[str] = set()

    def traverse(path: pathlib.Path) -> None:
        if path.name[0] == '.':
            return

        if path.is_dir():
            for child in path.iterdir():
                traverse(child)
        elif path.suffix == '.md':
            article_name = path.stem

            # unique name
            if article_name in used:
                raise RuntimeError('used name: ' + article_name)
            used.add(article_name)

            article = convert(path.relative_to(src), path.read_text('utf-8'))
            articles.append(article)

        else:
            # copy assets
            assets.append(path.relative_to(src))

    print(f'{src} =>\n {dst}')

    traverse(src / 'articles')
    articles = sorted(articles, reverse=True, key=lambda x: x.datetime)

    if dst.exists():
        # clear
        for child in dst.iterdir():
            if child.is_dir():
                shutil.rmtree(child, True)
            else:
                child.unlink()
    else:
        dst.mkdir(0o777, True, True)

    template_dir = src / 'templates'

    # create index
    index_path = dst / 'index.html'
    index_template = jinja2.Template(
        (template_dir / 'index.html').read_text(encoding='utf-8'))
    with index_path.open('w', encoding='utf-8') as f:
        rendered = index_template.render(css_path=css_path.name,
                                         articles=articles)
        f.write(rendered)

    # write articles
    article_template = jinja2.Template(
        (template_dir / 'article.html').read_text(encoding='utf-8'))
    for a in articles:
        write_path = dst / a.path.name
        write_path.parent.mkdir(0o777, True, True)
        print(f'{write_path.relative_to(dst)}: {a}')
        with write_path.open('w', encoding='utf-8') as f:
            rendered = article_template.render(css_path=css_path.name, a=a)
            f.write(rendered)

    # generate css
    with css_path.open('w', encoding='utf-8') as f:
        f.write(HtmlFormatter(style='default').get_style_defs('.codehilite'))
    print(css_path.relative_to(dst))

    # copy assets
    for asset in assets:
        target = dst / asset.name
        print(target.relative_to(dst))
        shutil.copyfile(src / asset, target)


def serve(root: pathlib.Path, port: int) -> None:
    '''
    launch http server with livereloading
    '''
    import bottle
    # Without this line templates won't auto reload because of caching.
    # http://bottlepy.org/docs/dev/tutorial.html#templates
    bottle.debug(True)

    app = bottle.Bottle()

    class MoldStampServer:
        def __init__(self) -> None:
            self.count = 0

    mss = MoldStampServer()

    @app.route('/hello')
    def hello():
        mss.count += 1
        return f'''<!DOCTYPE html><html>
<head></head>
<body>Hello World ! {mss.count}</body></html>'''

    from livereload import Server
    server = Server(app)

    server.watch(f'{root}/**/*.md')

    # server.watch
    server.serve(root='./index.html')


def main():
    parser = argparse.ArgumentParser(description='A static site generator')
    sub = parser.add_subparsers()

    gen = sub.add_parser('gen')
    gen.set_defaults(action='debug')

    gen.add_argument('src',
                     type=str,
                     help='''src root folder.
src/articles is markdown folder.
src/templates is html template folder.
                        ''')
    gen.add_argument('dst',
                     type=str,
                     help='''dst root folder to write html files.
Target folder to write index.html.
First, remove target and recreate that.
Then, generate articles into the folder.
                        ''')

    server = sub.add_parser('server')
    server.set_defaults(action='server')
    server.add_argument('src',
                        type=str,
                        help='''src root folder.
src/articles is markdown folder.
src/templates is html template folder.
                        ''')
    server.add_argument('--port',
                        '-p',
                        type=int,
                        default=8080,
                        help='''livereload server listen port
            ''')

    args = parser.parse_args()

    try:
        action = args.action
    except AttributeError:
        parser.print_help()
        sys.exit()

    if action == 'gen':
        src = pathlib.Path(args.src).resolve()
        dst = pathlib.Path(args.dst).resolve()
        generate(src, dst)

    elif action == 'server':
        src = pathlib.Path(args.src).resolve()
        serve(src, args.port)

    else:
        raise RuntimeError()


if __name__ == '__main__':
    main()
