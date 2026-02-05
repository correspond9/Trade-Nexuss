
# Blocks new orders if active
def blocked(user):
    if user is None:
        return True
    active = getattr(user, "active", None)
    if active is not None:
        return not active
    status = getattr(user, "status", "ACTIVE")
    return str(status).upper() != "ACTIVE"
