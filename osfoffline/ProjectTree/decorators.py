__author__ = 'himanshu'


#todo: REDO THIS.
def can_put_stuff_in(func):
    def check(self,*args):

        if self.kind not in [self.COMPONENT, self.PROJECT, self.FOLDER]:
            raise TypeError
        return func(self,*args)
    return check