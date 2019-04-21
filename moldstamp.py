#!/usr/bin/env python

import argparse
import os
import re
import toml
import pathlib
import shutil
import markdown2
from typing import List, Set, NamedTuple, MutableMapping, Any
import jinja2

VERSION = [0, 1]

HERE = pathlib.Path(__file__).resolve().parent

SPLITTER = re.compile(r'^\+\+\+$', re.M)
TITLE_MATCH = re.compile(r'^\s+<li><a href="[^"]*">([^<]*)')
LINK_PATTERN = [(re.compile(
    r'((([A-Za-z]{3,9}:(?:\/\/)?)(?:[\-;:&=\+\$,\w]+@)?[A-Za-z0-9\.\-]+(:[0-9]+)?|(?:www\.|[\-;:&=\+\$,\w]+@)[A-Za-z0-9\.\-]+)((?:\/[\+~%\/\.\w\-_]*)?\??(?:[\-\+=&;%@\.\w_]*)#?(?:[\.\!\/\\\w]*))?)'
), r'\1')]


class Article:
    def __init__(self, frontmatter, content, toc, title: str) -> None:
        self.title = title
        self.datetime = frontmatter.get('date')
        self.date = self.datetime.strftime('%Y-%m-%d')
        self.content = content
        self.toc = toc
        self.tags = frontmatter.get('tags', [])

        self.name = ''
        self.folder = None
        self.path = None

    def set_folder_name(self, folder, name):
        self.name = name
        self.folder = folder
        self.path = self.folder / f'{self.name}.html'

    def __str__(self) -> str:
        return f'<{self.title}>'


class Converted(NamedTuple):
    frontmatter: MutableMapping[str, Any]
    converted: str
    toc: str
    title: str


def convert(src: str) -> Converted:
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
    return Converted(frontmatter, converted, toc, title)


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

            article = convert(path.read_text('utf-8'))
            article.set_folder_name(path.relative_to(src).parent, article_name)
            articles.append(article)

        else:
            # copy assets
            assets.append(path.relative_to(src))

    print(f'{src} =>\n {dst}')

    traverse(src / 'articles')
    articles = sorted(articles, reverse=True, key=lambda x: x.datetime)

    # clear
    if dst.exists():
        shutil.rmtree(dst, True)
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
        write_path = dst / a.path
        write_path.parent.mkdir(0o777, True, True)
        print(a)
        with write_path.open('w', encoding='utf-8') as f:
            rendered = article_template.render(css_path=css_path.name, a=a)
            f.write(rendered)

    # generate css
    os.system(f'pygmentize -S default -f html -a .codehilite > {css_path}')

    # copy assets
    for a in assets:
        print(a)
        shutil.copyfile(src / a, dst / a)


def main():
    parser = argparse.ArgumentParser(description='A static site generator')

    parser.add_argument('src',
                        type=str,
                        help='''src root folder.
src/articles is markdown folder.
src/templates is html template folder.
                        ''')
    parser.add_argument('dst',
                        type=str,
                        help='''dst root folder to write html files.
Target folder to write index.html.
First, remove target and recreate that.
Then, generate articles into the folder.
                        ''')

    parser.add_argument('--verbose', '-v', action='store_true')

    args = parser.parse_args()
    src = pathlib.Path(args.src).resolve()
    dst = pathlib.Path(args.dst).resolve()

    generate(src, dst)


if __name__ == '__main__':
    main()
