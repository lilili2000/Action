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


import requests

res_date = datetime.datetime.now() + datetime.timedelta(days=2)

class AutoReservation:
    def __init__(
            self,
            username,
            password,

            reservation_time: str,
            reservation_arena: str,
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
            timeout=3
        )

        self.action_chains = ActionChains(self.driver)
        self.username = username
        self.password = password
        #设置为两天后
        self.reservation_date = res_date
        self.reservation_time = reservation_time
        self.reservation_arena = reservation_arena
        self.refresh_count = 5
        self.img_refresh_count = 10

    def wait_for_element(self, by, value):
        try:
            element = self.wait.until(ExpectedCond.presence_of_element_located((by, value)))
            return element
        except:
            print("等待超时，元素未找到，进行页面刷新")
            self.refresh_count -= 1
            if self.refresh_count < 0:
                raise Exception("刷新次数过多，请检查网络连接")
            self.driver.refresh()
            return self.wait_for_element(by, value)  # 递归调用，继续等待元素



    def login(self):
        self.res_msg("Subject:login")
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
        # TODO:检查校园生活服务平台的登录状态

    def jump_to_confirm_page(self):
        # 点击场馆预约，这里有一个页面跳转的动作
        self.wait_for_element(
                By.XPATH,
                '//ul[@class="ydfw_r_content"]//li[1]//a[1]'
        ).click()
        time.sleep(1)
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
            except:
                self.refresh_count -= 1
                if self.refresh_count <= 0:
                    return
                self.driver.refresh()

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

        # 点击预约，页面跳转
        time.sleep(1)
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
                        tmp_time = time.strftime("%H:%M", time.localtime())
                        if time.strftime("%H:%M", time.localtime()) < '07:00':
                            time.sleep(1)
                            continue
                        self.driver.execute_script("""
                            goToDate('{}')
                        """.format(self.reservation_date))
                    except:
                        raise Exception("跳转日期失败，刷新页面")
                    hoveredDate = self.driver.find_element(by=By.XPATH, value='//li[contains(@class, "hover")]').find_element(by=By.TAG_NAME, value='input').get_dom_attribute("value")
                    targetday = self.reservation_date.strftime("%Y-%m-%d")
                    if hoveredDate == targetday:
                        break       
            except:
                self.refresh_count -= 1
                if self.refresh_count <= 0:
                    return
                tempDriver.refresh()
                self.driver = tempDriver
                continue
            sleep(1)
            
            # 查找预约时间，判断是否可以预约
            reservationBtn = self.driver.find_element(
                by=By.XPATH,
                value='//font[contains(text(), "{}")]'.format(self.reservation_time)
            ).find_element(
                By.XPATH,
                value='../../td[contains(@align, "right")]//img')
            # 判断reservationBtn是否有onClick属性
            if reservationBtn.get_dom_attribute('onClick'):
                # 可以预约
                reservationBtn.click()
                # 进入预约验证页面点击verify_button1
                verifyBtn = self.wait.until(
                    ExpectedCond.element_to_be_clickable((By.ID, 'verify_button1'))
                )
                sleep(1)
                verifyBtn.click()
                # 等待直到valid_bg-img加载完成，从图片的src属性获取图片的base64编码
                self.wait.until(
                    ExpectedCond.visibility_of_element_located((By.CLASS_NAME, 'valid_bg-img'))
                )
                break
            else:
                # 不能预约，一秒钟刷新一次
                #raise Exception("场地：{}，日期：{}，时间：{}，无法预约".format(self.reservation_arena, self.reservation_date, self.reservation_time))
                sleep(1)
                self.refresh_count -= 1
                if self.refresh_count < 0:
                    return
                self.driver.refresh()
                


    def pass_verification(self):
        # 弹出验证码的模态窗口后进入该函数
        # 如果识别结果长度不足，则直接点击切换验证码，
        # 如果点击完成后，提示验证失败，则重新识别并点击
        # 直到识别成功

        while True:
            img_block = self.driver.find_element(
                By.CLASS_NAME, 'valid_bg-img'
            )
            verifyPic_base64 = img_block.get_dom_attribute('src').replace('data:image/jpg;base64,', '')

            # recogResults: list = nn_service_request.nn_service_request(verifyPicWithCharTarget_base64)
            recogResults = self.pass_capcha(verifyPic_base64)
            
            target = self.driver.find_element(By.CLASS_NAME,"valid_tips__text")
            move = ActionChains(self.driver)

            img_block_size = img_block.size
            img_block_width = img_block_size['width']
            img_block_height = img_block_size['height']

            try:
                for i in target.text[6:10]:
                    x_offset = recogResults[i]['X坐标值']
                    y_offset = recogResults[i]['Y坐标值']
                    print(f"Clicking at: {x_offset}, {y_offset}")

                    # 点击时计算偏移量
                    move.move_to_element(img_block).move_by_offset(x_offset - (img_block_width / 2), y_offset - (img_block_height / 2)-15).click().perform()

                    # print(recogResults[i]['X坐标值'], recogResults[i]['Y坐标值'])
                    # move.move_to_element(img_block).move_by_offset(-160 + recogResults[i]['X坐标值'], -80 + recogResults[i]['Y坐标值'] ).click().perform()
            except:
                pass
            
            sleep(1)
            # 检查是否通过验证，验证码模式窗口class = valid_popup是否关闭，以及验证成功id = verify_result是否成功
            isValidPopupClosed = self.driver.execute_script(
                """
                    return window.getComputedStyle(arguments[0]).getPropertyValue("display");
                """,
                self.driver.find_element(By.CLASS_NAME, 'valid_popup')
            ) == 'none'
            isVerifyResultShowed = self.driver.execute_script(
                """
                    return window.getComputedStyle(arguments[0]).getPropertyValue("display");
                """,
                self.driver.find_element(By.ID, 'verify_result')
            ) == 'block'
            if isValidPopupClosed and isVerifyResultShowed:
                submitBtn = self.driver.find_element(By.ID,'btn_sub')
                submitBtn.click()
                self.driver.switch_to.alert.accept()
                print("{}_{} reservation success".format(res_date, ar.reservation_time))
                self.res_msg("Subject:{}_{} reservation success".format(res_date, ar.reservation_time))
                break
            else:
                # 刷新验证码
                if self.img_refresh_count > 0:
                    self.driver.find_element(By.CLASS_NAME, 'valid_refresh').click()
                    sleep(1)
                    self.img_refresh_count -= 1
                else:
                    return


    def clean_up(self):
        self.driver.close()
        self.driver.quit()

    def pass_capcha(self, image):
        sleep(1)
        data = {"username": 'feeling2024', 
        "password": '12345678', 
        "ID": '73413759', 
        "b64": image, 
        "version": "3.1.1"}
        data_json = json.dumps(data)
        result = json.loads(requests.post("http://www.fdyscloud.com.cn/tuling/predict", data=data_json).text)
        result = result['data']
        return result

    def res_msg(self, message):
        EMAILS = ["1063870403@qq.com"]  # Receive error notifications by email
        YOUR_EMAIL = "17689375885@163.com"  # Account to send email from
        EMAIL_PASSWORD = "HATCAIWZLGETFXJU"  # Password for the email account
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
    args = parser.parse_args()
    ar = AutoReservation(
        args.username,
        args.password,
        #args.reservation_date,
        args.reservation_time,
        args.reservation_arena
    )
    try:
        ar.login()
        ar.jump_to_confirm_page()
        ar.pass_verification()
    finally:
        ar.clean_up()

