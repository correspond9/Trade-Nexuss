
# Updates positions from trades
def update(position, trade):
    position["qty"] += trade["qty"]
    return position
