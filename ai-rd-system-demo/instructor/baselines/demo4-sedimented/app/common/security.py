USER_TENANTS = {
    "alice": {"NORTH"},
    "bob": {"SOUTH"},
    "admin": {"NORTH", "SOUTH"},
}


def allowed_tenants(user: str) -> set[str]:
    return USER_TENANTS.get(user, set())
