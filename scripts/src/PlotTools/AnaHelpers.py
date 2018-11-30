'''
Helper functions for ROOT-based data analysis
'''


##### Import #####
import sys
import ROOT


##### Function definitions #####
def MakeROCCurve(disc_true, disc_false, useSpecificity=True) :
    """
    Make Receiver Operating Characteristic(ROC) curve
    from histograms of discriminant value
    === Arguments ===
    [Name]      (=[Default])          : [Description]
    disc_true   (Obligate)            : Histogram of discriminant value for  true samples
    disc_false  (Obligate)            : Discriminant discriminant value for false samples
    """

    isDifferBins = False
    if disc_true.GetXaxis().GetXmin () != disc_false.GetXaxis().GetXmin () : isDifferBins = True
    if disc_true.GetXaxis().GetXmax () != disc_false.GetXaxis().GetXmax () : isDifferBins = True
    if disc_true.GetXaxis().GetNbins() != disc_false.GetXaxis().GetNbins() : isDifferBins = True

    if isDifferBins : raise ValueError("Different bin setting")


    xMin   = disc_true .GetXaxis().GetXmin ()
    xMax   = disc_true .GetXaxis().GetXmax ()
    nBins  = disc_true .GetXaxis().GetNbins()
    nTrue  = disc_true .Integral()
    nFalse = disc_false.Integral()

    gr = ROOT.TGraph(nBins-1)
    oflow_i = nBins+1 # Overflow  bin
    uflow_i = 0       # Underflow bin

    for i in range(nBins-1) :

        nTrue_pos  = disc_true .Integral(      i, oflow_i)
        nFalse_neg = disc_false.Integral(uflow_i,     i-1) if not i==0 else 0

        sensitivity = float(  nTrue_pos ) /  nTrue
        specificity = float( nFalse_neg ) / nFalse

        if nFalse_neg == nFalse : reduction = 1e10
        else                    : reduction = float(nFalse) / (nFalse-nFalse_neg)

        if useSpecificity : gr.SetPoint(i, sensitivity, 1-specificity)
        else              : gr.SetPoint(i, sensitivity, reduction)

    return gr
