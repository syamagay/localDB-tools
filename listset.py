scan = { "selftrigger"   : [( "OccupancyMap-0", "#Hit" ),],
         "noisescan"     : [( "NoiseOccupancy","NoiseOccupancy" ), ( "NoiseMask", "NoiseMask" )],
         "totscan"       : [( "MeanTotMap", "Mean[ToT]" ),         ( "SigmaTotMap", "Sigma[ToT]" )],
         "thresholdscan" : [( "ThresholdMap", "Threshold[e]" ),    ( "NoiseMap", "Noise[e]" )],
         "digitalscan"   : [( "OccupancyMap", "Occupancy" ),       ( "EnMask", "EnMask" )],
         "analogscan"    : [( "OccupancyMap", "Occupancy" ),       ( "EnMask", "EnMask" )]}
stage = [ "wirebond", "encapsulation" ]
