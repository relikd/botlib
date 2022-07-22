#!/usr/bin/env python3
from sys import stderr
from threading import Timer
from datetime import datetime as date
from typing import List, Any, Optional, Iterable, Callable

CronCallback = Callable[[Any], None]


class RepeatTimer(Timer):
    ''' Repeatedly call function with defined time interval. '''

    def run(self) -> None:
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class Cron:
    ''' Call one or more functions with fixed time interval. '''

    class Job:
        ''' Holds information about the interval and callback method. '''

        def __init__(
            self,
            interval: int,
            callback: CronCallback,
            object: Any = None
        ):
            self.interval = interval
            self.callback = callback
            self.object = object

        def run(self, ts: int = 0) -> None:
            if self.interval > 0 and ts % self.interval == 0:
                self.callback(self.object)

    @staticmethod
    def simple(
        interval: int,
        callback: CronCallback,
        arg: Any = None,
        *, sleep: Iterable[int] = range(1, 8)
    ) -> 'Cron':
        ''' Convenient initializer. Add job and start timer. '''
        cron = Cron(sleep=sleep)
        cron.add_job(interval, callback, arg)
        cron.start()
        return cron

    def __init__(self, *, sleep: Iterable[int] = range(1, 8)):
        self.sleep = sleep
        self._timer = None  # type: Optional[RepeatTimer]
        self._last_t = -1
        self.clear()

    def clear(self) -> None:
        ''' Remove all previously added jobs. '''
        self.jobs = []  # type: List[Cron.Job]

    def add_job(self, interval: int, callback: CronCallback, arg: Any = None) \
            -> Job:
        ''' Create and queue a new job. '''
        assert callback and callable(callback), 'No Cron callback provided.'
        job = Cron.Job(interval, callback, arg)
        self.push(job)
        return job

    def push(self, job: Job) -> None:
        ''' Queue an existing job. '''
        assert isinstance(job, Cron.Job), type(job)
        self.jobs.append(job)

    def pop(self, key: str) -> Job:
        ''' Return and remove job with known key. '''
        return self.jobs.pop(self.jobs.index(self.get(key)))

    def get(self, key: str) -> Job:
        ''' Find job with known key. job.object must be list[0] or str.  '''
        for job in self.jobs:
            x = job.object
            if not x:
                continue
            if (isinstance(x, (list, tuple)) and x[0] == key) or x == key:
                return job
        raise KeyError('Key not found: ' + str(key))

    # CSV import / export

    def load_csv(
        self,
        fname: str,
        callback: CronCallback,
        *, cols: List[Callable[[str], Any]]
    ) -> int:
        '''
        Load comma separated CSV file. Return number of loaded jobs.
        First column must be time interval.
        `cols` is a list of value transformers, e.g., int, str, ...
        '''
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
                    self.add_job(int(time or 0), callback, obj)
        except FileNotFoundError:
            print('File "{}" not found. No jobs loaded.'.format(fname),
                  file=stderr)
        return len(self.jobs)

    def save_csv(self, fname: str, *, cols: List[str]) -> None:
        ''' Persist in-memory jobs to CSV file. `cols` are column headers. '''
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

    def start(self) -> None:
        ''' Start cron timer interval. Check every 15 sec. '''
        if not self._timer:
            self._timer = RepeatTimer(15, self._callback)
            self._timer.start()  # cancel()

    def stop(self) -> None:
        ''' Stop or pause timer. '''
        if self._timer:
            if self._timer.is_alive():
                self._timer.cancel()
            self._timer = None

    def fire(self) -> None:
        ''' Run all jobs immediatelly. '''
        now = date.now()
        self._last_t = now.day * 1440 + now.hour * 60 + now.minute
        for job in self.jobs:
            job.run()

    def _callback(self) -> None:
        ''' [internal] check if interval matches current time and execute. '''
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

    def __str__(self) -> str:
        return '\n'.join('@{}m {}'.format(job.interval, job.object)
                         for job in self.jobs)
