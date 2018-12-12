'''
Script for generate some simple plots from ROOT files
'''


##### Import #####
import sys, os
sys.path.append( os.path.dirname(os.path.abspath(__file__)) + "/.." )

import ROOT
from PlotHelpers import gHelper as PH
from PlotFromHistos.SimplePlots import Plot1D_fromHistos, Plot2D_fromHistos, PlotTGraphs


##### Functions #####
def DrawSimplePlots(inFile, options) :
    """
    === Arguments ===
        [Name]      (=[Default])            : [Description]
        inFile      (Obligate)              : Name or TFile instance of input file
        options     (Obligate)              : A list of python dictionary or a python dictionary
                                              In detail, see below

    === options (Should be given as a list of python dictionary or a python dictionary) ===

    +++ Contents of the dictionary +++
        *** For creating a  plot ***
        [key]       (=[Default])            : [Description]
        fileName    (=[tree/branchName or histName])
                                            : Name of output file
        logY/Z      (=False)                : If Y/Z(1D/2D) axis is shown as logarithm(True) or linear(False)
        subOpts     (Optional)              : If a lot of histograms have the same attributes,
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
    input_TFile = ROOT.TFile(inFile, "READ") if isinstance(inFile, str) else inFile


    #########################
    ## Parse options
    opts_list = PH.UnfoldPlotOptions(options)

    for opts_dict in opts_list :

        # Retrieve histograms
        histo = PH.RetrieveHisto(input_TFile, opts_dict)

        # Style
        logYZ    = opts_dict["logY/Z"]     if "logY/Z"     in opts_dict else False;
        objName  = opts_dict["histName"] if "histName" in opts_dict else opts_dict["branchName"]

        if "branchYName" in opts_dict : objName = opts_dict["branchYName"] + "_vs_" + objName
        fileName = opts_dict["fileName"] if "fileName" in opts_dict else objName.replace("/","_")
        if fileName.startswith("*") :
            fileName = objName.replace("/","_") + fileName[1:]

        ROOT.gStyle.SetErrorX(0.5)

        cl = ROOT.gROOT.GetClass( histo.ClassName() )
        if not cl.InheritsFrom("TH2") :
            Plot1D_fromHistos( histo, logYZ, fileName )
        else :
            Plot2D_fromHistos( histo, logYZ, fileName )


    #########################
    ## Close files
    input_TFile.Close()



##### For Testing #####
if __name__ == "__main__" :

    import optparse
    parser = optparse.OptionParser()
    (opts, args) = parser.parse_args()


    inFile = "TestSample.root"
    # If there are not ROOT files, create it
    if not os.path.exists(inFile) : PH.CreateTestSample(inFile)


    opts_list = [ { "treeName"   : "Data/Values",
                    "branchName" : "Value1",
                    # Example for folding
                    "subOpts"    :
                    [ { "binOpts"    : (50, -5, 45),
                        },
                      { "fileName"   : "2DPlot_FromTree",
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

    PH.outDir = "../TestData/Test_SimplePlot_fromFile"
    DrawSimplePlots(inFile, opts_list)
