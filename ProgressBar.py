import sys
import math
import numpy as np

class ProgressBar:
    def __init__(self,R,width=100):
        self.R = R-1
        self.width = width
    def Update(self,i):
        pct = i/self.R*100
        w = math.floor(pct)
        sys.stdout.write("\r"+'['+'|'*w+' '*(self.width-w-1)+'] '+str(np.round(pct,1))+'%')
        if pct == 100:
            sys.stdout.write('\n')
            