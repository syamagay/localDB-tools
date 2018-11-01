'''
script for generate ratio plot
'''


##### Import #####
import sys, os
sys.path.append( os.path.dirname(os.path.abspath(__file__)) + "/.." )

import ROOT
from PlotHelpers import gHelper as PH


##### Functions #####
def RatioPlot_fromHistos(histo1, histo2,
                         norm=False, logY=False,
                         fileName="",
                         yTitle="Events", rTitle="Ratio",
                         drawOpts="EP") :
    """
    === Arguments ===
        [Name]     (=[Default])          : [Description]
        histo1     (Obligate)            : Input histogram for numerator
        histo2     (Obligate)            : Input histogram for denominator
        norm       (=False)              : Normalize as both the histograms have the same area
        logY       (=False)              : If Y axis is shown as logarithm(True) or linear(False)
        fileName   (=[histo1.GetXaxis().GetTitle()])
                                         : File name for saved output file
        yTitle     (="Events")           : Title for Y axis of histograms
        rTitle     (="Ratio")            : Title for the y axis of the ratio graph
        drawOpts   (="EP")               : Draw options for drawing histograms
    """

    ####################
    ## Generate Objects
    # Ratio histogram
    if histo1.GetSumw2N() <= 0 : histo1.Sumw2()
    if histo2.GetSumw2N() <= 0 : histo2.Sumw2()
    if norm :
        histo1.Scale(1./histo1.Integral())
        histo2.Scale(1./histo2.Integral())

    rHisto = histo2.Clone("RatioHisto")
    rHisto.SetTitle("")
    rHisto.Divide(histo1)

    # TCanvas and TPads
    canvas = ROOT.TCanvas("Canvas", "RatioPlot", 800, 800)
    (hPad, rPad) = PH.MakePadsForRatioPlot()
    if logY : hPad.SetLogy()

    # TLegend
    leg = PH.MakeLegend([(histo1, "LP"), (histo2, "LP")])


    ####################
    ## Setup style
    # Histograms
    for h in [histo1, histo2, rHisto] :
        h.SetStats      ( 0 )
        h.SetMarkerStyle( histo1.GetMarkerStyle() )
        h.SetMarkerSize ( histo1.GetMarkerSize() )

    histo1.SetLineColor(ROOT.kBlue+1)
    histo2.SetLineColor(ROOT.kRed)
    histo1.SetMarkerColor(ROOT.kBlue+1)
    histo2.SetMarkerColor(ROOT.kRed)


    ####################
    ## Setup style for axes
    PH.AdjustRange(rHisto, logAxis=False)
    PH.AdjustRange(histo1, logAxis=logY)
    PH.AdjustRange(histo2, logAxis=logY)

    if histo2.GetMaximum() > histo1.GetMaximum() :
        histo1.SetMaximum( histo2.GetMaximum() )

    if histo2.GetMinimum() < histo1.GetMinimum() :
        histo1.SetMinimum( histo2.GetMinimum() )

    axis = PH.SetAxisStyleForRatioPlot(histo1, rHisto, yTitle, rTitle)
    if norm : h1AxisY.SetTitle( "Arb. unit" )
    if logY : axis.SetOption( "G" )


    ####################
    ## Drawing
    # Histograms
    hPad.Draw()
    rPad.Draw()

    hPad.cd()
    histo1.Draw(drawOpts)
    histo2.Draw(drawOpts+"SAME")
    PH.DrawATLASLabel()
    leg.Draw()
    axis.Draw()
    histo1.Draw(drawOpts+"AXIS SAME")

    rPad.cd()
    rHisto.Draw(drawOpts)
    atOne = PH.MakeBaseLine(rHisto)
    atOne.Draw("SAME")
    rHisto.Draw(drawOpts+" SAME")

    if fileName == "" :
        fileName = histo1.GetXaxis().GetTitle()

    fileName = fileName.replace("/","_")
    PH.SavePlot( canvas, fileName )

    canvas.Close()



#########################
## Prepare color palette for the 2D ratio plot
command  = "void userPaletteForRatio(Double_t baseLine, Double_t bright) {"
command += "  if( baseLine >= 0.0 and baseLine < 1.0 ) {"
command += "    Double_t Red   [] = {   0.0,   bright,           bright, bright};"
command += "    Double_t Green [] = {   0.0,   bright,           bright,    0.0};"
command += "    Double_t Blue  [] = {bright,   bright,              0.0,    0.0};"
command += "    Double_t Length[] = {   0.0, baseLine, 0.3+baseLine*0.7,    1.0};"
command += "    Int_t FI = TColor::CreateGradientColorTable(4, Length, Red, Green, Blue, 100);"
command += "  } else if( baseLine >= 1.0 ) {"
command += "    Double_t Red   [] = {   0.0, bright/baseLine};"
command += "    Double_t Green [] = {   0.0, bright/baseLine};"
command += "    Double_t Blue  [] = {bright,          bright};"
command += "    Double_t Length[] = {   0.0,             1.0};"
command += "    Int_t FI = TColor::CreateGradientColorTable(2, Length, Red, Green, Blue, 100);"
command += "  } else if( baseLine >= -3.0/7 and baseLine < 0.0 ) {"
command += "    Double_t scale    = 1.0/(1.0-baseLine);"
command += "    Double_t Red   [] = {      bright,           bright, bright};"
command += "    Double_t Green [] = {      bright,           bright,    0.0};"
command += "    Double_t Blue  [] = {bright*scale,              0.0,    0.0};"
command += "    Double_t Length[] = {         0.0, 0.3+baseLine*0.7,    1.0};"
command += "    Int_t FI = TColor::CreateGradientColorTable(3, Length, Red, Green, Blue, 100);"
command += "  } else {"
command += "    Double_t scale    = 1.0/((1.0-baseLine)*0.7);"
command += "    Double_t Red   [] = {      bright, bright};"
command += "    Double_t Green [] = {bright*scale,    0.0};"
command += "    Double_t Blue  [] = {         0.0,    0.0};"
command += "    Double_t Length[] = {         0.0,    1.0};"
command += "    Int_t FI = TColor::CreateGradientColorTable(2, Length, Red, Green, Blue, 100);"
command += "  }"
command += "}"
ROOT.gROOT.ProcessLine(command)



def RatioPlot2D_fromHistos(histo1, histo2,
                           norm=False, logZ=False, useAsym=True,
                           fileName="",
                           rTitle="Ratio", zTitle="Events",
                           drawOpts="") :
    """
    === Arguments ===
        [Name]     (=[Default])          : [Description]
        histo1     (Obligate)            : Input histogram for numerator
        histo2     (Obligate)            : Input histogram for denominator
        norm       (=False)              : Normalize as both the histograms have the same area
        logZ       (=False)              : If Z axis is shown as logarithm(True) or linear(False)
        useAsym    (=)                   : Use degree of asymmetry instead of the ratio
        fileName   (=[histo1.GetYaxis().GetTitle() + "_vs_" + histo1.GetXaxis().GetTitle()])
                                         : File name for saved output file
        rTitle     (="Ratio")            : Title for the y axis of the ratio graph
        zTitle     (="Events")           : Title for Z axis of histograms
        drawOpts   (="EP")               : Draw options for drawing histograms
    """

    ####################
    ## Generate Objects
    # Ratio histogram
    if histo1.GetSumw2N() <= 0 : histo1.Sumw2()
    if histo2.GetSumw2N() <= 0 : histo2.Sumw2()
    if norm :
        histo1.Scale(1./histo1.Integral())
        histo2.Scale(1./histo2.Integral())

    if useAsym :
        rHisto = histo2.GetAsymmetry(histo1)
        rTitle = "Asym."
    else :
        rHisto = histo2.Clone("RatioHisto")
        rHisto.Divide(histo1)
    rHisto.SetTitle("")

    eHisto = rHisto.Clone("ErrorHisto")
    eHisto.SetContent( rHisto.GetSumw2().GetArray() )

    if not useAsym : eHisto.Divide( rHisto ) # Relative error

    # TCanvas and TPads
    canvas = ROOT.TCanvas("Canvas", "RatioPlot", 500, 900)

    (h1Pad, h2Pad, rPad, ePad) = PH.MakePadsForRatioPlot2D()
    if logZ :
        h1Pad.SetLogz()
        h2Pad.SetLogz()


    ####################
    ## Setup style
    # Histograms
    if not useAsym : PH.AdjustRange(rHisto, logAxis=False)

    for h in [histo1, histo2, rHisto] :
        h.SetStats  (0)
        h.SetContour(100)

    # Error histogram for the ratio pad
    eHisto.SetFillColor(ROOT.kGray+3)
    eHisto.SetLineWidth(0)

    # Adjust range of the error histograms to its of the ratio histogram
    eMax, eMin = ( eHisto.GetMaximum(), PH.GetMinimumIgnoringEmpty(eHisto) )
    eHisto.SetMaximum( eMax*1.5 )
    eHisto.SetMinimum( eMin + (eMax-eMin)/500 )

    # Mask diverged bins if using asymmetry plot
    if useAsym :
        for i in range(rHisto.GetNcells()) :
            if abs( rHisto.GetBinContent(i) ) == 1.0 : eHisto.SetBinContent(i, eMax*1.25)


    ####################
    ## Setup style for axes
    if norm : zTitle = "Arb. unit"

    for axes in [rHisto.GetXaxis(),
                 histo1.GetYaxis(), histo2.GetYaxis(), rHisto.GetYaxis(),
                 histo1.GetZaxis(), histo2.GetZaxis(), rHisto.GetZaxis()] :
        axes.SetTitleOffset(2.7)
        axes.SetTitleSize(15)
        axes.SetTitleFont(43)
        axes.SetLabelSize(12)
        axes.SetLabelFont(43) # Absolute font size in pixel (precision 3)

    histo1.GetXaxis().SetLabelSize(0)
    histo2.GetXaxis().SetLabelSize(0)
    histo1.GetXaxis().SetTitleSize(0)
    histo1.GetXaxis().SetTitleSize(0)
    rHisto.GetXaxis().SetTitle(histo1.GetXaxis().GetTitle())
    rHisto.GetYaxis().SetTitle(histo1.GetYaxis().GetTitle())
    histo1.GetZaxis().SetTitle(zTitle + " ({0})".format(histo1.GetTitle()))
    histo2.GetZaxis().SetTitle(zTitle + " ({0})".format(histo2.GetTitle()))
    rHisto.GetZaxis().SetTitle(rTitle)


    ####################
    ## Drawing
    # Histograms
    bright   = 1.0 if useAsym else 0.9
    baseLine = 0.0 if useAsym else 1.0
    baseLine = (baseLine - rHisto.GetMinimum()) / (rHisto.GetMaximum() - rHisto.GetMinimum())

    h1Pad.Draw()
    h2Pad.Draw()
    rPad.Draw()
    ePad.Draw()

    h1Pad.cd()
    histo1.Draw(drawOpts+"COLZ")
    # histo1.Draw(drawOpts+"COLZ AXIS")
    h1Exe = ROOT.TExec( "h1ex", "gStyle->SetPalette(kBird)" )
    h1Exe.Draw()
    histo1.Draw(drawOpts+"COLZ SAME")
    histo1.Draw(drawOpts+"COLZ AXIS SAME")

    h2Pad.cd()
    histo2.Draw(drawOpts+"COLZ")
    # histo2.Draw(drawOpts+"COLZ AXIS")
    h2Exe = ROOT.TExec( "h2ex", "gStyle->SetPalette(kBird)" )
    h2Exe.Draw()
    histo2.Draw(drawOpts+"COLZ SAME")
    histo2.Draw(drawOpts+"COLZ AXIS SAME")

    rPad.cd()
    rHisto.Draw(drawOpts+"COLZ")
    # rHisto.Draw(drawOpts+"COLZ AXIS")
    rExe = ROOT.TExec( "rex", "userPaletteForRatio({0},{1})".format(baseLine, bright) )
    rExe.Draw()
    rHisto.Draw(drawOpts+"COLZ SAME")
    rPad.Update()
    rHisto.FindObject("palette").SetY1NDC(0.22)
    rHisto.Draw(drawOpts+"COLZ AXIS SAME")

    ePad.cd()
    eHisto.Draw(drawOpts+"BOX AP")

    if fileName == "" :
        fileName = histo1.GetYaxis().GetTitle() + "_vs_" + histo1.GetXaxis().GetTitle()

    fileName = fileName.replace("/","_")
    PH.SavePlot( canvas, fileName )

    canvas.Close()



##### For Testing #####
if __name__ == "__main__" :

    import optparse
    parser = optparse.OptionParser()
    (opts, args) = parser.parse_args()

    histo1 = ROOT.TH1D("Landau1", "Landau1;xAxis1;yAxis1", 100, -5, 20)
    histo2 = ROOT.TH1D("Landau2", "Landau2;xAxis2;yAxis2", 100, -5, 20)

    histo1.FillRandom("landau", 10000)
    histo2.FillRandom("landau", 10000)

    PH.outDir = "../TestData/Test_RatioPlot"
    PH.doDrawATLASLabel = True
    PH.lumi = 100.
    RatioPlot_fromHistos(histo1, histo2, False, False, "RatioPlot1D")

    # 2D Ratio
    histo2D1 = ROOT.TH2D("Gaus1", "Gaus1;xAxis1;yAxis1", 20, -5, 5, 20, -5, 5)
    histo2D2 = ROOT.TH2D("Gaus2", "Gaus2;xAxis2;yAxis2", 20, -5, 5, 20, -5, 5)

    for i in range(100000) :
        histo2D1.Fill( ROOT.gRandom.Gaus( 0.5, 2.1), ROOT.gRandom.Gaus(0., 2.1) )
        histo2D2.Fill( ROOT.gRandom.Gaus(-0.5, 1.9), ROOT.gRandom.Gaus(0., 1.9) )

    PH.doDrawATLASLabel = False
    RatioPlot2D_fromHistos(histo2D1, histo2D2, False, False, fileName="RatioPlot2D")
