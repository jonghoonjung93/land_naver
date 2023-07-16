from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from datetime import timedelta
from module.etc_util import printL, mode_check
import telegram
import asyncio, json
import time, datetime
import csv
import sqlite3

global_var = 0
global_msg_contents = []

def land_naver(building):
	options = Options()
	
	# global hostname
	if mode_check() == 'TEST':
		# options.add_argument("headless") #크롬창이 뜨지 않고 백그라운드로 동작됨
		pass
	else:
		options.add_argument("headless") #크롬창이 뜨지 않고 백그라운드로 동작됨

	# 아래 옵션 두줄 추가(NAS docker 에서 실행시 필요, memory 부족해서)
	options.add_argument('--no-sandbox')
	options.add_argument('--disable-dev-shm-usage')

	# headless로 동작할때 element를 못찾으면 아래 두줄 추가 (창크기가 작아서 못찾을수 있음)
	# options.add_argument("start-maximized")
	# options.add_argument("window-size=1920,1080")
	options.add_argument("window-size=1920,2160")	# 창크기가 작아서 전체 내용이 표시되지 않아서 크게 키움
	# options.add_argument("window-size=1300,2000")	# 이 크기로는 동그라미 클릭 오류가 가끔발생
	# options.add_argument("disable-gpu")
	# options.add_argument("lang=ko_KR")

	# 아래는 headless 크롤링을 막아놓은곳에 필요 (user agent에 HeadlessChrome 이 표시되는걸 방지)
	options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
	
    # config.json 파일처리 ----------------
	with open('config.json','r') as f:
		config = json.load(f)
	url = config[building]['URL']
	naver_bld_id = config[building]['NAVER_BLD_ID']
	address = config[building]['ADDRESS']
	memo = config[building]['MEMO']
	# ------------------------------------

	driver = webdriver.Chrome(options=options)

    # 건물정보 csv 파일처리 ----------------
	csv_data = []
	address_short = address.replace("고양시 일산동구 ","")
	file_name = f"csv/{building[3:]}_{memo}({address_short}).csv"
	with open(file_name,'r') as file:	# csv_data 라는 변수에 건물정보를 저장
		reader = csv.reader(file)
		for line in reader:
			csv_data.append(line)
	# for line in csv_data:	# line[0]:호수, line[1]:총면적, line[2]:전용면적, line[3]:세부용도
	# 	print(line[1])
	# ------------------------------------

	# 페이지 접속
	driver.get(url)
	time.sleep(2)

	# 해당건물 클릭
	driver.find_element(By.ID, naver_bld_id).find_element(By.CLASS_NAME, 'marker_transparent').click()	# 건물 동그라미 클릭
	time.sleep(2)

	scroll_bar = driver.find_element(By.XPATH, '//*[@id="listContents1"]/div')	# 좌측 매물리스트 스크롤바
	
	# for _ in range(10):	# 스크롤바 내리기 10회 반복
	while True:	# 스크롤바 내리기 무한반복 (필요한만큼)
		# print(driver.execute_script("return document.documentElement.scrollHeight"))
		new_height = driver.execute_script("return arguments[0].scrollHeight", scroll_bar)
		# print(new_height)
		driver.execute_script("arguments[0].scrollBy(0,2000);", scroll_bar)	# 스크롤바 내리기
		time.sleep(0.5)
		driver.execute_script("arguments[0].scrollBy(0,2000);", scroll_bar)	# 스크롤바 내리기
		time.sleep(0.5)
		last_height = driver.execute_script("return arguments[0].scrollHeight", scroll_bar)
		# print(last_height)
		if new_height == last_height:	# 더이상 내려가지 않을때
			break

	# 매물 가져오기
	items = driver.find_element(By.CLASS_NAME, 'item_list.item_list--article').find_elements(By.CLASS_NAME, 'item.false')
	printL(f"building :  {building}({memo}), {len(items)}")	# 매물 개수 확인

	# 날짜 (오늘)
	current_time = datetime.datetime.now()
	formatted_date = current_time.strftime("%Y%m%d")
	# 어제,그제 날짜 yyyymmdd 로 만들기
	today = current_time.date()
	yesterday_form = today - timedelta(days=1)
	yesterday = yesterday_form.strftime("%Y%m%d")
	# delete_day_form = today - timedelta(days=2)	# 삭제대상, 2일전 데이터는 삭제처리
	delete_day_form = today - timedelta(days=3)	# 삭제대상, 3일전 데이터는 삭제처리
	delete_day = delete_day_form.strftime("%Y%m%d")

	# DB 접속
	conn = sqlite3.connect('land_naver.sqlite3')
	cursor = conn.cursor()

	data_list = []	# DB에 insert 대상 매물 리스트
	new_list = []	# 신규 매물 리스트 (알림 대상)
	
	for item in items:
		name = item.find_element(By.CLASS_NAME, 'text').text
		# --- 매물번호 가져오기 (item_number) ----------------------------------------------------------------- #
		try:	# "네이버에서 보기" 버튼이 있는 경우
			naver_view = item.find_element(By.CLASS_NAME, 'label.label--cp')
			# printL(f"naver_view : {naver_view.text}")
			if naver_view.text == "네이버에서 보기":
				naver_view.click()
		except:	# "네이버에서 보기" 버튼이 없는 경우
			try:
				item.find_element(By.CLASS_NAME, 'text').click()
			except:
				pass
		# wait = WebDriverWait(driver, 10)
		# new_url = wait.until(EC.url_changes(driver.current_url))
		try:
			new_url = driver.current_url
			# printL(f"Changed URL: {new_url}")
			split_url = new_url.split("=")
			last_part = split_url[-1]
			item_number = last_part.split("&")[0]
			# printL(item_number)
			naver_bld_id = item_number	# naver_bld_id 는 클릭하고 나면 필요없으니, 여기부터는 이걸 매물번호로 활용
		except:
			naver_bld_id = "0000000000"
		# ------------------------------------------------------------------------------------------------ #
		type = item.find_element(By.CLASS_NAME, 'type').text
		price = item.find_element(By.CLASS_NAME, 'price').text
		info_area_type = item.find_element(By.CLASS_NAME, 'info_area').find_element(By.CLASS_NAME, 'type').text
		info_area_spec = item.find_element(By.CLASS_NAME, 'info_area').find_element(By.CLASS_NAME, 'spec').text
		agent_name_list = item.find_elements(By.CLASS_NAME, 'agent_name')
		agent_name = agent_name_list[1].text
		info_count = info_area_spec.count(",")
		if info_count == 2:
			var1, var2, var3 = info_area_spec.split(',')
		elif info_count == 1:
			var1, var2 = info_area_spec.split(',')
			var3 = ""
		else:
			var1 = info_area_spec
			var2 = ""
			var3 = ""
		size_total, size_real = var1.replace('m²','').split('/')	# 총면적, 전용면적 가져오기
		floor = var2.replace(' ','')[0]
		ho = ''
		try:	# csv 파일이 헤더만 있는경우 line[1]을 못가져오고 에러나는것에 대한 처리
			for line in csv_data[1:]:	# line[0]:호수, line[1]:총면적, line[2]:전용면적, line[3]:세부용도
				csv_size1 = int(float(line[1]))	# 현황이 없으면 이부분에서 에러남
				if csv_size1 == int(size_total) and floor == line[0][0]:	# 총면적이 같고, 층수가 같으면
					# print(f"size1={size1}:{floor}, csv_size1={csv_size1}:{line[1]}:{line[0]}")
					ho = ho + line[0]	# 같은 호수가 여러개일수 있음
					if ho is not None:	# 같은 호수가 여러개면 ,를 이용해서 나열
						ho = ho + ","
			if ho.endswith(","):	# 제일 끝에 , 가 있으면 삭제
				ho = ho[:-1]
		except:
			ho = '현황없음'
		# 중소형사무실 | 월세 | 3,000/190 | 사무실 | 251/135m², 2/7층, 북서향 | 251 | 135 | 2 |  하임빌공인중개사무소 | 214,221
		# print(f"{name} | {type} | {price} | {info_area_type} | {info_area_spec} | {size_total} | {size_real} | {floor} |  {agent_name} | {ho}")
		bld_id = building
		try:
			price_base, price_mon = price.split("/")
		except:
			price_base = price
			price_mon = ""
		tuple1 = (formatted_date, bld_id, memo, address_short, url, naver_bld_id, name, type, price, price_base, price_mon, info_area_type, info_area_spec, size_total, size_real, floor, agent_name, ho)
		# print(tuple1)
		data_list.append(tuple1)	# tuple 을 list 에 추가
		result = f"{name} | {type} | {price} | {info_area_type} | {info_area_spec} | {agent_name} | {ho}"
		# 해당 매물이 기존에 DB에 있는지 확인 (어제자와 비교)
		select_sql = f"SELECT * FROM land_item WHERE date='{yesterday}' AND bld_id = '{bld_id}' AND price = '{price}' AND info_area_spec = '{info_area_spec}' AND agent_name = '{agent_name}'"
		cursor.execute(select_sql)
		result_select = cursor.fetchone()
		# print(result_select)
		if result_select is not None:	# 매물을 어제자 DB에서 조회했는데 이미 있던 매물일 경우
			# print("있다")
			pass
		else:	# 매물이 어제자 DB에 없는 새로운 매물일 경우
			# print("없다. 새로운거 발견!!!!")
			new_list.append(tuple1)

	# print(new_list)

    # DB insert 처리
	delete_sql1 = f"DELETE FROM land_item WHERE date = '{delete_day}' AND bld_id = '{bld_id}'"	# 그저께 데이터 삭제
	cursor.execute(delete_sql1)
	delete_sql2 = f"DELETE FROM land_item WHERE date = '{formatted_date}' AND bld_id = '{bld_id}'"	# 당일자 삭제 (이미 있을때 다시 넣기 위해서)
	cursor.execute(delete_sql2)
	cursor.executemany("INSERT INTO land_item (date, bld_id, memo, address, url, naver_bld_id, name, type, price, price_base, price_mon, info_area_type, info_area_spec, size_total, size_real, floor, agent_name, ho) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);", data_list)
	conn.commit()
	conn.close()

	# time.sleep(1000)
	driver.quit()
	return(new_list)

# telegram 메세지 발송함수
async def tele_push(content): #텔레그램 발송용 함수
	if mode_check() == 'TEST':
		telegram_target = 'TELEGRAM-TEST'	# TEST 모드
	else:
		telegram_target = 'TELEGRAM'	# ONLINE 모드
	# telegram_target = 'TELEGRAM'	# 강제 ONLINE 모드
	# config.json 파일처리 ----------------
	with open('config.json','r') as f:
		config = json.load(f)
	token = config[telegram_target]['TOKEN']
	chat_ids = config[telegram_target]['CHAT-ID']
	# ------------------------------------

	current_time = datetime.datetime.now()
	formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
	bot = telegram.Bot(token = token)

	# 실패시 재시도를 여기서 하도록 변경
	for chat_id in chat_ids:
		# printL(f"chat_id : {chat_id}")
		send_retry = 0
		while True:	# 텔레그램 발송이 혹시 실패하면 최대 3회까지 성공할때까지 재시도
			try:
				# await bot.send_message(chat_id, formatted_time + "\n" + content, parse_mode = 'Markdown', disable_web_page_preview=True)
				await bot.send_message(chat_id, content, parse_mode = 'Markdown', disable_web_page_preview=True)
				printL(f"-- SEND success!!! : {chat_id}")
				break
			except:
				send_retry = send_retry + 1
				printL(f"-- tele_push failed!!! ({send_retry}) : chat_id = {chat_id}")
				time.sleep(3)
				if send_retry == 3:
					printL(f"-- tele_push aborted!!! : chat_id = {chat_id}")
					break
			else:	# 정상작동시
				pass
			finally:	# 마지막에 (정상,에러 상관없이)
				pass

	global global_var
	global_var = global_var + 1	# 보낸 메세지가 있으면 +1씩 올라감

def send_lists(lists):	# 전일자와 비교해서 현재 새로운 매물리스트를 메세지로 발송
	# print(len(lists))
	if len(lists) == 0:	# 어제자와 비교했을때 추가된 건이 없을때
		# print("추가 매물이 없음")
		pass
	else:
		# print("lists is not None")
		msg_content = ""
		for list in lists:
			if list[17] == "":
				ho = "Not found"
			else:
				ho = list[17]
			# if msg_content is not None:
			# 	msg_content = msg_content + "\n"
			# tuple1 = (formatted_date, bld_id, memo, address_short, url, naver_bld_id, name, type, price, price_base, price_mon, info_area_type, info_area_spec, size_total, size_real, floor, agent_name, ho)
			deep_link = f"https://new.land.naver.com/offices?articleNo={list[5]}"
			# msg_content = f"{msg_content}\*{list[2]}({list[3]}): {list[6]} {list[7]}\n - {list[8]} {list[12]}\n - {list[16]}\n - 호수 : _{ho}_\n"
			msg_content = f"{msg_content}\*[{list[2]}({list[3]})]({deep_link}): {list[6]} {list[7]}\n - {list[8]} {list[12]}\n - {list[16]}\n - 호수 : _{ho}_\n"
		printL(msg_content)
		global global_msg_contents
		global_msg_contents.append(msg_content)		# 메세지를 바로 보내지 않고 global list 변수에 담아놓기
		# asyncio.run(tele_push(msg_content)) #텔레그램 발송 (asyncio를 이용해야 함)
		

def initial_lists(lists):	# 건물 처음으로 추가시에 메세지는 보내지 않고 오늘 매물만 DB에 insert 하고 싶을때 사용
	msg_content = ""
	for list in lists:
		if list[17] == "":
			ho = "Not found"
		else:
			ho = list[17]
		# if msg_content is not None:
		# 	msg_content = msg_content + "\n"
		msg_content = f"{msg_content}\*{list[2]}({list[3]}): {list[6]} {list[7]}\n - {list[8]} {list[12]}\n - {list[16]}\n - 호수 : _{ho}_\n"
	printL(msg_content)
	printL(f"COUNT, {len(lists)}")
	global global_var
	global_var = global_var + 1	# 초기화 작업시 "새로운 매물이 없음" 메세지 보내지는거 방지. (뭔가 이미 보낸것처럼 +1)

# lists = land_naver('BLD2-19')
# send_lists(lists)

# ----------- MAIN ------------- 

#--- Start Time 기록 -----
flag = True
if flag:
	current_time = datetime.datetime.now()
	formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
	start_time = current_time.strptime(formatted_time, "%Y-%m-%d %H:%M:%S")
	printL(f"-- START : {start_time}")
	printL(f"-- {mode_check()} MODE")

# send_lists(land_naver('BLD2-19'))	# 로데오탑
# send_lists(land_naver('BLD2-17'))	# 하임빌
# initial_lists(land_naver('BLD2-16'))	# 하임빌	2-15부터 index number 변경됨
# initial_lists(land_naver('BLD2-18'))	# 로데오탑 (처음에 건물 추가할때는 이렇게 넣어야 됨)

#------- 각 건물별로 실행 ----------------------
# send_lists(land_naver('BLD1-05'))
# send_lists(land_naver('BLD1-02'))
flag = True
if flag:
	send_lists(land_naver('BLD1-01'))
	send_lists(land_naver('BLD1-02'))
	send_lists(land_naver('BLD1-03'))
	send_lists(land_naver('BLD1-04'))
	send_lists(land_naver('BLD1-05'))	#1차 동하넥서스
	send_lists(land_naver('BLD1-06'))	#1차 성우사카르
	send_lists(land_naver('BLD1-07'))	#1차
	send_lists(land_naver('BLD1-08'))
	send_lists(land_naver('BLD1-09'))	#1차
	send_lists(land_naver('BLD1-10'))
	send_lists(land_naver('BLD1-11'))	#1차
	send_lists(land_naver('BLD1-12'))	#1차 77건짜리 동그라미 선택 실패 사례발생, 화면크기 키워서 해결
	send_lists(land_naver('BLD1-13'))
	send_lists(land_naver('BLD1-14'))
	send_lists(land_naver('BLD1-17'))
	send_lists(land_naver('BLD1-18'))
	send_lists(land_naver('BLD1-19'))
	send_lists(land_naver('BLD1-20'))
	send_lists(land_naver('BLD1-21'))
	send_lists(land_naver('BLD1-23'))
	send_lists(land_naver('BLD1-24'))
	send_lists(land_naver('BLD1-25'))
	send_lists(land_naver('BLD1-26'))
	send_lists(land_naver('BLD1-27'))
	send_lists(land_naver('BLD1-28'))
	send_lists(land_naver('BLD1-29'))
	send_lists(land_naver('BLD1-30'))
	send_lists(land_naver('BLD1-31'))
	send_lists(land_naver('BLD1-32'))
	send_lists(land_naver('BLD1-33'))
	send_lists(land_naver('BLD1-34'))
	send_lists(land_naver('BLD1-36'))

	send_lists(land_naver('BLD2-01'))
	send_lists(land_naver('BLD2-02'))	#1차
	send_lists(land_naver('BLD2-03'))	#1차
	send_lists(land_naver('BLD2-04'))	#1차
	send_lists(land_naver('BLD2-06'))
	send_lists(land_naver('BLD2-07'))
	send_lists(land_naver('BLD2-08'))
	send_lists(land_naver('BLD2-09'))	#1차
	send_lists(land_naver('BLD2-11'))	#1차
	send_lists(land_naver('BLD2-12'))	#1차 원장내용없는 사태 발생, 에러처리완료
	send_lists(land_naver('BLD2-13'))	#1차
	send_lists(land_naver('BLD2-14'))	#1차
	send_lists(land_naver('BLD2-15'))
	send_lists(land_naver('BLD2-16'))	#1차 하임빌
	send_lists(land_naver('BLD2-17'))
	send_lists(land_naver('BLD2-18'))	#1차 로데오탑
	send_lists(land_naver('BLD2-19'))	#1차
	send_lists(land_naver('BLD2-20'))	#1차
	send_lists(land_naver('BLD2-21'))	#1차
	send_lists(land_naver('BLD2-22'))	#1차
	send_lists(land_naver('BLD2-24'))
	send_lists(land_naver('BLD2-27'))
	send_lists(land_naver('BLD2-28'))
	send_lists(land_naver('BLD2-29'))

# printL(f"global_msg_contents({len(global_msg_contents)}) : {global_msg_contents}")

#--- 모아뒀던 메세지 발송 -----
flag = True
if flag:
	# if global_var == 0:	# 전체적으로 보낼 메세지가 1건도 없을때
	if len(global_msg_contents) == 0:	# 보낼 메세지 list 변수안에 1건도 없을때
		if global_var == 0:		# 초기화 작업만 했을때는 메세지는 없지만 global_var는 0 이 아님
			msg_content = " - 새로운 매물이 없음"
			printL(msg_content)
			asyncio.run(tele_push(msg_content)) #텔레그램 발송 (asyncio를 이용해야 함)
	else:	# 보낼 메세지가 있을때
		printL(f"global_msg_contents ({len(global_msg_contents)})개")
		for msg in global_msg_contents:
			asyncio.run(tele_push(msg)) #텔레그램 발송 (asyncio를 이용해야 함)

#--- End Time 기록 -----
flag = True
if flag:
	current_time = datetime.datetime.now()
	formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
	end_time = current_time.strptime(formatted_time, "%Y-%m-%d %H:%M:%S")
	printL(f"-- END : {end_time}")
	printL(f"-- Elapsed time : {end_time - start_time}")
