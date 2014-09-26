import time
import json
import imp
import threading
import atexit

class TaskRunner:
    def __init__(self, sleep_interval=1):
        self.sleep_interval = sleep_interval
        self.tasks = []
        self.running = False
        self.paused = False
    
    def run(self):
        self.running = True
        while self.running:
            while self.running and not self.paused and self.run_pending_tasks():
                # keep running tasks until none are run. Stop looping if paused
                # or trying to quit.
                pass
            time.sleep(self.sleep_interval)

    def stop(self):
        self.running = False
        
    def run_threaded(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        atexit.register(self.stop_threaded)
        self.thread.start()

    def stop_threaded(self):
        if self.running:
            self.stop()
            self.thread.join()

    def pause_all(self):
        self.paused = True
        for task in self.tasks:
            task.paused = True
    
    def resume_all(self):
        for task in self.tasks:
            task.paused = False
        self.paused = False
    
    def stop_all(self):
        self.running = False
        for task in self.tasks:
            task.running = False
    
    def run_pending_tasks(self):
        now = time.time()
        num_run = 0
        for task in self.tasks:
            if task.run_time < now:
                task.run()
                num_run += 1
        return num_run
    
    def add_task(self, task):
        # thread-safe to do the following two steps in this order only:
        # do not want a task in the list that doesn't already know it's in
        # the list. The other way around is OK.
        task.add_runner(self)
        task.running = True
        task.paused = False
        self.tasks.append(task)
    
    def remove_task(self, task):
        # yes, O(N). Use an ordered_set for tasks if this actually matters.
        self.tasks.remove(task)
    
    @classmethod
    def from_json(cls, json_str):
        vals = json.loads(json_str)
        instance = cls(vals['sleep_interval'])
        for task in vals['tasks']:
            instance.add_task(eval(task))
        return instance
    
    def to_json(self):
        out_dict = {'sleep_interval': self.sleep_interval,
                    'tasks':[repr(task) for task in self.tasks]}
        return json.dumps(out_dict)

class Task:
    def __init__(self, function, run_time, period=None, stop_time=None):
        self.function = function
        self.run_time = run_time
        self.period = period
        self.stop_time = stop_time
        self._paused = False
        self._running = True
        
    @property
    def paused(self):
        return self._paused
    
    @paused.setter
    def paused(self, paused):
        self._paused = paused
        self.function.paused = paused

    @property
    def running(self):
        return self._running
    
    @running.setter
    def running(self, running):
        self._running = running
        self.function.running = running
    
    def add_runner(self, runner):
        self.runner = runner
    
    def run(self):
        if self.period:
            next_time = self.run_time + self.period
        self.function()
        if self.period and (self.stop_time is None or next_time < self.stop_time):
            self.run_time = next_time
        else:
            self._running = False
            self.runner.remove_task(self)

    def __repr__(self):
        return 'Task({function}, {run_time}, period={period}, stop_time={stop_time})'.format(**self.__dict__)

class ImportFunction:
    def __init__(self, function):
        self.function = function
        module, func_name = function.rsplit('.', 1)
        self.module = __import__(module, fromlist=[func_name])
        self.func_name = func_name
        self._paused = False
        self._running = True
    
    def __call__(self):
        self.module = imp.reload(self.module)
        return getattr(self.module, self.func_name)()
        
    def __repr__(self):
        return 'ImportFunction({})'.format(repr(self.function))

    @property
    def paused(self):
        return self._paused
    
    @paused.setter
    def paused(self, paused):
        self._paused = paused
        getattr(self.module, func_name).paused = paused

    @property
    def running(self):
        return self._running
    
    @running.setter
    def running(self, running):
        self._running = running
        getattr(self.module, func_name).running = running

