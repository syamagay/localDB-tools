###############
### Osaka Univ.
### K. Yajima
###############

import glob
import sys, os, func
sys.path.append( os.path.dirname(os.path.abspath(__file__)) + "/PlotTools" )

from PlotHelpers import gHelper as PH
import PlotFromHistos.SimplePlots as Plot
import base64

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

def drawScan(mod_name, scan_type, num_scan, log, Max, map_list):
    if int(num_scan) < 0 : raise ValueError("Invalid scan number")

    ROOT.gROOT.SetBatch()

    max_value = func.readJson("parameter.json") 

############
# Main loop
    #num_plot = []

    for map_type in datDict[scan_type]:
        if map_list[map_type[0]]: 
            h1 = ROOT.TH1D(mod_name+"_"+map_type[0]+"_Dist_"+num_scan,
                           mod_name+"_"+map_type[0]+"_Dist_"+num_scan+";"+map_type[1],
                           1000, 0, 1000)
        
            h2 = ROOT.TH2D(mod_name+"_"+map_type[0]+"_"+num_scan,
                           mod_name+"_"+map_type[0]+"_"+num_scan+";Column;Row",
                           NUM_COL*2, 0.5, NUM_COL*2+0.5, NUM_ROW*2, 0.5, NUM_ROW*2+0.5)
        
            # Chip loop
            for i in range(4) :
        
                # Open Files
                filename = "/tmp/data/chipId"+str(i+1)+"_"+map_type[0]+".dat"
                try :
                    f = open(filename)
                except :
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
        
            path_dir = "/tmp/" + scan_type
            PH.outDir = path_dir
    
            path_plot = num_scan + "_" +  map_type[0]
            Plot.Plot1D_fromHistos(h1, log, path_plot+"_1", "#Ch.", "histo", Max)
            Plot.Plot2D_fromHistos(h2, log, path_plot+"_2", map_type[1], Max)

            if Max == "":
                max_value[scan_type][map_type[0]] = [int(h2.GetBinContent(h2.GetMaximumBin())),log]
            else:
                max_value[scan_type][map_type[0]] = [int(Max),log]

    func.writeJson("parameter.json",max_value)
    #return max_value
