'''
Docstring for practice.oops
class Person:
    def __init__(self, name, language, job):
        self.name = name
        self.language = language
        self.job = job

p1 = Person('abhishek', 'hindi', 'ai develeoper')
print(p1.name, p1.language, p1.job)


# alternative way, usign repr. Add this method to define the string representation of the object
class Person:
    def __init__(self, name, language, job):
        self.name = name
        self.language = language
        self.job = job

    def __repr__(self):
        return f'name:{self.name} | langauge:{self.language} | job:{self.job}'

p1 = Person('abhishek', 'hindi', 'ai develeoper')
print(p1)

1. Person Class
Create a class named Person
Add attributes: name, salary
Create one object and print both values

class Person:
    def __init__(self,name, salary):
        self.name = name
        self.salary = salary

p1 = Person('abhi', 15000)
print(p1.name, p1.salary)

# alternative way
def __repr__(self):
    return f'name:{self.name} | salary:{self.salary}'
p1 = Person('abhi', 15000
print(p1)


2. Greeting Method
Create a class Person
Add a method greet
The method should print a greeting using the person's name

class Person:
    def __init__(self, )

'''