from PairTrading.data.fundamentals.common import FundamentalsBase
from PairTrading.data.fundamentals.util import *

import pandas as pd
import numpy as np
import statsmodels.api as sm
from datetime import datetime


import warnings
warnings.filterwarnings("ignore")

class FirmCharGetter(FundamentalsBase):

    def __init__(self, rawFile:dict):
        super().__init__(rawFile)
        
        # technicalData as pandas dataframe
        self.monthlyBar:pd.DataFrame = None 
        self.weeklyBar:pd.DataFrame = None
        self.dailyBar:pd.DataFrame = None 
        
        
    @classmethod
    def create(cls, rawFile:dict):
        return cls(rawFile)
    
    def setMonthlyBar(self, bar:pd.DataFrame) -> None:
        self.monthlyBar = bar 
        
    def setDailyBar(self, bar:pd.DataFrame) -> None:
        self.dailyBar = bar 
        
    def setWeeklyBar(self, bar:pd.DataFrame) -> None:
        self.weeklyBar = bar 
    
    
    def getBeta(self) -> float:
        """
            beta -- Beta:
            Estimated market beta from weekly returns and equal weighted market returns for 3 years 
            ending month t-1 with at least 52 weeks of returns.
        """
        return self.technicals["Beta"]
    
    def getBm(self) -> float:
        """ 
            bm -- Book-to-market:
            Book value of equity (ceq) divided by end of fiscal-year-end market capitalization.
        """       
        i:int = getFirstNonNullIndexPair(
            arr1=self.balanceSheet,
            arr2=self.balanceSheet,
            feature1Name="totalAssets",
            feature2Name="totalLiab"
            )
        
        bookValue:float = (float(self.balanceSheet[i]["totalAssets"])- float(self.balanceSheet[i]["totalLiab"])) 
        marketCap:float = self.highlights["MarketCapitalization"]
        
        return bookValue / marketCap
    
    def getCash(self) -> float:
        """ 
            cash -- Cash holdings:
            Cash and cash equivalents divided by average total assets.
        """
        
        i:int = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="cash"
        )
        iRange:list = getNonNullIndexRange(
            arr=self.balanceSheet,
            featureName="totalAssets"
        )
        
        cashEquivalents:float = float(self.balanceSheet[i]["cash"])
        avgTotalAssets:float = sum([float(self.balanceSheet[i]["totalAssets"]) for i in iRange]) / len(iRange)
        
        return cashEquivalents / avgTotalAssets
    
    def getCashDebt(self) -> float:
        """
            cashdebt -- Cash flow to debt:
            Earnings before depreciation and extraordinary items (ib+dp) divided by avg. total liabilities (lt).
        """
        earnings:float = self.shareStats["SharesOutstanding"] * self.highlights["EarningsShare"]
        
        iRange:list = getNonNullIndexRange(
            arr=self.balanceSheet,
            featureName="totalAssets"
        )
        avgTotalAssets:float = sum([float(self.balanceSheet[i]["totalAssets"]) for i in iRange]) / len(iRange)
        
        return earnings / avgTotalAssets
    
    def getCashPr(self) -> float:
        """
            cashpr -- Cash productivity:
            Fiscal year end market capitalization plus long term debt (dltt) minus total assets (at) divided by cash and equivalents (che).
        """
        marketCap:float = self.highlights["MarketCapitalization"]
        
        iDebt:int = getFirstNonNullIndexPair(
            arr1=self.balanceSheet, 
            arr2=self.balanceSheet, 
            feature1Name="longTermDebt", 
            feature2Name="totalAssets"
        )
        longTermDebt:float = float(self.balanceSheet[iDebt]["longTermDebt"])
        totalAsset:float = float(self.balanceSheet[iDebt]["totalAssets"])
        
        iCash:int = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="cash"
        )
        cashEquivalents:float = float(self.balanceSheet[iCash]["cash"])
        
        return (marketCap + longTermDebt - totalAsset) / cashEquivalents
        
    def getCfp(self) -> float:
        """
            cfp -- cash flow to price ratio:
            Operating cash flows divided by fiscal-year-end market capitalization
        """
        iCash:int = getFirstNonNullIndex(
            arr=self.cashFlow, 
            featureName="totalCashFromOperatingActivities")
        operatingCashFlow:float = float(self.cashFlow[iCash]["totalCashFromOperatingActivities"])
        marketCap:float = self.highlights["MarketCapitalization"]
        
        return operatingCashFlow / marketCap
          
    def getChcsho(self) -> float:
        """
            Change in shares outstanding:
            Annual percent change in shares outstanding (csho).
        """
        iCurrShares:int = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="commonStockSharesOutstanding"
        )
        currSharesOutstanding:float = float(self.balanceSheet[iCurrShares]["commonStockSharesOutstanding"])
        iPrevShares:int = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="commonStockSharesOutstanding",
            initIndex=4
        )
        prevSharesOutstanding:float = float(self.balanceSheet[iPrevShares]["commonStockSharesOutstanding"])
        
        return (currSharesOutstanding - prevSharesOutstanding) / prevSharesOutstanding
        
    
    def getChinv(self) -> float:
        """
            chinv -- Change in inventory:
            Change in inventory (inv) scaled by average total assets (at).
        """
        iCurrInv:int = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="inventory")
        iPrevInv:int = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="inventory",
            initIndex=4)
        
        changeInventory = float(self.balanceSheet[iCurrInv]["inventory"]) - float(self.balanceSheet[iPrevInv]["inventory"])
        iRange:list = getNonNullIndexRange(
            arr=self.balanceSheet,
            featureName="totalAssets"
        )
        avgTotalAssets:float = sum([float(self.balanceSheet[i]["totalAssets"]) for i in iRange]) / len(iRange)
        
        return changeInventory / avgTotalAssets
    
    def getAgr(self) -> float:
        """
            agr -- Asset growth:
            Annual percent change in total assets (at).
        """
        iCurr:int = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="totalAssets")
        iPrev:int = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="totalAssets",
            initIndex=4)
        currAsset:float = float(self.balanceSheet[iCurr]["totalAssets"]) 
        prevAsset:float = float(self.balanceSheet[iPrev]["totalAssets"])
        
        return (currAsset - prevAsset) / prevAsset
    
    def getCurrat(self) -> float:
        """
            currat -- Current ratio:
            Current assets / current liabilities
        """
        iCurr:int = getFirstNonNullIndexPair(
            arr1=self.balanceSheet, 
            arr2=self.balanceSheet, 
            feature1Name="totalCurrentAssets",
            feature2Name="totalCurrentLiabilities"
        )
        currentAsset:float = float(self.balanceSheet[iCurr]["totalCurrentAssets"])
        currentLiability:float = float(self.balanceSheet[iCurr]["totalCurrentLiabilities"])
        
        return currentAsset / currentLiability      
    
    def getPchcurrat(self) -> float:
        """
            pchcurrat -- % change in current ratio:
            Percent change in currat.
        """
        iCurr:int = getFirstNonNullIndexPair(
            arr1=self.balanceSheet, 
            arr2=self.balanceSheet, 
            feature1Name="totalCurrentAssets",
            feature2Name="totalCurrentLiabilities"
        )
        iPrev:int = getFirstNonNullIndexPair(
            arr1=self.balanceSheet, 
            arr2=self.balanceSheet, 
            feature1Name="totalCurrentAssets",
            feature2Name="totalCurrentLiabilities",
            initIndex=4
        )
        currentAsset:float = float(self.balanceSheet[iCurr]["totalCurrentAssets"])
        currentLiability:float = float(self.balanceSheet[iCurr]["totalCurrentLiabilities"])
        prevAsset:float = float(self.balanceSheet[iPrev]["totalCurrentAssets"])
        prevLiability:float = float(self.balanceSheet[iPrev]["totalCurrentLiabilities"])
        
        return (currentAsset/currentLiability - prevAsset/prevLiability) / (prevAsset/prevLiability)
        
    
    def getRoaq(self) -> float:
        """
            roaq -- Return on assets:
            Income before extraordinary items (ibq) divided by one quarter lagged total assets (atq).
        """
        return self.highlights["ReturnOnAssetsTTM"]
    
    def getRoeq(self) -> float:
        """
            roeq -- Return on equity:
            Earnings before extraordinary items divided by lagged common shareholders' equity.
        """
        return self.highlights["ReturnOnEquityTTM"]
    
    def getDy(self) -> float:
        """
            dy -- Dividend to price:
            Total dividends (dvt) divided by market capitalization at fiscal year-end.
        """
        iRange:list[int] = getNonNullIndexRange(
            arr=self.cashFlow, 
            featureName="dividendsPaid"
        )
        dividends:float = sum([float(self.cashFlow[i]["dividendsPaid"]) for i in iRange])
        marketCap:float = self.highlights["MarketCapitalization"]
        
        return dividends / marketCap
        
    def getIPO(self) -> float:
        ipoDate:datetime = datetime.strptime(self.general["IPODate"], "%Y-%m-%d")
        return 1 if (datetime.today() - ipoDate).years < 1 else 0
    
    def getRd(self) -> float:
        """
            rd -- R&D increase:
            An indicator variable equal to 1 if R&D expense as a percentage of total assets has an increase greater than 5%.
        """
        iCurr:int = getFirstNonNullIndexPair(
            arr1=self.incomeStatement, 
            arr2=self.balanceSheet, 
            feature1Name="researchDevelopment", 
            feature2Name="totalAssets"
        )
        iPrev:int = getFirstNonNullIndexPair(
            arr1=self.incomeStatement, 
            arr2=self.balanceSheet, 
            feature1Name="researchDevelopment", 
            feature2Name="totalAssets",
            initIndex=4
        )
        
        currRD:float = float(self.incomeStatement[iCurr]["researchDevelopment"]) / float(self.balanceSheet[iCurr]["totalAssets"])
        prevRD:float = float(self.incomeStatement[iPrev]["researchDevelopment"]) / float(self.balanceSheet[iPrev]["totalAssets"])
        
        rd:float = 1 if (currRD - prevRD) / prevRD > 0.05 else 0
        
        return rd 
    
    def getRdMve(self) -> float:
        """
            rd_mve: R&D expense divided by end-of-fiscal-year market capitalization
        """
        iCurrRange:list = getNonNullIndexRange(
            arr=self.incomeStatement,
            featureName="researchDevelopment"
        )
        
        marketCap:float = self.highlights["MarketCapitalization"]
        rd:float = sum([float(self.incomeStatement[i]["researchDevelopment"]) for i in iCurrRange])
        
        return rd / marketCap
    
    def getChtx(self) -> float:
        """
            chtx -- Change in tax expense:
            Percent change in total taxes (txtq) from quarter t-4 to t.
        """
        iCurr:int = getFirstNonNullIndex(
            arr=self.incomeStatement, 
            featureName="taxProvision")
        iPrev:int = getFirstNonNullIndex(
            arr=self.incomeStatement, 
            featureName="taxProvision",
            initIndex=4)
        
        currTax:float = float(self.incomeStatement[iCurr]["taxProvision"])
        prevTax:float = float(self.incomeStatement[iPrev]["taxProvision"])
        
        return (currTax - prevTax) / prevTax 
    
    def getEp(self) -> float:
        """
            ep -- Earnings to price:
            Annual income before extraordinary items (ib) divided by end of fiscal year market cap.
        """
        iRange:list[int] = getNonNullIndexRange(
            arr=self.incomeStatement, 
            featureName="incomeBeforeTax"
        )
        income:float = sum([float(self.incomeStatement[i]["incomeBeforeTax"]) for i in iRange])
        marketCap:float = self.highlights["MarketCapitalization"]
        
        return income / marketCap
    
    def getGma(self) -> float:
        """
            gma -- Gross profitability:
            Revenues (revt) minus cost of goods sold (cogs) divided by lagged total assets (at).
        """
        iLagged:int = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="totalAssets",
            initIndex=3)
        
        iPair:int = getFirstNonNullIndexPair(
            arr1=self.incomeStatement, 
            arr2=self.incomeStatement, 
            feature1Name="totalRevenue", 
            feature2Name="costOfRevenue")
        
        revenue:float = float(self.incomeStatement[iPair]["totalRevenue"])
        cogs:float = float(self.incomeStatement[iPair]["costOfRevenue"])
        laggedTotalAssets:float = float(self.balanceSheet[iLagged]["totalAssets"])
        
        return (revenue - cogs) / laggedTotalAssets
        
    
    def getLev(self) -> float:
        """
            lev -- Leverage:
            Total liabilities (lt) divided by fiscal year end market capitalization.
        """
        iCurr = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="totalLiab"
        )
        totalLiab:float = float(self.balanceSheet[iCurr]["totalLiab"])
        marketCap:float = self.highlights["MarketCapitalization"]
        
        return totalLiab / marketCap
    
    def getInvest(self) -> float:
        """
            invest -- Capital expenditures and inventory:
            Annual change in gross property, plant, and equipment (ppegt) + 
            annual change in inventories (invt) all scaled by lagged total assets (at).
        """
        iPpegCurr, iPpegPrev = getFirstNonNullIndexPairDistance(
            arr1=self.balanceSheet, 
            arr2=self.balanceSheet, 
            feature1Name="propertyPlantEquipment", 
            feature2Name="propertyPlantEquipment")
        
        iInvCurr, iInvPrev = getFirstNonNullIndexPairDistance(
            arr1=self.balanceSheet, 
            arr2=self.balanceSheet, 
            feature1Name="inventory", 
            feature2Name="inventory")
        
        iLagged = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="totalAssets")
        
        ppegChange:float = (float(self.balanceSheet[iPpegCurr]["propertyPlantEquipment"]) - float(self.balanceSheet[iPpegPrev]["propertyPlantEquipment"]))
        invChange:float = (float(self.balanceSheet[iInvCurr]["inventory"]) - float(self.balanceSheet[iInvPrev]["inventory"]))
        laggedTotalAssets:float = float(self.balanceSheet[iLagged]["totalAssets"])
        
        return (ppegChange + invChange) / laggedTotalAssets
    
    def getQuick(self) -> float:
        """
            quick -- Quick ratio:
            (current assets - inventory) / current liabilities.
        """
        iAsset:int = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="totalCurrentAssets"
        )
        iInv:int = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="inventory"
        )
        iLiab:int = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="totalCurrentLiabilities"
        )
        currAsset:float = float(self.balanceSheet[iAsset]["totalCurrentAssets"])
        currInv:float = float(self.balanceSheet[iInv]["inventory"])
        currLiab:float = float(self.balanceSheet[iLiab]["totalCurrentLiabilities"])
        
        return (currAsset - currInv) / currLiab
    
    def getPchquick(self) -> float:
        """
            pchquick -- % change in quick ratio
            Percent change in quick
        """
        iCurrAsset, iPrevAsset = getFirstNonNullIndexPairDistance(
            arr1=self.balanceSheet, 
            arr2=self.balanceSheet, 
            feature1Name="totalCurrentAssets", 
            feature2Name="totalCurrentAssets"
        )
        iCurrInv, iPrevInv = getFirstNonNullIndexPairDistance(
            arr1=self.balanceSheet, 
            arr2=self.balanceSheet, 
            feature1Name="inventory", 
            feature2Name="inventory"
        )
        iCurrLiab, iPrevLiab = getFirstNonNullIndexPairDistance(
            arr1=self.balanceSheet, 
            arr2=self.balanceSheet, 
            feature1Name="totalCurrentLiabilities", 
            feature2Name="totalCurrentLiabilities"
        )
        
        currAsset:float = float(self.balanceSheet[iCurrAsset]["totalCurrentAssets"])
        prevAsset:float = float(self.balanceSheet[iPrevAsset]["totalCurrentAssets"])
        currLiab:float = float(self.balanceSheet[iCurrLiab]["totalCurrentLiabilities"])
        prevLiab:float = float(self.balanceSheet[iPrevLiab]["totalCurrentLiabilities"])
        currInv:float = float(self.balanceSheet[iCurrInv]["inventory"])
        prevInv:float = float(self.balanceSheet[iPrevInv]["inventory"])
        
        return ((currAsset-currInv)/currLiab - (prevAsset-prevInv)/prevLiab) / ((prevAsset-prevInv)/prevLiab)
        
         
    def getDolvol(self) -> float:
        """
            dolvol -- Dollar trading volume:
            Natural log of trading volume times price per share from month t-2.
        """
        if self.monthlyBar.empty:
            raise ValueError("the monthly bar variable is empty")
        
        return np.log(self.monthlyBar.iloc[-2]["volume"] * self.monthlyBar.iloc[-2]["close"])
    
    def getEgr(self) -> float:
        """
            egr -- Growth in common shareholder equity:
            Annual percent change in book value of equity (ceq).
        """
        iCurr:int = getFirstNonNullIndexPair(
            arr1=self.balanceSheet, 
            arr2=self.balanceSheet, 
            feature1Name="totalAssets", 
            feature2Name="totalLiab"
        )
        iPrev:int = getFirstNonNullIndexPair(
            arr1=self.balanceSheet, 
            arr2=self.balanceSheet, 
            feature1Name="totalAssets", 
            feature2Name="totalLiab",
            initIndex=iCurr+4)
        
        currBook:float = float(self.balanceSheet[iCurr]["totalAssets"]) / float(self.balanceSheet[iCurr]["totalLiab"])
        prevBook:float = float(self.balanceSheet[iPrev]["totalAssets"]) / float(self.balanceSheet[iPrev]["totalLiab"])
        
        return (currBook - prevBook) / prevBook
    
    def getLgr(self) -> float:
        """
            lgr -- Growth in long-term debt:
            Annual percent change in total liabilities (lt).
        """
        iCurr, iPrev = getFirstNonNullIndexPairDistance(
            arr1=self.balanceSheet, 
            arr2=self.balanceSheet, 
            feature1Name="totalLiab", 
            feature2Name="totalLiab"
        )
        currLiab:float = float(self.balanceSheet[iCurr]["totalLiab"])
        prevLiab:float = float(self.balanceSheet[iPrev]["totalLiab"])
        
        return (currLiab - prevLiab) / prevLiab
        
    
    def getPs(self) -> float:
        """
            ps -- Financial statements score:
            Sum of 8 indicator variables for fundamental performance
            https://www.investopedia.com/terms/p/piotroski-score.asp
        """
        # profitability criteria
        iIncome:int = getFirstNonNullIndex(
            arr=self.cashFlow, 
            featureName="netIncome")
        
        netIncomeInd:float = 1 if float(self.cashFlow[iIncome]["netIncome"]) > 0 else 0
        roaInd:float = 1 if self.highlights["ReturnOnAssetsTTM"] > 0 else 0
        
        iCash:int = getFirstNonNullIndex(
            arr=self.cashFlow, 
            featureName="totalCashFromOperatingActivities")
        operatingCashFlow:float = float(self.cashFlow[iCash]["totalCashFromOperatingActivities"])
        netIncome:float = float(self.cashFlow[iIncome]["netIncome"])
        
        operatingCashFlowInd:float = 1 if operatingCashFlow > 0 else 0
        netIncomeInd:float = 1 if operatingCashFlow > netIncome else 0
        
        # Leverage, Liquidity, and Source of Funds Criteria
        iCurrDebt, iPrevDebt = getFirstNonNullIndexPairDistance(
            arr1=self.balanceSheet, 
            arr2=self.balanceSheet, 
            feature1Name="longTermDebt", 
            feature2Name="longTermDebt"
        )
        iCurrCurrent, iPrevCurrent = getFirstNonNullIndexPairDistance(
            arr1=self.balanceSheet,
            arr2=self.balanceSheet,
            feature1Name="totalCurrentAssets",
            feature2Name="totalCurrentLiabilities"
        )
        currAsset:float = float(self.balanceSheet[iCurrCurrent]["totalCurrentAssets"])
        prevAsset:float = float(self.balanceSheet[iPrevCurrent]["totalCurrentAssets"])
        currLiab:float = float(self.balanceSheet[iCurrCurrent]["totalCurrentLiabilities"])
        prevLiab:float = float(self.balanceSheet[iPrevCurrent]["totalCurrentLiabilities"])
        currDebt:float = float(self.balanceSheet[iCurrDebt]["longTermDebt"])
        prevDebt:float = float(self.balanceSheet[iPrevDebt]["longTermDebt"])
        
        currCurrentRatio:float = currAsset / currLiab
        prevCurrentRatio:float = prevAsset / prevLiab
        
        longTermDebtInd:float = 1 if currDebt < prevDebt else 0
        currRatioInd:float = 1 if currCurrentRatio > prevCurrentRatio else 0
        
        # Operating Efficiency Criteria
        iCurrProfitRange:list = getNonNullIndexRange(
            arr=self.incomeStatement,
            featureName="grossProfit"        
        )
        iPrevProfitRange:list = getNonNullIndexRange(
            arr=self.incomeStatement,
            featureName="grossProfit",
            initIndex=iCurrProfitRange[-1] + 4
        )
        
        currYearGrossProfit:float = sum([float(self.incomeStatement[i]["grossProfit"]) for i in iCurrProfitRange])
        prevYearGrossProfit:float = sum([float(self.incomeStatement[i]["grossProfit"]) for i in iPrevProfitRange])
        
        iCurrAsset, iPrevAsset = getFirstNonNullIndexPairDistance(
            arr1=self.balanceSheet, 
            arr2=self.balanceSheet, 
            feature1Name="totalAssets", 
            feature2Name="totalAssets")
        
        iCurrAsset2, iPrevAsset2 = getFirstNonNullIndexPairDistance(
            arr1=self.balanceSheet, 
            arr2=self.balanceSheet, 
            feature1Name="totalAssets", 
            feature2Name="totalAssets",
            initIndex=4)
        
        
        iCurrRevRange:list = getNonNullIndexRange(
            arr=self.incomeStatement, 
            featureName="totalRevenue")
        
        iPrevRevRange:list = getNonNullIndexRange(
            arr=self.incomeStatement,
            featureName="totalRevenue",
            initIndex=iCurrRevRange[-1]+1
        )
        
        currTotalRevenue:float = sum([float(self.incomeStatement[i]["totalRevenue"]) for i in iCurrRevRange])
        prevTotalRevenue:float = sum([float(self.incomeStatement[i]["totalRevenue"]) for i in iPrevRevRange])
        
        curTotalAssets:float = float(self.balanceSheet[iCurrAsset]["totalAssets"])
        prevTotalAssets:float = float(self.balanceSheet[iPrevAsset]["totalAssets"])
        
        curTotalAssets2:float = float(self.balanceSheet[iCurrAsset2]["totalAssets"])
        prevTotalAssets2:float = float(self.balanceSheet[iPrevAsset2]["totalAssets"])
        
        
        currAssetTurnOver:float = currTotalRevenue / ((curTotalAssets + prevTotalAssets)/2)
        prevAssetTurnOver:float = prevTotalRevenue / ((curTotalAssets2 + prevTotalAssets2)/2)
        
        grossMarginInd:float = 1 if currYearGrossProfit > prevYearGrossProfit else 0
        assetTurnOverInd:float = 1 if currAssetTurnOver > prevAssetTurnOver else 0
        
        return netIncomeInd + roaInd + operatingCashFlowInd + netIncomeInd + longTermDebtInd + currRatioInd + grossMarginInd + assetTurnOverInd
               
    
    def getMaxret(self) -> float:
        """
            maxret -- Maximum daily return:
            Maximum daily return from returns during calendar month t-1.
        """
        if self.dailyBar.empty:
            raise ValueError("the daily bar variable is empty")
        
        dailyReturn:pd.DataFrame = (self.dailyBar["close"] - self.dailyBar["open"]) / self.dailyBar["open"]
        
        return dailyReturn.max()
    
    def getRoic(self) -> float:
        """
            roic -- Return on invested capital:
            Annual earnings before interest and taxes (ebit) minus non-operating income (nopi) 
            divided by non-cash enterprise value (ceq+lt-che).
            enterprise value = market cap + total debt - cash and cash equivalents
        """
        iEbitRange:list = getNonNullIndexRange(
            arr=self.incomeStatement, 
            featureName="ebit")
        iIncome:list = getNonNullIndexRange(
            arr=self.incomeStatement, 
            featureName="nonOperatingIncomeNetOther")
        iShortDebt:int = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="shortTermDebt")
        iLongDebt:int = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="longTermDebt")
        iCash:int = getFirstNonNullIndex(
            arr=self.balanceSheet, 
            featureName="cash")
        
        ebit:float = sum([float(self.incomeStatement[i]["ebit"]) for i in iEbitRange])
        nonOperatingIncome:float = sum([float(self.incomeStatement[i]["nonOperatingIncomeNetOther"]) for i in iIncome])
        
        marketCap:float = self.highlights["MarketCapitalization"]
        shortTermDebt:float = float(self.balanceSheet[iShortDebt]["shortTermDebt"])
        longTermDebt:float = float(self.balanceSheet[iLongDebt]["longTermDebt"])
        cash:float = float(self.balanceSheet[iCash]["cash"])
        
        ev:float = marketCap + shortTermDebt + longTermDebt - cash 
        
        return (ebit - nonOperatingIncome) / ev 
              
    
    def getDepr(self) -> float:
        """
            depr -- Depreciation / PP&E:
            Depreciation divided by PP&E.
        """
        i = getFirstNonNullIndexPair(
            arr1=self.cashFlow, 
            arr2=self.balanceSheet, 
            feature1Name="depreciation", 
            feature2Name="propertyPlantEquipment")
        
        depreciation:float = float(self.cashFlow[i]["depreciation"])
        ppeg:float = float(self.balanceSheet[i]["propertyPlantEquipment"])
        
        return depreciation / ppeg
    
    def getPchdepr(self) -> float:
        """
            pchdepr -- % change in depreciation
            percent change in depr
        """
        iCurr:int = getFirstNonNullIndexPair(
            arr1=self.cashFlow, 
            arr2=self.balanceSheet, 
            feature1Name="depreciation", 
            feature2Name="propertyPlantEquipment")
        iPrev:int = getFirstNonNullIndexPair(
            arr1=self.cashFlow, 
            arr2=self.balanceSheet, 
            feature1Name="depreciation", 
            feature2Name="propertyPlantEquipment",
            initIndex=iCurr+4)
        
        currDepreciation:float = float(self.cashFlow[iCurr]["depreciation"])
        currPpeg:float = float(self.balanceSheet[iCurr]["propertyPlantEquipment"])
        
        prevDepreciation:float = float(self.cashFlow[iPrev]["depreciation"])
        prevPpeg:float = float(self.balanceSheet[iPrev]["propertyPlantEquipment"])
        
        return ((currDepreciation/currPpeg) - (prevDepreciation/prevPpeg)) / (prevDepreciation/prevPpeg)
        
    
    def getSgr(self) -> float:
        """
            sgr -- Sales growth:
            Annual percent change in sales (sale).
        """
        iCurrRange:list[int] = getNonNullIndexRange(
            arr=self.incomeStatement, 
            featureName="totalRevenue") 
        
        iPrevRange:list[int] = getNonNullIndexRange(
            arr=self.incomeStatement, 
            featureName="totalRevenue",
            initIndex=iCurrRange[-1]+1) 
        
        currYearRev:float = sum([float(self.incomeStatement[i]["totalRevenue"]) for i in iCurrRange])
        prevYearRev:float = sum([float(self.incomeStatement[i]["totalRevenue"]) for i in iPrevRange])
        
        return (currYearRev - prevYearRev) / prevYearRev
    
    def getSP(self) -> float:
        """
            SP -- Sales to price:
            Annual revenue (sale) divided by fiscal-year-end market capitalization.
        """
        iCurrRange:list[int] = getNonNullIndexRange(
            arr=self.incomeStatement, 
            featureName="totalRevenue")
        currYearRev:float = sum([float(self.incomeStatement[i]["totalRevenue"]) for i in iCurrRange])
        marketCap:float = self.highlights["MarketCapitalization"]
        
        return currYearRev / marketCap
        
    
    def getDivi(self) -> float:
        """
            divi -- Dividend initiation:
            An indicator variable equal to 1 if company pays dividends but did not in prior year
        """
        iCurrRange:list[int] = getNonNullIndexRange(
            arr=self.cashFlow, 
            featureName="dividendsPaid") 
        
        iPrevRange:list[int] = getNonNullIndexRange(
            arr=self.cashFlow, 
            featureName="dividendsPaid",
            initIndex=iCurrRange[-1]+1) 
    
        currDiv:float = sum([float(self.cashFlow[i]["dividendsPaid"]) for i in iCurrRange])
        prevDiv:float = sum([float(self.cashFlow[i]["dividendsPaid"]) for i in iPrevRange])
        
        divi:float = 1 if (currDiv > 0 and prevDiv < 0) else 0
        
        return divi
        
    def getDivo(self) -> float:
        """
            divo -- Dividend omission:
            An indicator variable equal to 1 if company does not pay dividend but did in prior year.
        """
        iCurrRange:list[int] = getNonNullIndexRange(
            arr=self.cashFlow, 
            featureName="dividendsPaid") 
        
        iPrevRange:list[int] = getNonNullIndexRange(
            arr=self.cashFlow, 
            featureName="dividendsPaid",
            initIndex=iCurrRange[-1]+1) 
    
        currDiv:float = sum([float(self.cashFlow[i]["dividendsPaid"]) for i in iCurrRange])
        prevDiv:float = sum([float(self.cashFlow[i]["dividendsPaid"]) for i in iPrevRange])
        
        divo:float = 1 if (currDiv < 0 and prevDiv > 0) else 0
        
        return divo
    
    def getTurn(self) -> float:
        """
            turn -- Share turnover:
            Average monthly trading volume for most recent 3 months scaled by number of shares outstanding in current month
        """
        avgTradeVol:float = self.monthlyBar.iloc[-3:]["volume"].sum() / 3
        sharesOutstanding:float = self.shareStats["SharesOutstanding"]
        
        return avgTradeVol / sharesOutstanding
    
    def getMve(self) -> float:
        """
            mve -- Size:
            Natural log of market capitalization at end of month t-1.
        """
        marketCap:float = self.highlights["MarketCapitalization"]
        
        return np.log(marketCap)
        
    
    def getSaleCash(self) -> float:
        """
            salecash -- Sales to cash:
            Annual sales divided by cash and cash equivalents
        """
        iRev:list[int] = getNonNullIndexRange(
            arr=self.incomeStatement, 
            featureName="totalRevenue") 
        
        iCash:list[int] = getNonNullIndexRange(
            arr=self.balanceSheet, 
            featureName="cash") 
        
        sales:float = sum([float(self.incomeStatement[i]["totalRevenue"]) for i in iRev])
        cash:float = sum([float(self.balanceSheet[i]["cash"]) for i in iCash])
        
        return sales / cash
        
    def getSaleInv(self, initIndex:int=0) -> float:
        """
            saleinv -- Sales to inventory:
            Annual sales divided by total inventory
        """
        iCurrRange = getNonNullIndexRangePair(
            arr1=self.incomeStatement, 
            arr2=self.balanceSheet, 
            feature1Name="totalRevenue", 
            feature2Name="inventory",
            initIndex=initIndex)
        
        currYearRev:float = sum([float(self.incomeStatement[i]["totalRevenue"]) for i in iCurrRange])
        currYearInv:float = sum([float(self.balanceSheet[i]["inventory"]) for i in iCurrRange])
        
        return currYearRev / currYearInv
    
    def getPchSaleInv(self) -> float:
        """
            pchsaleinv -- Percent change in saleinv
        """
        return (self.getSaleInv() - self.getSaleInv(initIndex=4)) / self.getSaleInv(initIndex=4)
        
        
    
    def getSaleRec(self) -> float:
        """
            salerec -- Sales to receivables:
            Annual sales divided by accounts receivable.
        """
        iCurrRange = getNonNullIndexRangePair(
            arr1=self.incomeStatement, 
            arr2=self.balanceSheet, 
            feature1Name="totalRevenue", 
            feature2Name="netReceivables")
        
        currYearRev:float = sum([float(self.incomeStatement[i]["totalRevenue"]) for i in iCurrRange])
        currYearRec:float = sum([float(self.balanceSheet[i]["netReceivables"]) for i in iCurrRange])
        
        return currYearRev / currYearRec
    
    def getSin(self) -> float:
        """
            sin -- Sin stocks:
            An indicator variable equal to 1 if a company's primary industry classification is in 
            smoke or tobacco, beer or alcohol, or gaming.
        """
        sin:float = 1 if self.general["GicSubIndustry"] in ("Tobacco", "Brewers", "Casinos & Gaming") else 0
        
        return sin
    
    def getRetvol(self) -> float:
        """
            retvol -- Return volatility:
            Standard deviation of daily returns from month t-1.
        """
        dailyReturn:pd.Series = (self.dailyBar["close"] - self.dailyBar["open"]) / self.dailyBar["open"]
        
        return dailyReturn.std()
    
    def getChmom(self) -> float:
        """
            chmom -- Change in 6-month momentum:
            Cumulative returns from months t-6 to t-1 minus months t-12 to t-7.
        """
        currMom:float = (self.monthlyBar.iloc[-1]["close"] - self.monthlyBar.iloc[-6]["close"]) / self.monthlyBar.iloc[-6]["close"]
        prevMom:float = (self.monthlyBar.iloc[-7]["close"] - self.monthlyBar.iloc[-12]["close"]) / self.monthlyBar.iloc[-12]["close"]
        
        return currMom - prevMom
    
    def getMom6m(self) -> float:
        """
            mom6m:
            5-month cumulative returns ending one month before month end
        """
        return (self.monthlyBar.iloc[-1]["close"] - self.monthlyBar.iloc[-16]["close"]) / self.monthlyBar.iloc[-16]["close"]
    
    def getMom12m(self) -> float:
        """
            mom12m:
            11-month cumulative returns ending one month before month end
        """
        return (self.monthlyBar.iloc[-1]["close"] - self.monthlyBar.iloc[-12]["close"]) / self.monthlyBar.iloc[-12]["close"]
    
    def getMom36m(self) -> float:
        """
            mom36m:
            Cumulative returns from months t-36 to t-13
        """
        return (self.monthlyBar.iloc[-13]["close"] - self.monthlyBar.iloc[-36]["close"]) / self.monthlyBar.iloc[-36]["close"]
    
    def getTb(self) -> float:
        """
            tb -- Tax income to book income:
            Tax income, calculated from current tax expense divided by maximum federal tax rate, 
            divided by income before extraordinary items
        """
        iRange = getNonNullIndexRangePair(
            arr1=self.incomeStatement, 
            arr2=self.incomeStatement, 
            feature1Name="taxProvision", 
            feature2Name="incomeBeforeTax")
        
        tax:float = sum([float(self.incomeStatement[i]["taxProvision"]) for i in iRange])
        income:float = sum([float(self.incomeStatement[i]["incomeBeforeTax"]) for i in iRange])
        fedRate:float = 0.37 
         
        return (tax / fedRate) / income
    
    def getOperProf(self) -> float:
        """
            operprof -- Operating profitability:
            Revenue minus cost of goods sold - SG&A expense - interest expense divided by lagged common shareholders' equity
        """
        iRevCost:int = getFirstNonNullIndexPair(
            arr1=self.incomeStatement, 
            arr2=self.incomeStatement, 
            feature1Name="totalRevenue", 
            feature2Name="costOfRevenue")
        
        iSgaInterest:int = getFirstNonNullIndexPair(
            arr1=self.incomeStatement, 
            arr2=self.incomeStatement, 
            feature1Name="sellingGeneralAdministrative", 
            feature2Name="interestExpense")
        
        iEquity:int = getFirstNonNullIndex(
            arr=self.balanceSheet,
            featureName="commonStock"
        )
        
        revenue:float = float(self.incomeStatement[iRevCost]["totalRevenue"])
        cost:float = float(self.incomeStatement[iRevCost]["costOfRevenue"])
        sga:float = float(self.incomeStatement[iSgaInterest]["sellingGeneralAdministrative"])
        interest:float = float(self.incomeStatement[iSgaInterest]["interestExpense"])
        equity:float = float(self.balanceSheet[iEquity]["commonStock"])
        
        return (revenue - cost - sga - interest) / equity
    
    def getPchgmPchsale(self) -> float:
        """
            pchgm_pchsale -- % change in gross margin - % change in sales:
            Percent change in gross margin (sale-cogs) minus percent change in sales (sale).
        """
        iCurrRange:list = getNonNullIndexRangePair(
            arr1=self.incomeStatement,
            arr2=self.incomeStatement,
            feature1Name="grossProfit",
            feature2Name="totalRevenue"
        )
        iPrevRange:list = getNonNullIndexRangePair(
            arr1=self.incomeStatement,
            arr2=self.incomeStatement,
            feature1Name="grossProfit",
            feature2Name="totalRevenue",
            initIndex=iCurrRange[-1]+1
        )
        
        currGrossMargin:float = sum([float(self.incomeStatement[i]["grossProfit"]) for i in iCurrRange])
        prevGrossMargin:float = sum([float(self.incomeStatement[i]["grossProfit"]) for i in iPrevRange])
        currSales:float = sum([float(self.incomeStatement[i]["totalRevenue"]) for i in iCurrRange])
        prevSales:float = sum([float(self.incomeStatement[i]["totalRevenue"]) for i in iPrevRange])
        
        return (currGrossMargin-prevGrossMargin)/prevGrossMargin - (currSales-prevSales)/prevSales
        
    def getCinvest(self) -> float:
        """
            cinvest -- Corporate investment:
            Change over one quarter in net PP&E (ppentq) divided by sales (saleq) - average of this variable 
            for prior 3 quarters; if saleq = 0, then scale by 0.01.
        """
        iRange:list = getNonNullIndexRangePair(
            arr1=self.balanceSheet,
            arr2=self.incomeStatement,
            feature1Name="propertyPlantAndEquipmentNet",
            feature2Name="totalRevenue",
            duration=5
        )
        
        currInvest:float = float(self.balanceSheet[iRange[0]]["propertyPlantAndEquipmentNet"]) / \
            float(self.incomeStatement[iRange[0]]["totalRevenue"])
        prevInvest:float = float(self.balanceSheet[iRange[1]]["propertyPlantAndEquipmentNet"])/ \
            float(self.incomeStatement[iRange[1]]["totalRevenue"])
            
        avgChInvest:float = sum([float(self.balanceSheet[iRange[i]]["propertyPlantAndEquipmentNet"])/ \
            float(self.incomeStatement[iRange[i]]["totalRevenue"]) - float(self.balanceSheet[iRange[i+1]]["propertyPlantAndEquipmentNet"])/ \
            float(self.incomeStatement[iRange[i+1]]["totalRevenue"]) for i in iRange[1:4]]) / 3
        
        return currInvest - prevInvest - avgChInvest
        
    
    def getAcc(self) -> float:
        """
            acc -- Working capital accruals:
            Annual income before extraordinary items (ib) minus operating cash flows (oancf) divided by average total assets (at); 
            if oancf is missing then set to change in act - change in che - change in lct + change in dlc + change in txp-dp.
        """
        iRange:list = getNonNullIndexRangePair(
            arr1=self.incomeStatement,
            arr2=self.balanceSheet,
            feature1Name="incomeBeforeTax",
            feature2Name="totalAssets"
        )
        iCash:int = getFirstNonNullIndex(
            arr=self.cashFlow, 
            featureName="totalCashFromOperatingActivities")
        
        income:float = sum([float(self.incomeStatement[i]["incomeBeforeTax"]) for i in iRange])
        cashFlow:float = float(self.cashFlow[iCash]["totalCashFromOperatingActivities"])
        avgAssets:float = sum([float(self.balanceSheet[i]["totalAssets"]) for i in iRange])
        
        return (income - cashFlow) / avgAssets
    
    def getAbsacc(self) -> float:
        """
            absacc -- Absolute accruals:
            Absolute value of acc
        """      
        return abs(self.getAcc())
    
    def getStdTurn(self) -> float:
        """
            std_turn -- Volatility of liquidity (share turnover):
            Monthly standard deviation of daily share turnover
        """
        if self.dailyBar.empty:
            raise ValueError("the daily bar variable is empty")
        iShare:int = getFirstNonNullIndex(
            arr=self.balanceSheet,
            featureName="commonStockSharesOutstanding"
        )
        shareOutstanding:float = float(self.balanceSheet[iShare]["commonStockSharesOutstanding"])
        
        return (self.dailyBar["volume"] / shareOutstanding).std()
    
    def getTang(self) -> float:
        """
            tang -- Debt capacity/firm tangibility:
            Cash holdings + 0.715 × receivables + 0.547 × inventory + 0.535 × PPE/ total assets
        """
        iCash:int = getFirstNonNullIndex(
            arr=self.balanceSheet,
            featureName="cash"
        )
        iRec:int = getFirstNonNullIndex(
            arr=self.balanceSheet,
            featureName="netReceivables"
        )
        iInv:int = getFirstNonNullIndex(
            arr=self.balanceSheet,
            featureName="inventory"
        )
        iPpeg:int = getFirstNonNullIndex(
            arr=self.balanceSheet,
            featureName="propertyPlantAndEquipmentNet"
        )
        iAssets:int = getFirstNonNullIndex(
            arr=self.balanceSheet,
            featureName="totalAssets"
        )
        
        cash:float = float(self.balanceSheet[iCash]["cash"])
        rec:float = float(self.balanceSheet[iRec]["netReceivables"])
        inv:float = float(self.balanceSheet[iInv]["inventory"])
        ppeg:float = float(self.balanceSheet[iPpeg]["propertyPlantAndEquipmentNet"])
        assets:float = float(self.balanceSheet[iAssets]["totalAssets"])
        
        return cash + 0.715*rec + 0.547*inv + 0.535*(ppeg/assets)
        
    
    def getStdDolvol(self) -> float:
        """
            std_dolvol -- Volatility of liquidity (dollar trading volume):
            Monthly standard deviation of daily dollar trading volume
        """
        if self.dailyBar.empty:
            raise ValueError("the daily bar variable is empty")
        
        return (self.dailyBar["volume"] * self.dailyBar["vwap"]).std()
    
    def getIdiovol(self) -> float:
        """
            idiovol -- Idiosyncratic return volatility:
            Standard deviation of residuals of weekly returns on weekly equal weighted market returns for 3 years 
            prior to month end
        """
        if self.weeklyBar.empty:
            raise ValueError("the weekly bar variable is empty")
        
        weeklyBar:pd.DataFrame = self.weeklyBar
        weeklyBar.insert(0, "x", range(1, 1+len(weeklyBar)))
        
        y:pd.Series = weeklyBar["close"]
        x:pd.Series = weeklyBar["x"]
        x = sm.add_constant(x)

        model = sm.OLS(y, x).fit()
        return model.resid.std()
    
    def getIll(self) -> float:
        """
            ill -- Illiquidity:
            Average of daily (absolute return / dollar volume)
        """
        if self.dailyBar.empty:
            raise ValueError("the daily bar variable is empty")
        
        return (self.dailyBar["close"] - self.dailyBar["open"] / self.dailyBar["vwap"]).mean()
    
    def getRsup(self) -> float:
        """
            rsup -- Revenue surprise:
            Sales from quarter t minus sales from quarter t-4 (saleq) divided by fiscal-quarter-end market capitalization 
            (cshoq * prccq).
        """
        iCurr, iPrev = getFirstNonNullIndexPairDistance(
            arr1=self.incomeStatement,
            arr2=self.incomeStatement,
            feature1Name="totalRevenue", 
            feature2Name="totalRevenue"
        )
        marketCap:float = self.highlights["MarketCapitalization"]
        currSales:float = float(self.incomeStatement[iCurr]["totalRevenue"])
        prevSales:float = float(self.incomeStatement[iPrev]["totalRevenue"])
        
        return (currSales - prevSales) / marketCap
    
    def getPchsalePchrect(self) -> float:
        """
            pchsale_pchrect -- % change in sales - % change in A/R:
            Annual percent change in sales (sale) minus annual percent change in receivables (rect)
        """
        iCurrRange:list = getNonNullIndexRangePair(
            arr1=self.incomeStatement,
            arr2=self.balanceSheet,
            feature1Name="totalRevenue",
            feature2Name="netReceivables"
        )
        iPrevRange:list = getNonNullIndexRangePair(
            arr1=self.incomeStatement,
            arr2=self.balanceSheet,
            feature1Name="totalRevenue",
            feature2Name="netReceivables",
            initIndex=iCurrRange[-1]+1
        )
        
        currSales:float = sum([float(self.incomeStatement[i]["totalRevenue"]) for i in iCurrRange])
        prevSales:float = sum([float(self.incomeStatement[i]["totalRevenue"]) for i in iPrevRange])
        currRec:float = sum([float(self.balanceSheet[i]["netReceivables"]) for i in iCurrRange])
        prevRec:float = sum([float(self.balanceSheet[i]["netReceivables"]) for i in iPrevRange])
        
        return ((currSales-prevSales)/prevSales) - ((currRec-prevRec)/prevRec)
    
    def getNincr(self) -> float:
        """
            nincr -- Number of earnings increases:
            Number of consecutive quarters (up to eight quarters) with an increase in earnings (ibq) 
            over same quarter in the prior year.
        """
        iRange:list = getNonNullIndexRange(
            arr=self.incomeStatement, 
            featureName="netIncome",
            duration=13)
        
        earningsList:list = [float(self.incomeStatement[i]["netIncome"]) for i in iRange]
        
        nincr:float = 0
        tmp:float = 0
        for i in range(8):
            if earningsList[i] > earningsList[i+4]:
                tmp += 1
            else:
                tmp = 0
            nincr = max(nincr, tmp)
        
        return nincr
    
    def getGrCAPX(self) -> float:
        """
            grCAPX:
            Percent change in capital expenditures from year t-2 to year t.
        """
        iCurrRange:list = getNonNullIndexRange(
            arr=self.cashFlow, 
            featureName="capitalExpenditures"
        )
        iPrevRange:list = getNonNullIndexRange(
            arr=self.cashFlow,
            featureName="capitalExpenditures",
            initIndex=8
        )
        
        currCapExp:float = sum([float(self.cashFlow[i]["capitalExpenditures"]) for i in iCurrRange])
        prevCapExp:float = sum([float(self.cashFlow[i]["capitalExpenditures"]) for i in iPrevRange])
        
        return (currCapExp - prevCapExp) / prevCapExp
    
    def getPchsalePchinvt(self) -> float:
        """
            pchsale_pchinvt:
            Annual percent change in sales (sale) minus annual percent change in inventory (invt).
        """
        iCurrRange:list = getNonNullIndexRangePair(
            arr1=self.incomeStatement, 
            arr2=self.balanceSheet, 
            feature1Name="totalRevenue", 
            feature2Name="inventory"
        ) 
        iPrevRange:list = getNonNullIndexRangePair(
            arr1=self.incomeStatement, 
            arr2=self.balanceSheet, 
            feature1Name="totalRevenue", 
            feature2Name="inventory",
            initIndex=iCurrRange[-1]+1
        ) 
        
        currYearSales:float = sum([float(self.incomeStatement[i]["totalRevenue"]) for i in iCurrRange])
        currYearInv:float = sum([float(self.balanceSheet[i]["inventory"]) for i in iCurrRange])
        prevYearSales:float = sum([float(self.incomeStatement[i]["totalRevenue"]) for i in iPrevRange])
        prevYearInv:float = sum([float(self.balanceSheet[i]["inventory"]) for i in iPrevRange])
        
        return ((currYearSales-prevYearSales)/prevYearSales) - ((currYearInv-prevYearInv)/prevYearInv)
    
    def getPchsalePchxsga(self) -> float:
        """
            pchsale_pchxsga:
            Annual percent change in sales (sale) minus annual percent change in SG&A (xsga).
        """
        iCurrRange:list = getNonNullIndexRangePair(
            arr1=self.incomeStatement, 
            arr2=self.incomeStatement, 
            feature1Name="totalRevenue", 
            feature2Name="sellingGeneralAdministrative"
        ) 
        iPrevRange:list = getNonNullIndexRangePair(
            arr1=self.incomeStatement, 
            arr2=self.incomeStatement, 
            feature1Name="totalRevenue", 
            feature2Name="sellingGeneralAdministrative",
            initIndex=iCurrRange[-1]+1
        ) 
        
        currYearSales:float = sum([float(self.incomeStatement[i]["totalRevenue"]) for i in iCurrRange])
        currYearSga:float = sum([float(self.incomeStatement[i]["sellingGeneralAdministrative"]) for i in iCurrRange])
        prevYearSales:float = sum([float(self.incomeStatement[i]["totalRevenue"]) for i in iPrevRange])
        prevYearSga:float = sum([float(self.incomeStatement[i]["sellingGeneralAdministrative"]) for i in iPrevRange])
        
        return ((currYearSales-prevYearSales)/prevYearSales) - ((currYearSga-prevYearSga)/prevYearSga)
    
    def getRealEstate(self) -> float:
        """
            realestate -- Buildings and capitalized leases divided by gross PP&E.
        """
        iCurr:int = getFirstNonNullIndexPair(
            arr1=self.balanceSheet, 
            arr2=self.balanceSheet, 
            feature1Name="capitalLeaseObligations", 
            feature2Name="propertyPlantEquipment"
        )
        
        return float(self.balanceSheet[iCurr]["capitalLeaseObligations"]) / float(self.balanceSheet[iCurr]["propertyPlantEquipment"])        
    
            
        