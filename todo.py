#!/usr/bin/python3
import os
import json
import argparse
from datetime import datetime

STORE_PATH = os.path.join(os.path.expanduser('~'), '.todo')
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
LIST_HELP = """List tasks. Optional sub-argumets: 
n/-n - for n first/last tasks. 
+project/@context - for filtering by context and projects"""
TASK_HELP = """Text of new task. 
Start with n symbols ! or 1 for setting priority n.
Mark any +word for grouping by +projects. 
Mention some @person or @context."""
PRIORITY_HELP = """Set or filter by priority. Exmaple:
-l -p 3+/-2/4 - listings tasks with ptiority more than 3/less than 2/exactly 4.
-p 100500 Call mommy."""


def uuid4():
    """10 ms faster, than import uuid4"""
    b = ''.join('%x' % x for x in os.urandom(16))
    return "%s-%s-%s-%s-%s" % (b[0:8], b[8:12], b[12:16], b[16:20], b[20:])


class Colors(object):
    _color = {
        'reset': '\033[00m',
        'bold': '\033[01m',
        'disable': '\033[02m',
        'underline': '\033[04m',
        'reverse': '\033[07m',
        'strikethrough': '\033[09m',
        'invisible': '\033[08m',

        'black': '\033[30m',
        'red': '\033[31m',
        'green': '\033[32m',
        'orange': '\033[33m',
        'blue': '\033[34m',
        'purple': '\033[35m',
        'cyan': '\033[36m',
        'lightgrey': '\033[37m',
        'darkgrey': '\033[90m',
        'lightred': '\033[91m',
        'lightgreen': '\033[92m',
        'yellow': '\033[93m',
        'lightblue': '\033[94m',
        'pink': '\033[95m',
        'lightcyan': '\033[96m',

        'bg_black': '\033[40m',
        'bg_red': '\033[41m',
        'bg_green': '\033[42m',
        'bg_orange': '\033[43m',
        'bg_blue': '\033[44m',
        'bg_purple': '\033[45m',
        'bg_cyan': '\033[46m',
        'bg_lightgrey': '\033[47m'
    }

    def __getattr__(self, item):
        color = self._color[item]

        def _f(text):
            return color + str(text) + self._color['reset']
        return _f


class MyEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Task):
            return {k: v for k, v in o.__dict__.items() if k!= 'order'}

        elif isinstance(o, datetime):
            return o.strftime(DATE_FORMAT)
        else:
            return json.JSONEncoder.default(self, o)


class Task(object):
    def __init__(self,  **kwargs):
        self.text = kwargs.get('text', '') or ''
        try:
            self.creation_date = datetime.strptime(kwargs.get('creation_date', '1970-01-01T00:00:01'), DATE_FORMAT)
        except ValueError:
            self.creation_date = datetime.utcnow()
        self.done = kwargs.get('done') or False
        self.priority = kwargs.get('priority') or 0
        self.uuid = kwargs.get('uuid') or str(uuid4())
        self.order = None

    def __str__(self):
        s = self.text
        if self.priority:
            s = "(%s) " % self.priority + s
        if self.done:
            s = C.strikethrough(s)
        else:
            if self.priority > 8:
                s = C.red(s)
            elif self.priority > 4:
                s = C.yellow(s)
        return s

    def console_view(self):
        return "%s | " % self.order + str(self)

    @staticmethod
    def from_text(text):
        t = Task()
        if text.startswith('!') or text.startswith('1'):
            import re
            t.priority = len(re.findall('^([1!]+).*', text)[0])
            text = text.lstrip('1! ')
        else:
            t.priority = 0
        t.text = text
        return t


class TasksStore(object):
    def __init__(self, store_dir):
        self.tasks = []
        self._dir = store_dir
        os.makedirs(self._dir, exist_ok=True)
        self.load_current()

    def load_current(self):
        file_path = os.path.join(self._dir, 'current.json')
        self.load_from_file(file_path)

    def load_from_file(self, file_path):
        try:
            raw_tasks = json.load(open(file_path))
            for i, t in enumerate(raw_tasks):
                task = Task(**t)
                task.order = i + 1
                self.tasks.append(task)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            pass

    def save(self):
        file_path = os.path.join(self._dir, 'current.json')
        json.dump(self.tasks, open(file_path, 'w'), cls=MyEncoder, ensure_ascii=False)

    def list(self, count, filter_word=None):
        if filter_word:
            filter_word = filter_word.lower()
            tasks = list(filter(lambda x: filter_word in x.text.lower(), self.tasks))
        else:
            tasks = self.tasks
        if count >= 0:
            return tasks[:count]
        else:
            return tasks[count:]

    def sort(self):
        self.tasks.sort(key=lambda x: (not x.done, x.priority, x.creation_date), reverse=True)
        for i, t in enumerate(self.tasks):
            t.order = i + 1


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-l', '--list', help=LIST_HELP, action='store_true')
    group.add_argument('-d', '--done', help="Mark task as done.\n Example: -d 10", type=int)
    parser.add_argument('-p', '--priority', help=PRIORITY_HELP, default=0)
    parser.add_argument('text', nargs='*', default=[], help=TASK_HELP)
    args = parser.parse_args()

    tasks_store = TasksStore(STORE_PATH)

    if args.list:
        try:
            n = int(args.text[0])
            args.text = args.text[1:]
        except (ValueError, IndexError):
            n = 10
        filter_word = ' '.join(args.text)
        tasks = tasks_store.list(n, filter_word)
        for t in tasks:
            print(t.console_view())
        print("Displayed %s%s/%s tasks" % ("last " if n<0 else "", min(abs(n), len(tasks)), len(tasks_store.tasks)))
    elif args.done:
            tasks_store.tasks[args.done-1].done = True
            tasks_store.sort()
            tasks_store.save()
    elif args.text:
        text = ' '.join(args.text)
        task = Task.from_text(text)
        if args.priority: task.priority = int(args.priority)
        print(str(task))
        tasks_store.tasks.append(task)
        tasks_store.sort()
        tasks_store.save()
        print("Tasks created: %s" % task.order)


if __name__ == '__main__':
    C = Colors()
    main()