import threading


class JobQueue(object):
    def __init__(self):
        self._queue = []
        self._lock = threading.Lock()
        self.current_job = ''

    def __str__(self):
        if self._queue:
            return ', '.join(self._queue)
        else:
            return 'Empty'

    def queue_list(self):
        if self._queue:
            return self._queue
        else:
            return []

    def add_job(self, job):
        with self._lock:
            if job not in self._queue and job != self.current_job:
                self._queue.append(job)

    def get_job(self):
        with self._lock:
            if self._queue:
                self.current_job = self._queue.pop(0)
                return self.current_job

    def release_current_job(self):
        self.current_job = ''
