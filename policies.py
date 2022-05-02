

import os
import sys
import numpy as np
import surface_points
from scipy.integrate import quad
##############################################################################
#80-120

### max i =96A
# current limit of battery model


C1 = [3.6, 4.0, 4.4, 4.8, 5.2, 5.6, 6.0, 7.0, 8.0]
C2 = [3.6, 4.0, 4.4, 4.8, 5.2, 5.6, 6.0, 7.0]
C3 = [3.6, 4.0, 4.4, 4.8, 5.2, 5.6]

C4_LIMITS = [0.1, 4.81] 

DIR = sys.argv[1]
FILENAME = sys.argv[2]

##############################################################################

# 16 % energy loss assumed 
def integrand(x, a):
    return a*x

Crated=100                  #kW tesla model
SOCo=  0.5                  #user input
SOC_desired= 0.8
Time_by_user= 5             #in minutes
#SOC= quad(integrand, 0, 10, args=(Crated))
# possibe since current assumed to be constant
avg_current=(SOC_desired-SOCo)*Crated*5/(4*Time_by_user)
print(avg_current)
#find current till the user soc
# get avg of currents so it becomes that current
# take it for 3 time intervals say 10min,15min,5 min
# show user for 3 time intervals,cost and all
####################################################33

# Pre-initialize arrays and counters
policies = -1.*np.ones((1000,4));
valid_policies = -1.*np.ones((1000,4));

count = valid_count = 0

# Generate policies
for c1, c2, c3 in [(c1,c2,c3) for c1 in C1 for c2 in C2 for c3 in C3]:
    print((c1+c2+c3)/3 )
    if avg_current*0.1<(c1+c2+c3)/3 <avg_current*1.1:
        print("test")
        c4 = 0.2/(1/6 - (0.2/c1 + 0.2/c2 + 0.2/c3))
        policies[count,:] = [c1, c2, c3, c4]
        count += 1
        
        if c4 >= C4_LIMITS[0] and c4 <= C4_LIMITS[1]:
            if c1 == 4.8 and c2 == 4.8 and c3 == 4.8:
                print('baseline')
            else:
                valid_policies[valid_count,:] = [c1, c2, c3, c4]
                valid_count += 1


policies = policies[0:count]
valid_policies = valid_policies[0:valid_count]


print('Count = ' + str(count))
print('Valid count = ' + str(valid_count))

np.savetxt(os.path.join(DIR, 'policies_' + FILENAME + '.csv'), valid_policies, delimiter=',', fmt='%1.3f')

surface_points.plot_surface(C1, C2, C3, C4_LIMITS, DIR, FILENAME)
