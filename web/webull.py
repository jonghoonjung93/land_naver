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

		# EDT 20시(KST 09시)부터는 Overnight 이라 별도 처리 필요함
		# KST 09:00 ~ 17:00 체크
		kst_tz = pytz.timezone('Asia/Seoul')
		kst_now = datetime.now(kst_tz)
		kst_start = kst_now.replace(hour=9, minute=0, second=0, microsecond=0)
		kst_end = kst_now.replace(hour=17, minute=0, second=0, microsecond=0)
		
		# 평일 오전 09:00 ~ 17:00 체크 (Overnight 장일때)
		if kst_start <= kst_now <= kst_end and kst_now.weekday() <= 4:
			url1 = "https://app.webull.com/stocks"
			driver.get(url1)
			action = ActionChains(driver)
			time.sleep(3)

			# TSLA 검색
			# Symbol/Name 플레이스홀더가 있는 입력창 찾기
			search_box = driver.find_element(By.XPATH, "//input[@placeholder='Symbol/Name']")
			search_box.send_keys("TSLA")
			time.sleep(2)
			# Tesla 검색결과 클릭
			tesla_result = driver.find_element(By.XPATH, "//span[text()='Tesla Inc']")
			tesla_result.click()
			time.sleep(3)

			# BeautifulSoup으로 파싱 (docker Linux 에서 파싱이 안되는 부분을 해결하기 위함)
			html = driver.find_element("id", "DomWrap").get_attribute("outerHTML")
			soup = BeautifulSoup(html, "html.parser")
			# 모든 <p> 태그 내용 가져오기
			p_tags = soup.find_all("p")
			result1 = "Overnight: "
			# printL(p_tags)
			if not p_tags:	# p_tags 가 null 이면 (즉, 휴일이라 Overnight 주가가 없을때)
				# printL("p_tags is null")
				small_v = soup.select_one('#DomWrap > div:nth-child(2) > div:nth-child(3)')# After 어쩌구 부분의 주가를 가져옴(xpath)
				text_parts = []
				for div in small_v.find_all('div'):
					div_text = div.text.strip()
					if div_text:  # 빈 텍스트가 아닌 경우만 추가
						text_parts.append(div_text)
				# printL(text_parts)
				result1 = f"{text_parts[0]}_H {text_parts[2]} {text_parts[3]} {text_parts[4]}"	# _H는 Holiday를 의미함
			else:	# p_tags 에 뭐가 있을때 (즉, 일반적인 평일 낮)
				# p 태그 내의 span 태그들을 찾기
				for p_tag in p_tags:
					span_tags = p_tag.find_all("span")
				for span in span_tags:
					# printL(span.text)
					result1 = result1 + span.text + " "
			# print("result1: " + result1)
			
			# 현재 날짜/시간 출력
			kst_now = datetime.now(kst_tz)
			formatted_time = kst_now.strftime("%H:%M %m/%d KST")
			result1 = result1 + " " + formatted_time
			# print(result1)
		else:
			url1 = "https://www.webull.com/quote/nasdaq-tsla"

			# webull TSLA 주가 조회
			driver.get(url1)
			action = ActionChains(driver)
			time.sleep(3)
			# result1 = driver.find_element(By.CLASS_NAME, "csr134").text	# csr134 -> csr133 이런식으로 class 이름이 자꾸 바뀜
			result1 = driver.find_element(By.XPATH, '//*[@id="app"]/section/div[1]/div/div[2]/div[1]/div[2]/div[2]/div[2]/div').text
			# printL(result1)
			
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
		else:	# Pre Market(검증O), After Hours(검증O), Overnight(검증O) 일때
			result1 = result1.replace(" Hours", "")
			result1 = result1.replace(" Market", "")
			result1 = result1.replace("Overnight", "OverN")
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