from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import Select
import telegram
import asyncio, json
import time, datetime

#-------------- 경기도 부동산포털에 접속해서 selenium을 활용해 건물내 각 호실별 정보조회 및 csv 파일 저장 프로그램 --------------#

def gris_gg(building):
	options = Options()
	# options.add_argument("headless") #크롬창이 뜨지 않고 백그라운드로 동작됨
	# 아래 옵션 두줄 추가(NAS docker 에서 실행시 필요, memory 부족해서)
	# options.add_argument('--no-sandbox')
	# options.add_argument('--disable-dev-shm-usage')

	# headless로 동작할때 element를 못찾으면 아래 두줄 추가 (창크기가 작아서 못찾을수 있음)
	# options.add_argument("start-maximized")
	# options.add_argument("window-size=1920,1080")
	# options.add_argument("window-size=1920,2160")	# 창크기가 작아서 전체 내용이 표시되지 않아서 크게 키움
	options.add_argument("window-size=1920,3000")	# 창크기가 작아서 전체 내용이 표시되지 않아서 크게 키움
	# options.add_argument("disable-gpu")
	# options.add_argument("lang=ko_KR")

	# 아래는 headless 크롤링을 막아놓은곳에 필요 (user agent에 HeadlessChrome 이 표시되는걸 방지)
	# options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
	
    # config.json 파일처리 ----------------
	with open('config.json','r') as f:
		config = json.load(f)
	url = config['GRIS_GG']['URL']
	address = config[building]['ADDRESS']
	memo = config[building]['MEMO']
	# ------------------------------------

	driver = webdriver.Chrome(options=options)

	# 페이지 접속
	driver.get(url)
	time.sleep(1)

	driver.find_element(By.CLASS_NAME, 'popup-close').click()	# 팝업창 닫기
	time.sleep(1)
	# keyword = "통합검색"
	# driver.find_element(By.XPATH, "//*[contains(text(),'" + keyword + "')]").click()	# 통합검색 클릭
	driver.find_element(By.XPATH, '//*[@id="container"]/div[3]/div/div[1]/div[1]/div[1]/div/a[1]').click()	# 통합검색 클릭
	driver.find_element(By.ID, 'searchText').send_keys(address)	# 주소입력
	driver.find_element(By.CLASS_NAME, 'submit').click()	# 검색버튼 클릭
	time.sleep(10)
	
	try:
		driver.find_element(By.XPATH, '//*[@id="ostpTab3"]/a').click()	# 건축물정보 버튼 클릭
	except:
	# 페이지 접속부터 재시도
		print("retry......")
		driver.get(url)
		time.sleep(1)
		driver.find_element(By.CLASS_NAME, 'popup-close').click()	# 팝업창 닫기
		time.sleep(1)
		driver.find_element(By.XPATH, '//*[@id="container"]/div[3]/div/div[1]/div[1]/div[1]/div/a[1]').click()	# 통합검색 클릭
		driver.find_element(By.ID, 'searchText').send_keys(address)	# 주소입력
		driver.find_element(By.CLASS_NAME, 'submit').click()	# 검색버튼 클릭
		time.sleep(10)
		driver.find_element(By.XPATH, '//*[@id="ostpTab3"]/a').click()	# 건축물정보 버튼 클릭
	
	time.sleep(5)

	select = Select(driver.find_element(By.ID, 'selHoNm'))
	options = driver.find_element(By.ID, 'selHoNm').find_elements(By.TAG_NAME, 'option')
	print(building + "Total : " + str(len(options)))
	# select.select_by_index(1) #select index value
	# select.select_by_visible_text("115") # select visible text
	# select.select_by_value("000201") # Select option value
	print("호수,총면적,전용면적,세부용도")
	
	address_short = address.replace("고양시 일산동구 ","")
	file_name = f"{building[3:]}_{memo}({address_short})"
	file = open(f"csv/{file_name}.csv", "w", encoding="utf-8-sig")
	file.write("호수,총면적,전용면적,세부용도\n")

	count = 0
	for option in options:
		output = option.text
		count = count + 1
		try:
			select.select_by_visible_text(option.text)
			time.sleep(1)
			buldExuseArea = driver.find_element(By.ID, 'buldExuseArea').text
			buldExposTotalArea = driver.find_element(By.ID, 'buldExposTotalArea').text
			buldHoInfoTb_list = driver.find_element(By.ID, 'buldHoInfoTb').find_elements(By.TAG_NAME, 'td')
			buldHoInfoTb = buldHoInfoTb_list[5].text.replace(",",".")
			# output = f"{output}, 전용면적 : {buldExuseArea}, 총면적 : {buldExposTotalArea}, 세부용도 : {buldHoInfoTb}"
			output = f"{output},{buldExposTotalArea},{buldExuseArea},{buldHoInfoTb}\n"
		except:
			output = f"데이터 없음\n"
		print(f"{str(count)}/{str(len(options))} {output}")
		file.write(output)

	file.close()

	# time.sleep(1000)

	result = 'aa'

	driver.quit()
	print(f"{building} : {str(len(options))} END")
	return(result)


# telegram 메세지 발송함수
async def tele_push(content): #텔레그램 발송용 함수
	# config.json 파일처리 ----------------
	with open('config.json','r') as f:
		config = json.load(f)
	token = config['TELEGRAM']['TOKEN']
	chat_id = config['TELEGRAM']['CHAT-ID']
	# ------------------------------------
	current_time = datetime.datetime.now()
	formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
	bot = telegram.Bot(token = token)
	# await bot.send_message(chat_id, formatted_time + "\n" + content)
	await bot.send_message(chat_id, formatted_time + "\n" + content, parse_mode = 'Markdown', disable_web_page_preview=True)

msg_content = "AAA"

# aa = gris_gg('BLD1-01')
# aa = gris_gg('BLD1-02')
# aa = gris_gg('BLD1-03')
# aa = gris_gg('BLD1-04')
# aa = gris_gg('BLD1-05')
# aa = gris_gg('BLD1-06')
# aa = gris_gg('BLD1-07')
# aa = gris_gg('BLD1-08')
# aa = gris_gg('BLD1-09')
# aa = gris_gg('BLD1-10')
# aa = gris_gg('BLD1-11')
# aa = gris_gg('BLD1-12')
# aa = gris_gg('BLD1-13')
# aa = gris_gg('BLD1-14')
# aa = gris_gg('BLD1-15') #데이터 없음.
# aa = gris_gg('BLD1-16')
# aa = gris_gg('BLD1-17')
# aa = gris_gg('BLD1-18') #데이터 없음. 1인건물?
# aa = gris_gg('BLD1-19')
# aa = gris_gg('BLD1-20') #데이터 없음. 1인건물?
# aa = gris_gg('BLD1-21')
# aa = gris_gg('BLD1-22') #데이터 없음. 1인건물?
# aa = gris_gg('BLD1-23')
# aa = gris_gg('BLD1-24')
# aa = gris_gg('BLD1-25')
# aa = gris_gg('BLD1-26')
# aa = gris_gg('BLD1-27')
# aa = gris_gg('BLD1-28')
# aa = gris_gg('BLD1-29')
# aa = gris_gg('BLD1-30')
# aa = gris_gg('BLD1-31')
# aa = gris_gg('BLD1-32')
# aa = gris_gg('BLD1-33')
# aa = gris_gg('BLD1-34')
# aa = gris_gg('BLD1-35')
# aa = gris_gg('BLD1-36')
# aa = gris_gg('BLD2-01')
# aa = gris_gg('BLD2-02')
# aa = gris_gg('BLD2-03')
# aa = gris_gg('BLD2-04')
# aa = gris_gg('BLD2-05')
# aa = gris_gg('BLD2-06') #데이터 없음. 1인건물?
# aa = gris_gg('BLD2-07')
# aa = gris_gg('BLD2-08')
# aa = gris_gg('BLD2-09')
# aa = gris_gg('BLD2-10') #데이터 없음. 1인건물?
# aa = gris_gg('BLD2-11')
# aa = gris_gg('BLD2-12') #데이터 없음. 1인건물?
# aa = gris_gg('BLD2-13')
# aa = gris_gg('BLD2-14')
# aa = gris_gg('BLD2-16')
# aa = gris_gg('BLD2-17')
# aa = gris_gg('BLD2-18')
# aa = gris_gg('BLD2-19')
# aa = gris_gg('BLD2-20')
# aa = gris_gg('BLD2-21')
# aa = gris_gg('BLD2-22')
# aa = gris_gg('BLD2-23')
# aa = gris_gg('BLD2-24')
# aa = gris_gg('BLD2-25')
# aa = gris_gg('BLD2-26')
# aa = gris_gg('BLD2-27')
# aa = gris_gg('BLD2-28')
# aa = gris_gg('BLD2-29')
# aa = gris_gg('BLD2-30')
# aa = gris_gg('BLD2-31')
# aa = gris_gg('BLD2-32')
# aa = gris_gg('BLD2-33')
# aa = gris_gg('BLD2-34')
# aa = gris_gg('BLD2-35')
# aa = gris_gg('BLD2-36')
# aa = gris_gg('BLD2-37')
# aa = gris_gg('BLD3-01')
# aa = gris_gg('BLD3-02')
# aa = gris_gg('BLD3-03')
# aa = gris_gg('BLD3-04')
# aa = gris_gg('BLD3-05')
# aa = gris_gg('BLD3-06')
# aa = gris_gg('BLD3-07')
# aa = gris_gg('BLD3-08')
# aa = gris_gg('BLD3-09')
# aa = gris_gg('BLD3-10')
# aa = gris_gg('BLD3-11')
# aa = gris_gg('BLD3-12')
# aa = gris_gg('BLD3-13')
# aa = gris_gg('BLD3-14')
# aa = gris_gg('BLD3-15')
# aa = gris_gg('BLD3-16')
# aa = gris_gg('BLD3-17')
# aa = gris_gg('BLD3-18')
# aa = gris_gg('BLD3-19')
# aa = gris_gg('BLD3-20')
# aa = gris_gg('BLD3-21')
# aa = gris_gg('BLD3-22')
# aa = gris_gg('BLD3-23')
# aa = gris_gg('BLD3-24')
# aa = gris_gg('BLD3-25')
# aa = gris_gg('BLD3-26')
# aa = gris_gg('BLD3-27')
# aa = gris_gg('BLD3-28')
# aa = gris_gg('BLD3-29')
# aa = gris_gg('BLD3-30')
# aa = gris_gg('BLD3-31')
# aa = gris_gg('BLD3-32')
# aa = gris_gg('BLD3-33')

print("END")
