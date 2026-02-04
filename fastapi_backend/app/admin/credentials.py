
# Admin-managed credentials store
CREDENTIALS = {}
def set_creds(data: dict):
    CREDENTIALS.update(data)
def get_creds():
    return CREDENTIALS
