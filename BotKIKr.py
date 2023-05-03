from BotConfig import *
import pandas as pd
import zipfile
import json
import pickle
import datetime
import requests


class BotKIKr:

    def __init__(self, api_key: str, api_secret: str, acc_no: str, mock: bool = False):
        self.mock = mock
        self.set_base_url(mock)
        self.api_key = api_key
        self.api_secret = api_secret

        self.acc_no = acc_no
        self.acc_no_prefix = acc_no.split('-')[0]
        self.acc_no_postfix = acc_no.split('-')[1]

        self.access_token = None
        if self.check_access_token():
            self.load_access_token()
        else:
            self.issue_access_token()

    def set_base_url(self, mock: bool = True):
        if mock:
            self.base_url = "https://openapivts.koreainvestment.com:29443"
        else:
            self.base_url = "https://openapi.koreainvestment.com:9443"

    def issue_access_token(self):
        path = "oauth2/tokenP"
        url = f"{self.base_url}/{path}"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.api_key,
            "appsecret": self.api_secret
        }

        resp = requests.post(url, headers=headers, data=json.dumps(data))
        resp_data = resp.json()
        self.access_token = f'Bearer {resp_data["access_token"]}'

        now = datetime.datetime.now()
        resp_data['timestamp'] = int(now.timestamp()) + resp_data["expires_in"]
        resp_data['api_key'] = self.api_key
        resp_data['api_secret'] = self.api_secret

        with open("token.dat", "wb") as f:
            pickle.dump(resp_data, f)

    def check_access_token(self):
        try:
            f = open("token.dat", "rb")
            data = pickle.load(f)
            f.close()

            expire_epoch = data['timestamp']
            now_epoch = int(datetime.datetime.now().timestamp())
            status = False

            if ((now_epoch - expire_epoch > 0) or
                (data['api_key'] != self.api_key) or
                (data['api_secret'] != self.api_secret)):
                status = False
            else:
                status = True
            return status
        except IOError:
            return False

    def load_access_token(self):
        with open("token.dat", "rb") as f:
            data = pickle.load(f)
            self.access_token = f'Bearer {data["access_token"]}'

    def issue_hashkey(self, data: dict):
        path = "uapi/hashkey"
        url = f"{self.base_url}/{path}"
        headers = {
           "content-type": "application/json",
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "User-Agent": "Mozilla/5.0"
        }
        resp = requests.post(url, headers=headers, data=json.dumps(data))
        haskkey = resp.json()["HASH"]
        return haskkey
    
    def fetch_symbols(self):
        df = self.fetch_kospi_symbols()
        kospi_df = df[['단축코드', '한글명', '그룹코드']].copy()
        kospi_df['시장'] = '코스피'

        df = self.fetch_kosdaq_symbols()
        kosdaq_df = df[['단축코드', '한글명', '그룹코드']].copy()
        kosdaq_df['시장'] = '코스닥'

        df = pd.concat([kospi_df, kosdaq_df], axis=0)

        return df

    def download_master_file(self, base_dir: str, file_name: str, url: str):
        os.chdir(base_dir)

        if os.path.exists(file_name):
            os.remove(file_name)

        resp = requests.get(url)
        with open(file_name, "wb") as f:
            f.write(resp.content)

        kospi_zip = zipfile.ZipFile(file_name)
        kospi_zip.extractall()
        kospi_zip.close()

    def parse_kospi_master(self, base_dir: str):
        file_name = base_dir + "/kospi_code.mst"
        tmp_fil1 = base_dir + "/kospi_code_part1.tmp"
        tmp_fil2 = base_dir + "/kospi_code_part2.tmp"

        wf1 = open(tmp_fil1, mode="w", encoding="cp949")
        wf2 = open(tmp_fil2, mode="w")

        with open(file_name, mode="r", encoding="cp949") as f:
            for row in f:
                rf1 = row[0:len(row) - 228]
                rf1_1 = rf1[0:9].rstrip()
                rf1_2 = rf1[9:21].rstrip()
                rf1_3 = rf1[21:].strip()
                wf1.write(rf1_1 + ',' + rf1_2 + ',' + rf1_3 + '\n')
                rf2 = row[-228:]
                wf2.write(rf2)

        wf1.close()
        wf2.close()

        part1_columns = ['단축코드', '표준코드', '한글명']
        df1 = pd.read_csv(tmp_fil1, header=None, encoding='cp949', names=part1_columns)

        field_specs = [
            2, 1, 4, 4, 4,
            1, 1, 1, 1, 1,
            1, 1, 1, 1, 1,
            1, 1, 1, 1, 1,
            1, 1, 1, 1, 1,
            1, 1, 1, 1, 1,
            1, 9, 5, 5, 1,
            1, 1, 2, 1, 1,
            1, 2, 2, 2, 3,
            1, 3, 12, 12, 8,
            15, 21, 2, 7, 1,
            1, 1, 1, 1, 9,
            9, 9, 5, 9, 8,
            9, 3, 1, 1, 1
        ]

        part2_columns = [
            '그룹코드', '시가총액규모', '지수업종대분류', '지수업종중분류', '지수업종소분류',
            '제조업', '저유동성', '지배구조지수종목', 'KOSPI200섹터업종', 'KOSPI100',
            'KOSPI50', 'KRX', 'ETP', 'ELW발행', 'KRX100',
            'KRX자동차', 'KRX반도체', 'KRX바이오', 'KRX은행', 'SPAC',
            'KRX에너지화학', 'KRX철강', '단기과열', 'KRX미디어통신', 'KRX건설',
            'Non1', 'KRX증권', 'KRX선박', 'KRX섹터_보험', 'KRX섹터_운송',
            'SRI', '기준가', '매매수량단위', '시간외수량단위', '거래정지',
            '정리매매', '관리종목', '시장경고', '경고예고', '불성실공시',
            '우회상장', '락구분', '액면변경', '증자구분', '증거금비율',
            '신용가능', '신용기간', '전일거래량', '액면가', '상장일자',
            '상장주수', '자본금', '결산월', '공모가', '우선주',
            '공매도과열', '이상급등', 'KRX300', 'KOSPI', '매출액',
            '영업이익', '경상이익', '당기순이익', 'ROE', '기준년월',
            '시가총액', '그룹사코드', '회사신용한도초과', '담보대출가능', '대주가능'
        ]

        df2 = pd.read_fwf(tmp_fil2, widths=field_specs, names=part2_columns)
        df = pd.merge(df1, df2, how='outer', left_index=True, right_index=True)

        del (df1)
        del (df2)
        os.remove(tmp_fil1)
        os.remove(tmp_fil2)
        return df

    def parse_kosdaq_master(self, base_dir: str):
        file_name = base_dir + "/kosdaq_code.mst"
        tmp_fil1 = base_dir +  "/kosdaq_code_part1.tmp"
        tmp_fil2 = base_dir +  "/kosdaq_code_part2.tmp"

        wf1 = open(tmp_fil1, mode="w", encoding="cp949")
        wf2 = open(tmp_fil2, mode="w")
        with open(file_name, mode="r", encoding="cp949") as f:
            for row in f:
                rf1 = row[0:len(row) - 222]
                rf1_1 = rf1[0:9].rstrip()
                rf1_2 = rf1[9:21].rstrip()
                rf1_3 = rf1[21:].strip()
                wf1.write(rf1_1 + ',' + rf1_2 + ',' + rf1_3 + '\n')

                rf2 = row[-222:]
                wf2.write(rf2)

        wf1.close()
        wf2.close()

        part1_columns = ['단축코드', '표준코드', '한글명']
        df1 = pd.read_csv(tmp_fil1, header=None, encoding="cp949", names=part1_columns)

        field_specs = [
            2, 1, 4, 4, 4,      # line 20
            1, 1, 1, 1, 1,      # line 27
            1, 1, 1, 1, 1,      # line 32
            1, 1, 1, 1, 1,      # line 38
            1, 1, 1, 1, 1,      # line 43
            1, 9, 5, 5, 1,      # line 48
            1, 1, 2, 1, 1,      # line 54
            1, 2, 2, 2, 3,      # line 64
            1, 3, 12, 12, 8,    # line 69
            15, 21, 2, 7, 1,    # line 75
            1, 1, 1, 9, 9,      # line 80
            9, 5, 9, 8, 9,      # line 85
            3, 1, 1, 1
        ]

        part2_columns = [
            '그룹코드', '시가총액규모', '지수업종대분류', '지수업종중분류', '지수업종소분류', # line 20
            '벤처기업', '저유동성', 'KRX', 'ETP', 'KRX100',  # line 27
            'KRX자동차', 'KRX반도체', 'KRX바이오', 'KRX은행', 'SPAC',   # line 32
            'KRX에너지화학', 'KRX철강', '단기과열', 'KRX미디어통신', 'KRX건설', # line 38
            '투자주의', 'KRX증권', 'KRX선박', 'KRX섹터_보험', 'KRX섹터_운송',   # line 43
            'KOSDAQ150', '기준가', '매매수량단위', '시간외수량단위', '거래정지',    # line 48
            '정리매매', '관리종목', '시장경고', '경고예고', '불성실공시',   # line 54
            '우회상장', '락구분', '액면변경', '증자구분', '증거금비율',     # line 64
            '신용가능', '신용기간', '전일거래량', '액면가', '상장일자',     # line 69
            '상장주수', '자본금', '결산월', '공모가', '우선주',     # line 75
            '공매도과열', '이상급등', 'KRX300', '매출액', '영업이익',   # line 80
            '경상이익', '당기순이익', 'ROE', '기준년월', '시가총액',    # line 85
            '그룹사코드', '회사신용한도초과', '담보대출가능', '대주가능'
        ]

        df2 = pd.read_fwf(tmp_fil2, widths=field_specs, names=part2_columns)
        df = pd.merge(df1, df2, how='outer', left_index=True, right_index=True)

        del (df1)
        del (df2)
        os.remove(tmp_fil1)
        os.remove(tmp_fil2)
        return df

    def fetch_kospi_symbols(self):
        base_dir = os.getcwd()
        file_name = "kospi_code.mst.zip"
        url = "https://new.real.download.dws.co.kr/common/master/" + file_name
        self.download_master_file(base_dir, file_name, url)
        df = self.parse_kospi_master(base_dir)
        return df

    def fetch_kosdaq_symbols(self):
        base_dir = os.getcwd()
        file_name = "kosdaq_code.mst.zip"
        url = "https://new.real.download.dws.co.kr/common/master/" + file_name
        self.download_master_file(base_dir, file_name, url)
        df = self.parse_kosdaq_master(base_dir)
        return df

    def fetch_marketday(self):
        t_n = datetime.datetime.now().strftime('%Y%m%d')
        headers = {
            "Content-Type": "application/json",
            "authorization": self.access_token,
            "appKey": self.api_key,
            "appSecret": self.api_secret,
            "tr_id": "CTCA0903R",
            'custtype': 'P'
        }
        path = 'uapi/domestic-stock/v1/quotations/chk-holiday'
        url = f"{KI_URL_PRACTICE}/{path}"
        params = {
            "BASS_DT": t_n,
            "CTX_AREA_NK": "",
            "CTX_AREA_FK": ""
        }
        res = requests.get(url, headers=headers, params=params)
        data = res.json()['output'][0]['bzdy_yn']

        return data

    def fetch_price(self, symbol: str) -> dict:
        path = "uapi/domestic-stock/v1/quotations/inquire-price"
        url = f"{self.base_url}/{path}"
        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "FHKST01010100"
        }
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": symbol
        }
        resp = requests.get(url, headers=headers, params=params)
        return resp.json()
    
    def get_caution_code_list(self, l, rm=False):
        a = []
        for _l in l:
            r = self.fetch_price(_l)['output']
            c = r['iscd_stat_cls_code']
            if (c == '51') or (c == '52') or (c == '53') or (c == '54') or (c == '58') or (c == '59'):
                if rm:
                    l.remove(_l)
                else:
                    a.append(_l)
            
        return l if rm else a
    
    def filter_code_list(self):
        kp = self.fetch_kospi_symbols()
        kd = self.fetch_kosdaq_symbols()
        kp = kp.loc[(kp['그룹코드'] == 'ST') 
                & (kp['시가총액규모'] != 0) 
                & (kp['시가총액'] != 0) 
                & (kp['우선주'] == 0) 
                & (kp['단기과열'] == 0) 
                & (kp['락구분'] == 0)
                & (kp['액면변경'] == 0) 
                & (kp['증자구분'] == 0)
                & (kp['ETP'] != 'Y') 
                & (kp['SRI'] != 'Y') 
                & (kp['ELW발행'] != 'Y') 
                & (kp['KRX은행'] != 'Y') 
                & (kp['KRX증권'] != 'Y')
                & (kp['KRX섹터_보험'] != 'Y')
                & (kp['SPAC'] != 'Y') 
                & (kp['저유동성'] != 'Y') 
                & (kp['거래정지'] != 'Y') 
                & (kp['정리매매'] != 'Y') 
                & (kp['관리종목'] != 'Y') 
                & (kp['시장경고'] != 'Y') 
                & (kp['경고예고'] != 'Y') 
                & (kp['불성실공시'] != 'Y') 
                & (kp['우회상장'] != 'Y') 
                & (kp['공매도과열'] != 'Y') 
                & (kp['이상급등'] != 'Y') 
                & (kp['회사신용한도초과'] != 'Y') 
                & (kp['담보대출가능'] != 'Y') 
                & (kp['대주가능'] != 'Y') 
                & (kp['신용가능'] == 'Y')
                & (kp['증거금비율'] != 100)
                & (kp['기준가'] > 1000) 
                & (kp['전일거래량'] > 200000) 
                ]
        kd = kd.loc[(kd['그룹코드'] == 'ST') 
                & (kd['시가총액규모'] != 0) 
                & (kd['시가총액'] != 0) 
                & (kd['우선주'] == 0) 
                & (kd['단기과열'] == 0) 
                & (kd['락구분'] == 0)
                & (kd['액면변경'] == 0) 
                & (kd['증자구분'] == 0)
                & (kd['ETP'] != 'Y') 
                & (kd['KRX은행'] != 'Y') 
                & (kd['KRX증권'] != 'Y')
                & (kd['KRX섹터_보험'] != 'Y')
                & (kd['SPAC'] != 'Y') 
                & (kd['투자주의'] != 'Y') 
                & (kd['거래정지'] != 'Y') 
                & (kd['정리매매'] != 'Y') 
                & (kd['관리종목'] != 'Y') 
                & (kd['시장경고'] != 'Y') 
                & (kd['경고예고'] != 'Y') 
                & (kd['불성실공시'] != 'Y') 
                & (kd['우회상장'] != 'Y') 
                & (kd['공매도과열'] != 'Y') 
                & (kd['이상급등'] != 'Y') 
                & (kd['회사신용한도초과'] != 'Y') 
                & (kd['담보대출가능'] != 'Y') 
                & (kd['대주가능'] != 'Y') 
                & (kd['신용가능'] == 'Y')
                & (kd['증거금비율'] != 100)
                & (kp['기준가'] > 1000) 
                & (kp['전일거래량'] > 200000) 
                ]
        _code_list = kp['단축코드'].to_list() + kd['단축코드'].to_list()
        code_list = self.get_caution_code_list(_code_list, True)

        return code_list
    
    def fetch_ohlcv_domestic(self, symbol: str, timeframe:str='D', start_day:str="", end_day:str="", adj_price:bool=True):
        path = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        url = f"{self.base_url}/{path}"

        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "FHKST03010100"
        }

        if end_day == "":
            now = datetime.datetime.now()
            end_day = now.strftime("%Y%m%d")

        if start_day == "":
            start_day = "19800104"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": symbol,
            "FID_INPUT_DATE_1": start_day,
            "FID_INPUT_DATE_2": end_day,
            "FID_PERIOD_DIV_CODE": timeframe,
            "FID_ORG_ADJ_PRC": 0 if adj_price else 1
        }
        resp = requests.get(url, headers=headers, params=params)
        return resp.json()
    
    def df_today_1m_ohlcv(self, code, to, _min):
        df = None
        a_d = []
        a_c = []

        min_lst = self.fetch_today_1m_ohlcv(code, to)['output2']
        min_cnt = _min - 1

        for i, m in enumerate(min_lst):
            min_div = int(m['stck_cntg_hour'][2:4]) % _min
            # ohlcv
            # stck_oprc stck_hgpr stck_lwpr stck_prpr cntg_vol
            if m['stck_cntg_hour'] != '153000' and min_div == min_cnt:
                opn = min_lst[i + min_cnt]['stck_oprc']
                chk_hig = max([int(min_lst[i + j]['stck_hgpr']) for j in range(_min)])
                chk_low = min([int(min_lst[i + j]['stck_lwpr']) for j in range(_min)])
                sum_vol = sum([int(min_lst[i + j]['cntg_vol']) for j in range(_min)])
                a_c.append(str(opn) + '|' + str(chk_hig) + '|' + str(chk_low) + '|' + m['stck_prpr'] + '|' + str(sum_vol))
            else:
                a_c.append((m['stck_oprc'] + '|' + m['stck_hgpr'] + '|' + m['stck_lwpr'] + '|' + m['stck_prpr'] + '|' + m['cntg_vol']))
            a_d.append(str(m['stck_bsop_date'] + m['stck_cntg_hour']))

        df = pd.DataFrame({'date': a_d, code: a_c})
        df = df.set_index('date')

        n_s = 0
        if _min == 3:
            n_s = 10
        elif _min == 5 or _min == 10:
            n_s = 11
        elif _min == 15:
            n_s = 16
            
        if to == '153000':
            df_h = df.head(1)
            df_b = df.iloc[n_s::_min, :]
            df = pd.concat([df_h, df_b])[::-1]
        else:
            df = df.iloc[::_min, :][::-1]
        return df
    
    def fetch_today_1m_ohlcv(self, symbol: str, to: str, once=False):
        o = {}
        _o = self._fetch_today_1m_ohlcv(symbol, to)
        o['output1'] = _o['output1']
        o['output2'] = _o['output2']

        if not once:
            t = datetime.datetime.strptime(to, '%H%M%S') - datetime.timedelta(minutes=30)
            while t >= datetime.datetime.strptime('090000', '%H%M%S'):
                _o = self._fetch_today_1m_ohlcv(symbol, t.strftime('%H%M%S'))
                o['output2'].extend(_o['output2'])
                t = t - datetime.timedelta(minutes=30)

        _l = o['output2']
        for i, l in enumerate(_l):
            if l['stck_cntg_hour'] == '090000':
                _l = _l[:i + 1]
                break
        o['output2'] = _l

        return o
    
    def _fetch_today_1m_ohlcv(self, symbol: str, to: str):
        headers = {
            "Content-Type": "application/json",
            "authorization": self.access_token,
            "appKey": self.api_key,
            "appSecret": self.api_secret,
            "tr_id": "FHKST03010200",
            "tr_cont": "",
        }
        path = 'uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice'
        url = f"{self.base_url}/{path}"
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_etc_cls_code": "",
            "fid_input_iscd": symbol,
            "fid_input_hour_1": to,
            "fid_pw_data_incu_yn": "Y"
        }
        res = requests.get(url, headers=headers, params=params)
        data = res.json()

        return data

    def fetch_balance(self) -> dict:
        output = {}
        data = self._fetch_balance()
        output['output1'] = data['output1']
        output['output2'] = data['output2']

        while data['tr_cont'] == 'M':
            fk100 = data['ctx_area_fk100']
            nk100 = data['ctx_area_nk100']

            data = self._fetch_balance(fk100, nk100, 'N')
            output['output1'].extend(data['output1'])
            output['output2'].extend(data['output2'])

        return output

    def _fetch_balance(self, ctx_area_fk100: str = "", ctx_area_nk100: str = "", trCont='') -> dict:
        path = "uapi/domestic-stock/v1/trading/inquire-balance"
        url = f"{self.base_url}/{path}"
        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "VTTC8434R" if self.mock else "TTTC8434R",
           "tr_cont": trCont
        }
        params = {
            'CANO': self.acc_no_prefix,
            'ACNT_PRDT_CD': self.acc_no_postfix,
            'AFHR_FLPR_YN': 'N',
            'OFL_YN': 'N',
            'INQR_DVSN': '01',
            'UNPR_DVSN': '01',
            'FUND_STTL_ICLD_YN': 'N',
            'FNCG_AMT_AUTO_RDPT_YN': 'N',
            'PRCS_DVSN': '01',
            'CTX_AREA_FK100': ctx_area_fk100,
            'CTX_AREA_NK100': ctx_area_nk100
        }

        res = requests.get(url, headers=headers, params=params)
        data = res.json()
        data['tr_cont'] = res.headers['tr_cont']
        return data

    def create_order(self, side: str, symbol: str, price: int, quantity: int, order_type: str) -> dict:
        path = "uapi/domestic-stock/v1/trading/order-cash"
        url = f"{self.base_url}/{path}"

        if self.mock:
            tr_id = "VTTC0802U" if side == "buy" else "VTTC0801U"
        else:
            tr_id = "TTTC0802U" if side == "buy" else "TTTC0801U"

        unpr = "0" if order_type == "01" or order_type == "06" else str(price)

        data = {
            "CANO": self.acc_no_prefix,
            "ACNT_PRDT_CD": self.acc_no_postfix,
            "PDNO": symbol,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": unpr
        }
        hashkey = self.issue_hashkey(data)
        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": tr_id,
           "custtype": "P",
           "hashkey": hashkey
        }
        resp = requests.post(url, headers=headers, data=json.dumps(data))
        return resp.json()
    
    def create_over_buy_order(self, symbol: str, quantity: int) -> dict:
        resp = self.create_order("buy", symbol, 0, quantity, "06")
        return resp

    def create_over_sell_order(self, symbol: str, quantity: int) -> dict:
        resp = self.create_order("sell", symbol, 0, quantity, "06")
        return resp

    def create_market_buy_order(self, symbol: str, quantity: int) -> dict:
        resp = self.create_order("buy", symbol, 0, quantity, "01")
        return resp

    def create_market_sell_order(self, symbol: str, quantity: int) -> dict:
        resp = self.create_order("sell", symbol, 0, quantity, "01")
        return resp

    def cancel_order(self, org_no: str, order_no: str, quantity: int, total: bool, order_type: str="00", price: int=100):
        return self.update_order(org_no, order_no, order_type, price, quantity, False, total)

    def update_order(self, org_no: str, order_no: str, order_type: str, price: int, quantity: int, is_change: bool = True, total: bool = True):
        path = "uapi/domestic-stock/v1/trading/order-rvsecncl"
        url = f"{self.base_url}/{path}"
        param = "01" if is_change else "02"
        data = {
            "CANO": self.acc_no_prefix,
            "ACNT_PRDT_CD": self.acc_no_postfix,
            "KRX_FWDG_ORD_ORGNO": org_no,
            "ORGN_ODNO": order_no,
            "ORD_DVSN": order_type,
            "RVSE_CNCL_DVSN_CD": param,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price),
            "QTY_ALL_ORD_YN": 'Y' if total else 'N'
        }
        hashkey = self.issue_hashkey(data)
        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "VTTC0803U" if self.mock else "TTTC0803U",
           "hashkey": hashkey
        }
        resp = requests.post(url, headers=headers, data=json.dumps(data))
        return resp.json()

    def fetch_open_order(self, param: dict):
        path = "uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"
        url = f"{self.base_url}/{path}"

        fk100 = param["CTX_AREA_FK100"]
        nk100 = param["CTX_AREA_NK100"]
        type1 = param["INQR_DVSN_1"]
        type2 = param["INQR_DVSN_2"]

        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "TTTC8036R"
        }

        params = {
            "CANO": self.acc_no_prefix,
            "ACNT_PRDT_CD": self.acc_no_postfix,
            "CTX_AREA_FK100": fk100,
            "CTX_AREA_NK100": nk100,
            "INQR_DVSN_1": type1,
            "INQR_DVSN_2": type2
        }

        resp = requests.get(url, headers=headers, params=params)
        return resp.json()