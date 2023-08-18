import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
import logging
import datetime

app = Flask(__name__)
app.secret_key = 'my_secret_key'

# Replace 'your_database.db' with the path to your SQLite3 database
DATABASE = '../land_naver.sqlite3'

# Configuring access log
# access_log_filename = 'access.log'
# access_handler = logging.FileHandler(access_log_filename)
# access_handler.setLevel(logging.INFO)
# access_handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s'))
# app.logger.addHandler(access_handler)

logging.basicConfig(filename='web.log', level=logging.DEBUG, format='%(asctime)s - %(message)s', datefmt='%Y.%m.%d %H:%M:%S')

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
    return render_template('login2.html')

@app.route('/login', methods=['POST'])
def login():
    userid = request.form['userid']
    password = request.form['password']
    
    conn = sqlite3.connect(DATABASE)  # Connect to your SQLite database
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM account WHERE userid = ? AND password = ?", (userid, password))
    user = cursor.fetchone()
    # conn.close()

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
        # logging.info(f"{last_login}, {login_count}, {session['userid']}")
        cursor.execute("UPDATE account SET last_login = ?, login_count = ? WHERE userid = ?", (last_login, login_count, session['userid']))
        conn.commit()
        conn.close()
        return redirect(url_for('display_land_items'))
    else:   # 로그인 실패
        flash('Invalid user ID or password. Please try again.', 'error')
        conn.close()
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('userid')
    return redirect(url_for('index'))

@app.route('/all')
def display_land_items():
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
def display_land_items_new():
    # Logging the access request
    # app.logger.info(f'Access: {request.method} {request.url}')

    # 날짜 (오늘)
    current_time = datetime.datetime.now()
    formatted_date = current_time.strftime("%Y%m%d")
    # formatted_date = '20230722'
    query = f'SELECT date, replace(bld_id,"BLD",""), memo, naver_bld_id, name, type, price, info_area_type, info_area_spec, ROUND(size_real*0.3025, 2), floor, agent_name, ho FROM land_item where date = "{formatted_date}" and new = "O";'
    items = query_database(query)
    return render_template('land_item5.html', items=items)

@app.before_request
def require_login():
    allowed_routes = ['index', 'login', 'logout']
    # print(request.endpoint)
    # print(session.get('userid'))
    if request.endpoint not in allowed_routes and 'userid' not in session:
        return redirect(url_for('index'))

@app.before_request
def log_request_info():
    #app.logger.debug(request.remote_addr)
    
    # app.logger.debug(f"userid : {session.get('userid')}, {request.base_url}")
    
    logging.info(f"userid : {session.get('userid')}, {request.base_url}")

    # app.logger.debug("BBB")
    #app.logger.debug(request.headers.get('X-Forwarded-For'))
    #app.logger.debug(request.environ.get('HTTP_X_REAL_IP', request.remote_addr))
    #app.logger.debug("Headers: %s", request.headers)

if __name__ == '__main__':
    app.run(debug=True)
