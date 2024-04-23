# import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
from scipy.optimize import fsolve

# For function improcess(input):
#   Input: Array of 4D values e.g. np.shape(input) = (2100, 4)
#   Output: Array of 4D values in the same size, Bézier control points in format [x0,x1,x2,x3]


# Used by improcess() to perform per-channel denoising, Bézier fitting and quantization
def processchannel(inputchannel):
    sz = len(inputchannel)
    datadict = {(np.arange(0, sz))[i]: inputchannel[i] for i in np.arange(0, sz)}

    # Data editing
    dsorted = sorted(inputchannel)
    dsdiffs = [None]*(sz-1)
    for i in range(len(dsdiffs)):
        # print("{} {} {} {}".format(i, dsorted[i], dsorted[i+1], dsorted[i] - dsorted[i+1]))
        dsdiffs[i] = dsorted[i] - dsorted[i+1]
    # plt.plot(range(len(dsdiffs)), dsdiffs, '.', label='dsdiffs')

    windowsize = 10 # min 4ish
    absjump = [None]*(sz-1-windowsize)
    for i in range(len(absjump)):
        # print("absjump {} {} {}".format(i, dsorted[i], abs(sum(dsdiffs[i:i+windowsize])), sum(dsdiffs[i:i+windowsize])))
        absjump[i] = abs(sum(dsdiffs[i:i+windowsize]))
    # plt.plot(range(len(absjump)), absjump, '.', label='absjump')

    # Only try to remove noise if there's a big jump
    if max(absjump) > 15: # min 5
        # In the first half
        if absjump.index(max(absjump)) <= sz/2:
            snipindex = absjump.index(max(absjump)) + windowsize
            # print("snipindex <= sz/2: maxjump is {} at {} of value {}".format(max(absjump), snipindex, dsorted[snipindex]))
            for i in range(snipindex):
                for key in list(datadict.keys()):
                    if datadict[key] <= dsorted[snipindex]:
                        del datadict[key]
        # In the 2nd half
        else:
            snipindex = absjump.index(max(absjump))
            # print("snipindex > sz/2: maxjump is {} at {} of value {}".format(max(absjump), snipindex, dsorted[snipindex]))
            for i in range(snipindex):
                for key in list(datadict.keys()):
                    if datadict[key] > dsorted[snipindex]:
                        del datadict[key]


    # Fit and plot the noiseless curve to the sigmoid func
    def fsigmoid(x, a, b, c, d):
        return d / (1.0 + np.exp(-a * (x - b))) + c
    popt, pcov = curve_fit(fsigmoid, list(datadict.keys()), list(datadict.values()), method='dogbox', bounds=([-1., 0, 0, 0], [1., 1+sz, 1+max(inputchannel), 1+np.ptp(inputchannel)]))
    # print("Sigmoid parameters:\n\t{}".format(popt))

    # Use derivative of sigmoid to estimate control point placement
    handlex = 0
    slopefactor = 13
    threshold = popt[0]*popt[3]/(4*slopefactor)
    while 1 < threshold/(popt[0]*popt[3]*(np.e**(popt[0]*(handlex-popt[1])))/(np.e**(popt[0]*(handlex-popt[1]))+1)**2):
        handlex += 1
        # print("handlex = [{}, {:.0f}] w/ thresh {:.04f}/{:.04f}".format(handlex, 2*np.floor(popt[1])-handlex, (popt[0]*popt[3]*(np.e**(popt[0]*(handlex-popt[1])))/(np.e**(popt[0]*(handlex-popt[1]))+1)**2), threshold))

    # Return bézier control points (bcp) in format [x0,y0,...,x3,y3]
    x0 = handlex
    x1 = x2 = int(popt[1])
    x3 = min(2*x1-x0, sz-1)
    y0 = y1 = int(fsigmoid(x0, *popt))
    y2 = y3 = int(fsigmoid(x3, *popt))
    bcp = [x0, y0, x1, y1, x1, y2, x3, y3]
    # print("Béziers:\n\t0: [{}, {}]\n\t1: [{}, {}]\n\t2: [{}, {}]\n\t3: [{}, {}]".format(*bcp))

    # Bézier creation and quantization
    outputwb = np.array([None]*sz)
    for x in range(0, sz):
        if x < x0:
            outputwb[x] = y0
        if x0 <= x <= x3:
            def bezierinputx(t):
                return (1-t)*((1-t)*((1-t)*x0+t*x1)+t*((1-t)*x1+t*x2))+t*((1-t)*((1-t)*x1+t*x2)+t*((1-t)*x2+t*x3))-x
            t = fsolve(bezierinputx, 0.5)
            bezieroutputy = (1-t)*((1-t)*((1-t)*y0+t*y1)+t*((1-t)*y1+t*y2))+t*((1-t)*((1-t)*y1+t*y2)+t*((1-t)*y2+t*y3))
            # print("t: {}\ti: {}\tcorresponding y: {}".format(t, x, int(bezieroutputy)))
            outputwb[x] = int(bezieroutputy[0])
        if x > x3:
            outputwb[x] = y3

    return outputwb, bcp


# Input: Array of 4D values e.g. np.shape(input) = (2100, 4)
# Output: Array of 4D values in the same size, Bézier control points in format [x0,x1,x2,x3]
def improcess(inputbyimages):
    sz = len(inputbyimages)
    smoothchannels = [[None for i in range(sz)] for j in range(4)]
    bcps = [[None for i in range(sz)] for j in range(4)]
    bcpptps = [[None for i in range(sz)] for j in range(4)]
    returnbcpx = [[None for i in range(4)] for j in range(2)]

    inputbychannels = np.transpose(inputbyimages)
    for i in range(4):
        smoothchannels[i], bcps[i] = processchannel(inputbychannels[i])
        bcpptps[i] = np.ptp(bcps[i][1::2])
        # print("smoothchannel[{}] sz{} {}".format(i, len(smoothchannels[i]), smoothchannels[i]))
        # print("bcps[{}]:\n\t0: [{}, {}]\n\t1: [{}, {}]\n\t2: [{}, {}]\n\t3: [{}, {}]".format(i, *bcps[i]))
        # plt.plot(np.arange(0, sz), smoothchannels[i], '.')
        # plt.plot(bcps[i][::2], bcps[i][1::2], '+')
    # plt.show()

    # Find red and blue channels, take avg x position of BCPs
    for i in range(4):
        returnbcpx[0][i] = bcps[bcpptps.index(sorted(bcpptps)[2])][i*2]
        returnbcpx[1][i] = bcps[bcpptps.index(sorted(bcpptps)[3])][i*2]
        # print("returnbcp[{}] = avg of {} and {}".format(i, bcps[bcpptps.index(sorted(bcpptps)[2])][i*2], bcps[bcpptps.index(sorted(bcpptps)[3])][i*2]))

    print("Smoothed output curves:\n\tCh0: {}\n\tCh1: {}\n\tCh2: {}\n\tCh3: {}\nPer-channel peak-to-peaks: {}\nReturned Bézier control point x coordinates:\n\t{}".format(*smoothchannels, bcpptps, returnbcpx))
    return np.transpose(smoothchannels), returnbcpx
