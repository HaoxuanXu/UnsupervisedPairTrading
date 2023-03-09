import baostock as bs 
from lib.patterns.base import Base
from lib.patterns.singleton import Singleton
from lib.patterns.timer import timer
from lib.patterns.retry import retry
from pandas import DataFrame, Series, to_numeric
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import logging 
from tqdm import tqdm
import concurrent.futures
from lib.dataEngine.asharedata import AShareDataClient


logger = logging.getLogger(__name__)

class BaoDataClient(Base, metaclass=Singleton):
    def __init__(self):
        self.client:bs = bs 
        self.client.login()
        
    @classmethod
    def create(cls):
        return cls()
    
    
    
    def close(self):
        self.client.logout()
        
    @timer()
    def getViableStocks(self) -> list:
        today:datetime = datetime.today()
        specifiedDate:str = (today - relativedelta(days=today.day)).strftime("%Y-%m-%d")
        res:list = []
        rs = self.client.query_all_stock(day=specifiedDate)
        data_list:list[str] = []
        while (rs.error_code == '0') & rs.next():
            row = rs.get_row_data()       
            if row[0].split(".")[0] in ("sz", "sh") and row[0].split(".")[1][:2] in ("60", "30", "00") and row[1] == "1":
                data_list.append(row[0])
                
        for symbol in tqdm(data_list, desc="total SH and SZ symbols"):
            if AShareDataClient.get_price(symbol.replace(".", ""), frequency="1d", count=10).mean() > 5:
                res.append(symbol)
        
        return res 
        
        # with concurrent.futures.ThreadPoolExecutor() as executor:     
        #     futures:dict = {}    
        #     for symbol in data_list:
        #         futures[symbol] = executor.submit(self._getDailyBarRaw, symbol=symbol)
        #     for symbol in concurrent.futures.as_completed(futures):
        #         if self._formatRawDailyBar(futures[symbol]).mean() > 5:
        #             res.append(symbol)
            
        return res 
    
    
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
        return to_numeric(result["close"])
    
    @retry(max_retries=3, retry_delay=5, incremental_backoff=2, logger=logger)
    def getDailyBar(self, symbol:str, endDate:datetime = datetime.today()) -> Series:
        raw = self._getDailyBarRaw(symbol, endDate=endDate)    
        return self._formatRawDailyBar(raw)
        
    @retry(max_retries=3, retry_delay=5, incremental_backoff=2, logger=logger)
    def _getDailyBarRaw(self, symbol:str, endDate:datetime = datetime.today()):
        return self.client.query_history_k_data_plus(
            code=symbol, 
            fields="date,close",
            start_date=(endDate - relativedelta(days=7)).strftime("%Y-%m-%d"),
            end_date=endDate.strftime("%Y-%m-%d"),
            frequency="d")
        
    def _formatRawDailyBar(self, raw) -> Series:
        dataList:list = []   
        while (raw.error_code == '0') & raw.next():
            dataList.append(raw.get_row_data())
        result = DataFrame(dataList, columns=raw.fields)
        result["date"] = result["date"].apply(lambda x: datetime.strptime(x, "%Y-%m-%d"))
        result = result.set_index("date")
        return to_numeric(result["close"])
        
    
    
    