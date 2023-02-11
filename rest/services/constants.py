from math import pi

# Mathematical constants
const_Arcs = 3600*180/pi         # Arcseconds per radian
DAS2R = 4.848136811095359935899141e-6 # Arcseconds to radians 
TURNAS = 1296000.0 # Arcseconds in a full circle 


# Date-related constants
JD_J2000_0 = 2451545.0 # Julian Day of J2000.0 epoch.
DJC = 36525.0

# Other constants required for calculation of acceleration
omegaEarth = 15.04106717866910/3600*(pi/180) # Earth rotation (derivative of GSMT at J2000) in rad/s

s0 = [
  [0, 0, 0, 0, 1, 0, 0, 0],
  [0, 0, 0, 0, 2, 0, 0, 0],
  [0, 0, 2, -2, 3, 0, 0, 0], 
  [0, 0, 2, -2, 1, 0, 0, 0], 
  [0, 0, 2, -2, 2, 0, 0, 0], 
  [0, 0, 2, 0, 3, 0, 0, 0], 
  [0, 0, 2, 0, 1, 0, 0, 0], 
  [0, 0, 0, 0, 3, 0, 0, 0], 
  [0, 1, 0, 0, 1, 0, 0, 0], 
  [0, 1, 0, 0, -1, 0, 0, 0], 
  [1, 0, 0, 0, -1, 0, 0, 0], 
  [1, 0, 0, 0, 1, 0, 0, 0], 
  [0, 1, 2, -2, 3, 0.0, 0], 
  [0, 1, 2, -2, 1, 0, 0, 0], 
  [0, 0, 4, -4, 4, 0, 0, 0], 
  [0, 0, 1, -1, 1, -8, 12, 0], 
  [0, 0, 2, 0, 0, 0, 0, 0], 
  [0, 0, 2, 0, 2, 0, 0, 0], 
  [1, 0, 2, 0, 3, 0, 0, 0], 
  [1, 0, 2, 0, 1, 0, 0, 0], 
  [0, 0, 2, -2, 0, 0, 0, 0], 
  [0, 1, -2, 2, -3, 0, 0, 0], 
  [0, 1, -2, 2, -1, 0, 0, 0], 
  [0, 0, 0, 0, 0, 8, -13, -1], 
  [0, 0, 0, 2, 0, 0, 0, 0], 
  [2, 0, -2, 0, -1, 0, 0, 0], 
  [0, 1, 2, -2, 2, 0, 0, 0], 
  [1, 0, 0, -2, 1, 0, 0, 0], 
  [1, 0, 0, -2, -1, 0, 0, 0], 
  [0, 0, 4, -2, 4, 0, 0, 0], 
  [0, 0, 2, -2, 4, 0, 0, 0], 
  [1, 0, -2, 0, -3, 0, 0, 0], 
  [1, 0-2, 0, -1, 0, 0, 0]
]
s01 = [
  [-0.00264073],
  [-0.00006353],
  [-0.00001175], 
  [-0.00001121], 
  [0.00000457], 
  [-0.00000202], 
  [-0.00000198], 
  [0.00000172], 
  [0.00000141], 
  [0.00000126], 
  [0.00000063], 
  [0.00000063], 
  [-0.00000046], 
  [-0.00000045], 
  [-0.00000036], 
  [0.00000024], 
  [-0.00000032], 
  [-0.00000028], 
  [-0.00000027], 
  [-0.00000026], 
  [0.00000021],
  [-0.00000019], 
  [-0.00000018], 
  [0.00000010], 
  [-0.00000015], 
  [0.00000014], 
  [0.00000014], 
  [-0.00000014], 
  [-0.00000014], 
  [-0.00000013], 
  [0.00000011], 
  [-0.00000011], 
  [-0.00000011]
]
s02 = [
  [3.9e-07],
  [2.0e-08],
  [-1.0e-08], 
  [-1.0e-08], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [1.0e-08], 
  [1.0e-08], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [1.2e-07], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [-5.0e-08], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00]
]
s1 = [
  [0, 0, 0, 0, 2, 0, 0, 0],
  [0, 0, 0, 0, 1, 0, 0, 0], 
  [0, 0, 2, -2, 3, 0, 0, 0]
]
s11= [
  [-7.00e-08],
  [1.73e-06], 
  [0.00e+00]
]
s12 = [
  [3.57e-06],
  [-3.00e-08], 
  [4.80e-07]
]
s2 = [
  [0, 0, 0, 0, 1, 0, 0, 0], 
  [0, 0, 2, -2, 2, 0, 0, 0], 
  [0, 0, 2, 0, 2, 0, 0, 0], 
  [0, 0, 0, 0, 2, 0, 0, 0], 
  [0, 1, 0, 0, 0, 0, 0, 0], 
  [1, 0, 0, 0, 0, 0, 0, 0], 
  [0, 1, 2, -2, 2, 0, 0, 0], 
  [0, 0, 2, 0, 1, 0, 0, 0], 
  [1, 0, 2, 0, 2, 0, 0, 0], 
  [0, 1, -2, 2, -2, 0, 0, 0], 
  [1, 0, 0, -2, 0, 0, 0, 0], 
  [0, 0, 2, -2, 1, 0, 0, 0], 
  [1, 0, -2, 0, -2, 0, 0, 0], 
  [0, 0, 0, 2, 0, 0, 0, 0], 
  [1, 0, 0, 0, 1, 0, 0, 0], 
  [1, 0, -2, -2, -2, 0, 0, 0], 
  [1, 0, 0, 0, -1, 0, 0, 0], 
  [1, 0, 2, 0, 1, 0, 0, 0], 
  [2, 0, 0, -2, 0, 0, 0, 0], 
  [2, 0, -2, 0, -1, 0, 0, 0], 
  [0, 0, 2, 2, 2, 0, 0, 0], 
  [2, 0, 2, 0, 2, 0, 0, 0], 
  [2, 0, 0, 0, 0, 0, 0, 0], 
  [1, 0, 2, -2, 2, 0, 0, 0], 
  [0, 0, 2, 0, 0, 0, 0, 0]
]
s21 = [
  [0.00074352], 
  [0.00005691], 
  [0.00000984], 
  [-0.00000885], 
  [-0.00000638], 
  [-0.00000307], 
  [0.00000223], 
  [0.00000167], 
  [0.00000130], 
  [0.00000093], 
  [0.00000068], 
  [-0.00000055], 
  [0.00000053], 
  [-0.00000027], 
  [-0.00000027], 
  [-0.00000026], 
  [-0.00000025], 
  [0.00000022], 
  [-0.00000021], 
  [0.00000020], 
  [0.00000017], 
  [0.00000013], 
  [-0.00000013], 
  [-0.00000012], 
  [-0.00000011]
]
s22 = [
  [-1.7e-07], 
  [6.0e-08], 
  [-1.0e-08], 
  [1.0e-08], 
  [-5.0e-08], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00], 
  [0.0e+00]
]
s3 = [
  [0, 0, 0, 0, 1, 0, 0, 0],
  [0, 0, 2, -2, 2, 0, 0, 0], 
  [0, 0, 2, 0, 2, 0, 0, 0],
  [0, 0, 0, 0, 2, 0, 0, 0]
]
s31 = [
  [3e-07],
  [-3e-08], 
  [-1e-08],
  [0e+00]
]
s32 = [
  [-2.342e-05],
  [-1.460e-06], 
  [-2.500e-07],
  [2.300e-07]
]
s4 = [
  [0, 0, 0, 0, 1, 0, 0, 0]
]
s41 = [
  [-2.6e-07]
]
s42= [
  [-1e-08]
]