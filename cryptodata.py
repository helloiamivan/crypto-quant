import pandas as pd
from bs4 import BeautifulSoup
import requests
import re
import json
import csv

def getCMCData(coinlist,start='20000101',end='29990101'):
    coinData = ['Date','Coin','Open','High','Low','Close','Volume','Marketcap']
    listSize = len(coinData)

    for coin in coinList:
        print('Getting historical data for ' + coin + '...')
        url = 'https://coinmarketcap.com/currencies/'+coin+'/historical-data/?start='+start+'&end='+end
        page = requests.get(url)
        soup = BeautifulSoup(page.text,'html.parser')
        data = soup.find_all("div", class_="table-responsive")

        for element in data[0].find_all('td'):
            stringElement = str(element)
            # If it is a date
            if "class=" in stringElement:
                dateStr = re.findall(r'<td class="text-left">(.*?)</td>', stringElement)[0]
                coinData.append(dateStr)
                coinData.append(coin)
            # If it is prices, volume or marketcap data
            else:
                numbers = re.findall(r'">(.*?)</td>', stringElement)[0]
                #numbers = re.findall(r"[-+]?\d*\.\d+|\d+", stringElement)[1]
                cleannumber = float(numbers.replace(',', '').replace('-','nan'))
                coinData.append(cleannumber)

    # Save all the data
    cleanData = [coinData[i:i+listSize] for i in range(0, len(coinData),listSize)]

    # Write to csv
    file = open('input/coindata.csv','w+')
    for item in cleanData:
        writer = csv.writer(file)
        writer.writerow(item)
    file.close()

    return file.name

def getCMCtickers(limit=100):
    request = "https://api.coinmarketcap.com/v1/ticker/?limit="+str(limit)
    response = requests.get(request)    
    tickers = json.loads(response.text)

    tickerList = []
    for element in tickers:
        tickerList.append(element['id'])

    return tickerList

def getCMCexchanges(coinlist):
    coinData = ['Number','Exchange','Pair','Volume','Price','Volume_Percent','Updated']
    listSize = len(coinData)

    allCoinsExchanges = {}

    for coin in coinList:
        print('Getting exchange data for ' + coin + '...')
        url = 'https://coinmarketcap.com/currencies/'+ coin + '/#markets'
        page = requests.get(url)
        soup = BeautifulSoup(page.text,'html.parser')
        data = soup.find_all("div", class_="table-responsive")
        exchanges = []
        
        for element in data[0].find_all('td'):
            stringElement = str(element)

            # Check for exchanges listed
            if '/exchanges/' in stringElement:
                exchange = re.findall(r'">(.*?)</a>', stringElement)[0]
                exchanges.append(exchange)

        # Check for unique exchange
        exchanges = list(set(exchanges))
        
        # Save into dictionary
        allCoinsExchanges[coin] = exchanges

        # Dump into a json file
        with open('input/exchangesdata.json', 'w+') as fp:
            json.dump(allCoinsExchanges, fp)
             
def cleanDataFrame(filepath):
    rawdata = pd.read_csv(filepath)
    coins = list(set(rawdata['Coin'].tolist()))

    # Set the index as date
    rawdata['Date'] = pd.to_datetime(rawdata['Date'],infer_datetime_format=True)
    rawdata.set_index('Date', inplace=True)

    # Now, loop through each coin and fill forward the date
    cleanData = pd.DataFrame()

    for coin in coins:
        # Data has to be sorted in ascending order before it can be casted into a different frequency
        temp = rawdata[rawdata['Coin'] == coin].sort_index(ascending=True).copy()
        cleanData = pd.concat([cleanData,temp.asfreq('D').ffill()])

    print('Clean data successfully saved in clean_coindata.csv')
    cleanData.to_csv('input/clean_coindata.csv')

if __name__ == "__main__":
    # Get the top n ranked coins in coinmarketcap
    coinList = getCMCtickers(50)

    getCMCexchanges(coinList)

    # Scrape and save all the data
    file = getCMCData(coinList)

    # Clean the dataframe of coins data
    cleanDataFrame(file)