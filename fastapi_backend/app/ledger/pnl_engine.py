
# Computes realized/unrealized PnL
def realized(buy, sell, qty):
    return (sell - buy) * qty
