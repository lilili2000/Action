import argparse
import base64
import io
import json
import smtplib
import time
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ExpectedCond
from time import sleep
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys


import requests

res_date = datetime.datetime.now() + datetime.timedelta(days=2)

def print_with_time(msg):
    print("[{}] {}".format(time.strftime("%H:%M:%S", time.localtime()), msg))

class AutoReservation:
    def __init__(
            self,
            username,
            password,
            resvation_times,
            reservation_time: str,
            reservation_arena: str,
            
            capcha_username: str = None,
            capcha_password: str = None,
            receive_email: str = None,
            send_email: str = None,
            send_email_key: str = None,
            **kwargs
    ):
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 启用无头模式
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        self.driver: WebDriver = webdriver.Chrome(service=ChromeService(), options=chrome_options)
        self.driver.set_window_size(1920, 1080)
        self.wait: WebDriverWait = WebDriverWait(
            self.driver,
            timeout=5,
        )

        self.action_chains = ActionChains(self.driver)
        self.username = username
        self.password = password
        #设置为两天后
        self.reservation_date = res_date
        self.reservation_times = resvation_times
        self.reservation_time = reservation_time
        self.reservation_arena = reservation_arena
        self.refresh_count = 5
        self.img_refresh_count = 20
        self.reserved = 0
        self.total = 100
        self.after_login_driver = None
        self.first_time = True

        self.capcha_username = capcha_username
        self.capcha_password = capcha_password
        self.receive_email = receive_email
        self.send_email = send_email
        self.send_email_key = send_email_key

    def wait_for_element(self, by, value):
        try:
            element = self.wait.until(ExpectedCond.presence_of_element_located((by, value)))
            return element
        except:
            print_with_time("等待超时，元素未找到，进行页面刷新")
            self.refresh_count -= 1
            if self.refresh_count < 0:
                raise Exception("刷新次数过多，请检查网络连接")
            self.driver.refresh()
            sleep(0.5)
            return self.wait_for_element(by, value)  # 递归调用，继续等待元素



    def login(self):
        # 创建邮件
        msg = MIMEMultipart()
        msg["Subject"] = "羽毛球场地预约开始"

        # 邮件正文
        body = "登录成功, 开始预约"+self.reservation_arena+"，预约时间为"+self.reservation_time
        msg.attach(MIMEText(body, "plain"))

        self.res_msg(msg.as_string())
        # 访问登录页面，点击”校内登录“按钮，等待页面跳转
        self.driver.get(r'https://elife.fudan.edu.cn/login.jsp')
        self.wait.until(
            ExpectedCond.element_to_be_clickable(
                (
                    By.CLASS_NAME,
                    "xndl"
                )
            )
        ).click()
        # 等待统一登录页面的用户名、密码和登录按钮显示出来
        
        self.wait.until(
            ExpectedCond.presence_of_element_located(
                (
                    By.ID,
                    'username'
                )
            )
        ).send_keys(self.username)
        self.wait.until(
            ExpectedCond.presence_of_element_located(
                (
                    By.ID,
                    'password'
                )
            )
        ).send_keys(self.password)
        self.wait.until(
            ExpectedCond.element_to_be_clickable(
                (
                    By.ID,
                    'idcheckloginbtn'
                )
            )
        ).click()
        # 保留driver
        self.after_login_driver = self.driver


    def jump_to_confirm_page(self) -> str:
        if self.first_time == False:
            while self.driver.window_handles.__len__() > 1:
                self.driver.switch_to.window(self.driver.window_handles[-1])
                self.driver.close()
            self.driver = self.after_login_driver
            self.driver.switch_to.window(self.driver.window_handles[0])
        self.first_time = False
        # 点击场馆预约，这里有一个页面跳转的动作
        self.wait_for_element(
                By.XPATH,
                '//ul[@class="ydfw_r_content"]//li[1]//a[1]'
        ).click()
        time.sleep(0.5)
        self.driver.switch_to.window(self.driver.window_handles[-1])

        # 选择场馆，场馆列表使用iframe标签内嵌了一个网页，要切换frame
        while True:
            try:
                WebDriverWait(self.driver, 3).until(
                    ExpectedCond.frame_to_be_available_and_switch_to_it(
                        (
                            By.ID,
                            'contentIframe'
                        )
                    )
                )
                break
            except Exception as e:
                print_with_time(e)
                self.refresh_count -= 1
                if self.refresh_count <= 0:
                    return
                self.driver.refresh()
                sleep(0.5)

        while True:
            try:
                WebDriverWait(self.driver, 3).until(
                    ExpectedCond.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//a[contains(text(), '{}')]".format(self.reservation_arena)
                        )
                    )
                ).click()
                break
            except:
                self.refresh_count -= 1
                if self.refresh_count <= 0:
                    return
                self.driver.refresh()
                sleep(0.5)

        # 点击预约，页面跳转
        time.sleep(0.5)
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.wait.until(
            ExpectedCond.element_to_be_clickable(
                (
                    By.CLASS_NAME,
                    'button_order'
                )
            )
        ).click()
        
        
        while True:
            tempDriver = self.driver
            # 选择日期和时间，时间选择列表是用iframe嵌入的页面，要切换frame到contentIframe
            try:
                WebDriverWait(self.driver, 3).until(
                    ExpectedCond.frame_to_be_available_and_switch_to_it(
                        (
                            By.ID,
                            'contentIframe'
                        )
                    )
                )
                
                # 用js代码跳转到指定日期，函数名为goToDate，不成功则重新跳转，直到成功
                while True:
                    try:
                        # 如果当前时间早于7:00则等到7:00
                        # tmp_time = time.strftime("%H:%M", time.localtime())
                        if time.strftime("%H:%M", time.localtime()) < '07:00':
                            time.sleep(1)
                            continue
                        self.driver.execute_script("""
                            goToDate('{}')
                        """.format(self.reservation_date))
                        print_with_time("跳转日期成功"+self.reservation_date.strftime("%Y-%m-%d"))
                    except:
                        raise Exception("跳转日期失败，刷新页面")
                    sleep(0.5)
                    hoveredDate = self.driver.find_element(by=By.XPATH, value='//li[contains(@class, "hover")]').find_element(by=By.TAG_NAME, value='input').get_dom_attribute("value")
                    targetday = self.reservation_date.strftime("%Y-%m-%d")
                    if hoveredDate == targetday:
                        break       

                sleep(0.2)
            
                # 查找预约时间，判断是否可以预约
                reservationBtn = self.driver.find_element(
                    by=By.XPATH,
                    value='//font[contains(text(), "{}")]'.format(self.reservation_time)
                ).find_element(
                    By.XPATH,
                    value='../../td[contains(@align, "right")]//img')
                # 判断是否有空场
                nums = reservationBtn.find_element(
                    By.XPATH,
                    value='../../td[contains(@class, "site_td4")]'
                )
                self.reserved = int(nums.find_element(
                    By.TAG_NAME,
                    'font'
                ).text)
                print_with_time("已预约人数：{}".format(self.reserved))
                self.total = int(nums.find_element(
                    By.TAG_NAME,
                    'span'
                ).text)
                print_with_time("总容量：{}".format(self.total))
                if self.reserved == self.total:
                    print_with_time("场地：{}，日期：{}，时间：{}，已满".format(self.reservation_arena, self.reservation_date, self.reservation_time))
                    return "next"
                # 判断reservationBtn是否有onClick属性
                if reservationBtn.get_dom_attribute('onClick'):
                    # 可以预约
                    sleep(0.3)
                    reservationBtn.click()
                    print_with_time("进入预约时间")
                    # 进入预约验证页面点击verify_button1
                    verifyBtn = self.wait.until(
                        ExpectedCond.element_to_be_clickable((By.ID, 'verify_button1')),
                        message="预约页面加载超时"
                    )
                    verifyBtn.click()
                    sleep(0.5)
                    WebDriverWait(self.driver, 2).until(
                        ExpectedCond.presence_of_all_elements_located((By.CLASS_NAME, 'valid_bg-img')),
                        message="验证码图片加载超时1",
                    )
                    break
                else:
                    # 不能预约，一秒钟刷新一次
                    #raise Exception("场地：{}，日期：{}，时间：{}，无法预约".format(self.reservation_arena, self.reservation_date, self.reservation_time))
                    print_with_time("无法预约，刷新")
                    self.refresh_count -= 1
                    if self.refresh_count < 0:
                        return "next"
                    self.driver.refresh()
                    sleep(1)
            except Exception as e:
                print_with_time(e)
                if self.reserved == self.total:
                    return "next"
                self.refresh_count -= 1
                if self.refresh_count <= 0:
                    print_with_time("刷新次数过多，休息一下吧")
                    sleep(30)
                    self.refresh_count=2
                tempDriver.refresh()
                sleep(1)
                self.driver = tempDriver
                continue
                


    def pass_verification(self):
        # 弹出验证码的模态窗口后进入该函数
        # 如果识别结果长度不足，则直接点击切换验证码，
        # 如果点击完成后，提示验证失败，则重新识别并点击
        # 直到识别成功

        while True:
            try:
                self.wait.until(
                    ExpectedCond.presence_of_element_located((By.CLASS_NAME, 'valid_bg-img')),
                    message="验证码图片加载超时2",
                )
                img_block = self.driver.find_element(
                    By.CLASS_NAME, 'valid_bg-img'
                )
                print_with_time("验证码图片加载成功")
                self.wait.until(
                    lambda driver: img_block.get_dom_attribute('src') != '',
                    message="验证码src属性加载超时",
                )
                self.wait.until(
                    ExpectedCond.element_to_be_clickable((By.CLASS_NAME, 'valid_refresh')),
                    message="验证码刷新按钮加载超时",
                )
                src = img_block.get_dom_attribute('src')
                verifyPic_base64 = src.replace('data:image/jpg;base64,', '')
            except Exception as e:
                print_with_time(e)
                if self.img_refresh_count > 0:
                    print_with_time("刷新验证码1")
                    self.driver.find_element(By.CLASS_NAME, 'valid_refresh').click()
                    sleep(0.5)
                    self.img_refresh_count -= 1
                continue

            # recogResults: list = nn_service_request.nn_service_request(verifyPicWithCharTarget_base64)
            recogResults = self.pass_capcha(verifyPic_base64)
            try:
                target = self.driver.find_element(By.CLASS_NAME,"valid_tips__text")
            except Exception as e:
                print_with_time(e)
                print_with_time("字符串获取失败")
            move = ActionChains(self.driver, 50)
            

            img_block_size = img_block.size
            img_block_width = img_block_size['width']
            img_block_height = img_block_size['height']

            try:
                for i in target.text[6:10]:
                    x_offset = recogResults[i]['X坐标值']
                    y_offset = recogResults[i]['Y坐标值']
                    # print_with_time(f"Clicking at: {x_offset}, {y_offset}")
                    # 点击时计算偏移量
                    move.move_to_element(img_block).move_by_offset(x_offset - (img_block_width / 2), y_offset - (img_block_height / 2)-15).click()
                move.perform()
                sleep(0.1)
                    # print_with_time(recogResults[i]['X坐标值'], recogResults[i]['Y坐标值'])
                    # move.move_to_element(img_block).move_by_offset(-160 + recogResults[i]['X坐标值'], -80 + recogResults[i]['Y坐标值'] ).click().perform()
            except Exception as e:
                print_with_time(e)
                pass
            
            # 检查是否通过验证，验证码模式窗口class = valid_popup是否关闭，以及验证成功id = verify_result是否成功
            def custom_condition(driver):
                isValidPopupClosed = driver.execute_script(
                    """
                        return window.getComputedStyle(arguments[0]).getPropertyValue("display");
                    """,
                    driver.find_element(By.CLASS_NAME, 'valid_popup')
                ) == 'none'
                isVerifyResultShowed = driver.execute_script(
                    """
                        return window.getComputedStyle(arguments[0]).getPropertyValue("display");
                    """,
                    driver.find_element(By.ID, 'verify_result')
                ) == 'block'
                return isValidPopupClosed and isVerifyResultShowed
            try:
                WebDriverWait(self.driver, 1).until(custom_condition, message="验证错误")
                
                submitBtn = self.driver.find_element(By.ID,'btn_sub')
                submitBtn.click()
                print_with_time("点击提交")
                sleep(0.2)

                has_alert = ExpectedCond.alert_is_present()(self.driver)
                if has_alert != False:
                    print_with_time("有弹窗，点击确定")
                    has_alert.accept()
                else:
                    print_with_time("没有弹窗，直接过")
                
                # 创建邮件
                msg = MIMEMultipart()
                msg["Subject"] = "场地预约成功"

                # 邮件正文
                body = "成功预约{}，时间为{}".format(self.reservation_arena, self.reservation_time)
                msg.attach(MIMEText(body, "plain"))
                self.res_msg(msg.as_string())
                print_with_time(body)
                break
            except Exception as e:
                print_with_time(e)
                # 刷新验证码
                if self.img_refresh_count > 0:
                    print_with_time("刷新验证码2")
                    self.driver.find_element(By.CLASS_NAME, 'valid_refresh').click()
                    sleep(0.3)
                    self.img_refresh_count -= 1
                else:
                    return



    def clean_up(self):
        self.driver.close()
        self.driver.quit()

    def pass_capcha(self, image):
        sleep(1)
        data = {"username": self.capcha_username, 
        "password": self.capcha_password, 
        "ID": '73413759', 
        "b64": image, 
        "version": "3.1.1"}
        data_json = json.dumps(data)
        result = json.loads(requests.post("http://www.fdyscloud.com.cn/tuling/predict", data=data_json).text)
        result = result['data']
        return result

    def res_msg(self, message):
        EMAILS = [self.receive_email]  # Receive error notifications by email
        YOUR_EMAIL = self.send_email # Account to send email from
        EMAIL_PASSWORD = self.send_email_key  # Password for the email account
        connection = smtplib.SMTP_SSL("smtp.163.com", 465)
        try:
            connection.ehlo()
            connection.login(YOUR_EMAIL, EMAIL_PASSWORD)
            connection.sendmail(YOUR_EMAIL, EMAILS, message)
        finally:
            connection.quit()
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", type=str)
    parser.add_argument("--password", type=str)
    #parser.add_argument("--reservation-date", type=str, help="预约日期，形式为yyyy-mm-dd")
    parser.add_argument("--reservation-time", type=str, help="预约时间段，形式为hh:mm")
    parser.add_argument("--reservation-arena", type=str, help="预约场地")
    parser.add_argument("--capcha-username", type=str, help="验证码识别服务用户名")
    parser.add_argument("--capcha-password", type=str, help="验证码识别服务密码")
    parser.add_argument("--receive-email", type=str, help="接收邮件地址")
    parser.add_argument("--send-email-key", type=str, help="发送邮件密钥")
    parser.add_argument("--send-email", type=str, help="发送邮件地址")
    args = parser.parse_args()
    # 将逗号分隔的字符串拆分为数组
    reservation_times = args.reservation_time.split(',')
    ar = AutoReservation(
        args.username,
        args.password,
        #args.reservation_date,
        reservation_times,
        args.reservation_time,
        args.reservation_arena,
        args.capcha_username,
        args.capcha_password,
        args.receive_email,
        args.send_email,
        args.send_email_key
    )
    try:


        ar.login()
        for reservation_time in reservation_times:
            ar.reservation_time = reservation_time
            print_with_time("开始预约时间：{}".format(reservation_time))
            msg = ar.jump_to_confirm_page()
            if msg == "next":
                continue
            ar.pass_verification()  

    finally:
        ar.clean_up()
