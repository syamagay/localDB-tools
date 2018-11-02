'''
script for generate some simple plots
'''


##### Import #####
import sys, os
sys.path.append( os.path.dirname(os.path.abspath(__file__)) + "/.." )

import ROOT
from PlotHelpers import gHelper as PH


##### Functions #####
def Plot1D_fromHistos(histo, logY=False, fileName="", yTitle="Events", drawOpts="EP") :
    """
    === Arguments ===
        [Name]     (=[Default])          : [Description]
        histo      (Obligate)            : Input histogram
        logY       (=False)              : If Y axis is shown as logarithm(True) or linear(False)
        fileName   (=[histo.GetXaxis().GetTitle()])
                                         : File name for saved output file
        yTitle     (="Events")           : Title for Y axis of histograms
        drawOpts   (="EP")               : Draw options for drawing histograms
    """

    ####################
    ## Generate Objects

    # TCanvas and TPads
    canvas = ROOT.TCanvas("Canvas", "Plot", 800, 600)
    hPad = ROOT.TPad("HistoPad", "Histogram", 0, 0, 1, 1)
    hPad.SetLeftMargin  (0.13)
    hPad.SetTopMargin   (0.05)
    hPad.SetBottomMargin(0.14)
    if logY : hPad.SetLogy()


    ####################
    ## Setup style
    histo.SetStats( 0 )
    PH.AdjustRange(histo, logAxis=logY)

    for axes in [histo.GetXaxis(), histo.GetYaxis()] :
        axes.SetTitleSize(35)
        axes.SetTitleFont(43)
        axes.SetLabelSize(23)
        axes.SetLabelFont(43) # Absolute font size in pixel (precision 3)

    histo.GetXaxis().SetTitleOffset(0.75)
    histo.GetYaxis().SetTitleOffset(1.0)
    histo.GetYaxis().SetTitle(yTitle)


    ####################
    ## Drawing
    hPad.Draw()
    hPad.cd()
    histo.Draw(drawOpts)
    PH.DrawATLASLabel()

    if fileName == "" :
        fileName = histo.GetXaxis().GetTitle()

    fileName = fileName.replace("/","_")
    PH.SavePlot( canvas, fileName )

    canvas.Close()



def Plot2D_fromHistos(histo, logZ=False, fileName="", zTitle="Events") :
    """
    === Arguments ===
        [Name]     (=[Default])          : [Description]
        histo      (Obligate)            : Input histogram
        logZ       (=False)              : If Y axis is shown as logarithm(True) or linear(False)
        fileName   (=[histo.GetXaxis().GetTitle()])
                                         : File name for saved output file
        zTitle     (="Events")           : Title for Z axis of histograms
    """

    ####################
    ## Generate Objects

    # TCanvas and TPads
    canvas = ROOT.TCanvas("Canvas", "Plot", 800, 600)
    hPad = ROOT.TPad("HistoPad", "Histogram", 0, 0, 1, 1)
    hPad.SetRightMargin (0.17)
    hPad.SetLeftMargin  (0.13)
    hPad.SetTopMargin   (0.05)
    hPad.SetBottomMargin(0.14)
    if logZ : hPad.SetLogz()


    ####################
    ## Setup style
    histo.SetStats( 0 )
    histo.SetContour(100)

    for axes in [histo.GetXaxis(), histo.GetYaxis(), histo.GetZaxis()] :
        axes.SetTitleSize(35)
        axes.SetTitleFont(43)
        axes.SetLabelSize(23)
        axes.SetLabelFont(43) # Absolute font size in pixel (precision 3)

    histo.GetXaxis().SetTitleOffset(0.80)
    histo.GetYaxis().SetTitleOffset(1.0)
    histo.GetZaxis().SetTitleOffset(0.9)
    histo.GetZaxis().SetTitle(zTitle)

    ####################
    ## Drawing
    hPad.Draw()
    hPad.cd()
    histo.Draw("COLZ")
    hPad.Update()
    pal = histo.FindObject("palette")
    if hasattr(pal, 'SetY1NDC') : pal.SetY1NDC(0.22)
    PH.DrawATLASLabel()

    if fileName == "" :
        fileName = histo.GetXaxis().GetTitle()

    fileName = fileName.replace("/","_")
    PH.SavePlot( canvas, fileName )

    print("close")
    canvas.Close()
    print("closed")

def PlotTGraphs(graphs, logY=False, fileName="",
                xTitle="xAxis", yTitle="yAxis",
                drawOpts="EP", legOpts="EP",
                editStyle=None) :
    """
    === Arguments ===
        [Name]     (=[Default])          : [Description]
        graphs     (Obligate)            : Input graph (TGraph or TMultiGraph)
        logY       (=False)              : If Y axis is shown as logarithm(True) or linear(False)
        fileName   (=[xTitle])           : File name for saved output file
        xTitle     (="xAxis")            : Title for Y axis of graph
        yTitle     (="yAxis")            : Title for Y axis of graph
        drawOpts   (="EP")               : Draw options for drawing graph
        legOpts    (="EP")               : Draw options for drawing legend
        editStyle  (=None)               : Function object to edit style of the axis of the graphs
    """


    ####################
    # Generate Objects

    # TCanvas and TPads
    canvas = ROOT.TCanvas("Canvas", "Plot", 800, 600)
    gPad = ROOT.TPad("GraphPad", "GraphPad", 0, 0, 1, 1)
    gPad.SetLeftMargin  (0.13)
    gPad.SetTopMargin   (0.05)
    gPad.SetBottomMargin(0.14)
    if logY : gPad.SetLogy()

    # TLegend
    cl = ROOT.gROOT.GetClass( graphs.ClassName() )
    if   cl.InheritsFrom("TMultiGraph") :
        gr_list  = graphs.GetListOfGraphs()
        leg_list = [ (gr_list.At(i), legOpts) for i in range( gr_list.GetSize() ) ]
    elif cl.InheritsFrom("TGraph") :
        leg_list = [ (graphs, legOpts), ]
    else :
        raise TypeError('Argument "graphs" must be TGraph or TMultiGraph')
    leg = PH.MakeLegend( leg_list )


    ####################
    ## Pre-drawing to instanciate
    gPad.Draw()
    gPad.cd()
    graphs.Draw("A")


    ####################
    ## Setup style

    for axes in [graphs.GetXaxis(), graphs.GetYaxis()] :
        axes.SetTitleSize(35)
        axes.SetTitleFont(43)
        axes.SetLabelSize(23)
        axes.SetLabelFont(43) # Absolute font size in pixel (precision 3)

    graphs.GetXaxis().SetTitle(xTitle)
    graphs.GetYaxis().SetTitle(yTitle)
    graphs.GetXaxis().SetTitleOffset(0.75)
    graphs.GetYaxis().SetTitleOffset(1.0)

    if not editStyle is None : editStyle(graphs)


    ####################
    ## Drawing
    graphs.Draw(drawOpts+"A")
    PH.DrawATLASLabel()
    leg.Draw()

    if fileName == "" :
        fileName = graphs.GetXaxis().GetTitle()

    fileName = fileName.replace("/","_")
    PH.SavePlot( canvas, fileName )

    canvas.Close()



##### For Testing #####
if __name__ == "__main__" :

    import optparse
    parser = optparse.OptionParser()
    (opts, args) = parser.parse_args()

    histo = ROOT.TH1D("Landau", "Landau;xAxis;yAxis", 100, -5, 20)
    histo.FillRandom("landau", 10000)

    PH.outDir = "../TestData/Test_SimplePlots"
    PH.doDrawATLASLabel = True
    PH.lumi = 100.
    Plot1D_fromHistos(histo, False, "Plot1D")

    # 2D Plot
    histo2D = ROOT.TH2D("Gaus", "Gaus;xAxis;yAxis", 20, -2, 2, 20, -2, 2)

    for i in range(100000) :
        histo2D.Fill( ROOT.gRandom.Gaus(), ROOT.gRandom.Gaus() )

    PH.doDrawATLASLabel = False
    Plot2D_fromHistos(histo2D, False, "Plot2D")

    # TGraph
    import numpy as np
    x = np.arange(0, 10, 0.1)
    y = np.sin(x)
    graph = ROOT.TGraph(len(x), x, y)
    PlotTGraphs(graph, False, "Graph")
