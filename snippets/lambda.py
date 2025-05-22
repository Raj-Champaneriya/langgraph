from typing import Union, Callable

Number = Union[int, float]
square: Callable[[Number], Number] = lambda x: x * x
x = 5 
print(f"The square of {x} is {square(x)}")

numbers = [1, 2, 3, 4, 5]
squared_numbers = list(map(lambda x: x * x, numbers))

print(f"Squared numbers: {squared_numbers}")
