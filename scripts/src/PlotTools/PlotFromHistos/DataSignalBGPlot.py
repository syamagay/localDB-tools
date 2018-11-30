'''
script for generate Data/Signal/BG plot
'''


##### Import #####
import sys, os
sys.path.append( os.path.dirname(os.path.abspath(__file__)) + "/.." )

import ROOT
from PlotHelpers import gHelper as PH


##### Functions #####
def DataSignalBGPlot_fromHistos(dataHisto, bgHistos=[], signalHistos=[],
                                logY=False, fileName="",
                                yTitle="Events", rTitle="Data/Bkgd.") :
    """
    ++++++++++ Generate Data/Signal/BG plot ++++++++++
    === Arguments ===
    [Name]        (=[Default])       : [Description]
    dataHisto     (Obligate or None) : A histogram for data (You can give None if no need)
    bgHistos      (=[])              : List of histograms for background
                                       These are shown as filled histogram
    signalHistos  (=[])              : List of histograms for signal
                                       These are shown as non-filled histogram
    logY          (=False)           : If Y axis is shown as logarithm(True) or linear(False)
    fileName      (=)                : Filename for saved output file
    yTitle        (="Events")        : Title for Y axis of histograms
    rTitle        (="Data/Bkgd.")    : Title for Y axis of ratio graph
    """

    ####################
    ## Pre-process for histograms
    if not isinstance(    bgHistos, list) : raise TypeError(    "\"bgHistos\" must be a list")
    if not isinstance(signalHistos, list) : raise TypeError("\"signalHistos\" must be a list")

    noData, noBkgd = (False, False)

    if dataHisto is None:
        if len(bgHistos) == 0 : raise ValueError("\"bgHistos\" must not be empty if dataHisto is None")
        dataHisto = bgHistos[0].Clone("EmptyHisto")
        dataHisto.Reset()
        noData = True

    totalBGHisto = None
    if len(bgHistos) == 0 :
        if dataHisto is None : raise ValueError("\"dataHisto\" must not be None if bgHistos is empty")
        totalBGHisto = dataHisto.Clone("EmptyHisto")
        totalBGHisto.Reset()
        noBkgd = True

    for h in [dataHisto] + bgHistos + signalHistos :
        if h.GetSumw2N() <= 0 : h.Sumw2()


    ####################
    ## Generate Objects
    # Histogram for total/stacked backgrounds
    stackBGHisto = ROOT.THStack("StackedBGHisto", "")
    for bgHisto in bgHistos :
        if totalBGHisto is None : totalBGHisto = bgHisto.Clone("TotalBGHisto")
        else :                    totalBGHisto.Add( bgHisto )
        stackBGHisto.Add( bgHisto, "HIST" )

    # Ratio histogram
    rHisto = dataHisto.Clone("RatioHisto")
    rHisto.SetTitle("")
    rHisto.Divide(totalBGHisto)

    # TCanvas and TPads
    canvas = ROOT.TCanvas("Canvas", "DataSignalBGPlot", 900, 800)
    (hPad, rPad) = PH.MakePadsForRatioPlot()
    if logY : hPad.SetLogy()

    # TLegend
    dataHisto.SetTitle("Data")
    totalBGHisto.SetTitle("Stat.+Syst. Uncertainty")
    leg_list = [(h, "F") for h in bgHistos] + [(h, "L") for h in signalHistos]
    if not noData : leg_list = [dataHisto] + leg_list
    if not noBkgd : leg_list = leg_list + [(totalBGHisto, "F")]
    leg = PH.MakeLegend( leg_list )


    ####################
    ## Setup style
    # Histograms
    for h in [dataHisto, rHisto] :
        h.SetStats(0)
        h.SetMarkerColor(ROOT.kBlack)
        h.SetLineColor(ROOT.kBlack)

    for h in bgHistos     :
        h.SetLineWidth(1)
        h.SetLineColor(ROOT.kBlack)

    for h in signalHistos :
        h.SetLineWidth(2)
        h.SetLineColor(h.GetFillColor())
        h.SetFillColor(0)

    # Error rectangles for stacked background
    totalBGHisto.SetMarkerStyle(0)
    totalBGHisto.SetFillStyle(3145)
    totalBGHisto.SetFillColor(ROOT.kGray)
    totalBGHisto.SetLineColor(ROOT.kWhite)
    ROOT.gStyle.SetHatchesLineWidth(1)
    ROOT.gStyle.SetErrorX(0.5)


    ####################
    ## Setup style for axes
    PH.AdjustRange(rHisto, logAxis=False)
    PH.AdjustRange(dataHisto, logAxis=logY)
    PH.AdjustRange(totalBGHisto, logAxis=logY)

    if totalBGHisto.GetMaximum() < dataHisto.GetMaximum() :
        totalBGHisto.SetMaximum( dataHisto.GetMaximum() )

    if totalBGHisto.GetMinimum() > dataHisto.GetMinimum() :
        totalBGHisto.SetMinimum( dataHisto.GetMinimum() )

    axis = PH.SetAxisStyleForRatioPlot(totalBGHisto, rHisto, yTitle, rTitle)
    if logY : axis.SetOption( "G" )


    ####################
    ## Drawing
    hPad.Draw()
    rPad.Draw()

    hPad.cd()
    totalBGHisto.Draw("E2")
    stackBGHisto.Draw("SAME")
    totalBGHisto.Draw("E2 SAME")
    for h in signalHistos : h.Draw("SAME HIST")
    if not noData :
        dataHisto.Draw("SAME")
    totalBGHisto.Draw("AXIS SAME")
    PH.DrawATLASLabel()
    leg.Draw()
    axis.Draw()

    rPad.cd()
    rHisto.Draw("EP")
    atOne = PH.MakeBaseLine(rHisto)
    atOne.Draw("SAME")
    rHisto.Draw("EP SAME")

    if fileName == "" :
        fileName = bgHistos[0].GetXaxis().GetTitle() if noData else dataHisto.GetXaxis().GetTitle()

    fileName = fileName.replace("/","_")
    PH.SavePlot( canvas, fileName )

    canvas.Close()



##### For Testing #####
if __name__ == "__main__" :

    import optparse
    parser = optparse.OptionParser()
    (opts, args) = parser.parse_args()

    dataHisto = ROOT.TH1D("LandauD1", "LandauD1;xAxisD1;yAxisD1", 50, -5, 45)
    sigHisto1 = ROOT.TH1D(  "GausS1",   "GausS1;xAxisS1;yAxisS1", 50, -5, 45)
    sigHisto2 = ROOT.TH1D(  "GausS2",   "GausS2;xAxisS2;yAxisS2", 50, -5, 45)
    bgHisto1  = ROOT.TH1D("LandauB1", "LandauB1;xAxisB1;yAxisB1", 50, -5, 45)
    bgHisto2  = ROOT.TH1D("LandauB2", "LandauB2;xAxisB2;yAxisB2", 50, -5, 45)
    bgHisto3  = ROOT.TH1D("LandauB3", "LandauB3;xAxisB3;yAxisB3", 50, -5, 45)

    myGaus1   = ROOT.TF1("myGaus1", "TMath::Gaus(x, 10, 3.0)", -5, 45)
    myGaus2   = ROOT.TF1("myGaus2", "TMath::Gaus(x, 20, 1.0)", -5, 45)

    dataHisto.FillRandom("landau" , 10000)
    sigHisto1.FillRandom("myGaus1", 1000)
    sigHisto2.FillRandom("myGaus2", 500)
    bgHisto1. FillRandom("landau" , 1000)
    bgHisto2. FillRandom("landau" , 3000)
    bgHisto3. FillRandom("landau" , 6000)

    bgHisto1 .SetFillColor(ROOT.kRed)
    bgHisto2 .SetFillColor(ROOT.kBlue)
    bgHisto3 .SetFillColor(ROOT.kYellow)
    sigHisto1.SetFillColor(ROOT.kGreen)
    sigHisto2.SetFillColor(ROOT.kViolet)

    bgHistos  = [ bgHisto1, bgHisto2, bgHisto3 ]
    sigHistos = [ sigHisto1, sigHisto2 ]

    PH.outDir = "../TestData/Test_DataBGPlot"
    DataSignalBGPlot_fromHistos(dataHisto, bgHistos, sigHistos, False, "DataBGPlot")
    DataSignalBGPlot_fromHistos(dataHisto,       [],        [], False, "DataPlot")
    DataSignalBGPlot_fromHistos(     None, bgHistos,        [], False, "BGPlot")
