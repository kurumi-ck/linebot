from __future__ import unicode_literals
import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage, 
    TextSendMessage,
    TemplateSendMessage,
    MessageTemplateAction,
    ImageSendMessage,
    ButtonsTemplate)
#import re
import configparser

#裁切IMG
from PIL import Image

#利用yf抓股價 matplotlib繪製圖表
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
plt.switch_backend('agg')

#網站截圖
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

#上傳圖檔
import pyimgur

import time

app = Flask(__name__)

# LINE 聊天機器人的基本資料
config = configparser.ConfigParser()
config.read('config.ini')

line_bot_api = LineBotApi(config.get('line-bot', 'channel_access_token'))
handler = WebhookHandler(config.get('line-bot', 'channel_secret'))


# 接收 LINE 的資訊
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    
    try:
        print(body, signature)
        handler.handle(body, signature)
        
    except InvalidSignatureError:
        abort(400)

    return 'OK'

#選單
@handler.add(MessageEvent, message=TextMessage)
def main(event):
    message = event.message.text
    if "股票 " in message:
        line_bot_api.reply_message(
            event.reply_token,
            TemplateSendMessage(
            alt_text = "股票資訊",
            template = ButtonsTemplate(
                        #thumbnail_image_url ="", 可放圖片
                        title = message + "股票資訊",
                        text = "請點選想查詢的股票資訊",
                        actions = [
                            MessageTemplateAction(
                                label= message[3:] + " 個股基本資訊",
                                text= "個股基本資訊 " + message[3:]),
                            MessageTemplateAction(
                                label= message[3:] + " 歷史股利",
                                text= "歷史股利 " + message[3:]),
                            MessageTemplateAction(
                                label= message[3:] + " 歷史股價",
                                text= "歷史股價 " + message[3:]),
                            MessageTemplateAction(
                                label= message[3:] + " 合理價",
                                text= "合理價 " + message[3:])
                        ],   
                    )
            )
        )
    if "合理價 " in message:
        line_bot_api.reply_message(
            event.reply_token,
            TemplateSendMessage(
            alt_text = "合理價位",
            template = ButtonsTemplate(
                        #thumbnail_image_url ="", 可放圖片
                        title = message,
                        text = "請點選想選擇的合理價計算方式",
                        actions = [
                            MessageTemplateAction(
                                label="綜合評估",
                                text= "fitprice m " + message[4:]),
                            MessageTemplateAction(
                                label= "以股利為重",
                                text= "fitprice d " + message[4:]),
                            MessageTemplateAction(
                                label= "以淨值為重",
                                text= "fitprice v " + message[4:])
                        ],   
                    )
            )
        )

    if "歷史股利 " in message:
        #截圖
        screenshot_dividend(message[5:])

        #上傳至圖庫再抓下來
        #傳送圖檔
        
        x = imr(message[5:])
        image_message = ImageSendMessage(
        original_content_url=x,
        preview_image_url=x
        )
            
        line_bot_api.reply_message(event.reply_token, image_message)

        #刪除圖片
        delete_pic(message[5:])

    if "個股基本資訊 " in message:
        #截圖
        screenshot_profile(message[7:])

        #上傳至圖庫再抓下來
        #傳送圖檔
        
        x = imr(message[7:])

        image_message = ImageSendMessage(
        original_content_url=x,
        preview_image_url=x
        )
            
        line_bot_api.reply_message(event.reply_token, image_message)

        #刪除圖片
        delete_pic(message[7:])
    
    if "歷史股價 " in message:
       
        plot_stcok_chart(message[5:])

        #上傳至圖庫再抓下來
        #傳送圖檔
        
        x = imr(message[5:])

        image_message = ImageSendMessage(
        original_content_url=x,
        preview_image_url=x
        )
            
        line_bot_api.reply_message(event.reply_token, image_message)

        #刪除圖片
        delete_pic(message[5:])

    if "K線圖 " in message:
        kline_words = message[4:]
        kline_words = kline_words.split("&")

        plot_stcok_k_chart(kline_words[0],kline_words[1])

        #上傳至圖庫再抓下來
        #傳送圖檔
        x = imr(kline_words[0])

        image_message = ImageSendMessage(
        original_content_url=x,
        preview_image_url=x
        )
            
        line_bot_api.reply_message(event.reply_token, image_message)

        #刪除圖片
        delete_pic(kline_words[0])

    if "fitprice m " in message:
        stock = message[11:]
        price =  name(stock)
        dividend =  fit_dividend(stock)
        value =  fit_value(stock)
        w = ["目前股價:","高價位:","合理價位:","低價位:","預期含息報酬率:","預計報酬區間"]

        mix_1 = dividend
        mix_1[0] = price
        mix_1[1] = round((dividend[1]*0.5 + value[1]*0.5),2)
        mix_1[2] = round((dividend[2]*0.5 + value[2]*0.5),2)
        mix_1[3] = round((dividend[3]*0.5 + value[3]*0.5),2)
        for x in range(4):
            print(w[x],mix_1[x])
        
        fpp(stock,mix_1[1],mix_1[2],mix_1[3])
        x = imr(stock)

        remuneration = [0,0,0]
        remuneration[0] = round(((float(price) + mix_1[4] - mix_1[1])/mix_1[1]*100),0)
        remuneration[1] = round(((float(price) + mix_1[4] - mix_1[2])/mix_1[2]*100),1)
        remuneration[2] = round(((float(price) + mix_1[4] - mix_1[3])/mix_1[3]*100),0)

        n = '\n'
        message = TextSendMessage(text='合理價-->綜合評估\n' + 
            w[0] + str(mix_1[0]) + n +
            w[1] + str(mix_1[1]) + n +
            w[2] + str(mix_1[2]) + n +
            w[3] + str(mix_1[3]) + n +
            w[4] + str(remuneration[1]) + "%" + n +
            w[5] + str(remuneration[0]) + "%~" + str(remuneration[2]) + "%"),ImageSendMessage(
            original_content_url=x,
            preview_image_url=x
            )

        line_bot_api.reply_message(event.reply_token,message)

        delete_pic(stock)
    if "fitprice d " in message:
        stock = message[11:]
        price =  name(stock)
        dividend =  fit_dividend(stock)
        value =  fit_value(stock)
        w = ["目前股價:","高價位:","合理價位:","低價位:","預期含息報酬率:","預計報酬區間"]
        
        mix_1 = dividend
        mix_1[0] = price
        mix_1[1] = round((dividend[1]*0.8 + value[1]*0.2),2)
        mix_1[2] = round((dividend[2]*0.8 + value[2]*0.2),2)
        mix_1[3] = round((dividend[3]*0.8 + value[3]*0.2),2)
        for x in range(4):
            print(w[x],mix_1[x])

        fpp(stock,mix_1[1],mix_1[2],mix_1[3])
        x = imr(stock)

        remuneration = [0,0,0]
        remuneration[0] = round(((float(price) + mix_1[4] - mix_1[1])/mix_1[1]*100),0)
        remuneration[1] = round(((float(price) + mix_1[4] - mix_1[2])/mix_1[2]*100),1)
        remuneration[2] = round(((float(price) + mix_1[4] - mix_1[3])/mix_1[3]*100),0)

        n = '\n'
        message = TextSendMessage(text='合理價-->以股利為重\n' + 
            w[0] + str(mix_1[0]) + n +
            w[1] + str(mix_1[1]) + n +
            w[2] + str(mix_1[2]) + n +
            w[3] + str(mix_1[3]) + n +
            w[4] + str(remuneration[1]) + "%" + n +
            w[5] + str(remuneration[0]) + "%~" + str(remuneration[2]) + "%"),ImageSendMessage(
            original_content_url=x,
            preview_image_url=x
            )
        line_bot_api.reply_message(event.reply_token,message )

        delete_pic(stock)
    if "fitprice v " in message:
        stock = message[11:]
        price =  name(stock)
        dividend =  fit_dividend(stock)
        value =  fit_value(stock)
        w = ["目前股價:","高價位:","合理價位:","低價位:","預期含息報酬率:","預計報酬區間"]
        
        mix_1 = dividend
        mix_1[0] = price
        mix_1[1] = round((dividend[1]*0.2 + value[1]*0.8),2)
        mix_1[2] = round((dividend[2]*0.2 + value[2]*0.8),2)
        mix_1[3] = round((dividend[3]*0.2 + value[3]*0.8),2)
        for x in range(4):
            print(w[x],mix_1[x])

        fpp(stock,mix_1[1],mix_1[2],mix_1[3])
        x = imr(stock)

        remuneration = [0,0,0]
        remuneration[0] = round(((float(price) + mix_1[4] - mix_1[1])/mix_1[1]*100),0)
        remuneration[1] = round(((float(price) + mix_1[4] - mix_1[2])/mix_1[2]*100),1)
        remuneration[2] = round(((float(price) + mix_1[4] - mix_1[3])/mix_1[3]*100),0)

        n = '\n'
        message = TextSendMessage(text='合理價-->以淨值為重\n' + 
            w[0] + str(mix_1[0]) + n +
            w[1] + str(mix_1[1]) + n +
            w[2] + str(mix_1[2]) + n +
            w[3] + str(mix_1[3]) + n +
            w[4] + str(remuneration[1]) + "%" + n +
            w[5] + str(remuneration[0]) + "%~" + str(remuneration[2]) + "%"),ImageSendMessage(
            original_content_url=x,
            preview_image_url=x
            )
        line_bot_api.reply_message(event.reply_token,message )

        delete_pic(stock)

    if "指令" in message:
        message = TextSendMessage(text='功能一:股票 + 空格 + 想查詢的股票代碼\n' + '範例: 股票 2330\n\n' +
          '功能二:K線圖 + 空格 + 想查詢的股票代碼 + & + 開始日期\n' + '範例: K線圖 2330&2022-01-01\n\n' + 
          '功能三:合理價 + 空格 + 想查詢的股票代碼\n' + '範例: 合理價 2330')
        line_bot_api.reply_message(event.reply_token,message )

#截圖股利
def screenshot_dividend(stock):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.set_window_size(515,900)
    stock = str(stock)
    Url = "https://tw.stock.yahoo.com/quote/" + stock + "/dividend"
    driver.get(Url)

    #滾動
    driver.execute_script("window.scrollBy(0, 900);")

    charts = driver.find_element(By.CLASS_NAME,"table-body-wrapper")

    action = ActionChains(driver)
    action.move_to_element(charts).perform()

    Png = stock + ".png"
    driver.get_screenshot_as_file(Png)

    #driver.close()

    img = Image.open(Png)      # 開啟圖片
    img_crop = img.crop((0,100,515,900))        # 裁切圖片
    img_crop.save(Png)

#截圖個股基本資訊
def screenshot_profile(stock):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.set_window_size(1000,1000)
    stock = str(stock)
    Url = "http://www.money-link.com.tw/stxba/index5.asp?id=" + stock
    driver.get(Url)

    #滾動
    driver.execute_script("window.scrollBy(0, 380);")

    Png = stock + ".png"
    driver.get_screenshot_as_file(Png)

    driver.close()

    img = Image.open(Png)      
    img_crop = img.crop((250,160,940,900))        
    img_crop.save(Png)
    
#繪製K線圖
def plot_stcok_k_chart(stock="0050" , start='2020-01-01'):
    picname = str(stock) 
    stock = str(stock)+".TW"
    df = yf.download(stock,start)
    mpf.plot(df, type='candle', mav=(5,20), volume=True, title=stock, savefig=picname + '.png')

#繪製歷史股價
def plot_stcok_chart(stock="0050"):
    picname = str(stock) 
    stock = str(stock)+".TW"
    df = yf.download(stock)
    mpf.plot(df, type='candle', volume=True, title=stock, savefig=picname + '.png')

#上傳至圖庫再抓下來 
def imr(name):
        CLIENT_ID = "b9c0b678cf5cb2c"
        name = str(name)
        PATH =name +".png" 
        title = "Uploaded with PyImgur"

        im = pyimgur.Imgur(CLIENT_ID)
        uploaded_image = im.upload_image(PATH, title=title)
        print(uploaded_image.title)
        print(uploaded_image.link)
        return uploaded_image.link

#刪除圖片
def delete_pic(name):
    fileTest = name + ".png"
    try:
        os.remove(fileTest)
    except OSError as e:
        print(e)
    else:
        print("File is deleted successfully")

#股利法
def fit_dividend(stock):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    stock = str(stock)
    Url = "https://goodinfo.tw/tw/StockDividendPolicy.asp?STOCK_ID=" + stock + "&SHOW_ROTC="
    driver.get(Url)
    
    

    time.sleep(0.5)
    #driver.find_element(By.XPATH, '//tbody/tr[1]/td[3]/nobr[1]/select[1]').click()
    #time.sleep(2)
    #driver.find_element(By.XPATH, '/html[1]/body[1]/table[2]/tbody[1]/tr[1]/td[3]/div[1]/table[1]/tbody[1]/tr[1]/td[1]/table[1]/tbody[1]/tr[1]/td[3]/nobr[1]/select[1]/option[5]').click()
    #time.sleep(2)
    try:
        print("<股利法>")
        x = driver.find_element(By.XPATH, '//body[1]/table[2]/tbody[1]/tr[1]/td[3]/div[1]/div[1]/div[1]/table[1]/tbody[1]/tr[6]/td[2]')
        print("股利發放近5年平均:" + x.text)
        price = float(x.text)

        time.sleep(1)

        print("高價位:",(price*32))
        print("合理價位:",(price*20))
        print("低價位:",(price*16))
        print("近三年平均股利:",(price))
        print()

    except:
        print("發生錯誤-->可能原因為此股票無發放股利")
        ans = [0,0,0,0,0]
        return ans

    driver.quit
    
    ans = [x.text,(price*32),(price*20),(price*16),(price)]

    return ans

#淨值比法
def fit_value(stock):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    stock = str(stock)
    Url = "https://goodinfo.tw/tw/StockBzPerformance.asp?STOCK_ID=" + stock
    driver.get(Url)

    time.sleep(1)
    
    try:
        print("<本淨比法>")
        y_value = driver.find_element(By.XPATH, '/html[1]/body[1]/table[2]/tbody[1]/tr[1]/td[3]/div[1]/div[1]/div[1]/table[1]/tbody[1]/tr[5]/td[1]/nobr[2]')
        print("最新淨值:" + y_value.text)
        price = float(y_value.text[:y_value.text.find(' ')])

        h_rate = driver.find_element(By.XPATH, '/html[1]/body[1]/table[2]/tbody[1]/tr[1]/td[3]/div[1]/div[1]/div[1]/table[1]/tbody[1]/tr[8]/td[15]')
        h_rate = float(h_rate.text)
        time.sleep(1)
        m_rate = driver.find_element(By.XPATH, '/html[1]/body[1]/table[2]/tbody[1]/tr[1]/td[3]/div[1]/div[1]/div[1]/table[1]/tbody[1]/tr[8]/td[13]')
        m_rate = float(m_rate.text)
        time.sleep(1)
        l_rate = driver.find_element(By.XPATH, '/html[1]/body[1]/table[2]/tbody[1]/tr[1]/td[3]/div[1]/div[1]/div[1]/table[1]/tbody[1]/tr[8]/td[14]')
        l_rate = float(l_rate.text)
        time.sleep(1)
    
        print("淨值比(高到低):" , h_rate , m_rate , l_rate)
        print("高價位:",round((price*h_rate), 2))
        print("合理價位:",round((price*m_rate), 2))
        print("低價位:",round((price*l_rate), 2))  

    except:
        print("發生錯誤-->可能原因為此股票為ETF")
        ans = [0,0,0,0]
        return ans
    
    ans = [y_value.text,round((price*h_rate), 2),round((price*m_rate), 2),round((price*l_rate), 2)]
    driver.quit
    return ans

#股票名稱及及時股價
def name(stock):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    stock = str(stock)
    Url = "https://goodinfo.tw/tw/BasicInfo.asp?STOCK_ID=" + stock
    driver.get(Url)

    time.sleep(1)

    n = driver.find_element(By.XPATH, '/html[1]/body[1]/table[2]/tbody[1]/tr[1]/td[3]/table[1]/tbody[1]/tr[1]/td[1]/table[1]/tbody[1]/tr[1]/th[1]/table[1]/tbody[1]/tr[1]/td[1]/nobr[1]')
    print(n.text)
    time.sleep(1)
    price =  driver.find_element(By.XPATH, '/html[1]/body[1]/table[2]/tbody[1]/tr[1]/td[3]/table[1]/tbody[1]/tr[1]/td[1]/table[1]/tbody[1]/tr[3]/td[1]')
    print("目前股價:" , price.text)
    time.sleep(1)
    driver.quit

    return price.text

#歷史股價配上合理價
def fpp(stock,hp,mp,lp):
    df = yf.download( stock + '.tw' , start = '2020-06-01')
    mpf.plot(df,hlines=dict(hlines=[hp,mp,lp],colors=['r','g','b'],linestyle='--'),savefig=stock + '.png',type='candle')

if __name__ == "__main__":
    app.run()