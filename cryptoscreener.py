import pandas as pd
import json
import urllib3
import csv
import sys
import urllib3
import cryptofolio

# Disable warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def screenUniverse(universeSelectionDate,minMarketCap,minimumListingPeriod,circulatingPct,minExchanges):
	# Get pandas data set
	coindata = pd.read_csv('input/clean_coindata.csv')

	dates = pd.to_datetime(coindata['Date'].copy().unique(),infer_datetime_format=True).sort_values(ascending=True).tolist()
	coindata['Date'] = pd.to_datetime(coindata['Date'],infer_datetime_format=True)

	# Filter market cap
	universe = coindata.ix[(coindata['Date'] == universeSelectionDate) & (coindata['Marketcap'] >= minMarketCap)]
	filter_mktcap = universe['Coin'].tolist()

	# Filter globalization
	filter_mktcap_glo = [] 
	exchanges = json.load(open('input/exchangesdata.json'))

	for coin in filter_mktcap:
		numberOfExchanges = len(exchanges[coin])
		if numberOfExchanges >= minExchanges:
			filter_mktcap_glo.append(coin)

	# Filter longevity
	filter_mktcap_glo_lon = []

	for coin in filter_mktcap_glo:
		tempcoinframe = coindata.ix[(coindata['Coin'] == coin)].dropna().copy()
		startDate = tempcoinframe['Date'].min()
		endDate = universeSelectionDate
		daysInExistence = (endDate - startDate).days
		if daysInExistence >= minimumListingPeriod:
			filter_mktcap_glo_lon.append(coin)

	# Filter volume traded
	filter_mktcap_glo_lon_vol = []
	http = urllib3.PoolManager()
	for coin in filter_mktcap_glo_lon:
		url = 'https://api.coinmarketcap.com/v1/ticker/' + coin
		response = http.request('GET',url)
		cleandata = json.loads(response.data)
		circulatingSupply = float(cleandata[0]['available_supply'])

		# Make volume to token volume
		tempcoinframe = coindata.ix[(coindata['Coin'] == coin)].copy()
		tempcoinframe['TokenVolume'] = tempcoinframe['Volume'] / tempcoinframe['Close']
		tempcoinframe = tempcoinframe.groupby(pd.Grouper(key='Date', freq='M')).sum()

		# Drop the last month and get the last 3 months only
		tempcoinframe.drop(tempcoinframe.tail(1).index,inplace=True)
		volList = tempcoinframe.tail(3)['TokenVolume'].tolist()
		
		if all(i >= circulatingSupply * circulatingPct for i in volList) == True:
			filter_mktcap_glo_lon_vol.append(coin)

	# # Write this to a file
	# file = open('filtered_coins.txt','w+')
	# file.writelines(["%s\n" % item  for item in filter_mktcap_glo_lon_vol])
	return filter_mktcap_glo_lon_vol
