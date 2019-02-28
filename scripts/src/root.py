###############
### Osaka Univ.
### K. Yajima
###############

import sys
import os
import pwd
import glob
import json
import ROOT

# path to directory
TMP_DIR    = '/tmp/{}'.format(pwd.getpwuid(os.geteuid()).pw_name) 
JSON_DIR   = '{}/json'.format(TMP_DIR)

sys.path.append( os.path.dirname(os.path.abspath(__file__)) + '/PlotTools' )
from PlotFromHistos import SimplePlots as Plot
from PlotHelpers    import gHelper as PH

uuid = 'localuser'
# keys of parameters
_par2d = [ 'histoType', 
           'mapType', 
           'xaxis', 
           'yaxis', 
           'zaxis', 
           'xrange', 
           'yrange', 
           'outrange' ]

_par1d = [ 'histoType', 
           'mapType', 
           'xaxis', 
           'yaxis', 
           'zaxis', 
           'xrange', 
           'outrange' ]

# draw map plots for the test 
def drawScan(testType, plotList):

    ROOT.gROOT.SetBatch()
    # scale: { chips: [ xrange, yrange ] }
    scale = { 1: [ 1, 1 ],
              2: [ 2, 1 ],
              3: [ 2, 2 ],
              4: [ 2, 2 ] }

    # get parameters from json
    jFile = '{0}/{1}_parameter.json'.format( JSON_DIR, uuid )
    if not os.path.isfile( jFile ):
        jFile_default = '{}/json/parameter_default.json'.format( os.path.dirname(os.path.dirname(os.path.abspath(__file__))) )
        with open(jFile_default, 'r') as f: jData_default = json.load(f)
        with open(jFile,         'w') as f: json.dump( jData_default, f, indent=4 )
    with open(jFile, 'r') as f: jData = json.load(f)
    jPar = jData.get(testType, {})

    # make plots for each map type
    for mapType in plotList:

        if not plotList[mapType]['draw']: continue

        chips  = plotList[mapType]['chips']

        zMax   = 0
        values = []

        histo_par2d={}
        for chipId in chips:

            filename = '{0}/{1}/dat/{2}_chipId{3}.dat'.format( TMP_DIR, uuid, mapType, chipId )

            if not os.path.isfile(filename): continue
            with open(filename) as f:
                for line, readline in enumerate(f.readlines()):
                    if line == 0:
                        # histo 1D
                        if readline.split()[0]=='Histo1d':
                            plotList[mapType].update({'HistoType': 1, 'draw': False})
                            break
                        # histo 3D
                        elif readline.split()[0]=='Histo3d':
                            plotList[mapType].update({'HistoType': 3, 'draw': False})
                            break
                        elif not 'Histo' in readline.split()[0]:
                            plotList[mapType].update({'HistoType': None, 'draw': False})
                            break

                    # histo 2D
                    if line<len(_par2d) and not 'h2' in locals(): 
                        histo_par2d.update({_par2d[line]: readline.split()}) 

                    if line==len(_par2d):
                        if not 'h2' in locals():
                            h2 = ROOT.TH2D( 
                                mapType,
                                '{0};{1};{2};{3}'.format( mapType, ' '.join(histo_par2d['xaxis']), ' '.join(histo_par2d['yaxis']), ' '.join(histo_par2d['zaxis']) ),
                                int(histo_par2d['xrange'][0])*scale[len(chips)][0], float(histo_par2d['xrange'][1]), float(histo_par2d['xrange'][0])*scale[len(chips)][0]+0.5,
                                int(histo_par2d['yrange'][0])*scale[len(chips)][1], float(histo_par2d['yrange'][1]), float(histo_par2d['yrange'][0])*scale[len(chips)][1]+0.5 
                            )

                        # row
                        if   len(chips) ==1: row = 0 
                        elif chipId=='1': row = int(histo_par2d['yrange'][0])-1 
                        elif chipId=='2': row = int(histo_par2d['yrange'][0])-1
                        elif chipId=='3': row = int(histo_par2d['yrange'][0])
                        elif chipId=='4': row = int(histo_par2d['yrange'][0])

                    if not line<len(_par2d):
                        data = readline.split()

                        # col
                        if   len(chips) ==1: col = 0
                        elif chipId=='1': col = int(histo_par2d['xrange'][0])-1
                        elif chipId=='2': col = int(histo_par2d['xrange'][0])*2-1
                        elif chipId=='3': col = 0
                        elif chipId=='4': col = int(histo_par2d['xrange'][0])

                        for value in data:
                            values.append(value)
                            h2.SetBinContent(col+1, row+1, float(value))
                            if zMax<float(value): zMax = float(value)

                            # col
                            if   len(chips) ==1: col = col + 1
                            elif chipId=='1': col = col - 1 
                            elif chipId=='2': col = col - 1
                            elif chipId=='3': col = col + 1 
                            elif chipId=='4': col = col + 1
       
                        # row
                        if   len(chips) ==1: row = row + 1
                        elif chipId=='1': row = row - 1 
                        elif chipId=='2': row = row - 1
                        elif chipId=='3': row = row + 1 
                        elif chipId=='4': row = row + 1


        if 'h2' in locals():
            parameter = jPar.get(mapType.split('-')[0], [])

            if plotList[mapType].get('parameter'):
                min_ =  int(plotList[mapType]['parameter']['min'])
                max_ =  int(plotList[mapType]['parameter']['max'])
                bin_ =  int(plotList[mapType]['parameter']['bin'])
                log_ = bool(plotList[mapType]['parameter']['log'])
            elif len(parameter)==4:
                min_ =  int(parameter[0])
                max_ =  int(parameter[1])
                bin_ =  int(parameter[2])
                log_ = bool(parameter[3])
            else:
                min_ = int(0)
                max_ = int(2*zMax)
                bin_ = int(max_)
                log_ = False 

            h1 = ROOT.TH1D( 
                mapType+'_Dist',
                '{0}_Dist;{1};#Ch'.format(mapType, ' '.join(histo_par2d['zaxis'])),
                bin_, min_, max_ 
            )

            for value in values: 
                h1.Fill(float(value))
 
            PH.outDir = '{0}/{1}/plot'.format(TMP_DIR, uuid)
    
            # output histos 
            path_plot = '{0}_{1}'.format(testType, mapType)
            Plot.Plot1D_fromHistos( 
                h1,
                log_,
                path_plot+'_1',
                '#Ch.',
                'histo',
                min_,
                max_
            )
            Plot.Plot2D_fromHistos( 
                h2, 
                log_, 
                path_plot+'_2', 
                ' '.join(histo_par2d['zaxis']), 
                min_, 
                max_ 
            )
            # delete 
            del h1
            del h2

            plotList[mapType].update({ 'parameter': { 
                                           'min': min_, 
                                           'max': max_, 
                                           'bin': bin_, 
                                           'log': log_ }, 
                                       'draw': False, 
                                       'HistoType': 2 })

    return plotList

# setting parameters while making plots
def setParameter(testType, mapType, plotList):

    inputData = {}
    inputData.update({ mapType.split('-')[0]: [ 
                           plotList[mapType]['parameter']['min'],
                           plotList[mapType]['parameter']['max'],
                           plotList[mapType]['parameter']['bin'],
                           plotList[mapType]['parameter']['log'] ] 
                     })

    jFile = '{0}/{1}_parameter.json'.format( JSON_DIR, uuid )

    if not os.path.isfile(jFile):
        jFile_default = '{}/json/parameter_default.json'.format( os.path.dirname(os.path.dirname(os.path.abspath(__file__))) )
        with open(jFile_default, 'r') as f: jData_default = json.load(f)
        with open(jFile,      'w') as f: json.dump( jData_default, f, indent=4 )
    with open(jFile,'r') as f:
        jData = json.load(f)
        if not testType in jData: 
            jData.update({testType: {}})
        jData[testType].update( inputData )

    with open(jFile,'w') as f: json.dump( jData, f, indent=4 )

# for grading
# criteria
_scanList = {
            'selftrigger': { 
                'mapType':   'OccupancyMap', 
                'criterion': 'more than one hit', 
                'threshold': 1, 
                'standard': 98
            },
            'std_exttrigger': { 
                'mapType':   'OccupancyMap', 
                'criterion': 'more than one hit', 
                'threshold': 1, 
                'standard': 98
            },
            'noisescan': { 
                'mapType':   'NoiseMask',    
                'criterion': 'noise mask = 1',    
                'threshold': 1, 
                'standard': 98
            },
            'std_noisescan': { 
                'mapType':   'NoiseMask',    
                'criterion': 'noise mask = 1',    
                'threshold': 1, 
                'standard': 98
            },
            'totscan': { 
                'mapType':   'MeanTotMap',   
                'distType':  'MeanTotDist',   
                'criterion': '8 < mean tot < 11', 
                'mean':  { '1':9.5, '2':9.5, '3':9.5, '4':9.5 },
                'sigma': { '1':1.5, '2':1.5, '3':1.5, '4':1.5 }, 
                'standard': 98
            },
            'std_totscan': { 
                'mapType':   'MeanTotMap',   
                'distType':  'MeanTotDist',   
                'criterion': '8 < mean tot < 11', 
                'mean':  { '1':9.5, '2':9.5, '3':9.5, '4':9.5 },
                'sigma': { '1':1.5, '2':1.5, '3':1.5, '4':1.5 }, 
                'standard': 98
            },
            'thresholdscan': { 
                'mapType':   'ThresholdMap', 
                'distType':  'ThresholdDist', 
                'criterion': 'within 5 sigma',
                'mean':  { '1':0,   '2':0,   '3':0,   '4':0   },
                'sigma': { '1':0,   '2':0,   '3':0,   '4':0   }, 
                'standard': 98,
                'scalesigma': 5
            },
            'std_thresholdscan': { 
                'mapType':   'ThresholdMap', 
                'distType':  'ThresholdDist', 
                'criterion': 'within 5 sigma',
                'mean':  { '1':0,   '2':0,   '3':0,   '4':0   },
                'sigma': { '1':0,   '2':0,   '3':0,   '4':0   }, 
                'standard': 98,
                'scalesigma': 5
            },
            'digitalscan': { 
                'mapType':   'EnMask',
                'criterion': 'enable mask = 1',
                'threshold': 1,
                'standard': 98
            },
            'std_digitalscan': { 
                'mapType':   'EnMask',
                'criterion': 'enable mask = 1',
                'threshold': 1,
                'standard': 98
            },
            'analogscan': { 
                'mapType':   'EnMask',       
                'criterion': 'enable mask = 1',   
                'threshold': 1, 
                'standard': 98
            },
            'std_analogscan': { 
                'mapType':   'EnMask',       
                'criterion': 'enable mask = 1',   
                'threshold': 1, 
                'standard': 98
            }
}

def makeDistFromDat(filename):
    histo_par1d = {}
    h1 = None
    with open(filename) as f:      
        for line, readline in enumerate(f.readlines()):
            if line == 0:
                if not 'Histo' in readline.split()[0]:
                    break
            if line<len(_par1d): 
                histo_par1d.update({ _par1d[line]: readline.split() }) 
            if line==len(_par1d): 
                h1 = ROOT.TH1D( 
                    histo_par1d['mapType'][0],
                    '{0};{1};{2}'.format( histo_par1d['mapType'][0], ' '.join(histo_par1d['xaxis']), ' '.join(histo_par1d['yaxis']) ),
                    int(histo_par1d['xrange'][0]), float(histo_par1d['xrange'][1]), float(histo_par1d['xrange'][2])
                )
                data = readline.split()
                for bin_, value in enumerate(data):
                    h1.SetBinContent( bin_+1, float(value) )
    return h1

def countPix(testType, plotList):

    ROOT.gROOT.SetBatch()
    
    countList = {}
    scoreList = {}
    parameters = {}
    parameter = ''
    
    if not testType in _scanList.keys(): return scoreList

    for type_ in plotList:
        if _scanList[testType]['mapType'] in type_: 
            mapType = type_
        if 'distType' in _scanList[testType]:
            if _scanList[testType]['distType'] in type_: 
                distType = type_

    if not 'mapType' in locals(): return scoreList

    # count enabled pixels
    chips = plotList[mapType]['chips']
    module_cnt = 0
    for chipId in chips:
        cnt=0
        filename = '{0}/{1}/dat/{2}_chipId{3}.dat'.format( TMP_DIR, uuid, mapType, chipId )
        if not os.path.isfile(filename): continue

        # map
        with open(filename) as f:      
            for line, readline in enumerate(f.readlines()):
                if line == 0:
                    if not 'Histo' in readline.split()[0]:
                        break
                if line<len(_par2d): 
                    if _par2d[line]=='xrange': 
                        Col = float(readline.split()[0])
                    if _par2d[line]=='yrange': 
                        Row = float(readline.split()[0])
                        if 'thresholdscan' in testType or 'totscan' in testType: break
                else:
                    data = readline.split()
                    if 'selftrigger' in testType or 'std_exttrigger' in testType:
                        for value in data:
                            if _scanList[testType]['threshold'] <= float(value):
                                cnt+=1
                    else:
                        cnt+=data.count('1')

        if not 'Col' in locals() or not 'Row' in locals(): break

        # threshold scan
        if 'thresholdscan' in testType:
            distfilename = '{0}/{1}/dat/{2}_chipId{3}.dat'.format(TMP_DIR, uuid, distType, chipId)
            h1 = makeDistFromDat(distfilename)
            if not h1: break
            f1 = ROOT.TF1('f1', 'gaus', h1.GetXaxis().GetXmin(), h1.GetXaxis().GetXmax())
            h1.Fit(f1)
            par = f1.GetParameters() 
            parameters.update({ chipId: {'mean': par[1], 'sigma': par[2]}, 'parameter': '' })
            parameter = 'mean: {0:.2f}, sigma: {1:.2f}'.format(par[1], par[2])

            cnt = h1.Integral(
                h1.FindBin(parameters[chipId]['mean'] - parameters[chipId]['sigma']*_scanList[testType]['scalesigma']), 
                h1.FindBin(parameters[chipId]['mean'] + parameters[chipId]['sigma']*_scanList[testType]['scalesigma'])
            )

            del h1
            del f1

        # tot scan
        elif 'totscan' in testType:
            distfilename = '{0}/{1}/dat/{2}_chipId{3}.dat'.format( TMP_DIR, uuid, distType, chipId )
            h1 = makeDistFromDat(distfilename)
            if not h1: break

            parameters.update({ chipId: {'mean': h1.GetMean(), 'rms': h1.GetRMS()} })
            parameter = 'average: {0:.2f}, rms: {1:.2f}'.format(h1.GetMean(), h1.GetRMS())

            cnt = h1.Integral(
                h1.FindBin(_scanList[testType]['mean'][chipId] - _scanList[testType]['sigma'][chipId]), 
                h1.FindBin(_scanList[testType]['mean'][chipId] + _scanList[testType]['sigma'][chipId])
            )
            del h1

        pix_chip = Col*Row
        countList.update({ chipId: {'totPix': int(pix_chip), 'countPix': cnt, 'parameter': parameter, 'parameters': parameters} })
 
    if not 'pix_chip' in locals(): return scoreList

    # grade the test for each chip and module 
    pix_mod = 0
    for chipId in chips:
        counts = countList.get(chipId,{}).get('countPix', 0)
        total  = countList.get(chipId,{}).get('totPix', pix_chip)
        rate = 100*counts/total
        if rate > _scanList[testType]['standard']: 
            score = 1
        else:
            score = 0
        scoreList.update({ chipId: { 'totPix': int(total), 
                                     'countPix': counts, 
                                     'rate': '{:.2f}'.format(rate), 
                                     'score': score, 
                                     'parameter': countList.get(chipId,{}).get(parameter,''), 
                                   }})
        module_cnt += counts
        pix_mod += pix_chip

    rate = 100*module_cnt/pix_mod
    if rate > _scanList[testType]['standard']:
        score = 1
    else:
        score = 0

    scoreList.update({ 'module': { 'totPix': int(pix_mod), 
                                   'countPix': module_cnt, 
                                   'rate': '{:.2f}'.format(rate), 
                                   'score': score, 
                                   'criterion': _scanList[testType]['criterion']
                                 }})

    return scoreList
