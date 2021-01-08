from ibapi import wrapper
from ibapi import client
from ibapi import contract
from ibapi import order
import pandas as pd
import os.path as opath
from collections import defaultdict


class Wrapper(wrapper.EWrapper): # used to receive messsages from TWS
    def __init__(self):
        pass

class Client(client.EClient): # used to send messages to TWS
    def __init__(self, wrapper):
        client.EClient.__init__(self, wrapper)

class PositionsApp(Wrapper, Client):

    def __init__(self):
        Wrapper.__init__(self)
        Client.__init__(self, wrapper=self)
        self.positions = []
        self.positions_df = None
        self.__unq_id = None
        self.contract_details = {}
        self.req_id_to_symbol = {}
        self.proccess_symbols = set([])
        self.options_contract_data = defaultdict(list)
        
    
    def get_contract(self, symbol, secType='STK', currency='USD', exchange='SMART', futures_month=None):
        sec_contract = contract.Contract()
        sec_contract.includeExpired = True
        sec_contract.symbol = symbol
        sec_contract.secType = secType
        sec_contract.currency = currency
        sec_contract.exchange = exchange
        #sec_contract.lastTradeDateOrContractMonth = futures_month
        return sec_contract

    def position(self, account: str, contract: contract.Contract,
                 position: float, avg_cost: float):
        super().position(account, contract, position, avg_cost)
        self.positions.append(
            [contract.symbol, contract.secType, position, avg_cost,
             account]
        )
        print(
            "Position.", "Account:", account, "Symbol:", contract.symbol,
            "SecType:", contract.secType, "Currency:", contract.currency,
            "Position:", position, "Avg cost:", avg_cost
        )

    def positionEnd(self):
        super().positionEnd()
        self.positions_df = pd.DataFrame(
            self.positions,
            columns=['symbol', 'security_type', 'position', 'avg_cost',
                     'account']
        )
        self.cancelPositions()
        self.disconnect()        
    
    def contractDetails(self, reqId, contract_details):
        super().contractDetails(reqId, contract_details)
        symbol = self.req_id_to_symbol[reqId]
        self.contract_details[symbol] = contract_details
        #if req_id in self.req_id_to_symbol[reqId]:
        unq_id = self.get_unique_id()
        self.req_id_to_symbol[unq_id] = symbol
        contract = contract_details.contract
        self.reqSecDefOptParams(unq_id, contract.symbol, "", "STK", contract.conId)
    
    def securityDefinitionOptionParameterEnd(self, reqId):
        symbol = self.req_id_to_symbol[reqId]
        self.proccess_symbols.remove(symbol)
        if len(self.proccess_symbols) == 0:
            self.disconnect()
                
    def securityDefinitionOptionParameter(self, reqId: int, exchange: str,
                                          underlyingConId: int, tradingClass: str, multiplier: str,
                                          expirations, strikes):
        super().securityDefinitionOptionParameter(
            reqId, exchange, underlyingConId, tradingClass, multiplier, expirations, strikes
        )
        '''
        print("SecurityDefinitionOptionParameter.",
              "ReqId:", reqId, "Exchange:", exchange, "Underlying conId:", underlyingConId, "TradingClass:", tradingClass,
              "Multiplier:", multiplier, "Expirations:", expirations, "Strikes:", str(strikes))
        
        '''
        data = {
            'ReqId': reqId, 'exchange': exchange,
            'underlyingConId': underlyingConId,
            'tradingClass': tradingClass,
            'multiplier': multiplier, 'expirations': expirations,
            'strikes': sorted(strikes)
        }
        self.options_contract_data[self.req_id_to_symbol[reqId]] = data
        
    def get_positions(self):
        unq_id = self.get_unique_id()
        req_id = f'positions_{unq_id}'
        self.reqPositions() # I think this function if from Client class

    def get_unique_id(self, filepath='counter.txt'):
        counter = 1
        if self.__unq_id is None:
            if not opath.exists(filepath):
                with open(filepath, 'w') as cnt_file:
                    cnt_file.write('1')
            else:
                with open(filepath, 'r') as cnt_file:
                    counter = int(cnt_file.read())
                with open(filepath, 'w') as cnt_file:
                    cnt_file.write(str(counter + 5))
        else:
            counter = self.__unq_id + 5
            self.__unq_id = counter
        return counter

    
    def get_contract_details(self, symbol):
        sec_contract = self.get_contract(symbol)
        unq_id = self.get_unique_id()
        self.proccess_symbols.add(symbol)
        self.req_id_to_symbol[unq_id] = symbol
        self.reqContractDetails(unq_id, sec_contract)
    
    def get_multiple_contract_details(self, symbols):
        self.proccess_symbols.update(symbols)
        for symbol in symbols:
            self.get_contract_details(symbol)

    
        
        

