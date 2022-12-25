from pandas import DataFrame, Series
from numpy import array
from sklearn.preprocessing import StandardScaler
from datetime import date

from PairTrading.lib.dataEngine import AlpacaDataClient

class PairCreator:
    _instance = None 
    # pair creator implements the singleton pattern
    def __new__(cls, clusterDF:DataFrame, dataClient:AlpacaDataClient):
        if cls._instance is None:
            cls._instance = super(PairCreator, cls).__new__(PairCreator)
        return cls._instance
    
    def __init__(self, clusterDF:DataFrame, dataClient:AlpacaDataClient):
        self.clusterDF:DataFrame = clusterDF
        self.dataClient:AlpacaDataClient = dataClient
        
    @classmethod
    def create(cls, clusterDF:DataFrame, client:AlpacaDataClient):
        return cls(clusterDF, client)
    
    def getFinalPairs(self, res:dict) -> dict[str, list]:
        finalPairs:dict = {}
        pairsDF:DataFrame = self._getTradeablePairs()
        viablePairs:list = [(val.split(",")[0], val.split(",")[1]) for val in pairsDF.index]
        
        tmpDict:dict = {}
        for pair1, pair2 in viablePairs:
            pair1DailyDF:array = array(self.dataClient.getDaily(pair1)["close"])
            pair2DailyDF:array = array(self.dataClient.getDaily(pair2)["close"])

            priceRatio:array = pair1DailyDF/ pair2DailyDF
                      
            if (priceRatio[-1] - priceRatio.mean()) / priceRatio.std() > 1:
                tmpDict[",".join([pair1, pair2])] = ((priceRatio[-1] - priceRatio.mean()) / priceRatio.std(), priceRatio.mean())
        tmpStd:list = list(Series({key:value[0] for key, value in tmpDict.items()}).sort_values(ascending=False).keys())
        for pair in tmpStd:
            finalPairs[pair] = (tmpDict[pair][0], tmpDict[pair][1])
        res["final_pairs"] = finalPairs 
        return res
    
    
    def _getTradeablePairs(self) -> DataFrame:
        
        pairCandidates:Series = Series(self._formPairs()).sort_values(ascending=False)
        pairData:array = array(pairCandidates).reshape(-1, 1)
        
        sc = StandardScaler()
        pairsDF:DataFrame = DataFrame(sc.fit_transform(pairData), index=pairCandidates.index, columns=["momentum_zscore"])     
        
        return pairsDF.loc[pairsDF["momentum_zscore"] > 1].sort_values(by=["momentum_zscore"], ascending=False)
                      
        
    def _formPairs(self) -> dict:
        pairCandidates:dict = {}       
        for clusterID in self.clusterDF["cluster_id"].unique():
            clusterDF = self.clusterDF.loc[self.clusterDF["cluster_id"] == clusterID].sort_values(by="momentum", ascending=False)
            head, tail = 0, len(clusterDF)-1
            while head < tail:
                pairCandidates[f"{clusterDF.iloc[head].name},{clusterDF.iloc[tail].name}"] = \
                abs(clusterDF.iloc[head].momentum - clusterDF.iloc[tail].momentum)
                head += 1
                tail -= 1
                
        return pairCandidates
    