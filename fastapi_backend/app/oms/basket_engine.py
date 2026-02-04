
# Handles basket order grouping
def create_basket(orders):
    return {"basket_id": id(orders), "orders": orders}
