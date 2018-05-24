from builtins import object
import time
import copy

__all__ = ["Telemetry"]


class Telemetry(object):

    def __init__(self, wrap_object=None, names=None):

        self.timestamp = None
        self.update_timestamp = None
        self.latest_valid_index = -1

        self.history = []
        self.history_size = 0

        self._invalid = True
        self.invalid_value = None
        self.generate_age = 0.
        self.update_age = 0.

        # self.source = ''
        self.values = {}

        if wrap_object is not None:
            attr_list = dir(wrap_object)
            for attr in attr_list:
                if not attr.startswith('__'):
                    # setattr(self, attr, None)
                    self.values[attr] = getattr(wrap_object, attr)
        elif names is not None:
            for attr in names:
                # setattr(self, attr, None)
                self.values[attr] = getattr(wrap_object, attr)
        else:
            raise IOError("Could not setup Telemetry class. Provide wrap_object or names.")

    def is_valid(self, timestamp=None):

        timestamp = time.time() if timestamp is None else timestamp
        if (0. < self.generate_age < self.time_age(timestamp)) or (0. < self.update_age < self.time_update(timestamp)):
            return False

        return not self._invalid

    def time_age(self, timestamp=None):

        timestamp = time.time() if timestamp is None else timestamp

        return timestamp - self.timestamp

    def time_update(self, timestamp=None):

        timestamp = time.time() if timestamp is None else timestamp

        return timestamp - self.update_timestamp

    def __getattr__(self, item):
        if item not in self.values:
            raise AttributeError("not %s" % (item))

        if self.is_valid():
            return self.values[item]
        else:
            return self.invalid_value

    def update(self, value):

        # Clear history
        while len(self.history) > self.history_size:
            del self.history[0]
            self.latest_valid_index -= 1

        if value == self.invalid_value:
            self._invalid = True
            return

        self._invalid = False

        if self.history_size > 0:
            self.history.append((self.update_timestamp, self.timestamp, copy.deepcopy(self.values)))
            if self.is_valid():
                self.latest_valid_index = len(self.history) - 1

        for attr in self.values:
            # setattr(self, attr, getattr(value, attr))
            self.values[attr] = getattr(value, attr)
        self.timestamp = getattr(value, "timestamp") if hasattr(value, "timestamp") else None
        self.update_timestamp = time.time()
        # append to history
