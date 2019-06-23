import pandas as pd
import numpy as np
from math import sqrt
from cvxopt import matrix
from cvxopt.blas import dot 
from cvxopt.solvers import qp, options
import matplotlib.pyplot as plt
import csv

# Settings here
#start = pd.to_datetime('2017/01/31')
end = pd.to_datetime('2018/01/31')
start = end - pd.DateOffset(days=365) 
returnFreq = 1
minWgtConstraint = 0.01
maxWgtConstraint = 0.25
periodicity = 'Monthly'

# Historical data set
coindata = pd.read_csv('coindata.csv')

# Filtered coin list (Add a manual step to this)
universe = [line.rstrip('\n') for line in open('filtered_coins.txt')]

# Clean the dates and set it as the index
dates = pd.to_datetime(coindata['Date'].copy().unique(),infer_datetime_format=True).sort_values(ascending=True).tolist()
coindata['Date'] = pd.to_datetime(coindata['Date'],infer_datetime_format=True)
#coindata = coindata.ix[(coindata['Date'] >= start) & (coindata['Date'] <= end)].copy()

# Options set 
options['show_progress'] = False

# Set date as index
coindata.set_index('Date', inplace=True)

# Get the prices
coinPrices = coindata[['Coin','Close']].copy()

# List of return vectors
returnLists = []
avgReturns = []

# Construct the return vectors for each coin
for coinptr in universe:
	temp = coinPrices.ix[coinPrices['Coin'] == coinptr]['Close'].sort_index(ascending=True).copy()
	if periodicity == 'Monthly':
		temp = temp.asfreq('M').ffill()
	temp = temp.pct_change(periods=returnFreq).dropna().copy()
	temp = temp[start:end].copy()
	returnLists.append(temp.values.tolist())
	avgReturns.append(np.mean(temp.values.tolist()))
	temp.to_csv('debug/'+coinptr+'returns.csv')

# Contruct covariance matrix
cov_matrix = matrix(np.cov(returnLists))

# Perform MV optimization here
# Number of assets
n = len(universe)

# Covariance matrix
S = cov_matrix
#print(S)
# Expected returns (historical in this case)
q = matrix(avgReturns)

# Portfolio must be fully invested (ie. Weights must sum to 1)
A_ones = np.matrix(np.ones((1,n)))
A = matrix(np.vstack((A_ones)))
b = matrix(np.matrix([1.0]).T)

# Min/Max Weight constraints
# Min weight must be > 0
minWgt = matrix(np.zeros((n,n)))
minWgt[::n+1] = -1.0
maxWgt = np.eye(n,n)
G = matrix(np.vstack([minWgt,maxWgt]))

# Max weight bounds
lowerBound = matrix(np.matrix(np.ones((n,1)))) * -minWgtConstraint
upperBound = matrix(np.matrix(np.ones((n,1)))) * maxWgtConstraint
h = matrix(np.vstack([lowerBound,upperBound]))

# Solve for tangency portfolio with cvx opt
soln = qp(S, -q, G, h, A, b)
x_opt = np.matrix(soln['x'])
x_opt = np.array(np.reshape(x_opt, (1,n)))[0]

# plt.figure(1, figsize=(6,6))
# plt.pie(x_opt, labels=universe, autopct='%1.1f%%')

# Get the allocation weights
allocation = list(zip(universe,x_opt*100))

print('Optimal % weights for each coin:')
for coinweightpair in allocation:
	print(coinweightpair)

with open('final_weights.csv','w+') as out:
    csv_out = csv.writer(out)
    csv_out.writerow(['Coin','Percentage_Weight'])

    for row in allocation:
        csv_out.writerow(row)
