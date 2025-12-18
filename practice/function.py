'''

def func(add):
    a, b = 3, 4
    c = a + b
    return c


# Write a program using functions to find greatest of three numbers.
def greatest(a,b,c):
    if a>=b and a>=c:
        print(f'a which is {a} is greatest number')
    elif b>=c and b>=a:
        print(f'b which is {b} is greatest number')
    else:
        print(f'c which is {c} is greatest number')

a,b,c = 2,3,4
greatest(a,b,c)


# Write a python program using function to convert Celsius to Fahrenheit

cel = 30
def temp(cel):
    return (cel * 9/5) + 32
far = temp(cel)
print(far)



# How do you prevent a python print() function to print a new line at the end
print("Hello", end=" ")
print("World")


# Write a recursive function to calculate the sum of first n natural numbers.

def nat(n):
    if n==1:
        return 1
    else:
        return n + nat(n-1)
n=17
result = nat(n)
print(result)


# Write a python function which converts inches to cm

def convert(inch):
    return inch * 2.54


   
# Write a python function to print multiplication table of a given number. 

def table(n):
    for i in range(1,11):
        print(f'{n} * {i} is {n*i}')
    i+=1
n=7
table(n)

'''

  

