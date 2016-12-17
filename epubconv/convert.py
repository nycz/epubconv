#!/usr/bin/env python3
import argparse
from datetime import datetime
from typing import Dict, List, Tuple
import hashlib
import os
import os.path
import re
import zipfile

from jinja2 import Environment, PackageLoader, StrictUndefined
env = Environment(loader=PackageLoader('epubconv', 'templates'),
                  undefined=StrictUndefined)

ChaptersAlias = List[Dict[str, str]]
FilesAlias = List[Tuple[str, str]]


def export_ocf_zip(archive_path: str, files: FilesAlias, opf: str) -> None:
    """Create an epub archive with the provided data."""
    opf_path = 'content.opf'
    container_template = env.get_template('container.xml.jinja')
    container = container_template.render({'opf_path': opf_path})
    with zipfile.ZipFile(archive_path, 'w', allowZip64=False) as f:
        f.writestr('mimetype', 'application/epub+zip')
        f.writestr(os.path.join('META-INF', 'container.xml'), container)
        f.writestr(opf_path, opf)
        for path, data in files:
            f.writestr(path, data)


def generate_opf(title: str, uid: str,
                 navigation_path: str, fallback_nav_path: str,
                 chapters: ChaptersAlias, language: str) -> str:
    template = env.get_template('package-document.opf.jinja')
    data = {
        'modified': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'language': language,
        'title': title,
        'uid': uid,
        'navigation_path': navigation_path,
        'fallback_nav_path': fallback_nav_path,
        'files': [{'id': os.path.splitext(c['path'])[0],
                   'path': c['path']}
                  for c in chapters],
        # TODO: this
        # 'stylesheet_path': 'arst',
        # 'creator': 'huhu',
        # 'description': 'lololo',
        # 'cover': {'path': 'bloop.jpg', 'media_type': 'image/jpeg'}
    }
    return template.render(data)


def generate_paragraphs(text: str, split_on_tabs: bool) -> List[str]:
    if split_on_tabs:
        paragraphs = [re.sub(r'\n+', '\n', x)
                      for x in re.split(r'\n(?:\t| {2,})', text)]
    else:
        paragraphs = [x.replace('\n', ' ')
                      for x in text.split('\n\n') if x.strip()]
    return [x.strip() for x in paragraphs]


def generate_chapters(fname: str, chapter_line_rx: str, ignore_line_rx: str,
                      split_on_tabs: bool) -> ChaptersAlias:
    with open(fname) as f:
        raw_lines = f.read().split('\n')  # type: List[str]
    if ignore_line_rx:
        lines = [line for line in raw_lines
                 if re.fullmatch(ignore_line_rx, line) is None]
    else:
        lines = raw_lines
    chapter_lines = [('', [])]  # type: List[Tuple[str, List[str]]]
    for line in lines:
        match = re.fullmatch(chapter_line_rx, line) if chapter_line_rx else None
        if match is not None:
            if not ''.join(chapter_lines[-1][1]).strip():
                chapter_lines.pop()
            chapter_lines.append((match.group('title'), []))
        else:
            chapter_lines[-1][1].append(line)
    content_template = env.get_template('content-document.xhtml.jinja')
    r = content_template.render
    return [{'title': title,
             'path': 'chapter-{:0>4}.xhtml'.format(n + 1),
             'data': r({'title': title,
                        'paragraphs': generate_paragraphs('\n'.join(lines),
                                                          split_on_tabs)})}
            for n, (title, lines) in enumerate(chapter_lines)]


def generate_navigation(uid: str, title: str, chapters: ChaptersAlias
                        ) -> Tuple[str, str, FilesAlias]:
    if len(chapters) == 1:
        nav_chapter_list = [{'path': chapters[0]['path'], 'title': title}]
    else:
        nav_chapter_list = [{'path': c['path'], 'title': c['title']}
                            for c in chapters]
    nav_template = env.get_template('nav.xhtml.jinja')
    ncx_template = env.get_template('toc.ncx.jinja')
    nav_path = 'nav.xhtml'
    ncx_path = 'toc.ncx'
    navigation = nav_template.render(title=title, chapters=nav_chapter_list)
    fallback_nav = ncx_template.render(uid=uid, title=title,
                                       chapters=nav_chapter_list)
    return nav_path, ncx_path, [(nav_path, navigation), (ncx_path, fallback_nav)]


def create_ebook(input_file: str, output_file: str,
                 title: str, split_on_tabs: bool,
                 chapter_regex: str, ignore_regex: str, language: str) -> None:
    hash_ = hashlib.md5()
    hash_.update(title.encode('utf-8'))
    uid = hash_.hexdigest()
    chapters = generate_chapters(input_file, chapter_regex, ignore_regex, split_on_tabs)
    nav_path, ncx_path, nav_files = generate_navigation(uid, title, chapters)
    opf = generate_opf(title, uid, nav_path, ncx_path, chapters, language)
    files = nav_files + [(c['path'], c['data']) for c in chapters]
    export_ocf_zip(output_file, files, opf)


def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file')
    parser.add_argument('title', help='Title of the book.')
    parser.add_argument('language', help='The language of the book, for '
                                         'example en-US or sv-SE.')
    parser.add_argument('output_file')
    parser.add_argument('-t', '--split-on-tabs', action='store_true',
                        help='Use indented lines as the start of paragraphs '
                             'instead of a blank line.')
    parser.add_argument('-c', '--chapter-regex',
                        help='A regex matching chapter heading lines. Use '
                             'the regex group "title" to capture the name of '
                             'the chapter.')
    parser.add_argument('-i', '--ignore-regex',
                        help='A regex matching lines to be ignored and not '
                             'included in the epub.')
    args = parser.parse_args()
    create_ebook(args.input_file, args.output_file, args.title,
                 args.split_on_tabs, args.chapter_regex, args.ignore_regex,
                 args.language)
