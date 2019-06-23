import pandas as pd
import numpy as np
from math import sqrt
from cvxopt import matrix
from cvxopt.blas import dot 
from cvxopt.solvers import qp, options
import matplotlib.pyplot as plt
import csv

class Portfolio:

	def __init__(self,positions,cash):
		self.positions = positions
		self.cash = cash

	def getPositions(self):
		return self.positions

	def getCash(self):
		return self.cash

	def getTransactionCost(self):
		pass

	def buy(self,coin,quantity):
		if coin in list(self.positions.keys()):
			self.positions[coin] += quantity
		else:
			self.positions[coin] = quantity

	def sell(self,coin,quantity):
		if coin in list(self.positions.keys()):
			if self.positions[coin] < quantity:
				self.positions[coin] = 0.0
				print('Warning, quantity you are trying to sell is ' + 
					'more than what you hold, selling max available.')
			else:
				self.positions[coin] -= quantity
		else:
			print('No short selling allowed!')

	# Gets the latest portfolio value
	def getValue(self,lastpricemap):
		value = float(0.0)	
		for coin in self.positions:
			value += lastpricemap[coin] * self.positions[coin]
		value = value + self.getCash()
		return value

	def getWeights(self,lastpricemap):
		weights = dict()
		portfolioValue = self.getValue(lastpricemap)

		for coin in self.positions:
			weights[coin] = (self.positions[coin] * lastpricemap[coin]) / portfolioValue
		return weights

	# This should return a dictionary of coins -> weights. Weights should sum to 1
	def getMVOptimizedWeights(self,optDate,universe,minWgtConstraint,maxWgtConstraint,returnFreq,periodicity,window_days):
		
		start = optDate - pd.DateOffset(days=window_days)
		end = optDate

		# Historical data set
		coindata = pd.read_csv('input/clean_coindata.csv')

		# Clean the dates and set it as the index
		dates = pd.to_datetime(coindata['Date'].copy().unique(),infer_datetime_format=True).sort_values(ascending=True).tolist()
		coindata['Date'] = pd.to_datetime(coindata['Date'],infer_datetime_format=True)

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

		# Get the allocation weights
		allocation = dict(zip(universe,x_opt))
		print(allocation)
		
		return allocation