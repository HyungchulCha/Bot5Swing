'''
[종목선정]
시가총액 300억이상
기준가 500이상
신고가(종가기준) 오늘종가가 지난 20봉중 신고가
거래량 비율 어제부터 10봉전까지 평균보다 250%이상
오늘포함 10봉간 최고최저폭 50%이하만
'''

# sym_lst = []

# for c in cl:

#     d = self.bkk.fetch_ohlcv_domestic(c, 'D', tn_1.strftime('%Y%m%d'), tn.strftime('%Y%m%d'))

#     h_l = []
#     l_l = []
#     c_l = []
#     v_l = []

#     for i in d['output2']:
#         h_l.append(float(i['stck_hgpr']))
#         l_l.append(float(i['stck_lwpr']))
#         c_l.append(float(i['stck_clpr']))
#         v_l.append(float(i['acml_vol']))

#     # 1
#     m_c = float(d['output1']['hts_avls'])
#     c_p = float(d['output1']['stck_prpr'])

#     c_l_t = c_l[0]
#     c_l_x = max(c_l[1:])

#     v_l_t = v_l[0]
#     v_l_a = np.mean(v_l[1:11])

#     h_l_x = max(h_l)
#     l_l_n = min(l_l)

#     if\
#     m_c >= 300 and\
#     c_p >= 500 and\
#     c_l_t > c_l_x and\
#     v_l_t >= v_l_a * 3.5 and\
#     l_l_n * 1.5 >= h_l_x\
#     :
#         sym_lst.append(c)

#     # 2
#     c_l_0 = c_l[0]
#     c_l_1 = c_l[1]

#     h_l_x = max(h_l[5:20])
#     l_l_n = min(l_l[5:20])

#     c_m05 = np.mean(c_l[:5])
#     c_m20 = np.mean(c_l[:20])
#     c_m60 = np.mean(c_l[:60])

#     if \
#     c_l_0 < (c_l_1 * 1.05) and \
#     ((h_l_x / l_l_n) - 1) * 100 > 1.1 and \
#     c_m05 > c_m20 > c_m60 and \
#     c_m20 * 1.05 > c_l_0 > c_m20 and \
#     c_l_0 > c_m05\
#     :
#         sym_lst.append(c)