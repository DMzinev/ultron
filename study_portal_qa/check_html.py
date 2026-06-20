import os
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.void_elements = ['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']
    def handle_starttag(self, tag, attrs):
        if tag not in self.void_elements:
            self.stack.append((tag, self.getpos()))
    def handle_endtag(self, tag):
        if tag in self.void_elements:
            return
        if not self.stack:
            print(f'Unmatched end tag: {tag} at line {self.getpos()[0]}')
            return
        last_tag, pos = self.stack.pop()
        if last_tag != tag:
            print(f'Mismatched tags: expected {last_tag} (opened at {pos[0]}), got {tag} at {self.getpos()[0]}')
            self.stack.append((last_tag, pos))

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(script_dir, ".."))
html_path = os.path.join(root_dir, "Study_Portal.html")

parser = MyHTMLParser()
parser.feed(open(html_path, encoding='utf-8').read())
if parser.stack:
    print(f'Unclosed tags: {[t[0] for t in parser.stack]}')
else:
    print('HTML structure looks good.')
