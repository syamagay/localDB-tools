import os, sys
# set path
os.environ['LIBPATH']=ROOTLIB
os.environ['LD_LIBRARY_PATH']=ROOTLIB
os.environ['PYTHONPATH']=ROOTLIB
sys.path.append(ROOTLIB)

# set parammeter
IPADDRESS=CHANGEIP
PORT=CHANGEPORT
pythonv = PYTHONV

scan = { "selftrigger"   : [( "OccupancyMap-0", "#Hit" ),],
         "noisescan"     : [( "NoiseOccupancy","NoiseOccupancy" ), ( "NoiseMask", "NoiseMask" )],
         "totscan"       : [( "MeanTotMap", "Mean[ToT]" ),         ( "SigmaTotMap", "Sigma[ToT]" )],
         "thresholdscan" : [( "ThresholdMap", "Threshold[e]" ),    ( "NoiseMap", "Noise[e]" )],
         "digitalscan"   : [( "OccupancyMap", "Occupancy" ),       ( "EnMask", "EnMask" )],
         "analogscan"    : [( "OccupancyMap", "Occupancy" ),       ( "EnMask", "EnMask" )]}

stage = [ "wirebond", "encapsulation" ]
