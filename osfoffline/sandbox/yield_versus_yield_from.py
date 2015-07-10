__author__ = 'himanshu'




#normal array
def get_vals_arr():
    return [i for i in range(10)]

def get_vals_gen():
    #creates a generator and then returns generator itself.
    return (i for i in range(10))


def get_vals_gen_yield():
    #creates generator and then yields its values out one by one
    for i in range(10):
        yield i,
    # yield (i for i in range(10))

# print(get_vals_arr())#[0,1,..9]
# print(get_vals_gen())# <generator object>

# for i in get_vals_gen_yield():
#     print(i)



def yield_generator():
    # THIS ENTIRE METHOD IS NOT RUN when you first
    # call this function. In the first time, only a generator object
    # is send to the variable.



    # when the first use of the generator occurs,
    # then this portion of the code is called as well.
    print('himanshu')
    mylist = [i for i in range(10)]
    print(mylist)

    # in the first use of the generator, you go all the way up to the yield
    # keyword and then return whatever you have. Then you pause execution of
    # the function until this generator is called upon again.
    for i in mylist:
        #the yield is the reason that this function creates a generator.
        yield i

generator = yield_generator()
for i in generator:
    print(i)



# problem: Figure out whats happening the code.

# def node._get_child_candidates(self, distance, min_dist, max_dist):
#     if self._leftchild and distance - max_dist < self._median:
#         yield self._leftchild
#     if self._rightchild and distance + max_dist >= self._median:
#         yield self._rightchild
#
# result, candidates = list(), [self]                                                       (1)
# while candidates:
#     node = candidates.pop()
#     distance = node._get_dist(obj)
#     if distance <= max_dist and distance >= min_dist:
#         result.extend(node._values)
#     candidates.extend(node._get_child_candidates(distance, min_dist, max_dist))           (2)
# return result


# (1) this is where code execution starts. result = list() list. candidates = list of self objects.
# (2) get the left and right child candidates of node. a generator is a iterable, thus this passes the type checker
#     you can do this. The extend will basically keep on iterating through the input iterable until there is nothing left.
#     THUS, you will first add all the left children then add all the right children.


# Advanced generator concepts

#Example:
class Bank(): # let's create a bank, building ATMs
    crisis = False
    def create_atm(self):
        while not self.crisis:
            yield "$100"

hsbc = Bank() #create the bank
corner_street_atm = hsbc.create_atm() # create the generator. When not in crisis, this generator will yield "$100"


# a way to get a value from a generator is the next() method.
print(corner_street_atm.next()) # $100

#make a list of the first 5 values that the generator gives you. generator is still on demand. new list is stored in memory.
print([corner_street_atm.next() for cash in range(5)]) # [$100, $100, $100, $100,$100]


hsbc.crisis = True # make it so generator will not yield $100 any more.
print(corner_street_atm.next()) # throws exception because generator does not go to any more yield keyword


wall_street_atm = hsbc.create_atm()
# even though this is a new generator, the class variable crisis=True so this generator will
# throw an error as well.
print(wall_street_atm.next())

hsbc.crisis = False # want atm's to not be in crisis anymore. Want them to yield $100 now.
#BUT, that wont occur. The generator has already been created and has ended.
print(corner_street_atm.next())  # raise exception


brand_new_atm = hsbc.create_atm() # new generator is not already done thus will actually go to the while code
for cash in brand_new_atm:
    print(cash)                   # $100 $100 $100 $100 $100 $100 $100  ...





