from typing import Optional

def nice_message(name: Optional[str]) -> str:
    if name is None:
        return "Hello, World!"
    else:
        return f"Hello, {name}!"
    
# Example usage
name1 = "Alice"
name2 = None
invalid_name = 123  # This will cause a type error if type checking is enforced
print(nice_message(invalid_name))  # This will raise a TypeError at runtime
print(nice_message(name1))  # Output: Hello, Alice!
print(nice_message(name2))  # Output: Hello, World!