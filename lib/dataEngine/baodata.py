import baostock as bs 
from lib.patterns.base import Base
from lib.patterns.singleton import Singleton
from pandas import DataFrame, Series
from datetime import datetime
from dateutil.relativedelta import relativedelta

class BaoDataClient(Base, metaclass=Singleton):
    def __init__(self):
        self.client:bs = bs 
        self.client.login()
        
    @classmethod
    def create(cls):
        return cls()
    
    
    
    def close(self):
        self.client.logout()
        
    
    def getViableStocks(self) -> list:
        today:datetime = datetime.today()
        specifiedDate:str = (today - relativedelta(days=today.day)).strftime("%Y-%m-%d")
        
        rs = self.client.query_all_stock(day=specifiedDate)
        data_list:list = []
        while (rs.error_code == '0') & rs.next():
            row = rs.get_row_data()
            
            if row[0].split(".")[0] in ("sz", "sh") and row[0].split(".")[1][:2] in ("60", "30", "00") and row[1] == "1":
                data_list.append(row[0])
        
        return data_list
    
    
    def get5MiuteBar(self, symbol:str, endDate:datetime = datetime.today()) -> Series:
        
        raw = self.client.query_history_k_data_plus(
            code=symbol, 
            fields="time,close",
            start_date=endDate.strftime("%Y-%m-%d"),
            end_date=endDate.strftime("%Y-%m-%d"),
            frequency="5")
        
        dataList:list = []   
        while (raw.error_code == '0') & raw.next():
            dataList.append(raw.get_row_data())
        result = DataFrame(dataList, columns=raw.fields)
        result["time"] = result["time"].apply(lambda x: datetime.strptime(x, "%Y%m%d%H%M%S%f"))
        result = result.set_index("time")
        return result["close"]
    
    def getDailyBar(self, symbol:str, endDate:datetime = datetime.today()) -> Series:
        raw = self.client.query_history_k_data_plus(
            code=symbol, 
            fields="date,close",
            start_date=(endDate - relativedelta(days=7)).strftime("%Y-%m-%d"),
            end_date=endDate.strftime("%Y-%m-%d"),
            frequency="d")
        
        dataList:list = []   
        while (raw.error_code == '0') & raw.next():
            dataList.append(raw.get_row_data())
        result = DataFrame(dataList, columns=raw.fields)
        result["date"] = result["date"].apply(lambda x: datetime.strptime(x, "%Y-%m-%d"))
        result = result.set_index("date")
        return result["close"]
        
    
    
    