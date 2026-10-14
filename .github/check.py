"""The practice repository's automatic checks.

    python3 .github/check.py course-content   every course folder has a README.md
    python3 .github/check.py house-style      no em or en dashes and no filler words in Markdown
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILLER = ('utilize', 'leverage', 'seamless')


def problem(path, line, text):
    print('::error file=%s,line=%d::%s' % (path, line, text))


def course_content():
    ok = True
    for folder in sorted((ROOT / 'courses').iterdir()):
        if folder.is_dir() and not (folder / 'README.md').is_file():
            problem('courses/%s' % folder.name, 1, 'Every course folder needs a README.md.')
            ok = False
    return ok


def house_style():
    ok = True
    for f in sorted(ROOT.rglob('*.md')):
        rel = f.relative_to(ROOT).as_posix()
        for n, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            if '—' in line or '–' in line:
                problem(rel, n, 'Use a period, comma or colon instead of a dash.')
                ok = False
            for word in FILLER:
                if re.search(r'\b%s' % word, line, re.I):
                    problem(rel, n, 'Say it plainly instead of "%s".' % word)
                    ok = False
    return ok


CHECKS = {'course-content': course_content, 'house-style': house_style}

if __name__ == '__main__':
    passed = CHECKS[sys.argv[1]]()
    print('passed' if passed else 'failed')
    sys.exit(0 if passed else 1)
