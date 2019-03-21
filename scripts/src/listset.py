import os, sys
# set path

# set parammeter
scan = { 'FE-I4B': { 'selftrigger'   : [( 'OccupancyMap-0', '#Hit' )],
                     'noisescan'     : [( 'NoiseOccupancy','NoiseOccupancy' ), ( 'NoiseMask', 'NoiseMask' )],
                     'totscan'       : [( 'MeanTotMap', 'Mean[ToT]' ),         ( 'SigmaTotMap', 'Sigma[ToT]' )],
                     'thresholdscan' : [( 'ThresholdMap', 'Threshold[e]' ),    ( 'NoiseMap', 'Noise[e]' )],
                     'digitalscan'   : [( 'OccupancyMap', 'Occupancy' ),       ( 'EnMask', 'EnMask' )],
                     'analogscan'    : [( 'OccupancyMap', 'Occupancy' ),       ( 'EnMask', 'EnMask' )]},
         'RD53A': { 'std_exttrigger'   : [( 'OccupancyMap', '#Hit' )],
                    'std_noisescan'    : [( 'NoiseOccupancy','NoiseOccupancy' ), ( 'NoiseMask', 'NoiseMask' )],
                    'std_totscan'      : [( 'MeanTotMap', 'Mean[ToT]' ),         ( 'SigmaTotMap', 'Sigma[ToT]' )],
                    'std_thresholdscan': [( 'ThresholdMap', 'Threshold[e]' ),    ( 'NoiseMap', 'Noise[e]' )],
                    'std_digitalscan'  : [( 'OccupancyMap', 'Occupancy' ),       ( 'EnMask', 'EnMask' )],
                    'std_analogscan'   : [( 'OccupancyMap', 'Occupancy' ),       ( 'EnMask', 'EnMask' )]} }

stage = [ 'encapsulation', 'wirebond' ]

summary_comment = [ 're-test', 'plan_to_re-test', 'failure', 'other' ]
