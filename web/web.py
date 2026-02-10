import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, jsonify, make_response
import logging
import datetime, time
# from datetime import datetime
# from module.etc_util import printL, mode_check, tele_push_admin
from config import *    # 허용하는 도메인 리스트 (config.py)
import telegram
import asyncio, json, os
# import json
from flask_cors import CORS

flag=True
if flag:
    app = Flask(__name__)
    app.secret_key = 'my_secret_key'
    # CORS(app)  # 모든 엔드포인트에서 CORS 활성화
    # cors = CORS(app, resources={r"/save_ip": {"origins": "http://land.iptime.org"}})
    # cors = CORS(app, resources={r"/save_ip": {"origins": "http://127.0.0.1:5200"}})
    cors = CORS(app, resources={r"/save_ip": {"origins": "*"}})

    # ALLOWED_DOMAINS = ["xxx.xxx.xxx", "127.0.0.1"]    # 실제 데이터는 config.py 에서 별도로 처리

    DATABASE = '../land_naver.sqlite3'

    # logging.basicConfig(filename='web.log', level=logging.DEBUG, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    # logging.basicConfig(filename='web.log', level=logging.DEBUG, format='%(asctime)s %(filename)s %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    logging.basicConfig(filename='../logs/web.log', level=logging.DEBUG, format='%(asctime)s [%(levelname)s] \t- %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

def query_database(query):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

def query_database_update(query):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    cursor.close()
    conn.close()

# telegram 메세지 발송함수
async def tele_push(userid, authcode): #텔레그램 발송용 함수
    # AUTH_TOKEN = config.py 처리
    # ------------------------------------
    logging.debug(f'telegram send : {userid}, {authcode}')
    query = f'SELECT chat_id from account WHERE userid = "{userid}"'
    chat_id = query_database(query)[0][0]
    logging.debug(f'userid : {userid}, chat_id :{chat_id}')
    content = f"인증코드 : [[{authcode}]]"
    # current_time = datetime.datetime.now()
    # formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    bot = telegram.Bot(token = AUTH_TOKEN)
    await bot.send_message(chat_id, content, parse_mode = 'Markdown', disable_web_page_preview=True)

def access_log(userid, public_ip, url):
    log_directory = "../logs"
    current_date = datetime.datetime.now().strftime("%Y%m%d")
    log_path = os.path.join(log_directory, f"access.log.{current_date}")
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

    with open(log_path, "a") as log_file:
        log_file.write(f"{formatted_time} [{userid}]\t{public_ip}\t{url}\n")

@app.route('/')
def index():
    return render_template('login4.html')

@app.route('/login', methods=['POST'])
def login():
    userid = request.form['userid']
    password = request.form['password']
    authcode_input = request.form['authentication_code']
    logging.debug(f'userid : {userid}, authcode = {authcode_input}')
    
    conn = sqlite3.connect(DATABASE)  # Connect to your SQLite database
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM account WHERE userid = ? AND password = ? AND available = '1'", (userid, password))
    user = cursor.fetchone()

    if user:    # 로그인 성공
        # 날짜 (오늘)
        current_time = datetime.datetime.now()
        last_login = current_time.strftime("%Y-%m-%d %H:%M:%S")

        # 인증번호 정상여부 확인 (입력받은 값과 DB 값 비교.)
        query = f'SELECT auth_code, auth_date from account WHERE userid = "{userid}"'
        authcode_db = query_database(query)[0][0]
        auth_date = query_database(query)[0][1]
        logging.debug(f'userid : {userid}, [DB]auth_code = {authcode_db}')
        logging.debug(f'userid : {userid}, [DB]auth_date = {auth_date}')

        if authcode_input == authcode_db or authcode_input == SUPER_CODE:   # 인증번호가 일치하거나 슈퍼코드일때
            # 인증후 로그인까지 시간차 구하기
            datetime_A = datetime.datetime.strptime(auth_date, '%Y-%m-%d %H:%M:%S')
            datetime_B = datetime.datetime.strptime(last_login, '%Y-%m-%d %H:%M:%S')
            time_difference = datetime_B - datetime_A
            seconds_difference = time_difference.total_seconds()    # 시간차이를 초로 변환
            logging.debug(f'userid : {userid}, 인증후 로그인까지 걸린시간(초) : {seconds_difference}')
            
            if seconds_difference < 180:     # 인증시간이 초과되지 않았을때 (3분)
                ok_auth = True
                # DB 에 결과 update
                query = f'UPDATE account SET auth_code = "PASS" WHERE userid = "{userid}"'
                query_database_update(query)
            else:
                ok_auth = False
                logging.debug(f"userid : {userid}, 인증시간이 초과되었습니다. {seconds_difference}초")
                flash(f'Authentication timeout({seconds_difference}s). [MAX:3min] Please try again.', 'error')
                logging.error(f"Authentication timeout({seconds_difference}s). Please try again.")
                cursor.close()
                conn.close()
                return redirect(url_for('index'))
        else:   # 인증번호가 틀렸을때
            ok_auth = False
            # DB 에 결과 update
            query = f'UPDATE account SET auth_code = "FAIL" WHERE userid = "{userid}"'
            query_database_update(query)

        if ok_auth:     # 인증번호 확인 결과 정상일때
            session['userid'] = user[0]  # Store user ID in session
            # session['auth_code'] = 'True' # 굳이 불필요한듯.
            # ------ last_login, login_count UPDATE 처리 -------- #
            if user[11] is None or user[11] == "":  # 기존 login_count 컬럼 확인
                before_login_count = 0
            else:
                before_login_count = int(user[11])
            login_count = before_login_count + 1
            logging.debug(f"Login Success. last({last_login}), cnt:{login_count}, userid:{session['userid']}")
            # 텔레그램에 메세지 전송
            asyncio.run(tele_push('tiptop', f'Login : {userid}')) #텔레그램 발송 (asyncio를 이용해야 함)
            cursor.execute("UPDATE account SET last_login = ?, login_count = ? WHERE userid = ?", (last_login, login_count, session['userid']))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('display_land_items'))
        else:       # 인증번호 확인 결과 실패일때
            flash(f'Invalid authentication code({authcode_input}). Please try again.', 'error')
            logging.error(f"Invalid authentication code. Please try again.({userid}/{password})")
            cursor.close()
            conn.close()
            return redirect(url_for('index'))
    else:   # 로그인 실패
        flash('Invalid user ID or password. Please try again.', 'error')
        logging.error(f"Invalid user ID or password. Please try again.({userid}/{password})")
        cursor.close()
        conn.close()
        return redirect(url_for('index'))

@app.route('/request_code', methods=['POST'])
def request_code():     # 인증코드 요청하는 부분 (텔레그램)
    userid = request.form['userid']
    password = request.form['password']
    logging.debug(f'입력된값 : {userid}, {password}')
    # 날짜 (오늘)
    current_time = datetime.datetime.now()
    auth_date = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    query = f'SELECT count(*) FROM account WHERE userid = "{userid}" AND password = "{password}" AND available = "1"'
    idpwd_check = query_database(query)[0][0]
    # logging.debug(idpwd_check)
    if idpwd_check == 1:    # ID,PW 가 맞고 해당 유저가 유효할 경우
        import random
        authentication_code = str(random.randint(1000, 9999))
        # 텔레그램에 메세지 전송
        asyncio.run(tele_push(userid, authentication_code)) #텔레그램 발송 (asyncio를 이용해야 함)

        # DB 에 update 처리
        query = f'UPDATE account SET auth_code = {authentication_code}, auth_date = "{auth_date}" WHERE userid = "{userid}"'
        query_database_update(query)
    else:
        query = f'UPDATE account SET auth_code = "BLOCK", auth_date = "{auth_date}" WHERE userid = "{userid}"'
        query_database_update(query)
    
    access_log(userid, public_ip="-------------", url=f"/request_code ({authentication_code})")  # 로깅

    return authentication_code

@app.route('/logout')
def logout():
    userid = session['userid']
    access_log(userid, public_ip="-------------", url="/logout") # 로깅
    session.pop('userid')
    return redirect(url_for('index'))

@app.route('/all')
def display_land_items():   # 전체 매물리스트
    # Logging the access request
    # app.logger.info(f'Access: {request.method} {request.url}')

    # 날짜 (오늘)
    current_time = datetime.datetime.now()
    formatted_date = current_time.strftime("%Y%m%d")
    today = current_time.strftime("%Y.%m.%d")
    # today_week = current_time.strftime("%A")    # 요일
    # today_week = current_time.weekday()
    today_week = '월화수목금토일'[current_time.weekday()]

    tmp_date1 = current_time - datetime.timedelta(days=1)
    one_day_ago = tmp_date1.strftime("%Y.%m.%d")
    # one_day_week = tmp_date1.strftime("%A")
    one_day_week = '월화수목금토일'[tmp_date1.weekday()]
    tmp_date2 = current_time - datetime.timedelta(days=2)
    two_day_ago = tmp_date2.strftime("%Y.%m.%d")
    # two_day_week = tmp_date2.strftime("%A")
    two_day_week = '월화수목금토일'[tmp_date2.weekday()]
    tmp_date3 = current_time - datetime.timedelta(days=3)
    three_day_ago = tmp_date3.strftime("%Y.%m.%d")
    # three_day_week = tmp_date3.strftime("%A")
    three_day_week = '월화수목금토일'[tmp_date3.weekday()]

    # logging.debug(f"day_ago : {one_day_ago} {two_day_ago} {three_day_ago}")
    arg_date = request.args.get('date', formatted_date) # argument 날짜 받아오고 없으면 당일자로 
    # logging.debug(f"arg_date : {arg_date}")

    if arg_date == formatted_date:  # 당일일 경우
        formatted_date = current_time.strftime("%Y%m%d")
    elif arg_date == one_day_ago:   # 전일
        formatted_date = one_day_ago.replace(".","")
    elif arg_date == two_day_ago:   # 2일전
        formatted_date = two_day_ago.replace(".","")
    elif arg_date == three_day_ago: # 3일전
        formatted_date = three_day_ago.replace(".","")

    # logging.debug(f"formatted_date : {formatted_date}")
    # logging.debug(f"today : {today}")
    
    # Get the value of the checkbox (True if checked, False if not)
    rm_dup = request.args.get('rm_dup', False)
    ho = "ho"
    def query_f(ho):
        # result_sql = f'SELECT ROW_NUMBER() OVER (ORDER BY bld_id) AS row_no, replace(bld_id,"BLD",""), memo, naver_bld_id, name, type, price, info_area_type, info_area_spec, ROUND(size_real*0.3025, 2), floor, agent_name, {ho} FROM land_item where date = "{formatted_date}"'
        result_sql = f'SELECT date, replace(bld_id,"BLD",""), memo, naver_bld_id, name, type, price, info_area_type, info_area_spec, ROUND(size_real*0.3025, 2), floor, agent_name, {ho} FROM land_item where date = "{formatted_date}"'
        return result_sql
    query = query_f(ho)
    # Add GROUP BY clause if checkbox is checked
    if rm_dup == 'true':
        ho = "MAX(ho) AS ho"
        query = query_f(ho)
        query += ' GROUP BY bld_id, price, size_real'
    query += ';'
    items = query_database(query)

    userid = session['userid']
    # query = f'SELECT line FROM account WHERE userid = "{userid}"'
    # line = query_database(query)
    # logging.debug(f'line = {line[0][0]}')

    return render_template('land_item7.html', items=items, userid=userid, today=today, today_week=today_week, one_day_ago=one_day_ago, one_day_week=one_day_week, two_day_ago=two_day_ago, two_day_week=two_day_week, three_day_ago=three_day_ago, three_day_week=three_day_week)

@app.route('/new')
def display_land_items_new():   # 금일 신규 매물리스트
    # Logging the access request
    # app.logger.info(f'Access: {request.method} {request.url}')

    # 날짜 (오늘)
    current_time = datetime.datetime.now()
    formatted_date = current_time.strftime("%Y%m%d")
    today = current_time.strftime("%Y.%m.%d")
    # today_week = current_time.strftime("%A")    # 요일
    # today_week = current_time.weekday()
    today_week = '월화수목금토일'[current_time.weekday()]

    tmp_date1 = current_time - datetime.timedelta(days=1)
    one_day_ago = tmp_date1.strftime("%Y.%m.%d")
    # one_day_week = tmp_date1.strftime("%A")
    one_day_week = '월화수목금토일'[tmp_date1.weekday()]
    tmp_date2 = current_time - datetime.timedelta(days=2)
    two_day_ago = tmp_date2.strftime("%Y.%m.%d")
    # two_day_week = tmp_date2.strftime("%A")
    two_day_week = '월화수목금토일'[tmp_date2.weekday()]
    tmp_date3 = current_time - datetime.timedelta(days=3)
    three_day_ago = tmp_date3.strftime("%Y.%m.%d")
    # three_day_week = tmp_date3.strftime("%A")
    three_day_week = '월화수목금토일'[tmp_date3.weekday()]

    # logging.debug(f"day_ago : {one_day_ago} {two_day_ago} {three_day_ago}")
    arg_date = request.args.get('date', formatted_date) # argument 날짜 받아오고 없으면 당일자로 
    # logging.debug(f"arg_date : {arg_date}")

    if arg_date == formatted_date:  # 당일일 경우
        formatted_date = current_time.strftime("%Y%m%d")
    elif arg_date == one_day_ago:   # 전일
        formatted_date = one_day_ago.replace(".","")
    elif arg_date == two_day_ago:   # 2일전
        formatted_date = two_day_ago.replace(".","")
    elif arg_date == three_day_ago: # 3일전
        formatted_date = three_day_ago.replace(".","")

    # logging.debug(f"formatted_date : {formatted_date}")
    # logging.debug(f"today : {today}")

    # Get the value of the checkbox (True if checked, False if not)
    rm_dup = request.args.get('rm_dup', False)
    ho = "ho"
    def query_f(ho):
        # result_sql = f'SELECT ROW_NUMBER() OVER (ORDER BY bld_id) AS row_no, replace(bld_id,"BLD",""), memo, naver_bld_id, name, type, price, info_area_type, info_area_spec, ROUND(size_real*0.3025, 2), floor, agent_name, {ho} FROM land_item where date = "{formatted_date}" and new = "O"'
        result_sql = f'SELECT date, replace(bld_id,"BLD",""), memo, naver_bld_id, name, type, price, info_area_type, info_area_spec, ROUND(size_real*0.3025, 2), floor, agent_name, {ho} FROM land_item where date = "{formatted_date}" and new = "O"'
        return result_sql
    query = query_f(ho)
    # Add GROUP BY clause if checkbox is checked
    if rm_dup == 'true':
        ho = "MAX(ho) AS ho"
        query = query_f(ho)
        query += ' GROUP BY bld_id, price, size_real'
    query += ';'
    items = query_database(query)
    
    userid = session['userid']
    # query = f'SELECT line FROM account WHERE userid = "{userid}"'
    # line = query_database(query)
    # logging.debug(f'line = {line[0][0]}')
    
    # return render_template('land_item5.html', items=items, userid=userid, today=formatted_date2, line=line[0][0])
    return render_template('land_item7.html', items=items, userid=userid, today=today, today_week=today_week, one_day_ago=one_day_ago, one_day_week=one_day_week, two_day_ago=two_day_ago, two_day_week=two_day_week, three_day_ago=three_day_ago, three_day_week=three_day_week)

@app.route('/my')
def display_land_items_my():   # 금일 신규 매물리스트
    # Logging the access request
    # app.logger.info(f'Access: {request.method} {request.url}')

    # 날짜 (오늘)
    current_time = datetime.datetime.now()
    formatted_date = current_time.strftime("%Y%m%d")
    today = current_time.strftime("%Y.%m.%d")
    # today_week = current_time.strftime("%A")    # 요일
    # today_week = current_time.weekday()
    today_week = '월화수목금토일'[current_time.weekday()]

    tmp_date1 = current_time - datetime.timedelta(days=1)
    one_day_ago = tmp_date1.strftime("%Y.%m.%d")
    # one_day_week = tmp_date1.strftime("%A")
    one_day_week = '월화수목금토일'[tmp_date1.weekday()]
    tmp_date2 = current_time - datetime.timedelta(days=2)
    two_day_ago = tmp_date2.strftime("%Y.%m.%d")
    # two_day_week = tmp_date2.strftime("%A")
    two_day_week = '월화수목금토일'[tmp_date2.weekday()]
    tmp_date3 = current_time - datetime.timedelta(days=3)
    three_day_ago = tmp_date3.strftime("%Y.%m.%d")
    # three_day_week = tmp_date3.strftime("%A")
    three_day_week = '월화수목금토일'[tmp_date3.weekday()]

    # logging.debug(f"day_ago : {one_day_ago} {two_day_ago} {three_day_ago}")
    arg_date = request.args.get('date', formatted_date) # argument 날짜 받아오고 없으면 당일자로 
    # logging.debug(f"arg_date : {arg_date}")

    if arg_date == formatted_date:  # 당일일 경우
        formatted_date = current_time.strftime("%Y%m%d")
    elif arg_date == one_day_ago:   # 전일
        formatted_date = one_day_ago.replace(".","")
    elif arg_date == two_day_ago:   # 2일전
        formatted_date = two_day_ago.replace(".","")
    elif arg_date == three_day_ago: # 3일전
        formatted_date = three_day_ago.replace(".","")

    # logging.debug(f"formatted_date : {formatted_date}")
    # logging.debug(f"today : {today}")

    # Get the value of the checkbox (True if checked, False if not)
    rm_dup = request.args.get('rm_dup', False)
    ho = "ho"
    userid = session['userid']
    def query_f(ho):
        result_sql = f'SELECT date, replace(bld_id,"BLD",""), memo, naver_bld_id, name, type, price, info_area_type, info_area_spec, ROUND(size_real*0.3025, 2), floor, agent_name, {ho} FROM land_item where date = "{formatted_date}" and agent_name = ( SELECT company FROM account WHERE userid = "{userid}" )'
        return result_sql
    query = query_f(ho)
    # Add GROUP BY clause if checkbox is checked
    if rm_dup == 'true':
        ho = "MAX(ho) AS ho"
        query = query_f(ho)
        query += ' GROUP BY bld_id, price, size_real'
    query += ';'
    items = query_database(query)
    
    # return render_template('land_item5.html', items=items, userid=userid, today=formatted_date2, line=line[0][0])
    return render_template('land_item7.html', items=items, userid=userid, today=today, today_week=today_week, one_day_ago=one_day_ago, one_day_week=one_day_week, two_day_ago=two_day_ago, two_day_week=two_day_week, three_day_ago=three_day_ago, three_day_week=three_day_week)

def admin_check(userid):    # 관리자 여부 체크
    query = f'SELECT admin FROM account WHERE userid = "{userid}"'
    admin_col = query_database(query)
    # logging.debug(f'admin_col : {admin_col[0][0]}')
    if admin_col[0][0]:
        return(True)
    else:
        logging.error("권한없는 user 의 관리자 페이지 접근, 로그아웃 처리")
        session.pop('userid')
        return(False)

@app.route('/adm/message')
def display_message_list():     # 메세지 발송내역 리스트 (결과확인)
    if admin_check(session['userid']):
        query = f'SELECT date, send_yn, retry, result, m.chat_id, a.username, message FROM message_list m, account a WHERE m.chat_id = a.chat_id ORDER BY m.date desc, m.id;'
        items = query_database(query)
        userid = session['userid']
        return render_template('message_list1.html', items=items, userid=userid)
    else:
        return redirect(url_for('index'))

@app.route('/adm/account')
def display_account():      # 계정 리스트
    if admin_check(session['userid']):
        # query = f'SELECT userid, username, admin, available, reg_date, type, location, memo, expire_date, last_login, login_count, chat_id FROM account ORDER BY admin desc,login_count desc;'
        query = f'SELECT userid, username, admin, available, reg_date, memo, last_login, login_count, auth_code, auth_date, chat_id FROM account ORDER BY admin desc,login_count desc;'
        items = query_database(query)
        userid = session['userid']
        # return render_template('account1.html', items=items)
        return render_template('account3.html', items=items, userid=userid)
    else:
        return redirect(url_for('index'))

@app.route('/adm/ranking')
def display_ranking():      # 중개사무소별 랭킹
    if admin_check(session['userid']):
        # 날짜 (오늘)
        current_time = datetime.datetime.now()
        formatted_date = current_time.strftime("%Y%m%d")
        # query = f'SELECT count(*), agent_name FROM land_item WHERE date = "{formatted_date}" GROUP BY agent_name ORDER BY 1 desc;'
        query = f'SELECT agent_name, count, chg, link, owner, address, tel1 FROM agent WHERE date = "{formatted_date}" ORDER BY count desc;'
        items = query_database(query)
        userid = session['userid']
        # return render_template('account1.html', items=items)
        return render_template('ranking1.html', items=items, userid=userid)
    else:
        return redirect(url_for('index'))

@app.route('/adm/a.log')
def display_a_log():      # access log viewer
    if admin_check(session['userid']):
        log_directory = "../logs"
        current_date = datetime.datetime.now().strftime("%Y%m%d")
        log_file_path = os.path.join(log_directory, f"access.log.{current_date}")
        try:
            with open(log_file_path, 'r') as log_file:
                log_content = log_file.read()
        except FileNotFoundError:
            log_content = 'Log file not found'
        
        userid = session['userid']
        return render_template('log.html', log_content=log_content, userid=userid)

@app.route('/adm/b.log')
def display_b_log():      # access log viewer
    if admin_check(session['userid']):
        log_directory = "../logs"
        current_date = datetime.datetime.now().strftime("%Y%m%d")
        log_file_path = os.path.join(log_directory, f"log.{current_date}")
        try:
            with open(log_file_path, 'r') as log_file:
                log_content = log_file.read()
        except FileNotFoundError:
            log_content = 'Log file not found'

        userid = session['userid']
        return render_template('log.html', log_content=log_content, userid=userid)

@app.route('/adm')
def admin_home():     # 관리자 페이지 메인
    return redirect(url_for('display_account'))

@app.route('/update_column', methods=['POST'])
def update_column():    # 관리자(account) 페이지에서 특정유저 ON/OFF 버튼 동작
    item_id = request.form.get('item_id')  # Retrieve the item ID from the request
    old_value = request.form.get('old_value')  # Retrieve the new value from the request
    
    # Update the SQLite3 database using item_id and new_value
    # Add your code here to update the database
    if old_value == "0":
        new_value = "1"
    else:
        new_value = "0"
    logging.debug(f"item_id : {item_id}, old_value : {old_value}, new_value : {new_value}")
    query = f'UPDATE account SET available = {new_value} WHERE userid = "{item_id}"'
    query_database_update(query)
    
    # Create a dictionary with the updated value
    response_data = {
        'new_value': new_value
    }
    # return "Success"  # Return a response
    return jsonify(response_data)  # Return a JSON response with the updated value

@app.route('/myinfo', methods=['GET'])
def my_info():
    return render_template('myinfo1.html')

@app.route('/update_password', methods=['POST'])
def update_password():
    old_password = request.form.get('oldPassword')
    new_password = request.form.get('newPassword')
    confirm_password = request.form.get('confirmPassword')
    userid = session['userid']

    logging.debug(f"userid : {userid}")
    logging.debug(f"old_password : {old_password}")
    logging.debug(f"new_password : {new_password}")
    logging.debug(f"confirm_password : {confirm_password}")

    # Check if old_password matches the user's current password
    validation_passed = False
    query = f'SELECT count(*) FROM account WHERE userid = "{userid}" AND password = "{old_password}"'
    result = query_database(query)
    logging.debug(result[0][0])
    if result[0][0] == 1:   # old_password 입력한값이 DB값과 일치할 경우
        logging.debug("old_password validation pass")
        if new_password == confirm_password:    # 패스워드 두번 입력값이 동일한 경우
            logging.debug("password confirm validation pass")
            validation_passed = True
    logging.debug(validation_passed)
    
    # Update the password in the database if validation passes
    if validation_passed:   # password 변경
        query = f'UPDATE account SET password = "{new_password}" WHERE userid = "{userid}"'
        query_database_update(query)

        # Return a success response
        response_data = {
           'message': 'Password updated successfully',
           'result': True
        }
        # return jsonify(message='Password updated successfully')
        return jsonify(response_data)
    else:
        # Return an error response
        response_data = {
           'message': 'Password update failed due to validation errors',
           'result': False
        }
        # return jsonify(error='Password update failed due to validation errors')
        return jsonify(response_data)

@app.route('/save_ip', methods=['POST'])
def save_ip():
    # logging.debug("------------------save_ip-----------------")
    data = request.get_json()
    # logging.debug(data)
    public_ip = data.get('ip')
    url = data.get('url')
    try:
        userid = session['userid']
    except: # 로그인이 안된 상태에서의 로그 기록을 위해
        userid = "None"
    logging.debug(f'userid : {userid}, 공인IP : {public_ip}, url : {url}')

    access_log(userid, public_ip, url)  # 로깅
    
    return jsonify({'message': 'IP address received successfully'})

#----- dashboard (일일 balance 데이터 뷰어) 추가 ------#
import pandas as pd
bal_data = []
@app.route('/bal')
def bal_data():
    global bal_data
    conn = sqlite3.connect("../../attendance/stock.sqlite3")
    cursor = conn.cursor()
    
    try:
        # SQL 쿼리 실행
        query = "SELECT date, user, stock_cnt, total_krw FROM stock_history WHERE user = 'TOTAL';"
        cursor.execute(query)

        # 결과 가져오기
        data = cursor.fetchall()

        # 데이터프레임 생성
        bal_data = pd.DataFrame(data, columns=["date", "user", "stock_cnt", "total_krw"])

        # total_krw 값을 10000으로 나누기
        bal_data["total_krw"] = (bal_data["total_krw"] / 10000).astype(int)

        # print(bal_data)

        if not bal_data.empty:
            pass
        else:
            print("⚠️ No data!")
    except Exception as e:
        print(f"❌ Error in fetch_stock_data: {e}")
    
    return render_template('balance.html', bal_data=bal_data)
#-------- dashboard 끝 ---------------------------#


#-------------------- hash 관련 추가부분 --------------------------------------------------------------------------#
# import hashlib

# @app.route('/join', methods=['GET'])   #회원가입 화면 템플릿지정
# def join():
#     return render_template('join.html')

# @app.route('/loginH', methods=['GET'])   #로그인 화면 템플릿지정
# def loginH():
#     return render_template('loginH.html')

# def query_database(query):
#     conn = sqlite3.connect(DATABASE)
#     cursor = conn.cursor()
#     cursor.execute(query)
#     result = cursor.fetchall()
#     cursor.close()
#     conn.close()
#     return result

# def query_database_insert(query):
#     conn = sqlite3.connect(DATABASE)
#     cursor = conn.cursor()
#     cursor.execute(query)
#     conn.commit()
#     cursor.close()
#     conn.close()

# @app.route('/join_work', methods=['POST'])  #회원가입 hash 암호화 및 DB 저장
# def join_work():
#     input_userid = request.form.get('inputUserid')
#     input_password = request.form.get('inputPassword')
#     confirm_password = request.form.get('confirmPassword')

#     logging.debug(f"input_userid : {input_userid}")
#     logging.debug(f"input_password : {input_password}")
#     logging.debug(f"confirm_password : {confirm_password}")

#     if input_password == confirm_password:    # 패스워드 두번 입력값이 동일한 경우
#         logging.debug("password confirm validation pass")
#         validation_passed = True
#     else:
#         validation_passed = False

#     if validation_passed:   # password 입력값이 같으면 회원가입 처리, DB저장
#         # 입력된 암호 hash 암호화처리
#         hash_object = hashlib.sha256()
#         hash_object.update(input_password.encode())
#         hash_string = hash_object.hexdigest()

#         query = f'INSERT INTO account_hash VALUES ("{input_userid}", "{hash_string}")'
#         query_database_insert(query)

#         message_text = 'success'
#             # Return a success response
#         response_data = {
#             'message': message_text,
#             'result': True
#         }
#         return jsonify(response_data)   
#     else:
#         message_text = 'fail'
#         # Return an error response
#         response_data = {
#            'message': message_text,
#            'result': False
#         }
#         return jsonify(response_data)

# @app.route('/login_work', methods=['POST'])  #로그인 처리
# def login_work():
#     input_userid = request.form.get('inputUserid')
#     input_password = request.form.get('inputPassword')

#     logging.debug(f"input_userid : {input_userid}")
#     logging.debug(f"input_password : {input_password}")

#     #입력된 암호 hash 암호화
#     hash_object = hashlib.sha256()
#     hash_object.update(input_password.encode())
#     hash_string = hash_object.hexdigest()
#     logging.debug(f"hash_string : {hash_string}")

#     #DB에서 해당 userid 의 hash 데이터 가져오기
#     query = f'SELECT count(*) FROM account_hash WHERE userid = "{input_userid}" AND password_hash = "{hash_string}"'
#     result = query_database(query)
#     logging.debug(result[0][0])

#     if result[0][0] == 1:   # 입력값과 DB 내부에 hash 암호화된 내용이 일치할 경우
#         logging.debug("userid/passwd_hash validation pass")
#         message_text = 'success'
#             # Return a success response
#         response_data = {
#             'message': message_text,
#             'result': True
#         }
#         return jsonify(response_data)
#     else:
#         message_text = 'fail'
#         # Return an error response
#         response_data = {
#            'message': message_text,
#            'result': False
#         }
#         return jsonify(response_data)

@app.route('/hash', methods=['GET'])   #hash 암호화
def hash():
    return render_template('hash.html')

@app.route('/hash_password', methods=['POST'])
def hash_password():
    import hashlib
    input_password = request.form.get('inputPassword')

    hash_object = hashlib.sha256()
    hash_object.update(input_password.encode())
    hash_string = hash_object.hexdigest()

    logging.debug(f"hash_string : {hash_string}")

    # Return a success response
    response_data = {
        'message': hash_string,
        'result': True
    }
    # return jsonify(message='Password updated successfully')
    return jsonify(response_data)
#----------------------------------------------------------------------------------------------#

#-------- 주가 위젯 추가 부분 시작 ---------------------#
# from flask import Flask, jsonify, make_response
# from flask_cors import CORS
from webull import stock_check

# CORS(app)
@app.route('/tsla')
def get_tsla():
    try:
        stock_info = stock_check()
        if stock_info:
            response = make_response(jsonify({
                "symbol": "TSLA",
                "market": stock_info["market"],
                "price": stock_info["price"],
                "mod": stock_info["mod"],
                "pct": stock_info["pct"],
                "time": stock_info["time"]
            }))
            # 캐시 방지 헤더 추가
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
        else:
            return jsonify({"error": "주가 정보를 가져올 수 없습니다"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/stock')
def get_stock():
    ticker = request.args.get('ticker', 'TSLA').upper()
    try:
        stock_info = stock_check(ticker)
        if stock_info:
            response = make_response(jsonify({
                "symbol": ticker,
                "market": stock_info["market"],
                "price": stock_info["price"],
                "mod": stock_info["mod"],
                "pct": stock_info["pct"],
                "time": stock_info["time"]
            }))
            # 캐시 방지 헤더 추가
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
        else:
            return jsonify({"error": f"{ticker} 주가 정보를 가져올 수 없습니다"})
    except Exception as e:
        return jsonify({"error": str(e)})

#-------- 주가 위젯 추가 부분 끝 ---------------------#

#-------- dashboard 추가 부분 시작 ---------------------#
@app.route('/dash1')
def get_dash1():
    return render_template('dashboard1.html')
@app.route('/dash2')
def get_dash2():
    return render_template('dashboard2.html')
#-------- dashboard 추가 부분 끝 ---------------------#

@app.before_request
def require_login():    # 로그인 여부 체크
    # allowed_routes = ['index', 'login', 'logout', 'static', 'request_code', 'save_ip']  # 이것들은 로그인이 안되어있어도 정상 작동됨
    allowed_routes = ['index', 'login', 'logout', 'static', 'request_code', 'save_ip', 'join', 'join_work', 'loginH', 'hash', 'hash_password', 'login_work', 'bal_data', 'get_tsla', 'get_dash1', 'get_dash2', 'get_stock']  # 이것들은 로그인이 안되어있어도 정상 작동됨
    # print(request.endpoint)
    # print(session.get('userid'))
    if request.endpoint not in allowed_routes and 'userid' not in session:
        return redirect(url_for('index'))
    
    if request.endpoint not in allowed_routes: # 세션 체크, (마지막 로그인했던 날짜와 오늘 날짜가 다른 경우 로그인 화면으로 보냄)
        userid = session['userid']
        query = f'SELECT last_login FROM account WHERE userid = "{userid}";'
        query_database(query)
        result_last_login = query_database(query)
        last_login_db = result_last_login[0][0][:10]    # last_login 컬럼의 YYYY-MM-DD 부분만 가져옴

        # 날짜 (오늘)
        current_time = datetime.datetime.now()
        current_date = current_time.strftime("%Y-%m-%d")
        # current_date = '2023-08-26'

        # logging.debug(f'------- last_login : {last_login_db}, {current_date}')
        if last_login_db != current_date:
            session.pop('userid')
            logging.debug(f'--- 로그인 세션 만료. last_login : {last_login_db}, {current_date}')
            return redirect(url_for('index'))

@app.before_request
def logging_test():     # 로깅 테스트

    logging.debug(f"userid : {session.get('userid')}, {request.base_url}")
    # logging.debug(f'session : {session}')

    #app.logger.debug(request.remote_addr)
    # app.logger.debug(f"userid : {session.get('userid')}, {request.base_url}")
    # logging.info(f"userid : {session.get('userid')}, {request.base_url}")
    # app.logger.debug("BBB")
    #app.logger.debug(request.headers.get('X-Forwarded-For'))
    #app.logger.debug(request.environ.get('HTTP_X_REAL_IP', request.remote_addr))
    #app.logger.debug("Headers: %s", request.headers)

@app.before_request
def block_unauthorized_access():    # 기존에 허가된 URL 로만 접속이 가능하도록 설정 (config.py 에 들어있음)
    # logging.debug(ALLOWED_DOMAINS)
    requested_host = request.host.split(':')[0]  # Remove port if present
    if requested_host not in ALLOWED_DOMAINS:
        logging.debug("접속을 거부합니다. Access forbidden, code=403")
        return Response("Access forbidden", status=403)

if __name__ == '__main__':
    app.run(debug=True)
