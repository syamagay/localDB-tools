import os, ROOT

ROOT.gROOT.LoadMacro( os.path.dirname(os.path.abspath(__file__)) + "/AtlasStyle.C" )
ROOT.SetAtlasStyle()
