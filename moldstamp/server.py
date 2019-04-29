import pathlib
import jinja2
from .assetfiles import AssetFiles


def setup_parser(parser):
    parser.add_argument('src',
                        type=str,
                        help='''src root folder.
src/articles is markdown folder.
src/templates is html template folder.
                        ''')
    parser.add_argument('--port',
                        '-p',
                        type=int,
                        default=8080,
                        help='''livereload server listen port
            ''')


def execute(args) -> None:
    '''
    launch http server with livereloading
    '''
    # port = args.port
    src = pathlib.Path(args.src).resolve()

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
