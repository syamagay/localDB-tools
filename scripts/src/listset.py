import os, sys
# set path

# set parammeter
scan = { "selftrigger"   : [( "OccupancyMap-0", "#Hit" ),],
         "noisescan"     : [( "NoiseOccupancy","NoiseOccupancy" ), ( "NoiseMask", "NoiseMask" )],
         "totscan"       : [( "MeanTotMap", "Mean[ToT]" ),         ( "SigmaTotMap", "Sigma[ToT]" )],
         "thresholdscan" : [( "ThresholdMap", "Threshold[e]" ),    ( "NoiseMap", "Noise[e]" )],
         "digitalscan"   : [( "OccupancyMap", "Occupancy" ),       ( "EnMask", "EnMask" )],
         "analogscan"    : [( "OccupancyMap", "Occupancy" ),       ( "EnMask", "EnMask" )]}

stage = [ "encapsulation", "wirebond" ]

summary_comment = [ "re-test", "plan_to_re-test", "failure", "other" ]
