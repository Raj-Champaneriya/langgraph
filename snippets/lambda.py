from typing import Union, Callable

square: Callable[[Union[int, float]], Union[int, float]] = lambda x: x * x
x = 5  # Changed from "Raj" to a number
print(f"The square of {x} is {square(x)}")

numbers = [1, 2, 3, 4, 5]
squared_numbers = list(map(lambda x: x * x, numbers))

print(f"Squared numbers: {squared_numbers}")