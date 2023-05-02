from BotConfig import *
import pandas as pd
import os
import pickle
import requests
import math


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