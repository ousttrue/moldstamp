import re
import pathlib
import datetime
import toml
import markdown2

SPLITTER = re.compile(r'^\+\+\+$', re.M)
MD_TITLE_MATCH = re.compile(r'^\s*#\s*(.*?)\s*\n')
LINK_PATTERN = [(
    re.compile(
        r'((([A-Za-z]{3,9}:(?:\/\/)?)(?:[\-;:&=\+\$,\w]+@)?[A-Za-z0-9\.\-]+(:[0-9]+)?|(?:www\.|[\-;:&=\+\$,\w]+@)[A-Za-z0-9\.\-]+)((?:\/[\+~%\/\.\w\-_]*)?\??(?:[\-\+=&;%@\.\w_]*)#?(?:[\.\!\/\\\w]*))?)'  # noqa: E501
    ),
    r'\1')]
TITLE_MATCH = re.compile(r'^\s+<li><a href="[^"]*">([^<]*)')


class Article:
    def __init__(self, md_path: pathlib.Path) -> None:
        self.title = None
        self.md_path = md_path  # relative path from source root
        self.name = md_path.stem
        # content
        self.datetime = None
        self.date = None
        self.content = ''
        self.tags = []

    def load(self, convert_md=True) -> None:
        '''
        convert markdown to html
        '''
        src = self.md_path.read_text(encoding='utf-8')
        splitted = SPLITTER.split(src, 2)
        if len(splitted) == 3:
            frontmatter = toml.loads(splitted[1])
            body = splitted[2]
        else:
            frontmatter = {}
            body = src
        self.datetime = frontmatter.get('date')
        if not self.datetime:
            self.datetime = datetime.datetime(2000,
                                              1,
                                              1,
                                              tzinfo=datetime.timezone.utc)
        self.date = self.datetime.strftime('%Y-%m-%d')
        self.tags = frontmatter.get('tags', [])

        self.title = ''
        m = MD_TITLE_MATCH.match(body)
        if m:
            self.title = m.group(1).strip()

        if convert_md:
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
            self.content = md.convert(body)

            # tocのtoplevelを削除する
            splitted = self.content.toc_html.strip().split('\n')
            self.toc = '\n'.join([x[2:] for x in splitted[2:-1]])

            m = TITLE_MATCH.match(splitted[1])

            if m:
                self.title = m.group(1)

    def __str__(self) -> str:
        return f'<{self.title}>'
