import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import logging
import datetime
from config import *

flag=True
if flag:
    app = Flask(__name__)
    app.secret_key = 'my_secret_key'

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

@app.route('/')
def index():
    return render_template('login3.html')

@app.route('/login', methods=['POST'])
def login():
    userid = request.form['userid']
    password = request.form['password']
    
    conn = sqlite3.connect(DATABASE)  # Connect to your SQLite database
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM account WHERE userid = ? AND password = ? AND available = '1'", (userid, password))
    user = cursor.fetchone()

    if user:    # 로그인 성공
        session['userid'] = user[0]  # Store user ID in session
        # ------ last_login, login_count UPDATE 처리 -------- #
        # 날짜 (오늘)
        current_time = datetime.datetime.now()
        last_login = current_time.strftime("%Y-%m-%d %H:%M:%S")
        if user[11] is None or user[11] == "":  # 기존 login_count 컬럼 확인
            before_login_count = 0
        else:
            before_login_count = int(user[11])
        login_count = before_login_count + 1
        logging.debug(f"Login Success. last({last_login}), cnt:{login_count}, userid:{session['userid']}")
        cursor.execute("UPDATE account SET last_login = ?, login_count = ? WHERE userid = ?", (last_login, login_count, session['userid']))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('display_land_items'))
    else:   # 로그인 실패
        flash('Invalid user ID or password. Please try again.', 'error')
        logging.error(f"Invalid user ID or password. Please try again.({userid}/{password})")
        cursor.close()
        conn.close()
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('userid')
    return redirect(url_for('index'))

@app.route('/all')
def display_land_items():   # 전체 매물리스트
    # Logging the access request
    # app.logger.info(f'Access: {request.method} {request.url}')

    # 날짜 (오늘)
    current_time = datetime.datetime.now()
    formatted_date = current_time.strftime("%Y%m%d")
    # formatted_date = '20230722'
    query = f'SELECT date, replace(bld_id,"BLD",""), memo, naver_bld_id, name, type, price, info_area_type, info_area_spec, ROUND(size_real*0.3025, 2), floor, agent_name, ho FROM land_item where date = "{formatted_date}";'
    items = query_database(query)
    return render_template('land_item5.html', items=items)

@app.route('/new')
def display_land_items_new():   # 금일 신규 매물리스트
    # Logging the access request
    # app.logger.info(f'Access: {request.method} {request.url}')

    # 날짜 (오늘)
    current_time = datetime.datetime.now()
    formatted_date = current_time.strftime("%Y%m%d")
    # formatted_date = '20230722'
    query = f'SELECT date, replace(bld_id,"BLD",""), memo, naver_bld_id, name, type, price, info_area_type, info_area_spec, ROUND(size_real*0.3025, 2), floor, agent_name, ho FROM land_item where date = "{formatted_date}" and new = "O";'
    items = query_database(query)
    return render_template('land_item5.html', items=items)

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
        return render_template('message_list1.html', items=items)
    else:
        return redirect(url_for('index'))

@app.route('/adm/account')
def display_account():      # 계정 리스트
    if admin_check(session['userid']):
        query = f'SELECT userid, username, admin, available, reg_date, type, location, memo, expire_date, last_login, login_count, chat_id FROM account ORDER BY admin desc,login_count desc;'
        items = query_database(query)
        return render_template('account1.html', items=items)
    else:
        return redirect(url_for('index'))

@app.route('/adm')
def admin_home():     # 관리자 페이지 메인
    return redirect(url_for('display_account'))

@app.before_request
def require_login():    # 로그인 여부 체크
    allowed_routes = ['index', 'login', 'logout', 'static']
    # print(request.endpoint)
    # print(session.get('userid'))
    if request.endpoint not in allowed_routes and 'userid' not in session:
        return redirect(url_for('index'))

@app.before_request
def log_request_info():     # 로깅 테스트
    #app.logger.debug(request.remote_addr)
    
    # app.logger.debug(f"userid : {session.get('userid')}, {request.base_url}")
    
    # logging.info(f"userid : {session.get('userid')}, {request.base_url}")
    logging.debug(f"userid : {session.get('userid')}, {request.base_url}")

    # app.logger.debug("BBB")
    #app.logger.debug(request.headers.get('X-Forwarded-For'))
    #app.logger.debug(request.environ.get('HTTP_X_REAL_IP', request.remote_addr))
    #app.logger.debug("Headers: %s", request.headers)

@app.before_request
def block_unauthorized_access():    # 기존에 허가된 URL 로만 접속이 가능하도록 설정
    # logging.debug(ALLOWED_DOMAINS)
    requested_host = request.host.split(':')[0]  # Remove port if present
    if requested_host not in ALLOWED_DOMAINS:
        logging.debug("접속을 거부합니다. Access forbidden, code=403")
        return Response("Access forbidden", status=403)

if __name__ == '__main__':
    app.run(debug=True)
