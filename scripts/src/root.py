###############
### Osaka Univ.
### K. Yajima
###############

import sys, os, pwd, glob, json

# path to directory
USER=pwd.getpwuid( os.geteuid() ).pw_name
USER_DIR = '/tmp/{}'.format( USER ) 
DAT_DIR  = '{}/dat'.format( USER_DIR )
PLOT_DIR = '{}/result'.format( USER_DIR )
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append( SCRIPT_DIR + "/src/PlotTools" )

from PlotHelpers import gHelper as PH
import PlotFromHistos.SimplePlots as Plot

import ROOT
from flask import session  # use Flask scheme

def drawScan( scan_type, num_scan, map_list ):

    ROOT.gROOT.SetBatch()

    json_file = SCRIPT_DIR + "/json/parameter_default.json"
    with open(json_file,'r') as f : json_data = json.load(f)
    scan_parameter = json_data.get(scan_type,{})

    value = ["histoType","mapType","xaxis","yaxis","zaxis","xrange","yrange","zrange"]
    for map_type in map_list :
        histo_value = {}
        files = glob.glob(DAT_DIR+"/"+str(session.get('uuid'))+"_"+str(num_scan)+"*"+map_type+".dat")
        if map_list[map_type] == 1 : cnt = 1
        else :                       cnt = 2
        zmax = 0
        word_entry = []
        for i,filename in enumerate(files) :
            for a in filename.split("_") :
                if "chipId" in a : chipId = int(a[6]) - 1
            with open(filename) as f :      
                readlines = f.readlines()
                for j, readline in enumerate(readlines) :
                    if j < len(value) :
                        if i == 0 : histo_value.update({ value[j] : readline.split() }) 
                    else :
                        words = readline.split()
                        if histo_value["histoType"][0] == "Histo2d" :
                            if j == len(value) :
                                if cnt == 1 :
                                    row = 0 
                                else :
                                    if   chipId==0 or chipId==1 : row = int(histo_value["yrange"][0])-1
                                    elif chipId==2 or chipId==3 : row = int(histo_value["yrange"][0])

                                if i == 0 :
                                    h2 = ROOT.TH2D(map_type+"_"+num_scan,
                                                   map_type+"_"+num_scan+";"+" ".join(histo_value["xaxis"])+";"+" ".join(histo_value["yaxis"])+";"+" ".join(histo_value["zaxis"]),
                                                   int(histo_value["xrange"][0])*cnt, float(histo_value["xrange"][1]), float(histo_value["xrange"][0])*cnt+0.5,
                                                   int(histo_value["yrange"][0])*cnt, float(histo_value["yrange"][1]), float(histo_value["yrange"][0])*cnt+0.5)

                            if cnt == 1 :
                                col = 0
                            else :
                                if   chipId==0 : col = int(histo_value["xrange"][0])-1
                                elif chipId==1 : col = int(histo_value["xrange"][0])*2-1
                                elif chipId==2 : col = 0
                                elif chipId==3 : col = int(histo_value["xrange"][0])

                            for k in range(int(histo_value["xrange"][0])) :
                                word_entry.append(words[k])
                                h2.SetBinContent(col+1, row+1, float(words[k]))
                                if zmax < float(words[k]) : zmax = float(words[k])
                                if cnt == 1 :
                                    col = col + 1
                                else :
                                    if   chipId==0 or chipId==1 : col = col - 1
                                    elif chipId==2 or chipId==3 : col = col + 1
       
                            if cnt == 1 :
                                row = row + 1
                            else :
                                if   chipId==0 or chipId==1 : row = row - 1
                                elif chipId==2 or chipId==3 : row = row + 1


        if histo_value["histoType"][0] == "Histo2d" :
            parameter = scan_parameter.get(map_type,[])
            if session['plot_list'].get(map_type) :
                h1d_min = int(session['plot_list'][map_type]['min'])
                h1d_max = int(session['plot_list'][map_type]['max'])
                h1d_bin = int(session['plot_list'][map_type]['bin'])
                h1d_log = bool(session['plot_list'][map_type]['log'])
            elif parameter :
                h1d_min = int(parameter[0])
                h1d_max = int(parameter[1])
                h1d_bin = int(parameter[2])
                h1d_log = bool(parameter[3])
            else :
                h1d_min = int(0)
                h1d_max = int(2*zmax)
                h1d_bin = int(h1d_max)
                h1d_log = False 

            h1 = ROOT.TH1D(map_type+"_Dist_"+num_scan,
                           map_type+"_Dist_"+num_scan+";"+" ".join(histo_value["zaxis"])+";#Ch",
                           h1d_bin, h1d_min, h1d_max )

            for word in word_entry : 
                h1.Fill(float(word))
 
            path_dir = PLOT_DIR + "/" + str(session.get('uuid'))
            PH.outDir = path_dir
    
            path_plot = num_scan + "_" +  map_type
            Plot.Plot1D_fromHistos(h1, h1d_log, path_plot+"_1", "#Ch.", "histo", h1d_min, h1d_max)
            Plot.Plot2D_fromHistos(h2, h1d_log, path_plot+"_2", " ".join(histo_value["zaxis"]), h1d_min, h1d_max)

            session['plot_list'].update({ map_type : { "min" : h1d_min, "max" : h1d_max, "bin" : h1d_bin, "log" : h1d_log } })

def setparameter(scan_type, map_type) :
    testname = SCRIPT_DIR + "/json/test.json"
    test = { "testscan" : {
             "testtype1" : [ 2, False ],
             "testtype2" : [ 100, True ] }}
    with open(testname,'r') as f :      
        json_data = json.load(f)
        scan_key = test.keys()
        for scan in scan_key :
            if not scan in json_data :
                json_data.update(test)
    with open(testname,'w') as f :      
        json.dump(json_data,f,indent=4)


