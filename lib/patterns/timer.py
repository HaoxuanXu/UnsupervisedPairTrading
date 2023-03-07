import time
import logging


def timer():
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            res = func(*args, **kwargs)
            duration = time.perf_counter() - start 
            
            print(f"time taken: {duration} seconds")
            
            return res 
        return wrapper
    return decorator

