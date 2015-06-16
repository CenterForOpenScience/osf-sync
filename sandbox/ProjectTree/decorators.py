__author__ = 'himanshu'


#  def logger(func):
# ...     def inner(*args, **kwargs): #1
# ...         print "Arguments were: %s, %s" % (args, kwargs)
# ...         return func(*args, **kwargs) #2
# ...     return inner


def can_put_stuff_in(func):
    def check(self, *args):
        if self.kind not in [self.FOLDER, self.COMPONENT, self.PROJECT]:
            raise TypeError
        func(self, *args)
    return check
#
# def dec_check(f):
#   def deco(self):
#     print 'In deco'
#     f(self)
#   return deco

