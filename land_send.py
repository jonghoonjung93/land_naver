from datetime import timedelta
from module.etc_util import printL, mode_check, tele_push_admin
import telegram
import asyncio, json
import time, datetime
import sqlite3

#------ 당일 발송대상 메세지를 TELEGRAM으로 발송하는 프로그램 ------------#

# telegram 메세지 발송함수
async def land_tele_push(content, token, chat_id, seq): #텔레그램 발송용 함수
    result = [1, 0, 0, 0]	# 대상자, 성공, 재시도, 실패 건수
    bot = telegram.Bot(token = token)

    # 실패시 재시도
    send_retry = 0
    while True:	# 텔레그램 발송이 혹시 실패하면 최대 3회까지 성공할때까지 재시도
        try:
            await bot.send_message(chat_id, content, parse_mode = 'Markdown', disable_web_page_preview=True)
            printL(f"-- SEND success!!!({seq}) : {chat_id}")
            result[1] = result[1] + 1	# 성공
            break
        except:
            send_retry = send_retry + 1
            result[2] = result[2] + 1	# 재시도
            printL(f"-- land_send(tele_push) failed!!!({seq}) (retry:{send_retry}) : chat_id = {chat_id}")
            time.sleep(3)
            if send_retry == 3:
                printL(f"-- land_send(tele_push) aborted!!!({seq}) : chat_id = {chat_id}")
                result[3] = result[3] + 1	# 실패
                printL(f"-- content({seq}) : {content}")
                break
        else:	# 정상작동시
            pass
        finally:	# 마지막에 (정상,에러 상관없이)
            pass
    # printL("-------------------------------------")
    return(result)

def main():     # 테이블에서 대상 조회하고 발송하는 MAIN
    # Connect to the SQLite database
    db_connection = sqlite3.connect('land_naver.sqlite3')  # Replace 'your_database.db' with your actual database file name
    cursor = db_connection.cursor()

    # 날짜 (오늘)
    current_time = datetime.datetime.now()
    formatted_date = current_time.strftime("%Y%m%d")
    
    # 과거일자 yyyymmdd 로 만들기
    today = current_time.date()
    delete_day_form = today - timedelta(days=5)	# 삭제대상, 3일전 데이터는 삭제처리
    delete_day = delete_day_form.strftime("%Y%m%d")
    
    flag_sms = True

    flag = True
    if flag:    # 과거 데이터 삭제(정리)
        try:
            cursor.execute(f'SELECT count(*) FROM message_list WHERE date <= {delete_day}')
            printL(f"-- 삭제대상 건수(before) : {cursor.fetchall()[0][0]}")
            cursor.execute(f'DELETE FROM message_list WHERE date <= "{delete_day}"')  # 삭제대상 과거 데이터 삭제 (delete_day포함 과거 모두)
            printL(f'-- DELETE : {delete_day} 이전 데이터 삭제처리 완료')
            cursor.execute(f'SELECT count(*) FROM message_list WHERE date <= {delete_day}')
            printL(f"-- 삭제대상 건수(after) : {cursor.fetchall()[0][0]}")
            db_connection.commit()
        except sqlite3.Error as e:
            printL(f"DELETE : An error occurred: {e}")

    flag = True
    if flag:    # DB 읽어서 SEND 처리
        try:
            # Select data from the 'message_list' table
            cursor.execute(f'SELECT * FROM message_list WHERE date = {formatted_date} AND send_yn = "0"')
            rows = cursor.fetchall()  # fetch 하면 list 변수안에 tuples 형태로 담아짐
            if len(rows) == 0:
                printL(f"-- 당일({formatted_date}) 발송 대상 데이터가 없습니다.")
            for row in rows:
                col_0_id = row[0]
                col_1_date = row[1]  # date
                col_9_chat_room = row[9]  # chat_room
                col_10_chat_id = row[10]  # chat_id
                col_11_message = row[11]  # message
                col_12_parse_mode = row[12]  # parse_mode
                col_13_preview = row[13]  # preview
                            
                if flag_sms:
                    func_result = asyncio.run(land_tele_push(col_11_message, col_9_chat_room, col_10_chat_id, col_0_id)) #텔레그램 발송 (asyncio를 이용해야 함)
                    tele_result = func_result[1]	#발송 결과
                    tele_result_retry = func_result[2]  # 재시도 회수
                    tele_result_fail = func_result[3]  # 실패 여부 (0:성공, 1:실패)
                    # printL(f"telegram send 결과 : {tele_result}, {tele_result_retry}")

                    # 발송후 결과값 Update
                    new_send_yn_value = tele_result
                    new_retry_value = tele_result_retry
                    new_result_value = tele_result_fail
                    
                    update_query = "UPDATE message_list SET send_yn = ?, retry = ?, result = ? WHERE id = ?"
                    cursor.execute(update_query, (new_send_yn_value, new_retry_value, new_result_value, col_0_id))
                    db_connection.commit()  # Commit the changes
                # print("-" * 20)  # Print a separator between rows
        except sqlite3.Error as e:
            printL(f"SEND : An error occurred: {e}")
        finally:
            # Close the database connection
            # db_connection.close()
            pass
    
    flag = True
    if flag:    # 관리자 보고
        # 총건수 체크
        cursor.execute(f'SELECT count(*) FROM message_list WHERE date = {formatted_date}')
        rows = cursor.fetchall()  # fetch 하면 list 변수안에 tuples 형태로 담아짐
        cnt_all = rows[0][0]
        # printL(f"총건수 : {cnt_all}")

        # 정상 발송건수 체크
        cursor.execute(f'SELECT count(*) FROM message_list WHERE date = {formatted_date} AND send_yn = "1"')
        rows = cursor.fetchall()  # fetch 하면 list 변수안에 tuples 형태로 담아짐
        cnt_ok = rows[0][0]
        # printL(f"정상발송 건수 : {cnt_ok}")

        # 재시도 발송건수 체크
        cursor.execute(f'SELECT count(*) FROM message_list WHERE date = {formatted_date} AND send_yn = "1" AND retry != "0"')
        rows = cursor.fetchall()  # fetch 하면 list 변수안에 tuples 형태로 담아짐
        cnt_retry = rows[0][0]
        # printL(f"재시도 건수 : {cnt_retry}")

        # 실패 발송건수 체크
        cursor.execute(f'SELECT count(*) FROM message_list WHERE date = {formatted_date} AND send_yn = "1" AND result != "0"')
        rows = cursor.fetchall()  # fetch 하면 list 변수안에 tuples 형태로 담아짐
        cnt_fail = rows[0][0]
        # printL(f"실패 건수 : {cnt_fail}")

        # 발송 대상인원 체크
        cursor.execute(f'SELECT count(*) FROM (SELECT * FROM message_list WHERE date = {formatted_date} GROUP BY chat_id)')
        rows = cursor.fetchall()  # fetch 하면 list 변수안에 tuples 형태로 담아짐
        cnt_users = rows[0][0]
        cursor.execute(f'SELECT count(*) FROM message_list WHERE date = {formatted_date} GROUP BY chat_id')
        rows = cursor.fetchall()  # fetch 하면 list 변수안에 tuples 형태로 담아짐
        cnt_1user = rows[0][0]
        # printL(f"발송 대상자 : {cnt_users}명 * {cnt_1user}건")

        completed_message = (
            f"\[SEND 완료] 총건수 : {cnt_all}\n"
            f" - 정상발송 건수 : {cnt_ok}\n"
            f" - 재시도 건수 : {cnt_retry}\n"
            f" - 실패 건수 : {cnt_fail}\n"
            f" - 발송 대상자 : {cnt_users}명 \* {cnt_1user}건"
        )
        printL(completed_message)
        if flag_sms:
            # pass
            asyncio.run(tele_push_admin(completed_message)) #텔레그램 발송 (asyncio를 이용해야 함)

    # DB Close
    db_connection.close()

if __name__ == "__main__":
    main()
