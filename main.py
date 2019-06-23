import cryptodata
import cryptofolio
from cryptoscreener import screenUniverse
import pandas as pd
import datetime
import matplotlib.pyplot as plt
from math import log
import sys
import csv
import time

# Historical data set
coindata = pd.read_csv('input/clean_coindata.csv')

# Rebalance functions here
def isRebalanceDate(date,freq):
	if freq.lower() == 'monthly':
		firstDayofMonth = datetime.datetime(date.year,date.month,1,0,0,0)
		return (firstDayofMonth == date)
	else:
		pass

# Read in user parameters
reader = csv.reader(open('parameters.csv', 'r'))
parameters = {}
for row in reader:
	k, v = row
	parameters[k] = v

# User parameters read in
backtestmode = str(parameters['Backtest Mode'])
minMarketCap = float(parameters['Minimum Market Cap'])
minimumListingPeriod = float(parameters['Minimum Listing Period']) + float(parameters['Offset'])
circulatingPct = float(parameters['Circulating Percentage'])
minExchanges = float(parameters['Minimum Exchange Listing'])
weightingScheme = parameters['Weighting Scheme']
minWeight = float(parameters['Minimum Weight'])
maxWeight = float(parameters['Maximum Weight'])
returnFreq = int(parameters['Offset'])
periodicity = parameters['Periodicity']
lookback = int(parameters['Lookback Window'])

# Clean the dates
dates = pd.to_datetime(coindata['Date'].copy().unique(),infer_datetime_format=True).sort_values(ascending=True).tolist()
coindata['Date'] = pd.to_datetime(coindata['Date'],infer_datetime_format=True)
coindata.set_index('Date', inplace=True)
coinPrices = coindata[['Coin','Close']].copy()

# Initial investment
indexLevel = []
initialInvestment = 1.0
firstRebalancePassed = False
portfolio = cryptofolio.Portfolio({},0.0)

# Backtest starts here
if backtestmode == 'True':
	startBacktest = pd.to_datetime(parameters['Start Date'])
	startptr = dates.index(startBacktest)
	dates = dates[startptr:]
	for date in dates:
		print(date)
		# Dictionary of prices
		latestPrices = pd.Series(coinPrices.ix[date].Close.values,index=coinPrices.ix[date].Coin.values).to_dict()

		# Initialize entry with equal weight
		if len(indexLevel) == 0:
			universe = list(latestPrices.keys())
			for coin in universe:
				weight = 1.0 / len(universe)	
				quantity = (initialInvestment * weight) / latestPrices[coin]
				portfolio.buy(coin,quantity)

		# Rebalance
		if isRebalanceDate(date,'monthly') and len(indexLevel) > 0:
			# Filter out unwanted coins based on marketcap, liquidity etc
			universe = screenUniverse(date-pd.DateOffset(days=1),minMarketCap,minimumListingPeriod,circulatingPct,minExchanges)
			
			# Remove coins which are manually screened away
			if parameters['Coins To Omit'] != '':

				coinstoremove = parameters['Coins To Omit'].split(';')
				print('Removing ' + ','.join(coinstoremove) + ' in the optimization...')
				universe_copy = universe
				universe = []

				for coin in universe_copy:
					if coin not in coinstoremove:
						universe.append(coin)

			if len(universe) < 2:
				weights = {}
				weights['bitcoin'] = 1.0
				print(weights)
			else:
				weights = portfolio.getMVOptimizedWeights(date-pd.DateOffset(days=1),universe,minWeight,maxWeight,returnFreq,periodicity,lookback)
			
			for coin in universe:
				if weightingScheme == 'MeanVariance':
					weight = weights[coin]
				else:
					weight = 1.0 / len(portfolio.getPositions().keys())

				quantity = portfolio.getValue(latestPrices) * weight / latestPrices[coin]

				if coin in list(portfolio.getPositions().keys()):
					portfolio.sell(coin,portfolio.getPositions()[coin])

				portfolio.buy(coin,quantity)

		indexLevel.append(portfolio.getValue(latestPrices))

	# Log base 10 for index level
	indexLevel_log = [log(price,10) for price in indexLevel]

	# Write the file to a csv file
	results = pd.DataFrame({'Dates':dates,'Index Level':indexLevel,'Log Index Level':indexLevel_log})
	results.to_csv('results/backtestResults_'+str(time.time())+'.csv',index=False)

	# For graphs popping up
	plt.plot_date(dates,indexLevel_log,'-')
	plt.title('Backtest Result')
	plt.gcf().autofmt_xdate()
	plt.show()

# Live mode
else:
	print('Performing optimization for ' + parameters['Start Date'] + '....')
	universeSelectionDate = pd.to_datetime(parameters['Start Date'])
	universe = screenUniverse(universeSelectionDate,minMarketCap,minimumListingPeriod,circulatingPct,minExchanges)

	# Remove coins which are manually screened away
	if parameters['Coins To Omit'] != '':

		coinstoremove = parameters['Coins To Omit'].split(';')
		print('Removing ' + ','.join(coinstoremove) + ' in the optimization...')
		universe_copy = universe
		universe = []

		for coin in universe_copy:
			if coin not in coinstoremove:
				universe.append(coin)

	print('Final weights:')
	weights = portfolio.getMVOptimizedWeights(universeSelectionDate,universe,minWeight,maxWeight,returnFreq,periodicity,lookback)
	print('Optimization successful! Writing results to final_weights.csv')

	with open('results/final_weights.csv','w') as f:
	    w = csv.writer(f)
	    w.writerow(weights.keys())
	    w.writerow(weights.values())

