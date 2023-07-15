import socket
import time, datetime
import os
import inspect

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