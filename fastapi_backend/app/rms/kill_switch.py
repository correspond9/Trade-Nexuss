
# Blocks new orders if active
def blocked(user):
    return not user.active
