# import matplotlib.pyplot as plt
# import numpy as np
from scipy.optimize import fsolve

# For function bezupdater(input):
#   Input: Number of images, 4D array of 2D coords in format [handle0, ctrlpt0, ctrlpt1, handle1]
#   Output: New array of size sz, output coords in format [handle0, ctrlpt0, ctrlpt1, handle1]
def bezupdater(sz, coords):
    outputcurve = [None for i in range(sz)]
    outputcoords = [[None for i in range(2)] for j in range(4)]
    x0,y0 = coords[0]
    x1,y1 = coords[1]
    x2,y2 = coords[2]
    x3,y3 = coords[3]
    x1 = max(x0, min(x1, x3))
    x2 = max(x0, min(x2, x3))
    y1 = max(y0, min(y1, y3))
    y2 = max(y0, min(y2, y3))
    # print("Béziers:\n\t0: [{}, {}]\n\t1: [{}, {}]\n\t2: [{}, {}]\n\t3: [{}, {}]".format(x0,y0,x1,y1,x2,y2,x3,y3))

    outputcoords = [[x0,y0],[x1,y1],[x2,y2],[x3,y3]]

    for x in range(0, sz):
        # print("x:{}".format(x))
        if x < x0:
            outputcurve[x] = y0
        if x0 <= x <= x3:
            def bezierinputx(t):
                return (1-t)*((1-t)*((1-t)*x0+t*x1)+t*((1-t)*x1+t*x2))+t*((1-t)*((1-t)*x1+t*x2)+t*((1-t)*x2+t*x3))-x
            t = fsolve(bezierinputx, 0.5)
            bezieroutputy = (1-t)*((1-t)*((1-t)*y0+t*y1)+t*((1-t)*y1+t*y2))+t*((1-t)*((1-t)*y1+t*y2)+t*((1-t)*y2+t*y3))
            # print("t: {}\ti: {}\tcorresponding y: {}".format(t, x, int(bezieroutputy)))
            outputcurve[x] = int(bezieroutputy[0])
        if x > x3:
            outputcurve[x] = y3
    # plt.plot(np.arange(0, sz), outputcurve, '.')
    # for i in range(4):
    #     plt.plot(outputcoords[i][0], outputcoords[i][1], '+')
    # plt.show()
    # print(outputcoords)

    return outputcurve, outputcoords

# Test func
# curve,coord = bezupdater(2100, [[680,1014],[1061,1014],[500,1410],[1442,1410]])