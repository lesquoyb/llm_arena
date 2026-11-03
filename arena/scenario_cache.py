"""Bounded reuse of deterministic scenario construction during artifact checks."""
import threading
from .core import digest, make_scenario


class ScenarioCache:
    def __init__(self, config):
        self.config=config;self.values={};self.teams={};self.lock=threading.Lock()

    def get(self, infos, seed):
        keys=[]
        with self.lock:
            for info in infos:
                identity=info['sha256']
                if identity not in self.teams:self.teams[identity]=digest(info.get('team'))
                keys.append((info['entrypoint'],self.teams[identity]))
            key=(tuple(keys),seed)
            if key in self.values:return self.values[key]
        scenario=make_scenario(self.config,[info['entrypoint'] for info in infos],seed,[info.get('team') for info in infos])
        value=(scenario,digest(scenario))
        with self.lock:
            self.values[key]=value
            while len(self.values)>256:self.values.pop(next(iter(self.values)))
        return value
