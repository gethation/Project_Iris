from binance.client import Client
import pandas as pd
client = Client("cc0ca83dfe29326a123d6f6603f16261144a86c53ffac0212c8afe96400139e3", 
                "f8c2ae97a77fd609b28792064685b52bd197d12d293c2edadb032c5585daa749", testnet=True)

from binance.enums import (
    SIDE_BUY,
    SIDE_SELL,
    ORDER_TYPE_LIMIT,
    TIME_IN_FORCE_GTC
)

symbol     = "BTCUSDT"     # 交易对
quantity   = 0.01         # 买入数量
time_in_force = TIME_IN_FORCE_GTC  # 挂单策略，GTC = 好到取消


def _handle_entry(order_detail, client):
    if order_detail['side'] == "SIDE_BUY":
        
        ticker = client.futures_symbol_ticker(symbol)
        order = client.futures_create_order(
            symbol=symbol,
            side=SIDE_BUY,
            type=ORDER_TYPE_LIMIT,
            timeInForce=time_in_force,
            quantity=order_detail['size'],
            price=int(float(ticker['price'])*1.05),
            reduceOnly=False
        )
        order_detail['entry'] = True


    elif order_detail['side']=="SIDE_SELL":
        
        ticker = client.futures_symbol_ticker(symbol)
        order = client.futures_create_order(
            symbol=symbol,
            side=SIDE_SELL,
            type=ORDER_TYPE_LIMIT,
            timeInForce=time_in_force,
            quantity=order_detail['size'],
            price=int(float(ticker['price'])*0.95),
            reduceOnly=False
        )

        order_detail['entry'] = True

def _handle_exit(spot_price, order_detail, client):
    if order_detail['side'] == "SIDE_BUY":
        
        if spot_price <= order_detail['stopprice']:

            ticker = client.futures_symbol_ticker(symbol)
            order = client.futures_create_order(
                symbol=symbol,
                side=SIDE_SELL,
                type=ORDER_TYPE_LIMIT,
                timeInForce=time_in_force,
                quantity=order_detail['size'],
                price=int(float(ticker['price'])*0.95),
                reduceOnly=True
            )
            order_detail['close'] = True

        elif spot_price >= order_detail['limitprice']:

            ticker = client.futures_symbol_ticker(symbol)
            order = client.futures_create_order(
                symbol=symbol,
                side=SIDE_SELL,
                type=ORDER_TYPE_LIMIT,
                timeInForce=time_in_force,
                quantity=order_detail['size'],
                price=int(float(ticker['price'])*0.95),
                reduceOnly=True
            )
            order_detail['close'] = True

    elif order_detail['side'] == "SIDE_SELL":

        if spot_price >= order_detail['stopprice']:

            ticker = client.futures_symbol_ticker(symbol)
            order = client.futures_create_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=ORDER_TYPE_LIMIT,
                timeInForce=time_in_force,
                quantity=order_detail['size'],
                price=int(float(ticker['price'])*1.05),
                reduceOnly=True
            )
            order_detail['close'] = True

    elif spot_price <= order_detail['limitprice']:

        ticker = client.futures_symbol_ticker(symbol)
        order = client.futures_create_order(
            symbol=symbol,
            side=SIDE_BUY,
            type=ORDER_TYPE_LIMIT,
            timeInForce=time_in_force,
            quantity=order_detail['size'],
            price=int(float(ticker['price'])*1.05),
            reduceOnly=True
        )
        order_detail['close'] = True


def Excutioner(spot_price, order_list, new_order, client):
    if new_order != None:
        order_list.extend(new_order)
    for order_detail in order_list:
        if order_detail['entry'] == False:
            _handle_entry(order_detail, client)

        elif order_detail['entry'] == True and order_detail['close'] == False: # check the triger of stop price and limit price
            _handle_exit(spot_price, order_detail, client)



            




