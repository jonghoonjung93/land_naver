from selenium import webdriver
import time

# 1.크롬접속
driver = webdriver.Chrome('C:\\경로\\chromedriver.exe')
driver.implicitly_wait(20)

# 2. 홈택스 접속

#  1) 홈택스로 이동
driver.get('https://www.hometax.go.kr/')
driver.implicitly_wait(10)

#  2) 로그인화면으로 이동
driver.find_element_by_id('textbox81212912').click() 
time.sleep(3)

#  3) iframe 전환 : 로그인화면은 화면전체가 iframe
iframe = driver.find_element_by_css_selector('#txppIframe')
driver.switch_to.frame(iframe)

#  4) 공인인증서 로그인 버튼 클릭
driver.find_element_by_css_selector('#trigger38').click() 
time.sleep(3)

#  5) iframe 전환 : 공인인증서 로그인 화면
iframe = driver.find_element_by_css_selector('#dscert')
driver.switch_to.frame(iframe)

#  6) 공인인증서 선택
driver.find_element_by_xpath('//*[@title="공인인증서명"]').click()
driver.implicitly_wait(3)

#  7) 패스워드 입력
passwd = '비밀번호'
driver.find_element_by_id('input_cert_pw').send_keys(passwd)
driver.implicitly_wait(3)

#  8) 확인버튼 클릭
driver.find_element_by_id('btn_confirm_iframe').click()
time.sleep(3)
