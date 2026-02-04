
# MIS auto square-off between 15:20–15:25
from datetime import time, datetime

def should_squareoff(product):
    now = datetime.now().time()
    return product == "MIS" and time(15,20) <= now <= time(15,25)
