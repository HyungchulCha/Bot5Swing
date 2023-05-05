from BotConfig import *
from dateutil.relativedelta import *
import yfinance as yf
import FinanceDataReader as fdr
import datetime
import pandas as pd
import os
import pickle
import requests
import math

def get_yfinance_df(f_list, time):

    krx = fdr.StockListing('KRX')
    ref_arr = []
    i = 1
    for fl in f_list:
        print(f'Check Market : {i} / {len(f_list)}')
        mrk = krx.loc[krx['Code'] == fl]['Market'].iloc[-1]
        if mrk == 'KOSPI':
            ref_arr.append(fl+'.KS')
        elif mrk == 'KOSDAQ':
            ref_arr.append(fl+'.KQ')
        i += 1

    tn_d = datetime.datetime.today()
    tn_8 = tn_d + relativedelta(days=-8)
    str_tn_d = tn_d.strftime('%Y-%m-%d')
    str_tn_8 = tn_8.strftime('%Y-%m-%d')

    df_arr = []
    i = 1
    for fsl in ref_arr:

        if time == 10:

            print(f'yfinance download : {i} / {len(ref_arr)}')
            df_sub_arr = []

            for j in reversed(range(8)):
                tn_b = tn_d - relativedelta(days=j)
                tn_a = tn_d - relativedelta(days=j+1)
                yf_df = yf.download(tickers=fsl, start=tn_a.strftime('%Y-%m-%d'), end=tn_b.strftime('%Y-%m-%d'), interval='5m', prepost=True)

                if not (yf_df.empty):

                    yf_df['Open_p'] = yf_df['Open'].shift(-1)
                    yf_df['High_p'] = yf_df['High'].shift(-1)
                    yf_df['Low_p'] = yf_df['Low'].shift(-1)
                    yf_df['Adj Close_p'] = yf_df['Adj Close'].shift(-1)
                    yf_df['Volume_p'] = yf_df['Volume'].shift(-1)

                    df_sub_sub_arr = []
                    h = 0
                    for x, row in yf_df.iterrows():
                        if h % 2 == 0:
                            if not (math.isnan(row['Adj Close_p'])):
                                str_o = row['Open']
                                str_h = max(row['High'], row['High_p'])
                                str_l = min(row['Low'], row['Low_p'])
                                str_c = row['Adj Close_p']
                                str_v = sum([row['Volume'], row['Volume_p']])
                                df_sub_sub_arr.append(str(str_o) + '|' + str(str_h) + '|' + str(str_l) + '|' + str(str_c) + '|' + str(str_v))
                            else:
                                df_sub_sub_arr.append(str(row['Open']) + '|' + str(row['High']) + '|' + str(row['Low']) + '|' + str(row['Adj Close_p']) + '|' + str(row['Volume']))
                        h += 1

                    df_sub_arr.append(pd.DataFrame({fsl.split('.')[0]: df_sub_sub_arr}))

            df_arr.append(pd.concat(df_sub_arr, axis=0).tail(80).reset_index(level=None, drop=True))

        elif time == 15:

            print(f'yfinance download : {i} / {len(ref_arr)}')
            
            yf_df = yf.download(tickers=fsl, start=str_tn_8, end=str_tn_d, interval='15m', prepost=True)
            df_sub_arr = []

            for x, row in yf_df.iterrows():
                df_sub_arr.append(str(row['Open']) + '|' + str(row['High']) + '|' + str(row['Low']) + '|' + str(row['Adj Close']) + '|' + str(row['Volume']))

            df_arr.append(pd.DataFrame({fsl.split('.')[0]: df_sub_arr}).tail(80).reset_index(level=None, drop=True))

        i += 1

    df = pd.concat(df_arr, axis=1)
    df.index.name = 'date'

    return df

def min_max_height(df):
    df_len = len(df)
    ar = [None, None, None, None, None]
    for i in range(df_len):
        if i < df_len - 5:
            hig_v = max(df.iloc[i:i+20]['high'])
            low_v = min(df.iloc[i:i+20]['low'])
            hgt_v = ((hig_v / low_v) - 1) * 100
            ar.append(round(hgt_v, 4))
    df['height'] = ar
    return df


def save_xlsx(url, df):
    df.to_excel(url)


def load_xlsx(url):
    return pd.read_excel(url)


def save_file(url, obj):
    with open(url, 'wb') as f:
        pickle.dump(obj, f)


def load_file(url):
    with open(url, 'rb') as f:
        return pickle.load(f)
    

def delete_file(url):
    if os.path.exists(url):
        for file in os.scandir(url):
            os.remove(file.path)


def get_qty(crnt_p, max_p):
    q = int(max_p / crnt_p)
    return 1 if q == 0 else q


def get_code_df(_df, code):
    _df_list = _df[code]
    opn_l = [float(dl.split('|')[0]) for dl in _df_list]
    hig_l = [float(dl.split('|')[1]) for dl in _df_list]
    low_l = [float(dl.split('|')[2]) for dl in _df_list]
    cls_l = [float(dl.split('|')[3]) for dl in _df_list]
    vol_l = [int(dl.split('|')[4]) for dl in _df_list]
    df = pd.DataFrame({'open': opn_l, 'high': hig_l, 'low': low_l, 'close': cls_l, 'vol': vol_l})
    return df


def moving_average(df):
    df['close_p'] = df['close'].shift()
    df['ma05'] = df['close'].rolling(5).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    df['ma05_p'] = df['ma05'].shift()
    df['ma20_p'] = df['ma20'].shift()
    df['ma60_p'] = df['ma60'].shift()
    return df


def rsi(df, period=14):
    _f = df.head(1)
    _o = {}
    dt = df.diff(1).dropna()
    u, d = dt.copy(), dt.copy()
    u[u < 0] = 0
    d[d > 0] = 0
    _o['u'] = u
    _o['d'] = d
    au = _o['u'].rolling(window = period).mean()
    ad = abs(_o['d'].rolling(window = period).mean())
    rs = au / ad
    _rsi = pd.Series(100 - (100 / (1 + rs)))
    rsi = pd.concat([_f, _rsi])
    return rsi


def rsi_vol_zremove(df, code):
    _a = []
    for i, d in df.iterrows():
        if d[code].split('|')[1] != '0':
            _a.append(int(d[code].split('|')[0]))
    df_c = pd.DataFrame({'close': _a})
    _rsi = rsi(df_c['close']).iloc[-1]
    rsi = 'less' if math.isnan(_rsi) else _rsi
    return rsi


def ror(pv, nv, pr=1, pf=0.00015, spf=0.003):
    cr = ((nv - (nv * pf) - (nv * spf)) / (pv + (pv * pf)))
    return pr * cr


def line_message(msg):
    print(msg)
    requests.post(LINE_URL, headers={'Authorization': 'Bearer ' + LINE_TOKEN}, data={'message': msg})