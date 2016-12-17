#!/usr/bin/env python3
import argparse
from datetime import datetime
import hashlib
import os
import os.path
import re
import zipfile

from jinja2 import Environment, PackageLoader
env = Environment(loader=PackageLoader('epubconv', 'templates'))


def export_ocf_zip(archive_path, files, opf):
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


def generate_opf(title, navigation_path, fallback_nav_path, chapters, language):
    template = env.get_template('package-document.opf.jinja')
    hash_ = hashlib.md5()
    hash_.update(title.encode('utf-8'))
    data = {
        'modified': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'language': language,
        'title': title,
        'id': hash_.hexdigest(),
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


def generate_paragraphs(text, split_on_tabs=False):
    if split_on_tabs:
        paragraphs = [re.sub(r'\n+', '\n', x) for x in text.split('\n\t')]
    else:
        paragraphs = [x.replace('\n', ' ')
                      for x in text.split('\n\n') if x.strip()]
    return [x.strip() for x in paragraphs]


def generate_chapters(fname, chapter_line_rx, ignore_line_rx,
                      split_on_tabs=False):
    with open(fname) as f:
        raw_lines = f.read().split('\n')
    lines = [line for line in raw_lines
             if re.fullmatch(ignore_line_rx, line) is None]
    chapter_lines = [('', [])]
    for line in lines:
        match = re.fullmatch(chapter_line_rx, line)
        if match:
            if not ''.join(chapter_lines[-1][1]).strip():
                chapter_lines.pop()
            chapter_lines.append((match.group('title'), []))
        else:
            chapter_lines[-1][1].append(line)
    content_template = env.get_template('content-document.xhtml.jinja')
    f = content_template.render
    return [{'title': title,
             'path': 'chapter-{:0>4}.xhtml'.format(n + 1),
             'data': f({'title': title,
                        'paragraphs': generate_paragraphs('\n'.join(lines),
                                                          split_on_tabs)})}
            for n, (title, lines) in enumerate(chapter_lines)]


def create_ebook(input_file, output_file, title, split_on_tabs,
                 chapter_regex, ignore_regex, language):
    chapters = generate_chapters(input_file, chapter_regex, ignore_regex)
    nav_template = env.get_template('nav.xhtml.jinja')
    ncx_template = env.get_template('toc.ncx.jinja')
    nav_chapter_list = [{'path': c['path'], 'title': c['title']} for c in chapters]
    navigation = nav_template.render(chapters=nav_chapter_list)
    fallback_nav = ncx_template.render(title=title, chapters=nav_chapter_list)
    nav_path = 'nav.xhtml'
    ncx_path = 'toc.ncx'
    opf = generate_opf(title, nav_path, ncx_path, chapters, language)
    files = [(nav_path, navigation), (ncx_path, fallback_nav)] +\
            [(c['path'], c['data']) for c in chapters]
    export_ocf_zip(output_file, files, opf)


def run():
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
