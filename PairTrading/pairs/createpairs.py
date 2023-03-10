from pandas import DataFrame, Series, concat
from numpy import array, dot
from sklearn.preprocessing import StandardScaler
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from lib.dataEngine import AlpacaDataClient
from lib.patterns import Singleton, Base

from tqdm import tqdm




class PairCreator(Base, metaclass=Singleton):
    
    def __init__(self, clusterDF:DataFrame, dataClient:AlpacaDataClient):
        self.clusterDF:DataFrame = clusterDF
        self.dataClient:AlpacaDataClient = dataClient
        
        
    @classmethod
    def create(cls, clusterDF:DataFrame, client:AlpacaDataClient):
        return cls(clusterDF, client)
    
    def getFinalPairs(self, trainDate:date) -> dict[str, list]:
        self._getMomentum()
        res = {"time": trainDate.strftime("%Y-%m-%d")}
        finalPairs:dict = {}
        pairsDF:DataFrame = self._getTradeablePairs()
        viablePairs:list = [(val.split(",")[0], val.split(",")[1]) for val in pairsDF.index]
                
        tmpDict:dict = {}
        for pair in viablePairs:      
            volumeRatio = self.dataClient.getDaily(pair[0]).values.reshape(-1, 1) / \
                self.dataClient.getDaily(pair[0]).values.reshape(-1, 1)
            ss = StandardScaler()
            if abs(ss.fit_transform(volumeRatio)[-1][0]) < 1:
                tmpDict[",".join(pair)] = (pairsDF.loc[",".join(pair)]["momentum"] - pairsDF.loc[",".join(pair)]["mean"]) / \
                    pairsDF.loc[",".join(pair)]["momentum_zscore"]

                
        for pair in list(tmpDict.keys()):
            finalPairs[pair] = tmpDict[pair]
        res["final_pairs"] = finalPairs 
        return res
    
    
    def _getTradeablePairs(self) -> DataFrame:
        
        pairCandidates:Series = Series(self._formPairs()).sort_values(ascending=False)
        pairData:array = array(pairCandidates).reshape(-1, 1)
        
        sc = StandardScaler()
        pairsDF:DataFrame = concat({
            "momentum_zscore": Series(sc.fit_transform(pairData).flatten(), index=pairCandidates.index), 
            "momentum": pairCandidates, 
            "mean": Series(sc.mean_[0], index=pairCandidates.index)}, axis=1)  
        
        return pairsDF.loc[pairsDF["momentum_zscore"] >= 1].\
            loc[pairsDF["momentum_zscore"] < 2].sort_values(by=["momentum_zscore"], ascending=False)
                      
        
    def _formPairs(self) -> dict:
        pairCandidates:dict = {}       
        for clusterID in self.clusterDF["cluster_id"].unique():
            clusterDF = self.clusterDF.loc[self.clusterDF["cluster_id"] == clusterID].sort_values(by="momentum", ascending=False)
            head, tail = 0, len(clusterDF)-1
            while head < tail:
                pairCandidates[f"{clusterDF.iloc[head].name},{clusterDF.iloc[tail].name}"] = \
                abs(clusterDF.iloc[head]["momentum"] - clusterDF.iloc[tail]["momentum"])
                head += 1
                tail -= 1
                
        return pairCandidates
    
    def _getMomentum(self) -> None:
        for stock in tqdm(self.clusterDF.index, desc="get latest momentum data"):
            currPrice:float = self.dataClient.getLastMinute(stock)
            prevPrice:float = self.dataClient.getMonthly(stock, 10).iloc[-2]["close"]            
            self.clusterDF.loc[stock]["momentum"] = (currPrice - prevPrice) / prevPrice
    
