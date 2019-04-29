import pathlib
from typing import List, Set, Optional
from .article import Article


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
