import socket
import time, datetime
import os
import inspect
import telegram
import json

def mode_check():
	hostname = socket.gethostname()
	if hostname == 'jungui-MacBookAir.local':
		MODE = "TEST"
	else:
		MODE = "ONLINE"
	return(MODE)

def printL(message):	# 로그파일 기록 함수 (맥북에서는 화면에도 출력)
	log_directory = "logs"
	current_date = datetime.datetime.now().strftime("%Y%m%d")
	log_path = os.path.join(log_directory, f"log.{current_date}")
	current_time = datetime.datetime.now()
	formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

	def get_parent_program_name():	# 해당 함수를 호출한 부모 프로그램명 알아내는 함수
		stack = inspect.stack()
		for frame_info in stack:
			frame = frame_info.frame
			if frame.f_globals['__name__'] == '__main__':
				parent_program_path = frame_info.filename
				parent_program_name = os.path.basename(parent_program_path)
				return parent_program_name
		return None
	parent_program_name = get_parent_program_name()

	if mode_check() == 'TEST':
		print(message)
	with open(log_path, "a") as log_file:
		log_file.write(f"{formatted_time} [{parent_program_name}] {message}\n")

# 관리자용 telegram 메세지 발송함수
async def tele_push_admin(content): #텔레그램 발송용 함수
	# config.json 파일처리 ----------------
	with open('config.json','r') as f:
		config = json.load(f)
	token = config['TELEGRAM-ADMIN']['TOKEN']
	chat_ids = config['TELEGRAM-ADMIN']['CHAT-ID']
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
				printL(f"-- SEND(admin) success!!! : {chat_id}")
				break
			except Exception as e:
				send_retry = send_retry + 1
				printL(f"-- tele_push(admin) failed!!! ({send_retry}) : chat_id = {chat_id} error={e}")
				time.sleep(3)
				if send_retry == 3:
					printL(f"-- tele_push(admin) aborted!!! : chat_id = {chat_id}")
					printL(f"-- content(admin) : {chat_id} {token}\n {content}")
					break
			else:	# 정상작동시
				pass
			finally:	# 마지막에 (정상,에러 상관없이)
				pass