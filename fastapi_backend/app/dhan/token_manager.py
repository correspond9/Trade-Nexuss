
# Auto / manual token toggle
MODE = "MANUAL"  # MANUAL | AUTO
TOKEN = None

def set_manual(token: str):
    global MODE, TOKEN
    MODE = "MANUAL"
    TOKEN = token

def set_auto():
    global MODE
    MODE = "AUTO"

def get_token():
    return TOKEN
