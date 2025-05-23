from typing import Annotated

email = Annotated[str, "Email address"]
print(email.__metadata__[0])

# Simple string with metadata
username = Annotated[str, "The user's display name"]

# Integer with range metadata
age = Annotated[int, "Must be between 0 and 120"]

# Multiple metadata items
password = Annotated[str, "User password", "Must be at least 8 characters"]

# Using for function parameters
def register_user(
    name: Annotated[str, "Full name"],
    email: Annotated[str, "Valid email address"],
    age: Annotated[int, "Must be 18 or older"]
):
    pass

print(password.__metadata__)
