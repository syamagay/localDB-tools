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
        files = glob.glob( '{0}/{1}/dat/*{2}.dat'.format( TMP_DIR, str(session.get('uuid')), mapType ))

        if session['plotList'][mapType]['chips']==1 : cnt = 1
        else :                                        cnt = 2

        zmax = 0
        entries = []
        for i,filename in enumerate( files ) :
            for txt in filename.split( "/" ) :
                if "chipId" in txt : chipId = int( txt.split("_")[0][6] ) - 1
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
                                if   chipId==0 or chipId==1 : row = int(histoPar["yrange"][0])-1
                                elif chipId==2 or chipId==3 : row = int(histoPar["yrange"][0])
                        if not j<len(par) :
                            words = readline.split()

                            if cnt==1 : col = 0
                            else :      
                                if   chipId==0 : col = int(histoPar["xrange"][0])-1
                                elif chipId==1 : col = int(histoPar["xrange"][0])*2-1
                                elif chipId==2 : col = 0
                                elif chipId==3 : col = int(histoPar["xrange"][0])

                            for k in range( int(histoPar["xrange"][0]) ) :
                                entries.append( words[k] )
                                h2.SetBinContent( col+1, row+1, float(words[k]) )
                                if zmax<float(words[k]) : zmax = float(words[k])
                                if cnt == 1 : col = col + 1
                                else : 
                                    if   chipId==0 or chipId==1 : col = col - 1
                                    elif chipId==2 or chipId==3 : col = col + 1
       
                            if cnt==1 : row = row + 1
                            else :     
                               if   chipId==0 or chipId==1 : row = row - 1
                               elif chipId==2 or chipId==3 : row = row + 1


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
        files = glob.glob( '{0}/localuser/dat/*{1}.dat'.format( TMP_DIR, mapType ))

        if plotList[mapType]['chips']==1 : cnt = 1
        else :                                        cnt = 2

        zmax = 0
        entries = []
        for i,filename in enumerate( files ) :
            for txt in filename.split( "/" ) :
                if "chipId" in txt : chipId = int( txt.split("_")[0][6] ) - 1
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
                                if   chipId==0 or chipId==1 : row = int(histoPar["yrange"][0])-1
                                elif chipId==2 or chipId==3 : row = int(histoPar["yrange"][0])
                        if not j<len(par) :
                            words = readline.split()

                            if cnt==1 : col = 0
                            else :      
                                if   chipId==0 : col = int(histoPar["xrange"][0])-1
                                elif chipId==1 : col = int(histoPar["xrange"][0])*2-1
                                elif chipId==2 : col = 0
                                elif chipId==3 : col = int(histoPar["xrange"][0])

                            for k in range( int(histoPar["xrange"][0]) ) :
                                entries.append( words[k] )
                                h2.SetBinContent( col+1, row+1, float(words[k]) )
                                if zmax<float(words[k]) : zmax = float(words[k])
                                if cnt == 1 : col = col + 1
                                else : 
                                    if   chipId==0 or chipId==1 : col = col - 1
                                    elif chipId==2 or chipId==3 : col = col + 1
       
                            if cnt==1 : row = row + 1
                            else :     
                               if   chipId==0 or chipId==1 : row = row - 1
                               elif chipId==2 or chipId==3 : row = row + 1


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

