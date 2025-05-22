from typing import TypedDict

class Person(TypedDict):
    name: str
    age: int
    is_student: bool
    hobbies: list[str]

def add_person(name: str, age: int, is_student: bool, hobbies: list[str]) -> Person:
    return Person(name=name, age=age, is_student=is_student, hobbies=hobbies)

def print_person_info(person: Person) -> None:
    print(f"Name: {person['name']}")
    print(f"Age: {person['age']}")
    print(f"Is Student: {person['is_student']}")
    print(f"Hobbies: {', '.join(person['hobbies'])}")
    
# Example usage
person1 = add_person("Alice", 25, True, ["reading", "hiking", "coding"])
print_person_info(person1)
