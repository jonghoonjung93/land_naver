import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, jsonify
import logging
import datetime
from config import *
# import json

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

def query_database_update(query):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    cursor.close()
    conn.close()

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
    formatted_date2 = current_time.strftime("%Y.%m.%d")
    # formatted_date = '20230722'
    
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
    query = f'SELECT line FROM account WHERE userid = "{userid}"'
    line = query_database(query)
    # logging.debug(f'line = {line[0][0]}')

    return render_template('land_item5.html', items=items, userid=userid, today=formatted_date2, line=line[0][0])

@app.route('/new')
def display_land_items_new():   # 금일 신규 매물리스트
    # Logging the access request
    # app.logger.info(f'Access: {request.method} {request.url}')

    # 날짜 (오늘)
    current_time = datetime.datetime.now()
    formatted_date = current_time.strftime("%Y%m%d")
    formatted_date2 = current_time.strftime("%Y.%m.%d")
    # formatted_date = '20230722'

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
    query = f'SELECT line FROM account WHERE userid = "{userid}"'
    line = query_database(query)
    # logging.debug(f'line = {line[0][0]}')
    
    return render_template('land_item5.html', items=items, userid=userid, today=formatted_date2, line=line[0][0])

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
        query = f'SELECT userid, username, admin, available, reg_date, type, location, memo, expire_date, last_login, login_count, chat_id FROM account ORDER BY admin desc,login_count desc;'
        items = query_database(query)
        userid = session['userid']
        # return render_template('account1.html', items=items)
        return render_template('account3.html', items=items, userid=userid)
    else:
        return redirect(url_for('index'))

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

@app.before_request
def require_login():    # 로그인 여부 체크
    allowed_routes = ['index', 'login', 'logout', 'static']
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
def block_unauthorized_access():    # 기존에 허가된 URL 로만 접속이 가능하도록 설정
    # logging.debug(ALLOWED_DOMAINS)
    requested_host = request.host.split(':')[0]  # Remove port if present
    if requested_host not in ALLOWED_DOMAINS:
        logging.debug("접속을 거부합니다. Access forbidden, code=403")
        return Response("Access forbidden", status=403)

if __name__ == '__main__':
    app.run(debug=True)
