'''
script for generate Data/Signal/BG plot
'''


##### Import #####
import sys, os
sys.path.append( os.path.dirname(os.path.abspath(__file__)) + "/.." )

import ROOT
from PlotHelpers import gHelper as PH
from PlotFromHistos.DataSignalBGPlot import DataSignalBGPlot_fromHistos


##### Functions #####
def DataSignalBGPlot(inFile, options) :
    """
    === Arguments ===
        [Name]      (=[Default])            : [Description]
        inFile      (Obligate)              : Name or TFile instance of input file
        options     (Obligate)              : A list of python dictionary or a python dictionary
                                              In detail, see below

    === "inFile" for Multiple input files mode (Should be a list of python dictionany) ===
        [key]       (=[Default])            : [Description]
        inputFile   (Obligate)              : Name or TFile instance of input file
        title       (=[inputFileName])      : Title for the histogram
        kind        (="BG")                 : "Data", "BG", or "Signal"
        color       (=UsingPalette)         : Color of histogram (e.g. ROOT.kYellow)

    === options (Should be given as a list of python dictionary or a python dictionary) ===

    +++ Contents of the dictionary +++
        *** For creating a  plot ***
        [key]       (=[Default])            : [Description]
        fileName    (=[tree/branchName or histName])
                                            : Name of output file
        logY        (=False)                : If Y axis is shown as logarithm(True) or linear(False)
        rTitle      (="Data/Bkgd.")         : Title for the y axis of the ratio graph
        subOpts     (Optional)              : If a lot of histograms have the same attributes,
                                              you can fold options like
               [ { "key1" : val1, "key2" : val2, ...
                   "subOpts" : [{ "subkey1_1" : subval1_1, "subkey2_1" : subval2_1, },
                                { "subkey1_2" : subval1_2, "subkey2_2" : subval2_2, }, ...
                               ],
                 }, ... ]
        histoOpts   (Only for single file mode)
                                            : A list of python dictionary
                                              You can add items with "*" (See below)
        *** histoOpts ***
            [key]       (=[Default])            : [Description]
            title*      (=[inputFileName])      : Title for the histogram
            kind*       (="BG")                 : "Data", "BG", or "Signal"
            color*      (=UsingPalette)         : Color of histogram (e.g. ROOT.kYellow)

        *** For retrieving histograms ( will be passed to PH.RetrieveHisto() ) ***
            [key]       (=[Default])            : [Description]
            *** Retrieve from TTree ***
            treeName*   (Obligate)              : Name of TTree in the inFile
            branchName* (Obligate)              : Name of TBranch in the TTree specified by treeName

            binOpts     (Optional)              : Range and number of division (Should be tuple)
                                                  (e.g. binOpts = [100(Div.), 0(xMin), 10(xMax)])
            selection   (="")                   : Selection for the entries
                                                  This will be applied only for data histogram
            *** Retrieve from TH1 ***
            histName*   (Obligate)              : Name of TH1 in the inFile
            rebin       (Optional)              : Factor for re-binning along the x axis
            *** For common settings ***
            titleX      (=[histo.GetXaxis().GetTitle()])
                                                : Title for the x axis
            unit        (="")                   : Unit for the x axis
    """

    #########################
    ## Open files
    from copy import deepcopy
    if isinstance(inFile, list) :
        multiFileMode = True
        inFileCopy = deepcopy(inFile)
        for inf_dict in inFileCopy :
            if not "inputFile" in inf_dict : raise ValueError("No \"inputFile\" attribute")
            inf = inf_dict["inputFile"]
            inf_dict["inputFile_i"] = ROOT.TFile(inf, "READ") if isinstance(inf, str) else inf
    else :
        multiFileMode = False
        inFileCopy = ROOT.TFile(inFile, "READ") if isinstance(inFile, str) else inFile


    #########################
    ## Default coler palette
    from array import array
    r, g, b = ( array('f',[0.]), array('f',[0.]), array('f',[0.]) )
    bgColors, sigColors = ([], [])
    numColor = 7  # 2 <= numColor <= 30
    for i in range(numColor) :
        ROOT.TColor.HLS2RGB(240., 0.9-(0.8/numColor)*i, 1., r, g, b)
        bgColors .append( ROOT.TColor(120+i, r[0], g[0], b[0]) )
        ROOT.TColor.HLS2RGB((360./numColor)*i, 0.5, 1., r, g, b)
        sigColors.append( ROOT.TColor(150+i, r[0], g[0], b[0]) )


    #########################
    ## Parse options
    opts_list = PH.UnfoldPlotOptions(options)

    for opts_dict in opts_list :

        # Pre-processing for histo options
        if multiFileMode :
            if     "histoOpts" in opts_dict : raise ValueError("\"histoOpts\" is imcompatible to multi-inputs")
        else :
            if not "histoOpts" in opts_dict : raise ValueError("No \"histoOpts\" despite single-input")

        if multiFileMode :
            histoOpts = deepcopy( inFileCopy )
            for i, histoOpt in enumerate(histoOpts) :
                histoOpt.update( opts_dict )
                histoOpt["inputFile_i"] = inFileCopy[i]["inputFile_i"] # Prevent segfault
                histoOpt["outHistName"] = histoOpt["inputFile_i"].GetName().replace(".","_")
        else :
            histoOpts = PH.UnfoldPlotOptions(opts_dict, "histoOpts")
            for histoOpt in histoOpts :
                histoOpt["inputFile_i"] = inFileCopy
                histoOpt["outHistName"] = ""

        # Retrieve histograms
        dataHisto, bgHistos, signalHistos = RetrieveHistos_forDataBGPlot(histoOpts, bgColors, sigColors)

        # Style
        logY     = opts_dict["logY"]     if "logY"     in opts_dict else False;
        rTitle   = opts_dict["rTitle"]   if "rTitle"   in opts_dict else "Data/Bkgd."
        fileName = opts_dict["fileName"] if "fileName" in opts_dict else bgHistos[0].GetName()
        fileName = fileName.replace("/","_").replace(" ","_")

        DataSignalBGPlot_fromHistos( dataHisto, bgHistos, signalHistos,
                                     logY=logY, rTitle=rTitle, fileName=fileName )

    #########################
    ## Close files
    if multiFileMode :
        for inf_dict in inFileCopy :
            if isinstance(inf_dict["inputFile"], str) : inf_dict["inputFile_i"].Close()
    else :
        if isinstance(inFile, str) : inFileCopy.Close()



def RetrieveHistos_forDataBGPlot(histoOptList, bgColors, sigColors) :
    """
    === Arguments ===
        [Name]       (=[Default])           : [Description]
        histoOptList (Obligate)             : A list of python dictionary
                                              In detail, see below
        bgColors     (Obligate)             : Color list for background histograms
        sigColors    (Obligate)             : Color list for signal histograms
    """

    #########################
    ## Prepare variables
    dataHisto, bgHistos, signalHistos = (None, [], [])
    hasDataHisto = False

    # Color palette
    bgColor  = [bgColors [len( bgColors)-i-1].GetNumber() for i in range(len( bgColors))]
    sigColor = [sigColors[len(sigColors)-i-1].GetNumber() for i in range(len(sigColors))]


    #########################
    ## Retrieving...
    for i, histoOpt in enumerate(histoOptList) :

        # "selection" is applied only for the data
        if "selection" in histoOpt :
            if not "kind" in histoOpt       : del histoOpt["selection"]
            elif histoOpt["kind"] != "Data" : del histoOpt["selection"]

        histo = PH.RetrieveHisto( histoOpt["inputFile_i"], histoOpt, histoOpt["outHistName"] )

        # Setup color
        if "color" in histoOpt : histo.SetFillColor( histoOpt["color"] )
        else :
            if not "kind" in histoOpt         : histo.SetFillColor( bgColor .pop() )
            elif histoOpt["kind"] == "BG"     : histo.SetFillColor( bgColor .pop() )
            elif histoOpt["kind"] == "Signal" : histo.SetFillColor( sigColor.pop() )

        if not "kind" in histoOpt : # Default = "BG"
            bgHistos.append( histo )
        elif histoOpt["kind"] == "Data" :
            if hasDataHisto : raise ValueError("Duplicate data histogram")
            hasDataHisto = True
            dataHisto = histo
        elif histoOpt["kind"] == "BG" :
            bgHistos.append( histo )
        elif histoOpt["kind"] == "Signal" :
            signalHistos.append( histo )
        else :
            raise ValueError("Unknown value for \"kind\" attribute ({0})".format(histoOpt["kind"]))

    return dataHisto, bgHistos, signalHistos



##### For Testing #####
if __name__ == "__main__" :

    import optparse
    parser = optparse.OptionParser()
    (opts, args) = parser.parse_args()


    ### Test single input file mode ###

    inFile = "TestSample.root"
    # If there are not ROOT files, create it
    if not os.path.exists(inFile) : PH.CreateTestSample(inFile)

    histoOpts_fromTree = [ { "treeName"   : "Data/Values",
                             "kind"       : "Data",
                             # "color"      : ROOT.kBlack, # <- cannot change color for data
                             },
                           { "treeName"   : "BG1/Values",
                             # "kind"       : "BG", # <- "kind" is BG in default
                             },
                           { "treeName"   : "BG2/Values", },
                           { "treeName"   : "BG3/Values", },
                           { "treeName"   : "Sig1/Values",
                             "kind"       : "Signal",
                             },
                           { "treeName"   : "Sig2/Values",
                             "kind"       : "Signal",
                             },
                           ]

    histoOpts_fromHisto = [ { "histName"   : "Data/Value1_h",
                              "kind"       : "Data",
                              },
                            { "histName"   : "BG1/Value1_h",
                              "title"      : "Background1",
                              "color"      : ROOT.kRed,
                              },
                            { "histName"   : "BG2/Value1_h",
                              "color"      : ROOT.kBlue,
                              },
                            { "histName"   : "BG3/Value1_h",
                              "color"      : ROOT.kYellow,
                              },
                            { "histName"   : "Sig1/Value1_h",
                              "title"      : "Signal1",
                              "kind"       : "Signal",
                              "color"      : ROOT.kGreen,
                              },
                            { "histName"   : "Sig2/Value1_h",
                              "kind"       : "Signal",
                              "color"      : ROOT.kViolet,
                              },
                            ]

    opts_list = [ { "branchName" : "Value1",
                    "binOpts"    : (50, -5, 45),
                    "histoOpts"  : histoOpts_fromTree
                    },
                  { "logY"       : True,
                    "rTitle"     : "Ratio Title",
                    "titleX"     : "X Title",
                    "unit"       : "X Unit",
                    "subOpts"    :
                        [ { "fileName"   : "DataBGPlot_FromTree_FromSingleFile",
                            "histoOpts"  : histoOpts_fromTree,
                            "branchName" : "Value1",
                            "binOpts"    : (50, -5, 45),
                            "selection"  : "Value1 < 5 || Value1 > 22",
                            # "selection" (e.g. blind analysis) (NOTICE:Applied only for data!)
                            },
                          { "fileName"   : "DataBGPlot_FromHist_FromSingleFile",
                            "histoOpts"  : histoOpts_fromHisto,
                            "rebin"      : 2,
                            },
                          ],
                    },
                  ]

    PH.outDir = "../TestData/Test_DataBGPlot_fromFile"
    DataSignalBGPlot(inFile, opts_list)


    ### Test multiple input files mode ###

    inFile = "TestSamples.root"
    # If there are not ROOT files, create it
    if not os.path.exists(inFile) : PH.CreateTestSample(inFile, True)

    file_list = [ { "inputFile"  : "Data_"+inFile,
                    "kind"       : "Data",
                    # "title"      : "Data",
                    },
                  { "inputFile"  : "BG1_"+inFile,
                    # "kind"       : "BG", # <- "kind" is BG in default
                    "title"      : "Background1",
                    "color"      : ROOT.kRed,
                    },
                  { "inputFile"  : "BG2_"+inFile,
                    "color"      : ROOT.kBlue,
                    },
                  { "inputFile"  : "BG3_"+inFile,
                    "color"      : ROOT.kYellow,
                    },
                  { "inputFile"  : "Sig1_"+inFile,
                    "kind"       : "Signal",
                    "title"      : "Signal1",
                    "color"      : ROOT.kGreen,
                    },
                  { "inputFile"  : "Sig2_"+inFile,
                    "kind"       : "Signal",
                    "color"      : ROOT.kViolet,
                    },
                  ]

    opts_list = [ { "treeName"   : "Values",
                    "branchName" : "Value1",
                    "binOpts"    : (50, -5, 45),
                    "logY"       : True,
                    },
                  { "logY"       : False,
                    "rTitle"     : "Ratio Title",
                    "titleX"     : "X Title",
                    "unit"       : "X Unit",
                    "subOpts"    :
                        [ { "fileName"   : "DataBGPlot_FromTree_FromMultiFile",
                            "treeName"   : "Values",
                            "branchName" : "Value2",
                            "binOpts"    : (50, -5, 45),
                            "selection"  : "Value2 < 5 || Value2 > 22", },
                          { "fileName"   : "DataBGPlot_FromHist_FromMultiFile",
                            "histName"   : "Value1_h",
                            "rebin"      : 2, },
                          ]
                    },
                  ]

    DataSignalBGPlot(file_list, opts_list)
