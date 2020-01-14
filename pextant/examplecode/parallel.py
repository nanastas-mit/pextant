from pathos.multiprocessing import ProcessingPool as Pool
x = [1,2,3]
y = [1,2,3]
class Test(object):
    def __init__(self, c):
        self.c = c
    def plus(self, x, y):
        return self.c + x+y

if __name__ == '__main__':
    p = Pool(4)
    t = Test(5)
    out = p.map(t.plus, x, y)
    print(out)