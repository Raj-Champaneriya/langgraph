from typing import Union

def square(x: Union[int, float]) -> float:
    return x * x

x = 5.25

print(f"The square of {x} is {square(x)}")