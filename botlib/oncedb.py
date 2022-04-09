#!/usr/bin/env python3
'''
Usage: Load existing `OnceDB()` and `put(cohort, uid, obj)` new entries.
       The db ensures that (cohort, uid) pairs are unique. You can add as
       many times as you like. Use an (reversed) iterator to enumerate
       outstanding entries `for rowid, cohort, uid, obj in reversed(db)`.
       Call `mark_done(rowid)` to not process an item again.

       Once in a while call `cleanup()` to remove old entries.
'''
import sqlite3
from typing import Tuple, Any, Callable, Iterator

DBEntry = Tuple[int, str, str, Any]


class OnceDB:
    def __init__(self, db_path: str) -> None:
        self._db = sqlite3.connect(db_path)
        self._db.execute('''
            CREATE TABLE IF NOT EXISTS queue(
                ts DATE DEFAULT (strftime('%s', 'now')),
                cohort TEXT NOT NULL,
                uid TEXT NOT NULL,
                obj BLOB,  -- NULL signals a done mark. OR: introduce new var
                PRIMARY KEY (cohort, uid)  -- SQLite will auto-create index
            );
        ''')

    def __del__(self) -> None:
        self._db.close()

    def cleanup(self, limit: int = 200) -> None:
        ''' Delete oldest (cohort) entries if more than limit exist. '''
        self._db.execute('''
            WITH _tmp AS (
                SELECT ROWID, row_number() OVER (
                    PARTITION BY cohort ORDER by ROWID DESC) AS c
                FROM queue
                WHERE obj IS NULL
            )
            DELETE FROM queue
            WHERE ROWID in (SELECT ROWID from _tmp WHERE c > ?);
        ''', (limit,))
        self._db.commit()

    def put(self, cohort: str, uid: str, obj: str) -> bool:
        ''' Silently ignore if a duplicate (cohort, uid) is added. '''
        try:
            self._db.execute('''
                INSERT INTO queue (cohort, uid, obj) VALUES (?, ?, ?);
                ''', (cohort, uid, obj))
            self._db.commit()
            return True
        except sqlite3.IntegrityError:
            # entry (cohort, uid) already exists
            return False

    def contains(self, cohort: str, uid: str) -> bool:
        ''' Test if cohort + uid pair exists in database. '''
        cur = self._db.cursor()
        cur.execute('''
            SELECT 1 FROM queue WHERE cohort IS ? AND uid is ? LIMIT 1;
            ''', (cohort, uid))
        flag = cur.fetchone() is not None
        cur.close()
        return flag

    def mark_done(self, rowid: int) -> None:
        ''' Mark (ROWID) as done. Entry remains in cache until cleanup(). '''
        if not isinstance(rowid, int):
            raise AttributeError('Not of type ROWID: {}'.format(rowid))
        self._db.execute('UPDATE queue SET obj = NULL WHERE ROWID = ?;',
                         (rowid, ))
        self._db.commit()

    def mark_all_done(self) -> None:
        ''' Mark all entries done. Entry remains in cache until cleanup(). '''
        self._db.execute('UPDATE queue SET obj = NULL;')
        self._db.commit()

    def foreach(
        self,
        callback: Callable[[str, str, Any], bool],
        *, reverse: bool = False
    ) -> bool:
        '''
        Exec for all until callback evaluates to false (or end of list).
        Automatically marks entries as done (only on success).
        '''
        for rowid, *elem in reversed(self) if reverse else self:
            if callback(*elem):
                self.mark_done(rowid)
            else:
                return False
        return True

    def __iter__(self) -> Iterator[DBEntry]:
        return self.iter()

    def __reversed__(self) -> Iterator[DBEntry]:
        return self.iter(desc=True)

    def iter(self, *, desc: bool = False) -> Iterator[DBEntry]:
        ''' Perform query on all un-marked / not-done entries. '''
        cur = self._db.cursor()
        cur.execute('''
            SELECT ROWID, cohort, uid, obj FROM queue
            WHERE obj IS NOT NULL
            ORDER BY ROWID {};
        '''.format('DESC' if desc else 'ASC'))
        yield from cur.fetchall()
        cur.close()
