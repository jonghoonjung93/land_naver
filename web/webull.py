from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from datetime import timedelta, datetime
import time
import socket
import os
import pytz
import re

def mode_check():
	hostname = socket.gethostname()
	if hostname == 'jungui-MacBookAir.local':
		MODE = "TEST"
	else:
		MODE = "ONLINE"
	return(MODE)

def printL(message):	# 로그파일 기록 함수 (맥북에서는 화면에도 출력)
	log_directory = "../logs"
	current_date = datetime.now().strftime("%Y%m%d")
	log_path = os.path.join(log_directory, f"log.{current_date}")
	current_time = datetime.now()
	formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

	if mode_check() == 'TEST':
		print(message)
	with open(log_path, "a") as log_file:
		log_file.write(f"{formatted_time} {message}\n")
		
def convert_to_kst(edt_time_str):
	try:
		# EDT 시간 파싱
		edt_time = datetime.strptime(edt_time_str, "%H:%M %m/%d EDT")
		edt_time = edt_time.replace(year=datetime.now().year)
		
		# EDT 시간대 설정
		edt_tz = pytz.timezone('US/Eastern')
		edt_time = edt_tz.localize(edt_time)
		
		# KST로 변환
		kst_tz = pytz.timezone('Asia/Seoul')
		kst_time = edt_time.astimezone(kst_tz)
		
		return kst_time.strftime("%H:%M %m/%d KST")
	except Exception as e:
		printL(f"시간 변환 에러: {str(e)}")
		return edt_time_str

def parse_stock_info(result):
	try:
		# 정규표현식으로 데이터 분리
		pattern = r'(.+?):\s*([\d.]+)\s*([+-][\d.]+)\s*([+-][\d.%]+)\s*(.+)'
		match = re.match(pattern, result)
		
		if match:
			market = match.group(1).strip()
			price = match.group(2).strip()
			mod = match.group(3).strip()
			pct = match.group(4).strip()
			time = match.group(5).strip()
			
			# 시간대 변환
			if "EDT" in time:
				time = convert_to_kst(time)
			
			return {
				"market": market,
				"price": price,
				"mod": mod,
				"pct": pct,
				"time": time
			}
		else:
			printL(f"데이터 파싱함수 실패: {result}")
			return None
	except Exception as e:
		printL(f"데이터 파싱 에러: {str(e)}")
		return None

def stock_check():
	printL("-- stock check start")
	options = Options()

	options.add_argument("headless") #크롬창이 뜨지 않고 백그라운드로 동작됨
				
	# 아래 옵션 두줄 추가(NAS docker 에서 실행시 필요, memory 부족해서)
	options.add_argument('--no-sandbox')
	options.add_argument('--disable-dev-shm-usage')
	
	try:
		driver = webdriver.Chrome(options=options)
		url1 = "https://www.webull.com/quote/nasdaq-tsla"
		
		# webull TSLA 주가 조회
		driver.get(url1)
		action = ActionChains(driver)
		time.sleep(3)
		result1 = driver.find_element(By.CLASS_NAME, "csr134").text
		
		# 데이터 파싱
		if "Open" in result1:	# 장이 Open 했을때 (Opening 이라는 문자열이 들어있음)
			result2 = driver.find_element(By.CLASS_NAME, "csr113").text
			result2 = result2.replace("\n", " ")
			result3 = result1.replace("Opening", f"Open: {result2}")
			stock_info = parse_stock_info(result3)
			if stock_info:
				printL(f"TSLA 주가 정보: {stock_info}")
				return stock_info
			return None
		else:	# Pre-market(검증O), After-hours(검증X), Over-night(검증X) 일때
			stock_info = parse_stock_info(result1)
			if stock_info:
				printL(f"TSLA 주가 정보: {stock_info}")
				return stock_info
			else:
				printL("데이터 파싱 실패")
				return None
		
	except Exception as e:
		printL(f"에러 발생: {str(e)}")
		raise e
		
	finally:
		if 'driver' in locals():
			driver.quit()

if __name__ == "__main__":
	stock_check()