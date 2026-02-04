
# Creates trades from executions
def create_trade(order, execution):
    return {
        "order_id": order["order_id"],
        "price": execution["price"],
        "qty": execution["qty"]
    }
