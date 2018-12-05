###############
### Osaka Univ.
### K. Yajima
###############

import glob
import sys, os, pwd, json
sys.path.append( os.path.dirname(os.path.abspath(__file__)) + "/PlotTools" )
JSON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)) ) + "/json"

from PlotHelpers import gHelper as PH
import PlotFromHistos.SimplePlots as Plot
import base64

import ROOT

USER=pwd.getpwuid( os.geteuid() ).pw_name
USER_DIR = '/tmp/{}'.format( USER ) 
DAT_DIR = '{}/dat'.format( USER_DIR )
PLOT_DIR = '{}/result'.format( USER_DIR )

##########
# Variables
NUM_COL = 80
NUM_ROW = 336

datDict = { "selftrigger"   : [("OccupancyMap-0", "#Hit"),],
            "noisescan"     : [("NoiseOccupancy","NoiseOccupancy"), ("NoiseMask", "NoiseMask")],
            "totscan"       : [("MeanTotMap", "Mean[ToT]"),         ("SigmaTotMap", "Sigma[ToT]")],
            "thresholdscan" : [("ThresholdMap", "Threshold[e]"),    ("NoiseMap", "Noise[e]")],
            "digitalscan"   : [("OccupancyMap", "Occupancy"),       ("EnMask", "EnMask")],
            "analogscan"    : [("OccupancyMap", "Occupancy"),       ("EnMask", "EnMask")]}

def drawScan(scan_type, num_scan, log, Max, map_list):
    if int(num_scan) < 0 : raise ValueError("Invalid scan number")

    ROOT.gROOT.SetBatch()

    if os.path.isfile( "{}/parameter.json".format( JSON_DIR ) ) :
        filePath = "{}/parameter.json".format( JSON_DIR )
    else :
        filePath = "{}/parameter_default.json".format( JSON_DIR )
    with open( filePath, 'r' ) as f : 
        dataJson = json.load( f )
    with open( "{}/parameter_default.json".format( JSON_DIR ), 'r' ) as f : 
        defaultJson = json.load( f )

############
# Main loop
    #num_plot = []

    for map_type in datDict[scan_type]:
        if map_list[map_type[0]]: 

            if Max == 0 : 
                h1d_max=int(defaultJson[scan_type][map_type[0]][0])
            else :
                h1d_max=int(Max)
            if len(defaultJson[scan_type][map_type[0]])==3 :
                h1d_bin=int(defaultJson[scan_type][map_type[0]][2])
            else :
                h1d_bin=h1d_max

            h1 = ROOT.TH1D(map_type[0]+"_Dist_"+num_scan,
                           map_type[0]+"_Dist_"+num_scan+";"+map_type[1],
                           h1d_bin, 0, h1d_max)
        
            h2 = ROOT.TH2D(map_type[0]+"_"+num_scan,
                           map_type[0]+"_"+num_scan+";Column;Row",
                           NUM_COL*2, 0.5, NUM_COL*2+0.5, NUM_ROW*2, 0.5, NUM_ROW*2+0.5)
        
            # Chip loop
            for i in range(4) :
        
                # Open Files
                filename = DAT_DIR+"/"+num_scan+"_chipId"+str(i+1)+"_"+map_type[0]+".dat"
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
                #os.remove(filename)
        
            path_dir = PLOT_DIR + "/" + scan_type
            PH.outDir = path_dir

    
            path_plot = num_scan + "_" +  map_type[0]
            Plot.Plot1D_fromHistos(h1, log, path_plot+"_1", "#Ch.", "histo", h1d_max)
            Plot.Plot2D_fromHistos(h2, log, path_plot+"_2", map_type[1], h1d_max)

            dataJson[scan_type][map_type[0]] = [int(h2.GetBinContent(h2.GetMaximumBin())),log]
            dataJson[scan_type][map_type[0]] = [int(h1d_max),log]

    fileName = "{}/parameter.json".format( JSON_DIR )
    with open( fileName, 'w' ) as f :
        json.dump( dataJson, f, indent=4 )
 
