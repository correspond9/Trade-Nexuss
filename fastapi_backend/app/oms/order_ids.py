
"""
Generate exchange-style order identifiers.

NSE-style order IDs are 14-character alphanumeric identifiers. We generate
an uppercase alphanumeric string of length 14 using a time+random mix to
reduce chance of collision.
"""
import time
import secrets
import string

ALPHABET = string.ascii_uppercase + string.digits

def generate(length: int = 14) -> str:
    # combine a millisecond timestamp suffix with random chars when possible
    # but keep result length exactly `length`.
    ts = str(int(time.time() * 1000))
    # pick random characters for remaining length
    rand_len = max(0, length - len(ts))
    rand = ''.join(secrets.choice(ALPHABET) for _ in range(rand_len))
    candidate = (rand + ts)[-length:]
    return candidate
