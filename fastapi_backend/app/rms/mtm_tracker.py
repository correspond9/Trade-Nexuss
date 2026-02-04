
# Tracks MTM (realized & unrealized)
def compute(position, price):
    return (price - position["avg_price"]) * position["qty"]
