import time
from fastapi import HTTPException

# In-memory token bucket & IP tracker (Phase 1)
RATE_LIMIT_DB = {}
MAX_REQUESTS_PER_MINUTE = 60

def check_rate_limit(ip: str):
    now = time.time()
    if ip not in RATE_LIMIT_DB:
        RATE_LIMIT_DB[ip] = []
    
    # Clean up old requests
    RATE_LIMIT_DB[ip] = [t for t in RATE_LIMIT_DB[ip] if now - t < 60]
    
    if len(RATE_LIMIT_DB[ip]) >= MAX_REQUESTS_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Protect free models.")
    
    RATE_LIMIT_DB[ip].append(now)
