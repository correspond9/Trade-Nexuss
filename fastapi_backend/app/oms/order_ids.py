
# Generates exchange-style order IDs
import time
def generate():
    return f"ORD{int(time.time()*1000)}"
