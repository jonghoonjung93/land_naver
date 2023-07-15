import requests
import xmltodict, json
import pandas as pd
import time
import sys
import time,datetime
from decimal import Decimal
from module.city_code import get_city_code
from module.etc_util import printL, mode_check

#-------------- 공공데이터(국토부) api를 활용해 건물내 각 호실별 정보조회 및 xlsx 파일 저장 프로그램 --------------#

def gg_data(building):
    # config.json 파일처리 ----------------
	with open('config.json','r') as f:
		config = json.load(f)
	service_key = config['GG_DATA']['KEY']
	address = config[building]['ADDRESS']
	memo = config[building]['MEMO']
	# ------------------------------------

	# --------- 시군구,법정동 코드 조회해오기 (module.city_code / get_city_code 함수) -----------
	flag = True
	if flag:
		words = address.split(' ')
		if len(words) == 4:
			si_name, gu_name, dong_name, bunji = address.split(' ')
			# printL(f"{si_name}, {gu_name}, {dong_name}")
			if "-" in bunji:
				bun, ji = bunji.split('-')
				bun = bun.zfill(4)
				ji = ji.zfill(4)
			else:
				bun = bunji.zfill(4)
				ji = "0000"

			# printL(f"{bun}, {ji}")
		else:
			printL(f"ADDRESS : {address}, 4단어가 아님. 확인필요")
		
		result = get_city_code(gu_name, dong_name)	# 시군구 코드, 법정동 코드 조회 함수 호출
		sigunguCd = result[0]
		bjdongCd = result[1]

		printL(f"시군구코드 : {sigunguCd}, 법정동코드 : {bjdongCd}")
	# -----------------------------------------------------------------------------------

	# --------- 공공데이터(국토부)에 api 접근해서 호수(호 Count) 체크하기 -----------
	flag = True
	if flag:
		max_attempts = 10
		retry_delay = 3
		title_count = 0
		while True:
			try:
				url_title = f"https://apis.data.go.kr/1613000/BldRgstService_v2/getBrTitleInfo?serviceKey={service_key}&sigunguCd={sigunguCd}&bjdongCd={bjdongCd}&platGbCd=0&bun={bun}&ji={ji}&numOfRows=100&pageNo=1"
				content_title = requests.get(url_title).content
				data_title_dict = xmltodict.parse(content_title)
				total_count_title = data_title_dict['response']['body']['totalCount']
				printL(f"{building} : 표재부 total_count : {total_count_title}")
				# 표제부 안에 item 이 0~N 개일때 처리가 달라야 함.
				if int(total_count_title) == 0:	# 0개 (내용물이 없는 경우) BLD1-15
					ho_count = 0
					sedae_count = 0
					fml_count = 0
				elif int(total_count_title) == 1:	# 1개 (일반적인 경우)
					# 표제부 item 한개짜리
					ho_count = data_title_dict['response']['body']['items']['item']['hoCnt']
					sedae_count = data_title_dict['response']['body']['items']['item']['hhldCnt']
					fml_count = data_title_dict['response']['body']['items']['item']['fmlyCnt']
				else:	# 2개 이상 (BLD3-33, BLD3-19)
					# 표제부 item 두개이상인 경우, dataframe 으로 변환해서 복수의 값을 더해줌
					json_data_title = data_title_dict['response']['body']['items']['item']
					df_title = pd.DataFrame(json_data_title)
					# printL(df_title)
					# printL(df_title['hoCnt'].values)
					ho_count = 0
					sedae_count = 0
					fml_count = 0
					for item in df_title['hoCnt'].values:
						ho_count = ho_count + int(item)
					for item in df_title['hhldCnt'].values:
						sedae_count = sedae_count + int(item)
					for item in df_title['fmlyCnt'].values:
						fml_count = fml_count + int(item)

				printL(f"{building} : 건축물대장 표제부({total_count_title}) 세대수={sedae_count}, 호수={ho_count}, 가구수={fml_count}")
				# Success
				break
			except:
				# Fail
				title_count  = title_count + 1
				printL(f"{building} : ERROR! 세대수,호수,가구수 가져오기 에러 ({title_count})")
				printL(url_title)
				time.sleep(retry_delay)
				if title_count == max_attempts:
					# 실패시
					ho_count = 0
					sedae_count = 0
					fml_count = 0
					break

	# --------- 공공데이터(국토부)에 api 접근해서 각 호실별 데이터 받아오기 (결과물 : Dataframe) -----------
	flag = True
	if flag:
		# sigunguCd = "41285"
		# bjdongCd = "10400"
		# bun = "0727"
		# ji = "0001"
		max_attempts = 100	# 재시도 최대값
		retry_delay = 3		# 재시도시 delay
		concat_df = pd.DataFrame()

		for attempt in range(max_attempts):
			try:
				page = 1
				while True:
					url = f"https://apis.data.go.kr/1613000/BldRgstService_v2/getBrExposPubuseAreaInfo?serviceKey={service_key}&numOfRows=100&pageNo={page}&sigunguCd={sigunguCd}&bjdongCd={bjdongCd}&platGbCd=0&bun={bun}&ji={ji}"
					# printL(url)
					content = requests.get(url).content
					data_dict = xmltodict.parse(content)
					total_count = data_dict['response']['body']['totalCount']
					if int(total_count) == 0:	# 데이터가 없는 경우 (1인소유 건물일 경우, 구분등기가 없음)
						break
					json_data = data_dict['response']['body']['items']['item']
					df = pd.DataFrame(json_data)
					concat_df = pd.concat([concat_df, df], ignore_index=True)
					printL(f"{building} : {page}, {len(json_data)} ({len(concat_df)} / {total_count})")

					if len(json_data) == 100:	# 가져온게 100건이면 다음 페이지로 넘어감
						page += 1
						if int(len(concat_df)) == int(total_count):	# BLD1-07(731-2) 딱 300건인 경우때문에 추가. 100건 받아왔지만 종료해야됨
							# printL(f"len(concat_df) = {len(concat_df)}, total_count = {total_count}")
							break
					else:
						break

				# If the code succeeds, break out of the loop
				break
			except Exception as e:
				# Handle the exception (optional)
				printL(url)
				printL(f"ERROR : Attempt {attempt + 1} failed: {str(e)}")
				concat_df = pd.DataFrame()	# 중간에 에러났으면 비워주고 다시 시작
				time.sleep(10)

			# Rest for 3 seconds before the next attempt
			time.sleep(retry_delay)

		else:
			# Code to execute if all attempts fail
			printL("Maximum attempts reached without succes")
			printL("- 주소가 정확히 입력되었는지, 서비스는 이상이 없는지 확인해주세요.")	# 잘못된 주소일때 : 'NoneType' object is not subscriptable
			printL(f"- 입력된 주소 : {address}")
			sys.exit(1)

		total_rows = len(concat_df)
		printL(f"Total rows: {total_rows}")
		if int(total_rows) == int(total_count):
			printL(f"{building} CHECKSUM OK! : {total_rows} == {total_count} ")
		else:
			printL(f"{building} CHECKSUM ERROR! : 가져온 데이터 값 : {total_rows}, 가져와야 하는 값 : {total_count} ")
	# ---------------------------------------------------------------------------------------

	# --------- Dataframe 가공 : 전용면적만 있기때문에, 총면적을 구하기 위해 동일호수의 전용면적을 모두 sum 하고 sort 처리 -----------
	flag = True
	if flag and total_rows != 0:
		sorted_df = concat_df.sort_values(by=['flrGbCdNm', 'flrNo', 'hoNm', 'exposPubuseGbCd'], ascending=[False, True, True, True])	# 지상구분,층,호수로 sort
		# sorted_df.to_excel(f"./xlsx/debug.xlsx", index=False)	# 디버그 할때 원천 데이터 찍어보는 용도
		sorted_df['totalArea'] = None	# Dataframe 에 총면적 컬럼추가
		prev_ho = '000'
		totalArea = 0
		new_df = pd.DataFrame()
		for index, row in sorted_df.iterrows():	# 한개한개 row 를 읽으면서 처리
			bldNm_val = row['bldNm']
			area_val = row['area']
			flrNo_val = row['flrNo']
			flrGbCdNm_val = row['flrGbCdNm']
			flrNoNm_val = row['flrNoNm']
			hoNm_val = row['hoNm']
			etcPurps_val = row['etcPurps']
			newPlatPlc_val = row['newPlatPlc']
			platPlc_val = row['platPlc']
			exposPubuseGbCdNm = row['exposPubuseGbCdNm']
			# printL(index, type(index), type(area_val))
			if hoNm_val == prev_ho:	# 이번에 읽은 호수가 앞에 호수와 중복일때는
				# printL("---111")
				# printL(totalArea, float(area_val))
				totalArea = Decimal(str(totalArea)) + Decimal(area_val)	# 총면적에 누적시키기
			else:
				# printL("---222")
				totalArea = Decimal(area_val)	# 새로운 호수일때
			prev_ho = hoNm_val

			# totalArea = "{:.2f}".format(totalArea)	# 소수점 2째자리값이 살짝 달라지네?
			pyung = float(totalArea) * 0.3025	# 평수 구하기
			new_pyung = "{:.2f}".format(round(pyung, 2))	# 소수점 2자리까지만 필요, 뒤에 0채워서 2자리 맞추기
			# printL(f"bldNm_val : {bldNm_val}")
			if exposPubuseGbCdNm == '전유':		# 전유부분만 새로운 Dataframe 에 저장하귀 위해 (공용은 면적만 사용하고 나머지는 불필요)
				new_bldNm = bldNm_val
				new_area = "{:.2f}".format(round(float(area_val), 2))
				new_etcPurps = etcPurps_val
				new_hoNm = hoNm_val
				new_flrGbCdNm = flrGbCdNm_val
				new_flrNoNm = flrNoNm_val
				new_newPlatPlc = newPlatPlc_val
				new_platPlc = platPlc_val
				new_areaPyung = "{:.2f}".format(round(float(area_val) * 0.3025, 2))
			# printL(f"new_bldNm : {new_bldNm}")
			new_row = pd.DataFrame(
				[[new_bldNm, new_flrGbCdNm, new_flrNoNm, new_hoNm, totalArea, new_area
      			, new_pyung, new_areaPyung, new_etcPurps, new_newPlatPlc, new_platPlc]]
				, columns=['건물명','구분','층','호수','총면적','전용면적','총면적(평)','전용면적(평)','세부용도','도로명주소','주소']
				)
			# new_df = new_df.append(new_row, ignore_index=True)    # 구버젼 문법 (지금은 사용안됨)
			new_df = pd.concat([new_df, new_row], ignore_index=True)
	# ------------------------------------------------------------------------------------------------------------

	# --------- Dataframe 을 지상/지하구분, 층, 호수별로 sort 하기 -----------
	flag = True
	if flag and total_rows != 0:
		temp_df = new_df.sort_values(by=['구분', '층', '호수', '총면적'], ascending=False)    # 거꾸로 sort (총면적이 큰게 위로 오도록)
		unique_df = temp_df.drop_duplicates(subset=['호수'])    # 호수 기준으로 제일 위에 (총면적 큰거) 한개의 row 만 남김
		# unique_df['호수'] = unique_df['호수'].astype(str).str.zfill(3)    # Warning 나와서 아래처럼 변경
		unique_df.loc[:, '호수'] = unique_df['호수'].astype(str).str.zfill(20)   # 234호 같은거는 0234 처럼 앞에 0 채워서 20자리로 만들기
		unique_df.loc[:, '층'] = unique_df['층'].astype(str).str.zfill(20)   # 1층 같은거는 01층 처럼 앞에 0 채워서 20자리로 만들기
		complete_df = unique_df.sort_values(by=['구분', '층', '호수'], ascending=[False, True, True])  # 호수 기준으로 다시 정상적으로 sort
		complete_df.loc[:, '호수'] = complete_df['호수'].astype(str).str.lstrip('0')  # 앞에 0 채운거 다시 지우기
		complete_df.loc[:, '층'] = complete_df['층'].astype(str).str.lstrip('0')  # 앞에 0 채운거 다시 지우기
	# ----------------------------------------------------------------

	# --------- Dataframe 을 Excel 파일로 저장하기 -----------
	address_short = address.replace("고양시 일산동구 ","")
	file_name = f"{building[3:]}_{memo}({address_short})"	
	flag = True
	if flag and total_rows != 0:	# Excel 파일 생성
		printL(f"{building} : Total 호수 = {str(len(complete_df))}, 원장세대수/호수/가구수 = {sedae_count}/{ho_count}/{fml_count}, 차이 : {len(complete_df)-int(ho_count)-int(sedae_count)-int(fml_count)}")
		# ------ 이부분에서 호수를 체크하는 로직이 필요함 ----------------#
		# sorted_df.to_excel(f"./xlsx/{file_name}_full.xlsx")			# 전체 데이타 (전유 + 공유)
		complete_df.to_excel(f"./xlsx/{file_name}.xlsx", index=False)	# 전유 데이터
	if total_rows == 0:	# 내용이 없어서 빈파일 생성만
		printL(f"{building} : WARNING 데이터 없음. 빈파일 생성")
		blank_row = pd.DataFrame(
			[['', '', '', '', '', ''
			, '', '', '', '', '']]
			, columns=['건물명','구분','층','호수','총면적','전용면적','총면적(평)','전용면적(평)','세부용도','도로명주소','주소']
			)
		blank_df = pd.DataFrame()
		blank_df = pd.concat([blank_df, blank_row], ignore_index=True)
		blank_df.to_excel(f"./xlsx/{file_name}.xlsx", index=False)	# 전유 데이터
	# ----------------------------------------------------

if __name__ == '__main__':
	# gg_data('BLD3-33')	# 표제부 item 이 두개
	# gg_data('BLD1-15')		# 아예 없는경우
	# gg_data('BLD1-01')	# 1개짜리 len... 3, 431

	# --------- MAIN 실행부분 (json 파일에서 건목록을 가져와서 실행) -----------
	flag = True
	if flag:
		current_time = datetime.datetime.now()
		formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
		start_time = current_time.strptime(formatted_time, "%Y-%m-%d %H:%M:%S")
		printL(f"-- START : {start_time}")
		
		with open('config.json','r') as f:
			config = json.load(f)
		bld_list = config
		for item in bld_list:
			if item[:3] == "BLD":
				printL(item)
				gg_data(item)
		
		current_time = datetime.datetime.now()
		formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
		end_time = current_time.strptime(formatted_time, "%Y-%m-%d %H:%M:%S")
		printL(f"-- END : {start_time} ~ {end_time}")
		printL(f"-- Elapsed time : {end_time - start_time}")
	# ----------------------------------------------------------------
