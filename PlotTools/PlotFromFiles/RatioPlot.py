'''
script for generate ratio plot
'''


##### Import #####
import sys, os
sys.path.append( os.path.dirname(os.path.abspath(__file__)) + "/.." )

import ROOT
from PlotHelpers import gHelper as PH
from PlotFromHistos.RatioPlot import RatioPlot_fromHistos, RatioPlot2D_fromHistos


##### Functions #####
def RatioPlot(inFile1, inFile2, options, scale=1.0,
              title1="A", title2="B", rTitle="") :
    """
    === Arguments ===
        [Name]      (=[Default])          : [Description]
        inFile1     (Obligate)            : Name or TFile instance of input file
        inFile2     (Obligate)            : Name or TFile instance of another input file
        options     (Obligate)            : A list of python dictionary or a python dictionary
                                            In detail, see below
        scale       (=1.0)                : Do histo1.Scale(scale)
        title1      (="A")                : Title for the histogram"1"
        title2      (="B")                : Title for the histogram"2"
        rTitle      (="")                 : Title for the y axis of the ratio graph
                                            If it isn't assigned, this will be "([title1])/([title2])"

    === options (Should be given as a list of python dictionary or a python dictionary) ===
    +++ Contents of the dictionary +++

        *** For creating a ratio plot ***
        [key]       (=[Default])          : [Description]
        fileName    (=[branchName or histName])
                                          : Name of output file
                                            It will be appended to the default name if this starts with "*"
        norm        (=False)              : Normalize as both the histograms have the same area
        logY/Z      (=False)              : If Y/Z(1D/2D) axis is shown as logarithm(True) or linear(False)
        subOpts     (Optional)            : If a lot of histograms have the same attributes,
                                            you can fold options like
               [ { "key1" : val1, "key2" : val2, ...
                   "subOpts" : [{ "subkey1_1" : subval1_1, "subkey2_1" : subval2_1, },
                                { "subkey1_2" : subval1_2, "subkey2_2" : subval2_2, }, ...
                               ],
                 }, ... ]

        *** For retrieving histograms ( will be passed to PH.RetrieveHisto() ) ***
            [key]       (=[Default])          : [Description]
            *** Retrieve from TTree ***
            treeName    (Obligate)            : Name of TTree in the inFile
            branchName  (Obligate)            : Name of TBranch in the TTree specified by treeName
            branchYName (Optional)            : Name of additional TBranch in the TTree specified by treeName
                                                This is used to get 2D histogram
            binOpts     (Optional)            : Range and number of division (Should be tuple)
                                                (e.g. binOpts = [100(Div.), 0(xMin), 10(xMax)])
            selection   (="")                 : Selection for the entries
            *** Retrieve from TH1/TH2 ***
            histName    (Obligate)            : Name of TH1/TH2 in the inFile
            rebin       (Optional)            : Factor for re-binning along the x axis
            rebinY      (Optional)            : Factor for re-binning along the y axis (Only for 2D histos)
            *** For common settings ***
            title       (=[tree/branchName or histName])
                                              : Title for the histogram
            titleX      (=[histo.GetXaxis().GetTitle()])
                                              : Title for the x axis
            titleY      (=[histo.GetYaxis().GetTitle()])
                                              : Title for the y axis (Only for 2D histos)
            unit        (="")                 : Unit for the x axis
            unitY       (="")                 : Unit for the y axis (Only for 2D histos)
    """

    #########################
    ## Open files
    inf1 = ROOT.TFile(inFile1, "READ") if isinstance(inFile1, str) else inFile1
    inf2 = ROOT.TFile(inFile2, "READ") if isinstance(inFile1, str) else inFile2


    #########################
    ## Parse options
    opts_list = PH.UnfoldPlotOptions(options)

    for opts_dict in opts_list :
        histo1 = PH.RetrieveHisto(inf1, opts_dict, "Histo1")
        histo2 = PH.RetrieveHisto(inf2, opts_dict, "Histo2")

        if scale != 1.0 :
            if histo1.GetSumw2N() <= 0 : histo1.Sumw2()
            histo1.Scale(scale)

        # Style
        histo1.SetTitle(title1)
        histo2.SetTitle(title2)
        histo1.SetMarkerStyle(24)

        norm     = opts_dict["norm"]     if "norm"     in opts_dict else False;
        logYZ    = opts_dict["logY/Z"]   if "logY/Z"   in opts_dict else False;
        objName  = opts_dict["histName"] if "histName" in opts_dict else opts_dict["branchName"]

        if "branchYName" in opts_dict : objName = opts_dict["branchYName"] + "_vs_" + objName
        fileName = opts_dict["fileName"] if "fileName" in opts_dict else objName.replace("/","_")
        if fileName.startswith("*") :
            fileName = objName.replace("/","_") + fileName[1:]

        if not rTitle :
            rTitle = "({0})/({1})".format(title2, title1)

        ROOT.gStyle.SetErrorX(0.5)

        cl = ROOT.gROOT.GetClass( histo1.ClassName() )
        if not cl.InheritsFrom("TH2") :
            RatioPlot_fromHistos  ( histo1, histo2,
                                    norm=norm, logY=logYZ,
                                    rTitle=rTitle, fileName=fileName )
        else :
            RatioPlot2D_fromHistos( histo1, histo2,
                                    norm=norm, logZ=logYZ,
                                    rTitle=rTitle, fileName=fileName )


    #########################
    ## Close files
    if isinstance(inFile1, str) : inf1.Close()
    if isinstance(inFile2, str) : inf2.Close()



##### For Testing #####
if __name__ == "__main__" :

    import optparse
    parser = optparse.OptionParser()
    (opts, args) = parser.parse_args()

    inFile1 = "TestSample.root"
    inFile2 = "AnotherTestSample.root"

    # If there are not ROOT files, create it
    if not os.path.exists(inFile1) : PH.CreateTestSample(inFile1)
    if not os.path.exists(inFile2) : PH.CreateTestSample(inFile2)

    opts_list = [ { "treeName"   : "Data/Values",
                    "branchName" : "Value1",
                    # Example for folding
                    "subOpts"    :
                    [ { "binOpts"    : (50, -5, 45),
                        },
                      { "fileName"   : "2DRatioPlot_FromTree",
                        "norm"       : False,
                        "logY/Z"     : False,
                        "branchYName": "Value2",
                        "binOpts"    : (50, -5, 45, 50, -5, 45),
                        "selection"  : "(Value1-5)*(Value1-5) + (Value2-4)*(Value2-4) > 3*3",
                        "titleX"     : "X Title",
                        "titleY"     : "Y Title",
                        "unit"       : "X Unit",
                        "unitY"      : "Y Unit",
                        },
                      ],
                    },
                  { "histName"   : "Data/Value1_h",
                    },
                  { "fileName"   : "2DRatioPlot_FromHisto",
                    "norm"       : True,
                    "logY/Z"     : True,
                    "histName"   : "Data/Value12_corr_h",
                    "rebin"      : 2,
                    "rebinY"     : 5,
                    "titleX"     : "X Title",
                    "titleY"     : "Y Title",
                    "unit"       : "X Unit",
                    "unitY"      : "Y Unit",
                    },
                  ]

    PH.outDir = "../TestData/Test_RatioPlot_fromFile"
    RatioPlot(inFile1, inFile2, opts_list, scale=1.0, title1="Test1", title2="Test2", rTitle="")
