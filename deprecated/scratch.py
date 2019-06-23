import pandas as pd

rawdata = pd.read_csv('coindata.csv')
coins = list(set(rawdata['Coin'].tolist()))

# Set the index as date
rawdata['Date'] = pd.to_datetime(rawdata['Date'],infer_datetime_format=True)
rawdata.set_index('Date', inplace=True)

# Now, loop through each coin and fill forward the date
print(coins)
cleanData = pd.DataFrame()

for coin in coins:
    # Data has to be sorted in ascending order before it can be casted into a different frequency
    temp = rawdata[rawdata['Coin'] == coin].sort_index(ascending=True).copy()
    cleanData = pd.concat([cleanData,temp.asfreq('D').ffill()])

cleanData.to_csv('coindata.csv')