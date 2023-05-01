from BotConfig import *
from BotUtil import *
import pandas as pd
import numpy as np
import os
import datetime

'''
해결 - 방금전봉보다 5프로 이하
해결 - 5봉전부터 과거 20봉간 최고최저폭 10~20%이상
해결 - 이평선 정배열 5 > 20 > 60
해결 - 지금종가가 20이평 100~105% 사이인지
해결 - 지금종가가 5이평 위에 있냐
'''

dir = os.getcwd()
flist = os.listdir(dir + '/BacktestData')
xlsx_list = np.array([x for x in flist if x.endswith('.xlsx')])

ttl_code_array = []
ttl_buy_array = []
ttl_sel_array = []
ttl_sucs_per_array = []
ttl_fail_per_array = []
ttl_prft_array = []

obj = {}
bal_obj = {}

if os.path.isfile(FILE_URL_BALANCE_LIST_TEST_5M):
    os.remove(FILE_URL_BALANCE_LIST_TEST_5M)

for x in np.nditer(xlsx_list):
    code = str(x).split('.')[0]
    _code_df = pd.read_excel(dir + '/BacktestData/' + str(x))
    _code_df = _code_df[::-1]

    code_df = pd.DataFrame({'open': _code_df['시가'].abs().to_list(), 'high': _code_df['고가'].abs().to_list(), 'low': _code_df['저가'].abs().to_list(), 'close': _code_df['현재가'].abs().to_list(), 'vol': _code_df['거래량'].abs().to_list()})
    temp_df = min_max_height(moving_average(code_df))

    buy_p = 0
    buy_c = 0
    sucs_c = 0
    fail_c = 0
    item_buy_c = 0
    item_sel_c = 0
    _ror = 1

    has_buy = False
    fst_lop = False
    bal_obj[code] = {'p': 0, 'q': 0, 'a': 0, 'pft': 1, 'sel': 1}

    prev_max = 0

    if fst_lop == False:
        if os.path.isfile(FILE_URL_BALANCE_LIST_TEST_5M):
            obj = load_file(FILE_URL_BALANCE_LIST_TEST_5M)
            if not (code in obj):
                obj[code] = bal_obj[code]
        else:
            obj = bal_obj
            save_file(FILE_URL_BALANCE_LIST_TEST_5M, obj)
        fst_lop = True

    for i, row in temp_df.iterrows():
        
        # buy

        if \
        (row['close'] < row['close_p'] * 1.05) and \
        (row['height'] > 1.1) and \
        (row['ma05'] > row['ma20'] > row['ma60']) and \
        (row['ma20'] * 1.05 > row['close'] > row['ma20']) and \
        (row['close'] > row['ma05']) and \
        has_buy == False\
        :
            bal_obj[code]['q'] = 10
            bal_obj[code]['a'] = int(row['close'])
            obj[code]['a'] = int(row['close'])
            buy_p = row['close'] * bal_obj[code]['q']
            has_buy = True
            item_buy_c += 1
            print('buy', bal_obj[code]['a'])

        bal_obj[code]['p'] = int(row['close'])
        bal_obj[code]['pft'] = (bal_obj[code]['p'] / bal_obj[code]['a']) if bal_obj[code]['a'] != 0 else 1
        # sell

        t1 = 0.02
        t2 = 0.03
        t3 = 0.04
        ct = 0.85

        if prev_max < bal_obj[code]['p']:
            prev_max = bal_obj[code]['p']
        
        # 하락
        if has_buy == True:
            if prev_max > bal_obj[code]['p']:
                if bal_obj[code]['pft'] > 1.1:
                    print(bal_obj[code]['pft'], 'tailing stop =======================')

                # 이익
                if 1 < bal_obj[code]['pft'] < 1.09:

                    pft_max = float(prev_max) / float(obj[code]['a'])
                    los_dif = pft_max - bal_obj[code]['pft']

                    if obj[code]['sel'] == 1 and has_buy == True:
                        if t1 <= los_dif:
                            sel_close = row['close'] * 2
                            _ror = ror((buy_p * 0.2), sel_close, _ror)
                            print(_ror)
                            bal_obj[code]['q'] = bal_obj[code]['q'] - 2
                            if sel_close - buy_p > 0:
                                sucs_c += 1
                            else:
                                fail_c += 1
                            item_sel_c += 1
                            print(f'1차매도 : 0.2 {los_dif}')
                            obj[code]['sel'] += 1
                    elif obj[code]['sel'] == 2 and has_buy == True:
                        if t2 <= los_dif:
                            sel_close = row['close'] * 3
                            _ror = ror((buy_p * 0.3), sel_close, _ror)
                            print(_ror)
                            bal_obj[code]['q'] = bal_obj[code]['q'] - 3
                            if sel_close - buy_p > 0:
                                sucs_c += 1
                            else:
                                fail_c += 1
                            item_sel_c += 1
                            print('2차매도 : 0.3')
                            obj[code]['sel'] += 1
                    elif obj[code]['sel'] == 3 and has_buy == True:
                        if t3 <= los_dif:
                            sel_close = row['close'] * 5
                            _ror = ror((buy_p * 0.5), sel_close, _ror)
                            print(_ror)
                            bal_obj[code]['q'] = bal_obj[code]['q'] - 5
                            if sel_close - buy_p > 0:
                                sucs_c += 1
                            else:
                                fail_c += 1
                            item_sel_c += 1
                            print('3차매도 : 0.5')

                            buy_p = 0
                            buy_c = 0
                            has_buy = False

                            obj[code]['sel'] += 1

                elif 1.09 <= bal_obj[code]['pft']:
                    sel_close = row['close'] * bal_obj[code]['q']
                    _ror = ror((buy_p * (bal_obj[code]['q'] / 10)), sel_close, _ror)
                    print(_ror)
                    if sel_close - buy_p > 0:
                        sucs_c += 1
                    else:
                        fail_c += 1
                    item_sel_c += 1
                    buy_p = 0
                    buy_c = 0
                    has_buy = False

                # 손절
                elif bal_obj[code]['pft'] <= ct and has_buy == True:
                    sel_close = row['close'] * bal_obj[code]['q']
                    _ror = ror((buy_p * (bal_obj[code]['q'] / 10)), sel_close, _ror)
                    print(_ror)
                    if sel_close - buy_p > 0:
                        sucs_c += 1
                    else:
                        fail_c += 1
                    item_sel_c += 1
                    print(bal_obj[code]['q'])
                    print('손절')

                    buy_p = 0
                    buy_c = 0
                    has_buy = False

    if sucs_c != 0:
        sucs_per = round(((sucs_c * 100) / (sucs_c + fail_c)), 2)
        fail_per = round((100 - sucs_per), 2)
        prft_per = round(((_ror - 1) * 100), 2)
    else:
        sucs_per = 0
        if item_buy_c > 0:
            fail_per = round((100 - sucs_per), 2)
            prft_per = round(((_ror - 1) * 100), 2)
        else:
            fail_per = 0
            prft_per = 0

    ttl_code_array.append(code)
    ttl_buy_array.append(item_buy_c)
    ttl_sel_array.append(item_sel_c)
    ttl_sucs_per_array.append(sucs_per)
    ttl_fail_per_array.append(fail_per)
    ttl_prft_array.append(prft_per)

    print('종목:{}, 매수: {}회, 매도: {}회, 성공률 : {}%, 실패율 : {}%, 누적수익률 : {}%'.format(code, item_buy_c, item_sel_c, sucs_per, fail_per, prft_per))

    save_file(FILE_URL_BALANCE_LIST_TEST_5M, obj)
    
prft_df = pd.DataFrame({'code': ttl_code_array, 'buy': ttl_buy_array, 'sell': ttl_sel_array, 'success': ttl_sucs_per_array, 'fail': ttl_fail_per_array, 'profit': ttl_prft_array})
prft_df = prft_df.sort_values('profit', ascending=False)
prft_df.to_excel(dir + '/BacktestResult/Bot3mBacktest' + datetime.datetime.now().strftime('%m%d%H%M%S') + '.xlsx')