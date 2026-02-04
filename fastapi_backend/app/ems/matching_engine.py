
# Matches orders at bid/ask
def execute(order, price):
    return {"trade_price": price, "qty": order["qty"]}
