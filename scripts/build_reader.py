#!/usr/bin/env python3
"""Build a self-contained bilingual reader from reviewed, aligned JSON."""
import argparse
import base64
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ASSETS = Path(__file__).resolve().parent.parent / 'assets'
TAGS = set('p br em strong b i sup sub span a cite code pre ul ol li blockquote math mrow mi mn mo mtext mspace mfrac msqrt mroot msup msub msubsup mover munder munderover mfenced mtable mtr mtd mstyle mpadded mphantom menclose semantics'.split())
VOID = {'br'}
SKIP = {'math', 'cite', 'a', 'code', 'pre'}
MATH_ATTRS = set('display mathvariant stretchy fence separator accent accentunder columnalign rowalign columnspacing rowspacing linethickness lspace rspace width height depth notation open close separators'.split())


def esc(value):
    return html.escape(str(value), quote=True)


def safe_url(value):
    value = str(value).strip()
    parts = urlsplit(value)
    if parts.scheme not in {'http', 'https'} or not parts.netloc:
        raise ValueError('Links must be absolute HTTP(S) URLs')
    return value


class RichText(HTMLParser):
    """Strict rich-text subset; unsupported markup fails, never disappears."""
    def __init__(self, glossary=(), cap=12):
        super().__init__(convert_charrefs=True)
        self.out, self.stack, self.seen = [], [], set()
        self.cap = cap
        forms = {}
        for index, word in glossary:
            for form in word['forms']:
                key = form.lower()
                if key in forms and forms[key] != index:
                    raise ValueError('Ambiguous glossary alias; use block glossary_ids: ' + form)
                forms[key] = index
        self.forms = forms
        choices = sorted(forms, key=len, reverse=True)
        self.pattern = re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(x) for x in choices) + r')(?!\w)', re.I) if choices else None

    def handle_starttag(self, tag, attrs):
        if tag not in TAGS:
            raise ValueError('Unsupported rich-text tag: ' + tag)
        clean = []
        for key, value in attrs:
            if key == 'href' and tag == 'a':
                clean.append('href="' + esc(safe_url(value)) + '"')
            elif key in MATH_ATTRS and (tag == 'math' or 'math' in self.stack):
                clean.append(key + '="' + esc(value) + '"')
            elif key == 'xmlns' and tag == 'math' and value == 'http://www.w3.org/1998/Math/MathML':
                clean.append('xmlns="' + value + '"')
            else:
                raise ValueError('Unsupported rich-text attribute: ' + key)
        self.out.append('<' + tag + (' ' + ' '.join(clean) if clean else '') + '>')
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            raise ValueError('Unbalanced rich text near ' + tag)
        self.stack.pop()
        self.out.append('</' + tag + '>')

    def handle_data(self, data):
        if not self.pattern or any(t in SKIP for t in self.stack):
            self.out.append(esc(data))
            return
        last = 0
        for match in self.pattern.finditer(data):
            index = self.forms[match.group().lower()]
            self.out.append(esc(data[last:match.start()]))
            term = esc(match.group())
            if index not in self.seen and len(self.seen) < self.cap:
                term = f'<button class="vocab" type="button" data-word="{index}" aria-expanded="false" aria-controls="word-popup" aria-label="查看释义：{term}">{term}</button>'
                self.seen.add(index)
            self.out.append(term)
            last = match.end()
        self.out.append(esc(data[last:]))

    def handle_decl(self, decl):
        raise ValueError('Declarations are not supported in rich text')

    def handle_comment(self, data):
        raise ValueError('Comments are not supported in rich text')

    def handle_pi(self, data):
        raise ValueError('Processing instructions are not supported')

    def result(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Text must be a nonempty string')
        self.feed(value)
        self.close()
        if self.stack:
            raise ValueError('Unclosed rich-text tag: ' + self.stack[-1])
        return ''.join(self.out)


def rich(value, glossary=(), cap=12):
    return RichText(glossary, cap).result(value)


def validate_glossary(items):
    result, ids = [], set()
    for item in items:
        word = dict(item)
        for field in ('id', 'term', 'meaning', 'detail'):
            if not isinstance(word.get(field), str) or not word[field].strip():
                raise ValueError('Glossary requires nonempty ' + field)
        if word['id'] in ids:
            raise ValueError('Duplicate glossary ID')
        ids.add(word['id'])
        aliases = word.get('forms', [])
        if not isinstance(aliases, list) or any(not isinstance(x, str) or not x.strip() for x in aliases):
            raise ValueError('Glossary forms must be nonempty strings')
        word['forms'] = list(dict.fromkeys([word['term'], *aliases]))
        result.append(word)
    return result


def image_data(path, base):
    target = (base / path).resolve()
    if not target.is_relative_to(base.resolve()):
        raise ValueError('Image must be inside the content JSON directory')
    data = target.read_bytes()
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        mime = 'image/png'
    elif data.startswith(b'\xff\xd8\xff'):
        mime = 'image/jpeg'
    elif data.startswith((b'GIF87a', b'GIF89a')):
        mime = 'image/gif'
    elif data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        mime = 'image/webp'
    else:
        raise ValueError('Image must be a PNG, JPEG, GIF or WebP raster')
    return 'data:' + mime + ';base64,' + base64.b64encode(data).decode('ascii')


def build(data, base):
    if data.get('schema_version') != 1:
        raise ValueError('Expected schema_version 1')
    words = validate_glossary(data.get('glossary', []))
    by_id = {w['id']: (i, w) for i, w in enumerate(words)}
    cap = data.get('annotation_limit', 12)
    if not isinstance(cap, int) or not 0 <= cap <= 100:
        raise ValueError('annotation_limit must be between 0 and 100')
    ids, body, toc = set(), [], []
    counts = {k: 0 for k in ('pair', 'note', 'equation', 'figure', 'table')}

    def take_id(value):
        if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_-]*', value) or value in ids:
            raise ValueError('IDs must be unique and start with a letter')
        ids.add(value)
        return 'content-' + value

    def pair(block):
        selected = [by_id[x] for x in block['glossary_ids']] if 'glossary_ids' in block else list(enumerate(words))
        en = rich(block['en'], selected, cap)
        zh = rich(block['zh'])
        locator = '<div class="source-locator">' + esc(block['source_locator']) + '</div>' if block.get('source_locator') else ''
        return locator + '<div class="en-block" lang="en"><div class="lang-label">ENGLISH</div>' + en + '</div><div class="zh-block" lang="zh-CN"><div class="lang-label">中文</div>' + zh + '</div>'

    sections = data['sections']
    if not isinstance(sections, list) or not sections:
        raise ValueError('At least one section is required')
    for section in sections:
        sid = take_id(section['id'])
        title = '<span class="heading-en">' + esc(section['title_en']) + '</span><span class="zh-block">' + esc(section['title_zh']) + '</span>'
        toc.append(f'<li><a href="#{sid}">{esc(section["title_en"])} · {esc(section["title_zh"])}</a></li>')
        body.append(f'<section id="{sid}"><h2>{title}</h2>')
        for block in section['blocks']:
            bid = take_id(block['id'])
            kind = block.get('kind', 'pair')
            if kind not in counts:
                raise ValueError('Unknown block kind: ' + kind)
            counts[kind] += 1
            if kind in {'pair', 'note'}:
                label = '<div class="note-label">译者注 / Translator note</div>' if kind == 'note' else ''
                body.append(f'<div id="{bid}" class="reading-pair {kind}">' + label + pair(block) + '</div>')
            elif kind == 'equation':
                math = block['mathml'].strip()
                if not re.match(r'<math(?:\s|>)', math) or not math.endswith('</math>'):
                    raise ValueError('Equation requires a MathML math root')
                body.append(f'<div id="{bid}" class="equation">' + rich(math) + '<span class="eq-number">' + esc(block.get('number', '')) + '</span></div>')
            elif kind == 'figure':
                if not block.get('alt'):
                    raise ValueError('Figure requires alt text')
                src = image_data(block['file'], base)
                body.append(f'<figure id="{bid}"><img src="{src}" alt="{esc(block["alt"])}"><figcaption class="reading-pair">' + pair(block) + '</figcaption></figure>')
            elif kind == 'table':
                headers, rows = block['headers'], block['rows']
                if not headers or any(not isinstance(h, list) or len(h) != 2 for h in headers):
                    raise ValueError('Table headers require [English, Chinese] pairs')
                if any(len(row) != len(headers) for row in rows):
                    raise ValueError('Table rows must match header count')
                th = ''.join('<th scope="col"><span class="heading-en">' + esc(h[0]) + '</span><span class="zh-block">' + esc(h[1]) + '</span></th>' for h in headers)
                tr = ''.join('<tr>' + ''.join('<td>' + esc(cell) + '</td>' for cell in row) + '</tr>' for row in rows)
                body.append(f'<figure id="{bid}"><div class="table-scroll" tabindex="0" role="region" aria-label="数据表"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div><figcaption class="reading-pair">' + pair(block) + '</figcaption></figure>')
        body.append('</section>')
    source = data['source']
    metadata = ' · '.join(esc(source[x]) for x in ('authors', 'identifier', 'version') if source.get(x))
    if source.get('url'):
        metadata += ' · <a href="' + esc(safe_url(source['url'])) + '">原文 / Source</a>'
    coverage = esc(source['coverage'])
    title_en, title_zh = esc(data['title_en']), esc(data['title_zh'])
    css = (ASSETS / 'base.css').read_text(encoding='utf-8') + '\n' + (ASSETS / 'reader.css').read_text(encoding='utf-8')
    script = (ASSETS / 'reader.js').read_text(encoding='utf-8')
    # Embedded JSON must not terminate the script element.
    payload = json.dumps(words, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    page = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>{title_en} | 双语精读</title><style>{css}</style></head>
<body><main><header><p class="eyebrow">BILINGUAL PAPER READER</p><h1><span class="paper-title-en en-block">{title_en}</span><span class="paper-title-zh zh-block">{title_zh}</span></h1><p class="metadata">{metadata}</p><p class="coverage">阅读范围 / Coverage: {coverage}</p></header>
{(ASSETS / 'toolbar.html').read_text(encoding='utf-8')}
<nav aria-label="章节目录"><details><summary>目录 / Contents</summary><ul>{''.join(toc)}</ul></details></nav>
{''.join(body)}
<footer>英文原文 → 中文翻译 → 语境词义 · 本地离线阅读</footer></main>
{(ASSETS / 'dialogs.html').read_text(encoding='utf-8')}
<script type="application/json" id="glossary-data">{payload}</script><script>{script}</script></body></html>'''
    return page, counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('content', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.content.resolve() == args.output.resolve():
        parser.error('Output must differ from input')
    try:
        data = json.loads(args.content.read_text(encoding='utf-8'))
        page, counts = build(data, args.content.parent)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(page, encoding='utf-8')
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, 'Build failed: ' + str(error) + '\n')
    print(json.dumps({'output': str(args.output), 'blocks': counts, 'glossary_entries': len(data.get('glossary', []))}, ensure_ascii=False))


if __name__ == '__main__':
    main()
