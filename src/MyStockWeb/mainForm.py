#!/usr/bin/env python
#coding=utf-8
from django.shortcuts import render
import pandas_datareader
import matplotlib.pyplot as plt
import pandas as pd
from mpl_finance import candlestick2_ochl
import sys
from io import BytesIO
import base64
import imp
imp.reload(sys)

def display(request):
    return render(request, 'main.html')

# 計算BIAS的函數 
def calBIAS(df,periodList):    
    for period in periodList:
        df['MA'+str(period)] = df['Close'].rolling(window=period).mean() 
        df['MA'+str(period)].fillna(value = df['Close'], inplace = True)
        df['BIAS'+str(period)] = (df['Close'] - df['MA'+str(period)])/df['MA'+str(period)]*100 
    return df

def calBuyPoints(df):
    cnt=0    
    buyDate=''
    while cnt<=len(df)-1:
        if(cnt>=30):    # 前幾天有誤差，從第30天算起
            # 規則1：這天中期BIAS小於或等於-7
            if df.iloc[cnt]['BIAS12']<=-7:
                buyDate = buyDate+df.iloc[cnt]['Date'] + ','
            #規則2：當天BIAS6上穿BIAS24
            if  df.iloc[cnt]['BIAS6']>df.iloc[cnt]['BIAS24'] and df.iloc[cnt-1]['BIAS6']<df.iloc[cnt-1]['BIAS24']:
                buyDate = buyDate+df.iloc[cnt]['Date'] + ','
        cnt=cnt+1
    return buyDate 

def calSellPoints(df):
    cnt=0    
    sellDate=''
    while cnt<=len(df)-1:
        if(cnt>=30):    #前幾天有誤差，從第30天算起
            # 規則1：這天中期BIAS大於等於7
            if df.iloc[cnt]['BIAS12']>=7:
                sellDate = sellDate+df.iloc[cnt]['Date'] + ','
            # 規則2：當天BIAS6下穿BIAS24
            if  df.iloc[cnt]['BIAS6']<df.iloc[cnt]['BIAS24'] and df.iloc[cnt-1]['BIAS6']>df.iloc[cnt-1]['BIAS24']:
                sellDate = sellDate+df.iloc[cnt]['Date'] + ','
        cnt=cnt+1
    return sellDate 

def draw(request):
    stockCode = request.POST.get('stockCode')
    startDate = request.POST.get('startDate')
    endDate = request.POST.get('endDate')
    stock = pandas_datareader.get_data_yahoo(stockCode+'.ss',startDate,endDate)
    # 移除最後一天多餘的股票交易資料
    stock.drop(stock.index[len(stock)-1],inplace=True)
    filename='D:\\stockData\ch11\\'+stockCode+startDate+endDate+'.csv'
    stock.to_csv(filename)
    # 從檔案中讀取指定股票在指定範圍內的交易資料
    df = pd.read_csv(filename,encoding='gbk')
    list = [6,12,24]    # 周期清單
    stockDataFrame = calBIAS(df,list)
    
    figure = plt.figure()         
    (axPrice, axBIAS) = figure.subplots(2, sharex=True)
    # 繪制K線 
    candlestick2_ochl(ax = axPrice, 
              opens=df["Open"].values, closes=df["Close"].values,
              highs=df["High"].values, lows=df["Low"].values,
              width=0.75, colorup='red', colordown='green')
    axPrice.set_title("K線圖和均線圖")
    stockDataFrame['Close'].rolling(window=6).mean().plot(ax=axPrice,color="red",label='6日均線')
    stockDataFrame['Close'].rolling(window=12).mean().plot(ax=axPrice,color="blue",label='12日均線')
    stockDataFrame['Close'].rolling(window=24).mean().plot(ax=axPrice,color="green",label='24日均線')
    axPrice.legend(loc='best')      # 繪制圖例
    axPrice.set_ylabel("價格（單位：元）")
    axPrice.grid(linestyle='-.')        
    # 繪制BIAS指標線
    stockDataFrame['BIAS6'].plot(ax=axBIAS,color="blue",label='BIAS6')
    stockDataFrame['BIAS12'].plot(ax=axBIAS,color="green",label='BIAS12')
    stockDataFrame['BIAS24'].plot(ax=axBIAS,color="purple",label='BIAS24')
    plt.legend(loc='best') 
    plt.rcParams['font.sans-serif']=['SimHei']       
    axBIAS.set_title("BIAS指標圖")
    axBIAS.grid(linestyle='-.') 
    major_index=stockDataFrame.index[stockDataFrame.index%5==0]
    major_xtics=stockDataFrame['Date'][stockDataFrame.index%5==0]
    plt.xticks(major_index,major_xtics)
    plt.setp(plt.gca().get_xticklabels(), rotation=30) 
    # 把儲存在plt物件中的圖形存入到buffer快取物件中
    buffer = BytesIO()
    plt.savefig(buffer)
    plt.close()     
    base64img = base64.b64encode(buffer.getvalue())    
    img = "data:image/png;base64,"+base64img.decode()
    
    buyDate = calBuyPoints(stockDataFrame)
    sellDate = calSellPoints(stockDataFrame)  
    
    return render(request, 'stock.html', {
            'img': img,'stockCode':stockCode,
            'buyDate':buyDate,'sellDate':sellDate
        })