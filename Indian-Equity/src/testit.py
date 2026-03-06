class Addition:
    def __inti__(self, a, b):
        pass


    def add(self, a, b):
        return a + b
    

class Subtract:
    def __init__(self):
        pass
        # self.a = 
        # self.b = b

    def sub(self, a, b):
        return a - b
    

class Calculator(Addition, Subtract):
    def __init__(self, a, b):
        super().__init__()
        self.a = a
        self.b = b

    def calc_add(self):
        return self.add(self.a, self.b)
    
    def calc_sub(self):
        return self.sub(self.a, self.b)
    

calc = Calculator(6, 7)
print(calc.calc_add())
print(calc.calc_sub())