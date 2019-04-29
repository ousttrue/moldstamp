import pathlib
import shutil
import jinja2
from pygments.formatters import HtmlFormatter
from .assetfiles import AssetFiles


def setup_parser(parser):
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


def execute(src: pathlib.Path, dst: pathlib.Path) -> None:
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
