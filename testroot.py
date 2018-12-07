###############
### Osaka Univ.
### K. Yajima
###############

import sys, os, pwd, json
sys.path.append( os.path.dirname(os.path.abspath(__file__)) + "/scripts/src/PlotTools" )
from PlotHelpers import gHelper as PH
import PlotFromHistos.SimplePlots as Plot
import ROOT

USER=pwd.getpwuid( os.geteuid() ).pw_name
USER_DIR = '/tmp/{}'.format( USER ) 
PLOT_DIR = '{}/result'.format( USER_DIR )

#ROOT.gROOT.SetBatch()

h1 = ROOT.TH1D("test1D", "test1D", 100,0,100)
for i in [ 0, 1, 2, 3, 4, 5, 6, 7, 8, 9 ] :
    h1.Fill(10.*i)

path_dir = PLOT_DIR + "/test"
PH.outDir = path_dir

Plot.Plot1D_fromHistos(h1, False, "test_plot", "y", "histo", 100)
