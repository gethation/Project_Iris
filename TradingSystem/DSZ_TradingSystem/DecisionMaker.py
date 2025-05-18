import json
import math
import datetime

class SupportAndResistance():
    def __init__(self, levels_file, base_percentage):

        self.levels_file = levels_file
        self.base_percentage = base_percentage

    def init_SupRes(self):

        with open(self.levels_file, 'r') as f:
            self.levels = json.load(f)

        self.SupRes_Areas = self.levels['area']
        
        upper_expandArea = [[self.SupRes_Areas[0][0] * (1 + 0.8/100*(i+1)+ 0.2), 
                             self.SupRes_Areas[0][0] * (1 + 0.8/100*(i+1))] for i in range(2)]
        

        lower_expandArea = [[self.SupRes_Areas[-1][1] * (1- 0.8/100*(i+1)), 
                             self.SupRes_Areas[-1][1] * (1- 0.8/100*(i+1) - 0.2)] for i in range(2)]
        
        self.SupRes_Areas = upper_expandArea + self.SupRes_Areas + lower_expandArea
            

    def lock_levels(self, current_kline, account_information):
        self.sup_low = None
        self.mid = None
        self.base_size = None

        for i in range(len(self.SupRes_Areas)-1):
            if self.SupRes_Areas[i][1] >= current_kline['close'] and current_kline['close'] >= self.SupRes_Areas[i+1][0]:
                self.sup_low, self.sup_high = self.SupRes_Areas[i+1][1], self.SupRes_Areas[i+1][0]
                self.res_low, self.res_high = self.SupRes_Areas[i][1], self.SupRes_Areas[i][0]
                break

        if self.sup_low != None:
            # 中线
            self.mid = (self.sup_high + self.res_low) // 2
            self.base_size = math.floor(account_information['value'] * self.base_percentage / current_kline['close'])
    
    def decision_making(self, current_kline, account_information):

        Order = None

        if self.sup_low == None:
            return Order
        
        ClosePrice = current_kline['close']
        OpenPrice = current_kline['open']
        stage = account_information['size']

        # Cross the support upper track
        if OpenPrice < self.sup_high and ClosePrice > self.sup_high:
            if stage == 0:

                Order = [{'side':"SIDE_BUY",
                          'size':self.base_size,
                          'price':ClosePrice,
                          'limitprice':self.mid, # 止盈
                          'stopprice':self.sup_low,# 止損
                          'entry':False,
                          'close':False}, 

                         {'side':"SIDE_BUY",
                          'size':self.base_size,
                          'price':ClosePrice,
                          'limitprice':self.res_low, # 止盈
                          'stopprice':self.sup_low,# 止損
                          'entry':False,
                          'close':False}] 
                
            elif stage == self.base_size:

                Order = [{'side':"SIDE_BUY",
                          'size':self.base_size,
                          'price':ClosePrice,
                          'limitprice':self.mid, # 止盈
                          'stopprice':self.sup_low,# 止損
                          'entry':False,
                          'close':False}]
                

        # Cross the resistance lower track
        if OpenPrice > self.res_low and ClosePrice < self.res_low:
            if stage == 0:

                Order = [{'side':"SIDE_SELL",
                          'size':self.base_size,
                          'price':ClosePrice,
                          'limitprice':self.mid, # 止盈
                          'stopprice':self.res_high,# 止損
                          'entry':False,
                          'close':False}, 

                         {'side':"SIDE_SELL",
                          'size':self.base_size,
                          'price':ClosePrice,
                          'limitprice':self.sup_high, # 止盈
                          'stopprice':self.res_high,  # 止損
                          'entry':False,
                          'close':False}] 
                
            elif stage == self.base_size:

                Order = [{'side':"SIDE_SELL",
                          'size':self.base_size,
                          'price':ClosePrice,
                          'limitprice':self.mid, # 止盈
                          'stopprice':self.res_high,# 止損
                          'entry':False,
                          'close':False}]
        return Order
    
    def next(self, current_kline, account_information):
        self.init_SupRes()
        self.lock_levels(current_kline, account_information)
        
        return self.decision_making(current_kline, account_information)
       
