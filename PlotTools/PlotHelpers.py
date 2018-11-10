'''
Helper functions for ROOT-based PlotTools
'''


##### Import #####
import os
import AtlasStyle.OfficialAtlasStyle


##### Class definitions #####
class SingletonType(type) :
    _instance = None

    def __call__(cls, *args, **kwargs) :
        if cls._instance is None :
            cls._instance = super(SingletonType, cls).__call__(*args, **kwargs)

        return cls._instance



class Singleton(object) :
    __metaclass__ = SingletonType



class PlotHelpers(Singleton) :
    """
    Helper class for ROOT-based PlotTools
    """
    def __init__(self) :
        self.outDir = os.path.dirname(os.path.abspath(__file__)) + "/Data/TestDir"
        #self.saveExts = ["pdf", "png"]
        self.saveExts = ["png"]

        # For ATLAS label
        self.iLabel = None
        self.doDrawATLASLabel = False
        self.kind = "Internal"
        self.lumi = -1.
        self.TeV  = 13



    def GetMinimumIgnoringEmpty(self, histo) :
        """
        Get a value filled in the bin containing minimum value,
        but ignoring bins with zero (empty bins)
        """
        hMin = histo.GetMaximum()
        for i in range( histo.GetNbinsX() ) :
            for j in range( histo.GetNbinsY() ) :
                if   histo.GetDimension() == 1 : tmp = histo.GetBinContent(i+1)
                elif histo.GetDimension() == 2 : tmp = histo.GetBinContent(i+1, j+1)
                if   tmp < hMin and tmp != 0.0 : hMin = tmp

        return hMin



    def AdjustRange(self, histo, logAxis=False, ignoreEmpty=True) :
        """
        Adjust the range of the given histogram
        === Arguments ===
        [Name]      (=[Default])          : [Description]
        histo       (Obligate)            : Input histogram to adjust the range
        logAxis     (=False)              : Is the axis logarithmical?
        ignoreEmpty (=True)               : Ignoring bins containing zero value (empty bins)
        """
        hMax = histo.GetMaximum()
        hMin = self.GetMinimumIgnoringEmpty(histo) if ignoreEmpty else histo.GetMinimum()
        width = hMax - hMin

        if logAxis :
            histo.SetMaximum( hMax*10.0 )
            histo.SetMinimum( hMin/10.0 )
            if hMax <= 0.0 : histo.SetMaximum( 1.0 )
            if hMin <= 0.0 : histo.SetMinimum( hMax/1e5 )

        else :
            histo.SetMaximum( hMax + width*0.2 )
            histo.SetMinimum( hMin - width*0.15 )
            if hMin < width*0.15 : histo.SetMinimum( 0.0 )



    def DrawATLASLabel(self) :
        """
        Draw a text box with ATLAS label
        === Options (Defined as class variables) ===
        [Name]      (=[Default])          : [Description]
        kind        (="Internal")         : (e.g. "Internal", "Preliminary"...)
        lumi        (=-1.)                : Integrated luminosity (won't be shown if lumi<0)
        TeV         (=13)                 : Center-of-mass energy (won't be shown if lumi<0)
        doDrawATLASLabel
                    (=False)              : Do you want to draw it?
        """
        if not self.doDrawATLASLabel : return

        from ROOT import TPaveText, kBlack

        h, w = (0.15, 0.2)
        x1, x2, y1, y2 = (0.9-w, 0.9, 0.9-h, 0.9)

        self.iLabel = TPaveText(x1, y1, x2, y2, "NDC")
        self.iLabel.SetFillColor(0)
        self.iLabel.SetBorderSize(0)
        self.iLabel.SetTextAlign(32) # H:Right V:Center
        self.iLabel.SetTextSize(0.04)

        self.iLabel.AddText("#font[72]{ATLAS} "+self.kind)
        if self.lumi > 0. :
            self.iLabel.AddText("#sqrt{s} = "+str(self.TeV)+" TeV: "+
                           "#scale[0.6]{#int}L dt = "+str(self.lumi)+" fb^{-1}")

        self.iLabel.Draw()



    def MakePadsForRatioPlot(self) :
        """
        Make TPads(hPad, rPad) for the ratio plot
        and return it
        """

        from ROOT import TPad
        hPad = TPad("HistoPad", "Histogram", 0, 0.35, 1,  1.0) # TPads for Histogram
        rPad = TPad("RatioPad",     "Ratio", 0,    0, 1, 0.35) # TPads for Ratio

        rPad.SetTopMargin(0.07)
        hPad.SetBottomMargin(0.01)
        rPad.SetBottomMargin(0.23)
        rPad.SetGridy()

        return hPad, rPad



    def MakePadsForRatioPlot2D(self) :
        """
        Make TPads(h1Pad, h2Pad, rPad, ePad) for the ratio plot
        and return it
        """

        bMargin = 0.15
        iMargin = 0.05

        hHeight = (1 - bMargin) / (3 - iMargin - 2*bMargin)
        tMargin = iMargin * hHeight / (1.0 - 2*hHeight)

        from ROOT import TPad
        h1Pad = TPad("Histo1Pad", "Histogram1", 0., 1.0-  hHeight, 1., 1.0          ) # TPads for Histogram
        h2Pad = TPad("Histo2Pad", "Histogram2", 0., 1.0-2*hHeight, 1., 1.0  -hHeight) # TPads for Histogram
        rPad  = TPad( "RatioPad", "RatioHisto", 0.,            0., 1., 1.0-2*hHeight) # TPads for Ratio
        ePad  = TPad( "ErrorPad", "ErrorHisto", 0.,            0., 1., 1.0-2*hHeight) # TPads for Error

        for pad in [h1Pad, h2Pad, rPad, ePad] :
            pad.SetTopMargin   (iMargin)
            pad.SetBottomMargin(iMargin)
            pad.SetLeftMargin  (0.15)
            pad.SetRightMargin (0.18)

        rPad.SetTopMargin   (tMargin)
        rPad.SetBottomMargin(bMargin)
        ePad.SetTopMargin   (tMargin)
        ePad.SetBottomMargin(bMargin)

        # Make the error pad transparent
        ePad.SetFillStyle(4000)
        ePad.SetFillColor(0)
        ePad.SetFrameFillStyle(4000)

        return h1Pad, h2Pad, rPad, ePad



    def MakeBaseLine(self, histo) :
        """
        Make a base line for the ratio graph
        """
        from ROOT import TF1, kRed

        atOne = TF1("AtOne", "1.0", histo.GetXaxis().GetXmin(), histo.GetXaxis().GetXmax())
        atOne.SetLineWidth(2)
        atOne.SetLineColor(kRed)

        return atOne



    def MakeLegend(self, histos, displacement=[0.,0.,]) :
        """
        Make TLegend instance
        === Arguments ===
            [Name]       (=[Default])          : [Description]
            histos       (Obligate)            : A list of TH1 instances or tuples of histo and option
                                                 e.g.) histos=[h1, h2], or histos=[(h1,"LP"), (h2, "F")]
            displacement (=[0.,0.])            : Displacement from the default position
        """
        from ROOT import TLegend

        n = len(histos)        # nEntries
        h, w = (0.052*n, 0.23) # (height, width)
        dx, dy = (displacement[0], displacement[1])

        if n > 8 :
            w = w*1.8
            h = 0.055*(n+1)/2

        x1, x2, y1, y2 = (0.9-w+dx, 0.9+dx, 0.75-h+dy, 0.75+dy)
        leg = TLegend(x1, y1, x2, y2, "", "NDC")

        if n > 8 : leg.SetNColumns(2)

        for histo in histos :
            if isinstance(histo, tuple) : leg.AddEntry(histo[0], histo[0].GetTitle(), histo[1])
            else                        : leg.AddEntry(histo   , histo   .GetTitle(), "ELP")

        # Style
        leg.SetMargin(0.25)
        leg.SetTextSize(0.035)
        leg.SetTextFont(42)
        leg.SetBorderSize(0)
        leg.SetFillColor(0)

        return leg



    def SetAxisStyleForRatioPlot(self, hHisto, rHisto,
                                 yTitle="Events", rTitle="Ratio") :
        """
        Setup style of axes for the ratio plot
        Return TGaxis for Y axis of hHisto overwriting the default axis
        === Arguments ===
            [Name]       (=[Default])          : [Description]
            hHisto       (Obligate)            : A histogram
            rHisto       (Obligate)            : A histogram for the ratio graph
            yTitle       (="Events")           : Title of y axis
            rTitle       (="Ratio")            : Title of y axis for the ratio graph
        """
        from ROOT import TGaxis

        h1AxisX = hHisto.GetXaxis()
        h1AxisY = hHisto.GetYaxis()
        rAxisX  = rHisto.GetXaxis()
        rAxisY  = rHisto.GetYaxis()
        axis = TGaxis( h1AxisX.GetXmin(), hHisto.GetMinimum(),
                       h1AxisX.GetXmin(), hHisto.GetMaximum(),
                       hHisto.GetMinimum(), hHisto.GetMaximum(), 510, "" )

        h1AxisY.SetTitle( yTitle )
        rAxisX .SetTitle( hHisto.GetXaxis().GetTitle() )
        rAxisY .SetTitle( rTitle )

        for a in [h1AxisY, rAxisX, rAxisY, axis] :
            a.SetTitleSize(20)
            a.SetTitleFont(43)
            a.SetLabelSize(15)
            a.SetLabelFont(43) # Absolute font size in pixel (precision 3)

        rAxisY.SetNdivisions(505)

        # Remove labels of XAxis
        h1AxisX.SetLabelSize(0.)

        # Remove labels of YAxis
        h1AxisY.SetLabelSize(0.)
        h1AxisY.SetTickLength(0)

        h1AxisY.SetTitleOffset(1.55)
        rAxisX .SetTitleOffset(3.)
        rAxisY .SetTitleOffset(1.55)

        return axis



    def RetrieveHisto(self, inFile, options, outHistName="") :
        """
        === Arguments ===
            [Name]      (=[Default])          : [Description]
            inFile      (Obligate)            : Input file (must be TFile)
            options     (Obligate)            : See below
            outHistName (="")                 : Name for retrieved histogram

        === Options (Should be given as a python dictionary) ===
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
            *** Common settings ***
            title       (=[tree/branchName or histName])
                                              : Title for the histogram
            titleX      (=[histo.GetXaxis().GetTitle()])
                                              : Title for the x axis
            titleY      (=[histo.GetYaxis().GetTitle()])
                                              : Title for the y axis (Only for 2D histos)
            unit        (="")                 : Unit for the x axis
            unitY       (="")                 : Unit for the y axis (Only for 2D histos)
        """

        # Set object name and
        # determine if the histogram is retrieved from TH1/TH2 or TTree
        objName = ""
        isTree = False
        if "histName" in options :
            objName = options["histName"]
        else :
            isTree = True
            if "treeName" in options :
                objName = options["treeName"]
            else :
                raise ValueError("No histName or treeName")

        oHistName = objName if not outHistName else outHistName

        # Prepare to get the histogram from TTree
        if isTree :
            if not "branchName" in options :
                raise ValueError("No branchName")

            branchName = options["branchName"]
            if "branchYName" in options :
                branchName = options["branchYName"] + ":" + branchName

            if not outHistName :
                oHistName = oHistName + "_" + branchName.replace(":", "_vs_") + "_h"

            bin = options["binOpts"]   if "binOpts"   in options else ()
            sel = options["selection"] if "selection" in options else ""

            bin = ", ".join( [ str(i) for i in bin ] )

            tree = inFile.Get( objName )
            tree.Draw( branchName + ">>{0}({1})".format(oHistName.replace("/", "_"), bin), sel, "goff" )

        # Get histograms
        from ROOT import gDirectory, gROOT
        histo = gDirectory.Get( oHistName.replace("/", "_") ) if isTree else inFile.Get( objName )

        if not histo :
            raise RuntimeError("Not found retrieved object. Name of the histogram might be wrong.")

        cls = gROOT.GetClass( histo.ClassName() )

        isTH2 = False
        if cls.InheritsFrom("TH1") :
            if cls.InheritsFrom("TH2") : isTH2 = True
            if cls.InheritsFrom("TH3") : raise RuntimeError("Retrieved object is TH3, which is unsupported")
        else :
            raise RuntimeError("Retrieved object is not TH1")

        # Set histograms up
        unit  = " [{0}]".format(options["unit"])  if "unit"  in options else "";
        unitY = " [{0}]".format(options["unitY"]) if "unitY" in options else "";

        if not isTree :
            if outHistName : histo.SetName( outHistName )
            if isTH2 :
                if "rebin"  in options : histo.RebinX( options["rebin"] )
                if "rebinY" in options : histo.RebinY( options["rebinY"] )
            else :
                if "rebin"  in options : histo.Rebin( options["rebin"] )

        if "title"  in options : histo.SetTitle( options["title"] )
        else                   : histo.SetTitle( oHistName )

        if "titleX" in options : histo.GetXaxis().SetTitle( options["titleX"]           + unit )
        elif isTree            : histo.GetXaxis().SetTitle( options["branchName"]       + unit )
        else                   : histo.GetXaxis().SetTitle( histo.GetXaxis().GetTitle() + unit )
        if isTH2 :
                if "titleY" in options : histo.GetYaxis().SetTitle( options["titleY"]           + unitY )
                elif isTree            : histo.GetYaxis().SetTitle( options["branchYName"]      + unitY )
                else                   : histo.GetYaxis().SetTitle( histo.GetYaxis().GetTitle() + unitY )

        return histo



    def SavePlot(self, canvas, fileName) :
        if not os.path.isdir(self.outDir) :
            print("Make output directory : {}".format(self.outDir))
            os.makedirs(self.outDir)

        from ROOT import gROOT, TFile
        if not gROOT.IsBatch() :
            stdin = raw_input('>> ')

        for ext in self.saveExts :
            name = self.outDir + "/" + fileName + "." + ext
            if ext == "root" :
                of = TFile(name, "RECREATE")
                c = canvas.Clone("CanvasForSave")
                of.Add( c )
                of.Write()
                of.Close()
            else :
                canvas.SaveAs( name )



    def UnfoldPlotOptions(self, options, keyForFolding="subOpts") :
        """
        Unfold option list
        This procedure is executed recursively

        === Arguments ===
        [Name]        (=[Default])          : [Description]
        options       (Obligate)            : A list of python dictionary or a python dictionary
        keyForFolding (="subOpts")          : Name of the key used for folding options

        === Example ===
        [ { "key1" : val1, "key2" : val2,
            "subOpts" : [{ "subkey1_1" : subval1_1, "subkey2_1" : subval2_1, },
                         { "subkey1_2" : subval1_2, "subkey2_2" : subval2_2, },
                         ],
            },
          ]
        ===>>>
        [ { "key1" : val1, "key2" : val2, "subkey1_1" : subval1_1, "subkey2_1" : subval2_1, },
          { "key1" : val1, "key2" : val2, "subkey1_2" : subval1_2, "subkey2_2" : subval2_2, },
         ]
        """
        from copy import deepcopy

        # Check inputs
        if   isinstance(options, dict) : opts_list = [options,]
        elif isinstance(options, list) : opts_list =  options
        else                           : raise TypeError("\"options\" must be a list of dict. or a dict.")


        #########################
        ## Unfold options
        unfold_opts = []

        for opts_dir in opts_list :
            if not keyForFolding in opts_dir :
                unfold_opts.append( opts_dir )
                continue

            common_opts = deepcopy(opts_dir) # Common attributes
            del common_opts[ keyForFolding ]

            subOpts_list = deepcopy( opts_dir[ keyForFolding ] )
            subOpts_list = self.UnfoldPlotOptions(subOpts_list, keyForFolding) # Recursive process
            for subOpts in subOpts_list : subOpts.update( common_opts )
            unfold_opts.extend( deepcopy(subOpts_list) )

        return unfold_opts



    def CopyAllObjects(self, source, destination) :
        """
        Copy all TObject from "source" to "destination"
        "source" and "destination" should be an instance which inherits TDirectory
        """
        from ROOT import gROOT

        keys = source.GetListOfKeys()
        destination.cd()
        for key in keys :
            cl = gROOT.GetClass( ( key.GetClassName() ) )
            if cl.InheritsFrom("TTree") :
                oldTree = key.ReadObj()
                newTree = oldTree.CloneTree(-1, "fast")
                newTree.Write()
            else :
                key.ReadObj().Write()



    def CreateTestSample(self, fileName, SeparateFile=False) :
        """
        Create sample ROOT files for testing
        """

        import ROOT
        from array import array

        sampleList = [("Data", 10000),
                      ( "BG1",  6000), ( "BG2",  3000), ( "BG3",  1000),
                      ("Sig1",  1000), ("Sig2",  1000),
                      ]

        ## Create ROOT files for each category
        for sample in sampleList :
            sampleName    = sample[0]
            sampleEntries = sample[1]

            tmpFileName = "{0}_{1}".format(sampleName, fileName)
            if SeparateFile :
                print("Creating sample ROOT file ({0}) for testing...".format(tmpFileName))

            f  = ROOT.TFile(tmpFileName, "RECREATE")
            tr = ROOT.TTree("Values", "N-tuple for the testing ({0})".format(sampleName))

            Value1, Value2, Value3 = ( (array('d', [0.]), array('d', [0.]), array('d', [0.]) ))
            tr.Branch( "Value1", Value1, "Value1/D")
            tr.Branch( "Value2", Value2, "Value2/D")
            tr.Branch( "Value3", Value3, "Value3/D")

            rand = ROOT.gRandom.Gaus if "Sig" in sampleName else ROOT.gRandom.Landau
            arg = [0., 1.]
            if   sampleName == "Sig1" : arg = [10, 3.0]
            elif sampleName == "Sig2" : arg = [20, 1.0]

            for i in range(sampleEntries) :
                Value1[0] = rand(arg[0], arg[1])
                Value2[0] = rand(arg[0], arg[1])
                Value3[0] = rand(arg[0], arg[1])
                tr.Fill()

            tr.Draw("Value1>>Value1_h(50, -5, 45)", "", "GOFF")
            tr.Draw("Value2>>Value2_h(50, -5, 45)", "", "GOFF")
            tr.Draw("Value3>>Value3_h(50, -5, 45)", "", "GOFF")
            tr.Draw("Value2:Value1>>Value12_corr_h(50, -5, 45, 50, -5, 45)", "", "GOFF")

            f.Write()
            f.Close()

        ## Create merged ROOT file
        print("Creating sample ROOT file ({0}) for testing...".format(fileName))
        outFile = ROOT.TFile(fileName, "RECREATE")

        for sample in sampleList :
            tmpFileName = "{0}_{1}".format(sample[0], fileName)

            inFile = ROOT.TFile(tmpFileName, "READ")
            outDir = outFile.mkdir(sample[0])
            self.CopyAllObjects(inFile, outDir)

            inFile.Close()

            if not SeparateFile : os.system( "rm {0}".format(tmpFileName) )

        outFile.Write()
        outFile.Close()



### Global instance ###
gHelper = PlotHelpers()
