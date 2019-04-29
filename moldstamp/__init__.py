#!/usr/bin/env python

import sys
import argparse
import pathlib
import shutil
from typing import List, Set, Optional
import jinja2
from pygments.formatters import HtmlFormatter
from .article import Article

VERSION = [0, 1]

HERE = pathlib.Path(__file__).resolve().parent


class AssetFiles:
    def __init__(self) -> None:
        self.used: Set[str] = set()
        self.articles: List[Article] = []
        self.assets: List[pathlib.Path] = []

    def traverse(self, path: pathlib.Path) -> None:
        if path.name[0] == '.':
            return

        if path.is_dir():
            for child in path.iterdir():
                self.traverse(child)
        elif path.suffix == '.md':
            article_name = path.stem

            # unique name
            if article_name in self.used:
                raise RuntimeError('used name: ' + article_name)
            self.used.add(article_name)

            self.articles.append(Article(path))

        else:
            # copy assets
            self.assets.append(path)

    def load(self, convert_md=True) -> None:
        for a in self.articles:
            try:
                a.load(convert_md)
            except AttributeError as e:
                print(e)

    def sort(self) -> None:
        self.articles = sorted(self.articles,
                               reverse=True,
                               key=lambda x: x.datetime)

    def get_article(self, name: str) -> Optional[Article]:
        for a in self.articles:
            if a.name == name:
                return a


def generate(src: pathlib.Path, dst: pathlib.Path) -> None:
    '''
    ソースフォルダから目標フォルダにファイルを変換しながら移し替える
    '''

    css_path = dst / 'default.css'

    print(f'{src} =>\n {dst}')

    asset_files = AssetFiles()
    asset_files.traverse(src / 'articles')
    asset_files.load()
    asset_files.sort()

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
                                         articles=asset_files.articles)
        f.write(rendered)

    # write articles
    article_template = jinja2.Template(
        (template_dir / 'article.html').read_text(encoding='utf-8'))
    for a in asset_files.articles:
        write_path = dst / f'{a.name}.html'
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
    for asset in asset_files.assets:
        target = dst / asset.name
        print(target.relative_to(dst))
        shutil.copyfile(src / asset, target)


def serve(src: pathlib.Path, port: int) -> None:
    '''
    launch http server with livereloading
    '''
    import bottle
    # Without this line templates won't auto reload because of caching.
    # http://bottlepy.org/docs/dev/tutorial.html#templates
    bottle.debug(True)

    app = bottle.Bottle()

    template_dir = src / 'templates'
    css_path = 'default.css'

    @app.route('/index.html')
    def index():
        asset_files = AssetFiles()
        asset_files.traverse(src / 'articles')
        asset_files.load(convert_md=False)
        asset_files.sort()
        index_template = jinja2.Template(
            (template_dir / 'index.html').read_text(encoding='utf-8'))
        return index_template.render(css_path=css_path,
                                     articles=asset_files.articles)

    @app.route('/<article>')
    def article(article):
        asset_files = AssetFiles()
        asset_files.traverse(src / 'articles')

        name = pathlib.Path(article).stem

        a = asset_files.get_article(name)
        if not a:
            return f'{name} not found'

        try:
            a.load()

            article_template = jinja2.Template(
                (template_dir / 'article.html').read_text(encoding='utf-8'))

            return article_template.render(css_path=css_path, a=a)
        except Exception as e:
            return f'{article} => {e}'

    from livereload import Server
    server = Server(app)

    # server.watch
    def watch(target: src):
        print(f'watch: {target}')
        server.watch(target)

    watch(f'{src}/')

    # start
    server.serve(root='./index.html')


def main():
    parser = argparse.ArgumentParser(description='A static site generator')
    sub = parser.add_subparsers()

    gen = sub.add_parser('gen')
    gen.set_defaults(action='gen')

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
