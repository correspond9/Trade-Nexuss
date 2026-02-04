
# Persistent position storage hook
positions = {}
def get(user, symbol):
    return positions.get((user, symbol), {"qty":0, "avg_price":0})
def save(user, symbol, pos):
    positions[(user, symbol)] = pos
