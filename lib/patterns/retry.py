import time
import logging


def retry(max_retries=3, retry_delay=1, incremental_backoff=2, logger=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            retry_delay = retry_delay
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        raise(e)
                    if logger:
                        logger.warning(f"Retryable error caught: {e}. Retrying...")
                    time.sleep(retry_delay)
                    retry_delay *= incremental_backoff
        return wrapper
    return decorator

