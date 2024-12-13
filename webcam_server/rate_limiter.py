from flask import request, jsonify
from functools import wraps
from datetime import datetime, timedelta
import redis
import os

redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=int(os.environ.get('REDIS_PORT', 6379))
)

def rate_limit(requests_per_minute=60):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            client_ip = request.remote_addr
            key = f'rate_limit:{client_ip}:{f.__name__}'
            
            # Get current request count
            count = redis_client.get(key)
            if count is None:
                redis_client.setex(key, 60, 1)
            elif int(count) >= requests_per_minute:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            else:
                redis_client.incr(key)
            
            return f(*args, **kwargs)
        return wrapped
    return decorator 