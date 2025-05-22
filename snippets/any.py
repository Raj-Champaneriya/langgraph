from typing import Any

def print_value(x: Any) -> None:
    """
    Prints the value of x. The type of x can be any.
    
    Args:
        x (Any): The value to print.
    """
    print(x)
    
# Example usage
if __name__ == "__main__":
    print_value(42)          # Prints an integer
    print_value("Hello")     # Prints a string
    print_value([1, 2, 3])   # Prints a list
    print_value({"key": "value"})  # Prints a dictionary
    print_value(None)        # Prints None