from collections import OrderedDict

class SimpleCache:
    def __init__(self, capacity=100):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        if key not in self.cache:
            return None

        # Move to end to make it "Least Recently Used" (LRU)
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        
        # If we exceed capacity, remove the first (oldest) item
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
