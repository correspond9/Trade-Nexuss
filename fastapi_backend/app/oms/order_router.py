
from app.ems.execution_engine import execute
from app.trading.trade_engine import create_trade

def route(order):
    exec_res = execute(order)
    if exec_res.get("status") == "FILLED":
        trade = create_trade(order, {"price": exec_res.get("price"), "qty": exec_res.get("qty")})
        return {"status":"FILLED","trade":trade}
    return exec_res
