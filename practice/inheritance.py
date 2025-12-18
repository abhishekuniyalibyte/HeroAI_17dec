'''
Docstring for practice.inheritance


class Company:   # parent class
    def __init__(self, location):
        self.location = location


class Employee(Company):      # child class
    def __init__(self, name, profile, location):
        super().__init__(location)      # initialize parent
        self.name = name
        self.profile = profile


emp = Employee(
    name="Abhi",
    profile="python_ai_developer",
    location="noida"
)

print(emp.name, emp.profile, emp.location)   

'''
 
CLASS  METHOD : A class method is a method which is bound to the class and not the object of the class. 
@classmethod decorator is used to create a class method

