from lib.dataEngine.baodata import BaoDataClient

client = BaoDataClient.create()

print(client.getViableStocks())