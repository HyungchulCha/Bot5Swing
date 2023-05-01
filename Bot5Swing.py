from BotConfig import *
from BotUtil import *
from BotKIKr import BotKIKr
import pandas as pd
import datetime
import threading
import os

class Bot5Swing():

    
    def __init__(self):

        self.mock = True
        self.key = KI_APPKEY_IMITATION if self.mock else KI_APPKEY_PRACTICE
        self.secret = KI_APPSECRET_IMITATION if self.mock else KI_APPSECRET_PRACTICE
        self.account = KI_ACCOUNT_IMITATION if self.mock else KI_ACCOUNT_PRACTICE

        self.bkk = BotKIKr(self.key, self.secret, self.account, self.mock)
        self.bdf = None
        self.b_l = None
        self.q_l = None
        self.r_l = None

        self.tot_evl_price = 0
        self.buy_max_price = 0

        self.bool_marketday = False
        self.bool_stockorder = False
        self.bool_stockorder_timer = False
        self.bool_marketday_end = False
        self.bool_threshold = False

        self.init_marketday = None
        self.init_stockorder_timer = None


    def init_per_day(self):

        self.bkk = BotKIKr(self.key, self.secret, self.account, self.mock)
        self.bdf = load_xlsx(FILE_URL_DATA_5M).set_index('date')
        self.b_l = self.bdf.columns.to_list()
        self.q_l = self.get_guant_code_list()
        self.r_l = list(set(self.get_balance_code_list()).difference(self.q_l))

        self.tot_evl_price = self.get_total_price()
        self.buy_max_price = self.tot_evl_price / 20
        self.init_marketday = self.bkk.fetch_marketday()

        line_message(f'Bot5Swing \n평가금액 : {self.tot_evl_price}원, 다른종목: {len(self.r_l)}개')
    

    def stock_order(self):

        tn = datetime.datetime.now()
        tn_153000 = tn.replace(hour=15, minute=30, second=0)
        tn_div = tn.minute % 5
        tn_del = None

        if tn_div == 0:
            tn_del = 1
        elif tn_div == 1:
            tn_del = 2
        elif tn_div == 2:
            tn_del = 3
        elif tn_div == 3:
            tn_del = 4
        elif tn_div == 4:
            tn_del = 5

        tn_del_min = tn - datetime.timedelta(minutes=tn_del)
        tn_df_idx = tn_del_min.strftime('%Y%m%d%H%M00') if tn < tn_153000 else tn.strftime('%Y%m%d153000')
        tn_df_req = tn_del_min.strftime('%H%M00') if tn < tn_153000 else '153000'

        print('##################################################')

        if self.bool_threshold and tn_div == 4:
            self.bdf = self.bdf[:-1]
        self.bool_threshold = False

        bal_lst = self.get_balance_code_list(True)
        sel_lst = []

        for code in self.b_l:

            min_lst = self.bkk.fetch_today_1m_ohlcv(code, tn_df_req, True)['output2'][:5]
            cur_prc = min_lst[0]['stck_prpr']
            self.bdf.at[tn_df_idx, code] = cur_prc

            is_late = tn_div == 2 or tn_div == 3 or tn_div == 4

            if (not is_late):

                is_remain = code in self.r_l
                is_alread = code in bal_lst
                is_buy = self.can_i(code, self.bdf[code], 'buy')
                is_sel = self.can_i(code, self.bdf[code], 'sel')
                
                if is_buy and (not is_alread) and (not is_remain):
                    
                    ord_q = self.get_qty(int(cur_prc), self.buy_max_price)
                    buy_r = self.bkk.create_market_buy_order(code, ord_q) if tn < tn_153000 else self.bkk.create_over_buy_order(code, ord_q)

                    if buy_r['rt_cd'] == '0':
                        print(f'매수 - 종목: {code}, 수량: {ord_q}주')
                        sel_lst.append({'c': '[B] ' + code, 'r': str(ord_q) + '주'})
                    else:
                        msg = buy_r['msg1']
                        print(f'{msg}')

                if is_sel and is_alread:

                    sel_r = self.bkk.create_market_sell_order(code, bal_lst[code]['q']) if tn < tn_153000 else self.bkk.create_over_sell_order(code, bal_lst[code]['q'])
                    _ror = self.ror(bal_lst[code]['ptp'], bal_lst[code]['ctp'])

                    if sel_r['rt_cd'] == '0':
                        print(f'매도 - 종목: {code}, 수익: {round(_ror, 4)}')
                        sel_lst.append({'c': '[S] ' + code, 'r': round(_ror, 4)})

                    else:
                        msg = sel_r['msg1']
                        print(f'{msg}')

        sel_txt = ''
        for sl in sel_lst:
            sel_txt = sel_txt + '\n' + str(sl['c']) + ' : ' + str(sl['r'])
        
        _tn = datetime.datetime.now()
        _tn_152000 = _tn.replace(hour=15, minute=20, second=0)
        _tn_div = _tn.minute % 5
        _tn_sec = _tn.second
        _tn_del = None

        if _tn_div == 0:
            if tn_div == 4: 
                _tn_del = 0
                _tn_sec = 0
            else:
                _tn_del = 5
        elif _tn_div == 1:
            if tn_div == 4: 
                _tn_del = 0
                _tn_sec = 0
            else:
                _tn_del = 4
        elif _tn_div == 2:
            _tn_del = 3
        elif _tn_div == 3:
            _tn_del = 2
        elif _tn_div == 4:
            _tn_del = 1

        if _tn > _tn_152000:
            self.init_stockorder_timer = threading.Timer((60 * (30 - _tn.minute)) - _tn_sec, self.stock_order)
        else:
            self.init_stockorder_timer = threading.Timer((60 * _tn_del) - _tn_sec, self.stock_order)

        if self.bool_stockorder_timer:
            self.init_stockorder_timer.cancel()

        self.init_stockorder_timer.start()

        line_message(f'Bot5Self \n시작 : {tn}, \n표기 : {tn_df_idx} \n종료 : {_tn}, {sel_txt}')


    def market_to_excel(self, rebalance=False):

        _code_list = list(set(self.get_guant_code_list() + self.get_balance_code_list()))

        tn = datetime.datetime.now()
        if rebalance:
            tn = tn.replace(hour=15, minute=30, second=0)
        tn_091000 = tn.replace(hour=9, minute=10, second=0)
        
        if tn > tn_091000:

            tn_div = tn.minute % 5
            tn_del = None

            if tn_div == 0:
                tn_del = 6
            elif tn_div == 1:
                tn_del = 7
            elif tn_div == 2:
                tn_del = 8
            elif tn_div == 3:
                tn_del = 9
            elif tn_div == 4:
                tn_del = 5

            tn_req = ''
            tn_int = int(tn.strftime('%H%M%S'))
            tn_pos_a = 153000 <= tn_int
            tn_pos_b = 152000 < tn_int and tn_int < 153000
            tn_pos_c = tn_int <= 152000

            if tn_pos_a:
                tn_req = '153000'
            elif tn_pos_b:
                tn_req = '151900'
            elif tn_pos_c:
                tn_req = (tn - datetime.timedelta(minutes=tn_del)).strftime('%H%M00')
            
            df_a = []
            for c, code in enumerate(_code_list):
                print(f"{c + 1}/{len(_code_list)} {code}")
                df_a.append(self.bkk.df_today_1m_ohlcv(code, tn_req, 5))
            df = pd.concat(df_a, axis=1)
            df = df.loc[~df.index.duplicated(keep='last')]

            print('##################################################')
            line_message(f'File Download Complete : {FILE_URL_DATA_5M}')
            print(df)
            df.to_excel(FILE_URL_DATA_5M)

            _tn = datetime.datetime.now()
            _tn_div = _tn.minute % 5

            if tn_pos_c and _tn_div == 4:
                self.bool_threshold = True

    
    def deadline_to_excel(self):
        save_file(FILE_URL_QUANT_LAST_5M, self.bkk.filter_code_list())
        self.market_to_excel(True)

    
    def get_total_price(self):
        _total_eval_price = int(self.bkk.fetch_balance()['output2'][0]['tot_evlu_amt'])
        return _total_eval_price if _total_eval_price < 20000000 else 20000000
        
    
    def get_balance_code_list(self, obj=False):
        l = self.bkk.fetch_balance()['output1']
        a = []
        o = {}
        if len(l) > 0:
            for i in l:
                if int(i['ord_psbl_qty']) != 0:
                    if obj:
                        p = i['prpr']
                        q = i['ord_psbl_qty']
                        a = i['pchs_avg_pric']
                        o[i['pdno']] = {
                            'q': q,
                            'p': p,
                            'a': a,
                            'max': p,
                            'pft': p/a,
                            'sel': 1,
                            'ptp': float(a) * int(q),
                            'ctp': float(p) * int(q)
                        }
                    else:
                        a.append(i['pdno'])
        return o if obj else a
    
    
    def get_guant_code_list(self):
        _l = load_file(FILE_URL_QUANT_LAST_5M)
        l = [str(int(i)).zfill(6) for i in _l]
        return l
    

if __name__ == '__main__':

    B5 = Bot5Swing()
    # B5.market_to_excel(True)
    # B5.deadline_to_excel()

    while True:

        try:

            t_n = datetime.datetime.now()
            t_085000 = t_n.replace(hour=8, minute=50, second=0)
            t_090500 = t_n.replace(hour=9, minute=5, second=0)
            t_152500 = t_n.replace(hour=15, minute=25, second=0)
            t_153000 = t_n.replace(hour=15, minute=30, second=0)
            t_160000 = t_n.replace(hour=16, minute=0, second=0)

            if t_n >= t_085000 and t_n <= t_153000 and B5.bool_marketday == False:
                if os.path.isfile(os.getcwd() + '/token.dat'):
                    os.remove('token.dat')
                B5.init_per_day()
                B5.bool_marketday = True
                B5.bool_marketday_end = False

                line_message(f'Stock Start' if B5.init_marketday == 'Y' else 'Holiday Start')

            if B5.init_marketday == 'Y':

                if t_n > t_152500 and t_n < t_153000 and B5.bool_stockorder_timer == False:
                    B5.bool_stockorder_timer = True

                if t_n >= t_090500 and t_n <= t_153000 and B5.bool_stockorder == False:
                    B5.stock_order()
                    B5.bool_stockorder = True

            if t_n == t_160000 and B5.bool_marketday_end == False:

                if B5.init_marketday == 'Y':
                    B5.deadline_to_excel()
                    B5.bool_stockorder_timer = False
                    B5.bool_stockorder = False

                B5.bool_marketday = False
                B5.bool_marketday_end = True

                line_message(f'Stock End' if B5.init_marketday == 'Y' else 'Holiday End')

        except Exception as e:

            line_message(f"Bot5 Error : {e}")
            break