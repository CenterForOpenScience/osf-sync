__author__ = 'himanshu'

class Item(object):
    def __init__(self, name='a', items=[]):
        self.items = items
        self.name = name

    def add_item(self, item):
        self.items.append(item)



if __name__=="__main__":

    alpha = Item(name='a')
    alpha.add_item(Item('b'))
    print(alpha.items[0].items[0].items[0])




