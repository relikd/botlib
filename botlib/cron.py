#!/usr/bin/env python3
from sys import stderr
from threading import Timer
from datetime import datetime as date


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class Cron:
    class Job:
        def __init__(self, interval, callback, object=None):
            self.interval = interval
            self.callback = callback
            self.object = object

        def run(self, ts=0):
            if self.interval > 0 and ts % self.interval == 0:
                self.callback(self.object)

    @staticmethod
    def simple(interval: int, callback, arg=None, *, sleep=range(1, 8)):
        cron = Cron(sleep=sleep)
        cron.add_job(interval, callback, arg)
        cron.start()
        return cron

    def __init__(self, *, sleep=range(1, 8)):
        self.sleep = sleep
        self._timer = None
        self._last_t = -1
        self.clear()

    def clear(self):
        self.jobs = []

    def add_job(self, interval: int, callback, arg=None):
        job = Cron.Job(interval, callback, arg)
        self.push(job)
        return job

    def push(self, job):
        assert isinstance(job, Cron.Job), type(job)
        self.jobs.append(job)

    def pop(self, key):
        return self.jobs.pop(self.jobs.index(self.get(key)))

    def get(self, key):
        for x in self.jobs:
            obj = x.object
            if not obj:
                continue
            if (isinstance(obj, list) and obj[0] == key) or obj == key:
                return x
        raise KeyError('Key not found: ' + str(key))

    # CSV import / export

    def load_csv(self, fname: str, callback, *, cols: []):
        self.clear()
        try:
            with open(fname) as fp:
                for line in fp.readlines():
                    if line.startswith('#'):
                        continue
                    time, *obj = [x.strip() or None for x in line.split(',')]
                    obj = [fn(o) if o else None for o, fn in zip(obj, cols)]
                    if len(obj) < len(cols):
                        obj += [None] * (len(cols) - len(obj))
                    self.add_job(int(time), callback, obj)
        except FileNotFoundError:
            print('File "{}" not found. No jobs loaded.'.format(fname),
                  file=stderr)
        return len(self.jobs)

    def save_csv(self, fname: str, *, cols: [str]):
        with open(fname, 'w') as fp:
            fp.write(' , '.join(['# interval'] + cols) + '\n')
            for job in self.jobs:
                if not job.object:
                    continue
                fp.write(str(job.interval))
                if isinstance(job.object, list):
                    for x in job.object:
                        fp.write(',' + ('' if x is None else str(x)))
                else:
                    fp.write(',' + str(job.object))
                fp.write('\n')

    # Handle repeat timer

    def start(self):
        if not self._timer:
            self._timer = RepeatTimer(15, self._callback)
            self._timer.start()  # cancel()

    def stop(self):
        if self._timer:
            if self._timer.is_alive():
                self._timer.cancel()
            self._timer = None

    def fire(self):
        now = date.now()
        self._last_t = now.day * 1440 + now.hour * 60 + now.minute
        for job in self.jobs:
            job.run()

    def _callback(self):
        now = date.now()
        if now.hour in self.sleep:
            return
        # Timer called multiple times per minute. Assures fn is called once.
        ts = now.day * 1440 + now.hour * 60 + now.minute
        if self._last_t == ts:
            return
        self._last_t = ts
        for job in self.jobs:
            job.run(ts)

    def __str__(self):
        return '\n'.join('@{}m {}'.format(job.interval, job.object)
                         for job in self.jobs)
