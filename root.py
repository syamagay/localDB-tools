###############
### Osaka Univ.
### K. Yajima
###############

import glob
import sys, os
sys.path.append( os.path.dirname(os.path.abspath(__file__)) + "/PlotTools" )

from PlotHelpers import gHelper as PH
import PlotFromHistos.SimplePlots as Plot

import ROOT

##########
# Variables
NUM_COL = 80
NUM_ROW = 336

datDict = { "selftrigger" : [("OccupancyMap-0", "#Hit"),],
            "noisescan" : [("NoiseOccupancy","NoiseOccupancy"), ("NoiseMask", "NoiseMask")],
            "totscan" : [("MeanTotMap", "Mean[ToT]"), ("SigmaTotMap", "Sigma[ToT]")],
            "thresholdscan" : [("ThresholdMap", "Threshold[e]"), ("NoiseMap", "Noise[e]")],
            "digitalscan" : [("OccupancyMap", "Occupancy"), ("EnMask", "EnMask")],
            "analogscan" : [("OccupancyMap", "Occupancy"), ("EnMask", "EnMask")]}

def drawScan(scan_type, mod_name):
    if scan_type in datDict:
        
    else:

###########
## Scan number
#num_scan  = raw_input('Enter the scan number ->  ')
#if int(num_scan) < 0 : raise ValueError("Invalid scan number")
#
#
###########
## Scan directory
#inDir = "ScanData/"
#
#scanDirs=glob.glob(inDir+"%06d"%int(num_scan)+"_*")
#if len(scanDirs) != 1 : raise ValueError("Valid directory not found")
#
# TODO : More sophisticated way
#scan_type = scanDirs[0].split("_")[1]
#mod_name = os.path.basename( glob.glob(scanDirs[0]+"/*_chipId1.json.after")[0] ).split("_")[0]


############
# Main loop
for map_type in datDict[scan_type] :

    print mod_name, map_type, num_scan

    h1 = ROOT.TH1D(mod_name+"_"+map_type[0]+"_Dist_"+num_scan,
                   mod_name+"_"+map_type[0]+"_Dist_"+num_scan+";"+map_type[1],
                   1000, 0, 1000)

    h2 = ROOT.TH2D(mod_name+"_"+map_type[0]+"_"+num_scan,
                   mod_name+"_"+map_type[0]+"_"+num_scan+";Column;Row",
                   NUM_COL*2, 0.5, NUM_COL*2+0.5, NUM_ROW*2, 0.5, NUM_ROW*2+0.5)

    # Chip loop
    for i in range(4) :

        # Open Files
        #filename = scanDirs[0]+"/"+mod_name+"_chipId"+str(i+1)+"_"+map_type[0]+".dat"
        filename = "/tmp/"+mod_name+"_chipId"+str(i+1)+"_"+map_type[0]+".dat"
        try :
            f = open(filename)
        except :
            print("File not found : " + filename)
            continue

        # Readlines
        readlines = f.readlines()

        # Pixel loop
        if   i==0 or i==1 : row = NUM_ROW-1
        elif i==2 or i==3 : row = NUM_ROW

        for readline in readlines :
            words = readline.split()
            if len(words) != 80 : continue

            if   i==0 : col = NUM_COL-1
            elif i==1 : col = NUM_COL*2-1
            elif i==2 : col = 0
            elif i==3 : col = NUM_COL

            for word in words :
                h1.Fill(float(word))
                h2.SetBinContent(col+1, row+1, float(word))

                if   i==0 or i==1 : col = col - 1
                elif i==2 or i==3 : col = col + 1

            if   i==0 or i==1 : row = row - 1
            elif i==2 or i==3 : row = row + 1

        f.close()

    PH.outDir = os.path.dirname(os.path.abspath(__file__)) + "/Data/" + "%06d"%int(num_scan) + "_" + scan_type

    Plot.Plot1D_fromHistos(h1, False, num_scan+"_"+mod_name+"_"+map_type[0]+"_Dist", "#Ch.")
    Plot.Plot2D_fromHistos(h2, False, num_scan+"_"+mod_name+"_"+map_type[0], map_type[1])
