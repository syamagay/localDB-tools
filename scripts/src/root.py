###############
### Osaka Univ.
### K. Yajima
###############

import sys, os, pwd, glob, json

# path to directory
TMP_DIR = '/tmp/{}'.format( pwd.getpwuid( os.geteuid() ).pw_name ) 
JSON_DIR = '{}/json'.format( TMP_DIR )
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append( SCRIPT_DIR + "/src/PlotTools" )

from PlotHelpers import gHelper as PH
import PlotFromHistos.SimplePlots as Plot

import ROOT
from flask import session  # use Flask scheme

def drawScan( testType ):

    ROOT.gROOT.SetBatch()

    jsonFile = JSON_DIR + "/{}_parameter.json".format(session.get('uuid'))
    with open( jsonFile, 'r' ) as f : jsonData = json.load( f )
    jsonPar = jsonData.get( testType, {} )

    par = ["histoType","mapType","xaxis","yaxis","zaxis","xrange","yrange","zrange"]

    for mapType in session.get( 'plotList' ) :

        if not session['plotList'][mapType]['draw'] : continue

        histoPar = {}
        #files = glob.glob( '{0}/{1}/dat/*{2}.dat'.format( TMP_DIR, str(session.get('uuid')), mapType ))
        files = glob.glob( '{0}/{1}/dat/{2}*.dat'.format( TMP_DIR, str(session.get('uuid')), mapType ))

        if session['plotList'][mapType]['chips']==1 : cnt = 1
        else :                                        cnt = 2

        zmax = 0
        entries = []
        for i,filename in enumerate( files ) :
            for txt in filename.split( "/" ) :
                if "chipId" in txt : chipId = int( txt.split(".")[0].split("chipId")[1] )
            with open( filename ) as f :      
                readlines = f.readlines()
                if not readlines[0].split()[0] == "Histo2d" :
                    session['plotList'][mapType].update({ "HistoType" : 1, "draw" : False })
                else :
                    for j, readline in enumerate(readlines) :
                        if j<len(par) and i==0 : histoPar.update({ par[j] : readline.split() }) 
                        if j==len(par) :
                            if i==0 :
                                h2 = ROOT.TH2D( mapType,
                                                mapType+";"+" ".join(histoPar["xaxis"])+";"+" ".join(histoPar["yaxis"])+";"+" ".join(histoPar["zaxis"]),
                                                int(histoPar["xrange"][0])*cnt, float(histoPar["xrange"][1]), float(histoPar["xrange"][0])*cnt+0.5,
                                                int(histoPar["yrange"][0])*cnt, float(histoPar["yrange"][1]), float(histoPar["yrange"][0])*cnt+0.5 )
                            if cnt==1 : row = 0 
                            else :
                                if   chipId==1 or chipId==2 : row = int(histoPar["yrange"][0])-1
                                elif chipId==3 or chipId==4 : row = int(histoPar["yrange"][0])
                        if not j<len(par) :
                            words = readline.split()

                            if cnt==1 : col = 0
                            else :      
                                if   chipId==1 : col = int(histoPar["xrange"][0])-1
                                elif chipId==2 : col = int(histoPar["xrange"][0])*2-1
                                elif chipId==3 : col = 0
                                elif chipId==4 : col = int(histoPar["xrange"][0])

                            for k in range( int(histoPar["xrange"][0]) ) :
                                entries.append( words[k] )
                                h2.SetBinContent( col+1, row+1, float(words[k]) )
                                if zmax<float(words[k]) : zmax = float(words[k])
                                if cnt == 1 : col = col + 1
                                else : 
                                    if   chipId==1 or chipId==2 : col = col - 1
                                    elif chipId==3 or chipId==4 : col = col + 1
       
                            if cnt==1 : row = row + 1
                            else :     
                               if   chipId==1 or chipId==2 : row = row - 1
                               elif chipId==3 or chipId==4 : row = row + 1


        if histoPar :
            parameter = jsonPar.get( mapType.split("-")[0], [] )

            if session['plotList'][mapType].get('parameter') :
                h1d_min =  int(session['plotList'][mapType]['parameter']['min'])
                h1d_max =  int(session['plotList'][mapType]['parameter']['max'])
                h1d_bin =  int(session['plotList'][mapType]['parameter']['bin'])
                h1d_log = bool(session['plotList'][mapType]['parameter']['log'])
            elif len(parameter)==4 :
                h1d_min =  int(parameter[0])
                h1d_max =  int(parameter[1])
                h1d_bin =  int(parameter[2])
                h1d_log = bool(parameter[3])
            else :
                h1d_min = int(0)
                h1d_max = int(2*zmax)
                h1d_bin = int(h1d_max)
                h1d_log = False 

            h1 = ROOT.TH1D( mapType+"_Dist",
                            mapType+"_Dist"+";"+" ".join(histoPar["zaxis"])+";#Ch",
                            h1d_bin, h1d_min, h1d_max )

            for word in entries : 
                h1.Fill( float(word) )
 
            path_dir = TMP_DIR + "/" + str(session.get('uuid')) + "/plot"
            PH.outDir = path_dir
    
            path_plot = testType + "_" + mapType
            Plot.Plot1D_fromHistos( h1, 
                                    h1d_log, 
                                    path_plot+"_1", 
                                    "#Ch.", 
                                    "histo", 
                                    h1d_min, 
                                    h1d_max 
                                  )
            Plot.Plot2D_fromHistos( h2, 
                                    h1d_log, 
                                    path_plot+"_2", 
                                    " ".join(histoPar["zaxis"]), 
                                    h1d_min, 
                                    h1d_max 
                                  )

            session['plotList'][mapType].update({ "parameter" : { "min" : h1d_min, "max" : h1d_max, "bin" : h1d_bin, "log" : h1d_log }, "draw" : False, "HistoType" : 2 })

def localDrawScan( testType, plotList ):

    ROOT.gROOT.SetBatch()

    jsonFile = JSON_DIR + "/localuser_parameter.json"
    with open( jsonFile, 'r' ) as f : jsonData = json.load( f )
    jsonPar = jsonData.get( testType, {} )

    par = ["histoType","mapType","xaxis","yaxis","zaxis","xrange","yrange","zrange"]

    for mapType in plotList :

        if not plotList[mapType]['draw'] : continue

        histoPar = {}
        #files = glob.glob( '{0}/localuser/dat/*{1}.dat'.format( TMP_DIR, mapType ))
        files = glob.glob( '{0}/localuser/dat/{1}*.dat'.format( TMP_DIR, mapType ))

        if plotList[mapType]['chips']==1 : cnt = 1
        else :                                        cnt = 2

        zmax = 0
        entries = []
        for i,filename in enumerate( files ) :
            for txt in filename.split( "/" ) :
                if "chipId" in txt : chipId = int( txt.split(".")[0].split("chipId")[1] ) 
            with open( filename ) as f :      
                readlines = f.readlines()
                if not readlines[0].split()[0] == "Histo2d" :
                    plotList[mapType].update({ "HistoType" : 1, "draw" : False })
                else :
                    for j, readline in enumerate(readlines) :
                        if j<len(par) and i==0 : histoPar.update({ par[j] : readline.split() }) 
                        if j==len(par) :
                            if i==0 :
                                h2 = ROOT.TH2D( mapType,
                                                mapType+";"+" ".join(histoPar["xaxis"])+";"+" ".join(histoPar["yaxis"])+";"+" ".join(histoPar["zaxis"]),
                                                int(histoPar["xrange"][0])*cnt, float(histoPar["xrange"][1]), float(histoPar["xrange"][0])*cnt+0.5,
                                                int(histoPar["yrange"][0])*cnt, float(histoPar["yrange"][1]), float(histoPar["yrange"][0])*cnt+0.5 )
                            if cnt==1 : row = 0 
                            else :
                                if   chipId==1 or chipId==2 : row = int(histoPar["yrange"][0])-1
                                elif chipId==3 or chipId==4 : row = int(histoPar["yrange"][0])
                        if not j<len(par) :
                            words = readline.split()

                            if cnt==1 : col = 0
                            else :      
                                if   chipId==1 : col = int(histoPar["xrange"][0])-1
                                elif chipId==2 : col = int(histoPar["xrange"][0])*2-1
                                elif chipId==3 : col = 0
                                elif chipId==4 : col = int(histoPar["xrange"][0])

                            for k in range( int(histoPar["xrange"][0]) ) :
                                entries.append( words[k] )
                                h2.SetBinContent( col+1, row+1, float(words[k]) )
                                if zmax<float(words[k]) : zmax = float(words[k])
                                if cnt == 1 : col = col + 1
                                else : 
                                    if   chipId==1 or chipId==2 : col = col - 1
                                    elif chipId==3 or chipId==4 : col = col + 1
       
                            if cnt==1 : row = row + 1
                            else :     
                               if   chipId==1 or chipId==2 : row = row - 1
                               elif chipId==3 or chipId==4 : row = row + 1


        if histoPar :
            parameter = jsonPar.get( mapType.split("-")[0], [] )

            if plotList[mapType].get('parameter') :
                h1d_min =  int(plotList[mapType]['parameter']['min'])
                h1d_max =  int(plotList[mapType]['parameter']['max'])
                h1d_bin =  int(plotList[mapType]['parameter']['bin'])
                h1d_log = bool(plotList[mapType]['parameter']['log'])
            elif len(parameter)==4 :
                h1d_min =  int(parameter[0])
                h1d_max =  int(parameter[1])
                h1d_bin =  int(parameter[2])
                h1d_log = bool(parameter[3])
            else :
                h1d_min = int(0)
                h1d_max = int(2*zmax)
                h1d_bin = int(h1d_max)
                h1d_log = False 

            h1 = ROOT.TH1D( mapType+"_Dist",
                            mapType+"_Dist"+";"+" ".join(histoPar["zaxis"])+";#Ch",
                            h1d_bin, h1d_min, h1d_max )

            for word in entries : 
                h1.Fill( float(word) )
 
            path_dir = TMP_DIR + "/localuser/plot"
            PH.outDir = path_dir
    
            path_plot = testType + "_" + mapType
            Plot.Plot1D_fromHistos( h1, 
                                    h1d_log, 
                                    path_plot+"_1", 
                                    "#Ch.", 
                                    "histo", 
                                    h1d_min, 
                                    h1d_max 
                                  )
            Plot.Plot2D_fromHistos( h2, 
                                    h1d_log, 
                                    path_plot+"_2", 
                                    " ".join(histoPar["zaxis"]), 
                                    h1d_min, 
                                    h1d_max 
                                  )

            plotList[mapType].update({ "parameter" : { "min" : h1d_min, "max" : h1d_max, "bin" : h1d_bin, "log" : h1d_log }, "draw" : False, "HistoType" : 2 })

def setParameter(testType, mapType) :

    inputData = {}
    inputData.update({ mapType.split("-")[0] : [ session['plotList'][mapType]['parameter']['min'],
                                                 session['plotList'][mapType]['parameter']['max'],
                                                 session['plotList'][mapType]['parameter']['bin'],
                                                 session['plotList'][mapType]['parameter']['log'] ] })

    filename = JSON_DIR + "/{}_parameter.json".format(session.get('uuid'))

    with open(filename,'r') as f :      
        jsonData = json.load(f)
        if not testType in jsonData    : jsonData.update({ testType : { "Summary" : False }})
        elif not "Summary" in jsonData : jsonData[testType].update({ "Summary" : False })
        jsonData[testType].update( inputData )

    with open(filename,'w') as f : json.dump( jsonData, f, indent=4 )

def countPix( testType, serialNumber ) :

    #print("{0} ->  [ {1} ]".format(serialNumber,testType))

    ROOT.gROOT.SetBatch()
    
    thr = 0.98
    thr_sigma = 5

    par = ["histoType", "mapType", "xaxis", "yaxis", "zaxis", "xrange", "yrange", "zrange"]

    scanList = { "selftrigger"   : { "mapType" : "OccupancyMap-0", "criterion" : "more than one hit", "threshold" : 1 },
                 "noisescan"     : { "mapType" : "NoiseMask",      "criterion" : "noise mask = 1",    "threshold" : 1 },
                 "totscan"       : { "mapType" : "MeanTotMap",     "criterion" : "8 < mean tot < 11", "mean" : { 1:9.5, 2:9.5, 3:9.5, 4:9.5 },     "sigma" : { 1:1.5, 2:1.5, 3:1.5, 4:1.5 } },
                 "thresholdscan" : { "mapType" : "ThresholdMap",   "criterion" : "within 5 sigma",    "mean" : { 1:0,   2:0,   3:0,   4:0   },     "sigma" : { 1:0,   2:0,   3:0,   4:0   } },
                 "digitalscan"   : { "mapType" : "EnMask",         "criterion" : "enable mask = 1",   "threshold" : 1 },
                 "analogscan"    : { "mapType" : "EnMask",         "criterion" : "enable mask = 1",   "threshold" : 1 }}

    mapType = scanList[testType]["mapType"]
    
    histoPar = {}
    #files = glob.glob( '{0}/{1}/dat/*{2}.dat'.format( TMP_DIR, str(session.get('uuid')), mapType ))
    files = glob.glob( '{0}/{1}/dat/{2}*.dat'.format( TMP_DIR, str(session.get('uuid')), mapType ))

    scorePar = {}
#    scorePar = { "selftrigger"   : { "totPix" : 0, "countPix" : 0, "criterion" : "more than one hit", "parameter" : "" } 
#                 "noisescan"     : { "totPix" : 0, "countPix" : 0, "criterion" : "noise mask = 1",    "parameter" : "" } 
#                 "totscan"       : { "totPix" : 0, "countPix" : 0, "criterion" : "8 < mean tot < 11", "parameter" : "" } 
#                 "thresholdscan" : { "totPix" : 0, "countPix" : 0, "criterion" : "within 5 sigma",    "parameter" : "" } 
#                 "digitalscan"   : { "totPix" : 0, "countPix" : 0, "criterion" : "enable mask = 1",   "parameter" : "" } 
#                 "analogscan"    : { "totPix" : 0, "countPix" : 0, "criterion" : "enable mask = 1",   "parameter" : "" } 

    module_cnt = 0
    entries = {}
    scorePar.update({ "module" : {} })
    for i,filename in enumerate( files ) :
        for txt in filename.split( "/" ) :
            if "chipId" in txt : chipId = int( txt.split(".")[0].split("chipId")[1] ) 
        with open( filename ) as f :      
            scorePar.update({ chipId : {} })
            entries.update({ chipId : [] })
            readlines = f.readlines()
            if readlines[0].split() != ['Histo2d'] : continue
            for j,readline in enumerate(readlines) :
                if j<len(par) and i==0 : histoPar.update({ par[j] : readline.split() }) 
                if not j<len(par) :
                    words = readline.split()
                    for k in range( int(histoPar["xrange"][0]) ) :
                        entries[chipId].append( words[k] )

    if histoPar == {}:
        for i in entries :
            scorePar[i].update({ "totPix" : 0, "countPix" : 0, "criterion" : scanList[testType]["criterion"], "score" : 0 })
        scorePar["module"].update({ "totPix" : 0, "countPix" : 0, "criterion" : scanList[testType]["criterion"], "score" : 0 })
        return scorePar

    if testType == "thresholdscan" :
        jsonFile = JSON_DIR + "/{}_parameter.json".format(session.get('uuid'))
        with open( jsonFile, 'r' ) as f : jsonData = json.load( f )
        jsonPar = jsonData.get( testType, {} )
        parameter = jsonPar.get( mapType )

        h1d_min =  int(parameter[0])
        h1d_max =  int(parameter[1])
        h1d_bin =  int(parameter[2])
        h1d_log = bool(parameter[3])

        for i in entries :
            h1 = ROOT.TH1D( mapType+"_chipId"+str(i),
                            mapType+"_chipId"+str(i)+";"+" ".join(histoPar["zaxis"])+";#Ch",
                            h1d_bin, h1d_min, h1d_max )
            f1 = ROOT.TF1( 'f1', "gaus", 500, h1d_max )
            for word in entries[i] : 
                h1.Fill( float(word) )
            h1.Fit(f1,"R")
            h1.Fit(f1,"","",f1.GetParameter(1)-3*f1.GetParameter(2),f1.GetParameter(1)+3*f1.GetParameter(2))
            par = f1.GetParameters()  
            scanList[testType]["mean"][i] = par[1]
            scanList[testType]["sigma"][i] = thr_sigma*par[2]
            scorePar[i].update({ "parameter" : "mean : {0:.2f}, sigma : {1:.2f}".format( par[1], par[2] ) })

    if testType == "totscan" :
        jsonFile = JSON_DIR + "/{}_parameter.json".format(session.get('uuid'))
        with open( jsonFile, 'r' ) as f : jsonData = json.load( f )
        jsonPar = jsonData.get( testType, {} )
        parameter = jsonPar.get( mapType )

        h1d_min =  int(parameter[0])
        h1d_max =  int(parameter[1])
        h1d_bin =  int(parameter[2])
        h1d_log = bool(parameter[3])

        for i in entries :
            h1 = ROOT.TH1D( mapType+"_chipId"+str(i),
                            mapType+"_chipId"+str(i)+";"+" ".join(histoPar["zaxis"])+";#Ch",
                            h1d_bin, h1d_min, h1d_max )
            for word in entries[i] : 
                h1.Fill( float(word) )
            scorePar[i].update({ "parameter" : "average : {0:.2f}, rms : {1:.2f}".format( h1.GetMean(), h1.GetRMS() ) })

    for i in entries :
        cnt = 0
        for word in entries[i] :
            if testType == "totscan" or testType == "thresholdscan" :
                if scanList[testType]["mean"][i]-scanList[testType]["sigma"][i] <= float(word) <= scanList[testType]["mean"][i]+scanList[testType]["sigma"][i] : cnt+=1
            else :
                if scanList[testType]["threshold"] <= float(word) : cnt+=1

        pix_num = float(histoPar["xrange"][0]) * float(histoPar["yrange"][0])
        scorePar[i].update({ "totPix" : int(pix_num), "countPix" : cnt, "criterion" : scanList[testType]["criterion"] })
        if cnt/pix_num > thr : scorePar[i].update({ "score" : 1 })
        else :                 scorePar[i].update({ "score" : 0 })
        module_cnt += cnt

    pix_num = float(histoPar["xrange"][0]) * float(histoPar["yrange"][0]) * float(session['plotList'][scanList[testType]["mapType"]]["chips"])
    scorePar["module"].update({ "totPix" : int(pix_num), "countPix" : module_cnt, "criterion" : scanList[testType]["criterion"] })
    if module_cnt/pix_num > thr : scorePar["module"].update({ "score" : 1 })
    else :                        scorePar["module"].update({ "score" : 0 })
    
    return scorePar
