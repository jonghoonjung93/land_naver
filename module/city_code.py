import PublicDataReader as pdr
import json
from PublicDataReader import BuildingLedger

#-------------- 시군구코드와 법정동코드 조회하기 --------------#
def get_city_code(sigungu_name, bdong_name):
    # config.json 파일처리 ----------------
    with open('config.json','r') as f:
        config = json.load(f)
    service_key = config['GG_DATA']['KEY']
    # ------------------------------------
    # print(service_key)

    # 데이터 조회 인스턴스 만들기
    api = BuildingLedger(service_key)
    # print(pdr.__version__)

    # sigungu_name = "일산동구"
    # bdong_name = "식사동"
    # sigungu_name = "분당구"
    # bdong_name = "백현동"

    code = pdr.code_bdong()

    result = code.loc[(code['시군구명'].str.contains(sigungu_name)) &
            (code['읍면동명']==bdong_name)]

    # print("-------------------------------------------")
    sigungu_code = result['시군구코드'].values[0]
    total_code = result['법정동코드'].values[0]
    bubjd_code = total_code.replace(sigungu_code,'')
    # print(f"시군구코드 : {sigungu_code}")
    # print(f"법정동코드 : {bubjd_code} ({total_code})")
    
    return(sigungu_code, bubjd_code)

if __name__ == '__main__':
    sigungu_name = "일산동구"
    bdong_name = "장항동"
    get_city_code(sigungu_name, bdong_name)
