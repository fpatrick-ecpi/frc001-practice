"""The practice bot: reads a practice request and answers on the same page.

If something needs fixing, it says what. If the request is right, it puts the
change on its own branch and gives a link to open the pull request. Here you
open the pull request and merge it yourself; in ECPI's repository the bot opens
it and the system owner merges it.
"""
import base64
import json
import os
import re
import urllib.error
import urllib.request

API = 'https://api.github.com/repos/%s/' % os.environ.get('REPO', '')
MARK = '<!-- practice-bot -->'
FILLER = ('utilize', 'leverage', 'seamless', 'basically')
VAGUE = ('some', 'several', 'various', 'stuff', 'things')


def call(method, path, data=None, ok404=False):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(data).encode() if data is not None else None,
                                 headers={'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
                                          'Accept': 'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        if ok404 and e.code == 404:
            return None
        raise


def fields(body):
    """An issue form's answers: '### Label' then the value."""
    out, label = {}, None
    for line in (body or '').splitlines():
        m = re.match(r'^###\s+(.*)$', line)
        if m:
            label = m.group(1).strip()
            out[label] = ''
        elif label:
            out[label] = (out[label] + '\n' + line).strip()
    return {k: ('' if v == '_No response_' else v) for k, v in out.items()}


def problems(f):
    found = []
    week, reading, why = f.get('Week', ''), f.get('Reading', ''), f.get('Why students read it', '')
    if week not in ('1', '2', '3', '4', '5'):
        found.append('Pick a week from 1 to 5.')
    if not reading:
        found.append('Name the reading.')
    if not why:
        found.append('Say why students read it, in one or two sentences.')
    for label, text in (('Reading', reading), ('Why students read it', why)):
        if '—' in text or '–' in text:
            found.append('**%s** has a dash. Use a period, comma or colon instead.' % label)
        for word in FILLER:
            if re.search(r'\b%s\b' % word, text, re.I):
                found.append('**%s** says "%s". Say it plainly.' % (label, word))
        for word in VAGUE:
            if re.search(r'\b%s\b' % word, text, re.I):
                found.append('**%s** says "%s". Name exactly what you mean.' % (label, word))
    if why and len(re.findall(r'[.!?](\s|$)', why)) > 2:
        found.append('**Why students read it** is more than two sentences. Keep it to one or two.')
    return found


def reply(number, text):
    comments = call('GET', 'issues/%d/comments?per_page=100' % number) or []
    mine = [c for c in comments if MARK in c['body']]
    body = MARK + '\n' + text
    if mine:
        call('PATCH', 'issues/comments/%d' % mine[-1]['id'], {'body': body})
    else:
        call('POST', 'issues/%d/comments' % number, {'body': body})


def put_on_branch(number, week, reading, why):
    branch = 'practice-request-%d' % number
    main = call('GET', 'git/ref/heads/main')['object']['sha']
    if call('GET', 'git/ref/heads/' + branch, ok404=True):
        call('PATCH', 'git/refs/heads/' + branch, {'sha': main, 'force': True})   # an edit starts again from main
    else:
        call('POST', 'git/refs', {'ref': 'refs/heads/' + branch, 'sha': main})
    path = 'courses/prc101/week%s-reading.md' % week
    have = call('GET', 'contents/%s?ref=%s' % (path, branch), ok404=True)
    if have:
        text = base64.b64decode(have['content']).decode().rstrip('\n') + '\n- %s\n' % reading
    else:
        text = ('# Week %s reading list\n\nBefore you begin, please make sure you have reviewed the following:\n\n'
                '- %s\n' % (week, reading))
    data = {'message': 'Add %s to the Week %s reading list\n\nFrom practice request #%d: %s' % (reading, week, number, why),
            'content': base64.b64encode(text.encode()).decode(), 'branch': branch}
    if have:
        data['sha'] = have['sha']
    call('PUT', 'contents/' + path, data)
    return branch, path


def main():
    number = int(os.environ['ISSUE'])
    issue = call('GET', 'issues/%d' % number)
    f = fields(issue['body'])
    found = problems(f)
    if found:
        reply(number, "I couldn't do this yet. Please fix:\n\n" + '\n'.join('- ' + p for p in found)
              + '\n\nThen edit your request (the **...** menu on it, then **Edit**), and I try again.')
        return
    branch, path = put_on_branch(number, f['Week'], f['Reading'], f['Why students read it'])
    compare = 'https://github.com/%s/compare/main...%s?expand=1' % (os.environ['REPO'], branch)
    reply(number, 'Done. I added **%s** to `%s` on the branch `%s`.\n\n' % (f['Reading'], path, branch)
          + '1. [Open the pull request](%s), then press **Create pull request**.\n' % compare
          + '2. Wait for the checks. A green check means passed.\n'
          + '3. Press **Merge pull request**, then **Confirm merge**.\n\n'
          + "In ECPI's repository the bot opens the pull request and the system owner merges it. "
          + 'Here you do both, so you see every step.')


if __name__ == '__main__':
    main()
