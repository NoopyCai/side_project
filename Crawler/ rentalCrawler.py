import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning
import json
import re
from bs4 import BeautifulSoup
import emoji
import time
import schedule
import datetime

# 關閉 SSL 警告
urllib3.disable_warnings(InsecureRequestWarning)

# LINE Channel Config
# LINE_CHANNEL_ACCESS_TOKEN = "CCCIRx+kcuU2XmwOh8qY/GkEMQiP5IxGnIHoJgQuN8FQ233XbfyYvzsd44Lb++j5Afz56l2KObchrWb0vq753H5dmsv/ABYPxbu2CoaC4qwhbZVM4w7ywdliX3z0wKJ9CwzwKjtZ/mUo1qiuYgw7UgdB04t89/1O/w1cDnyilFU="  # 請替換成您的 Channel Access Token
# LINE_USER_ID = "U8588fb1fa69ed939416fb6235988ec35"  # 請替換成您的 User ID
# LINE_API_URL = "https://api.line.me/v2/bot/message/push"

# Google Chat Webhook
GOOGLE_CHAT_WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAAA0Wr2GQg/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=DbuYawV9tEjOSqix66w-3iPazKvIB3wMFrqs68RUQlw"  # 請替換成您的 Google Chat Webhook URL

# Google Chat Message
def send_message(message):
    """發送訊息到 Google Chat"""
    data = {
        "text": message
    }
    
    try:
        response = requests.post(GOOGLE_CHAT_WEBHOOK_URL, json=data)
        response.raise_for_status()
        print("訊息已成功發送到 Google Chat")
    except Exception as e:
        print(f"發送訊息到 Google Chat 時發生錯誤：{e}")

# LINE Message
'''
def send_line_message(message):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    
    data = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }
    
    try:
        response = requests.post(LINE_API_URL, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        print("訊息已成功發送到 LINE")
    except Exception as e:
        print(f"發送訊息時發生錯誤：{e}")
'''

def parse_update_time(update_info):
    """解析更新時間，返回分鐘數"""
    if "分鐘內更新" in update_info:
        minutes_match = re.search(r'(\d+)分鐘內更新', update_info)
        if minutes_match:
            return int(minutes_match.group(1))
    elif "小時內更新" in update_info:
        hours_match = re.search(r'(\d+)小時內更新', update_info)
        if hours_match:
            return int(hours_match.group(1)) * 60
    return None

def extract_price(item):
    """提取價格資訊"""
    try:
        # find price element
        price_div = item.find("div", class_="item-info-price")
        if not price_div:
            price_div = item.find("div", class_="price")  # 備用價格class
            
        if price_div:
            # try to get the full price text
            price_text = price_div.get_text().strip()
            
            # 使用正則表達式提取數字
            # 匹配格式：
            # 1. "XX,XXX" 或 "XX.XXX"
            # 2. "$XX,XXX" 或 "NT$XX,XXX"
            # 3. "XX萬"
            price_patterns = [
                r'(?:NT\$|\$)?([0-9,]+)(?:\s*元)?',  # 一般價格格式
                r'([0-9]+)萬',  # "X萬" 格式
                r'([0-9]+[\.,][0-9]+)萬'  # "X.X萬" 格式
            ]
            
            for pattern in price_patterns:
                match = re.search(pattern, price_text)
                if match:
                    price_str = match.group(1)
                    if '萬' in price_text:
                        # 處理"萬"的情況
                        try:
                            price = float(price_str.replace(',', ''))
                            if '.' in price_str:
                                price = int(price * 10000)  # X.X萬轉換為實際數字
                            else:
                                price = int(price * 10000)  # X萬轉換為實際數字
                            return str(price)
                        except ValueError:
                            continue
                    else:
                        # 一般價格處理
                        try:
                            return price_str.replace(',', '')
                        except ValueError:
                            continue
            
            # 如果上述模式都無法匹配，檢查是否有其他數字
            numbers = re.findall(r'\d+', price_text)
            if numbers:
                return numbers[0]
                
        return "價格未顯示"
    except Exception as e:
        print(f"提取價格時發生錯誤：{e}")
        return "價格未顯示"

def create_line_message(title, price, house_info, update_info, detail_url, image_url=""):
    """創建 LINE 訊息"""
    # 移除重複的更新資訊
    house_info = [info for info in house_info if update_info not in info]
    
    # 加入圖片連結
    image_section = f"🖼️ 圖片：{image_url}\n" if image_url else ""
    
    return (
        f"\n【新房屋上架】\n"
        f"{title}\n"
        # f"💰 租金：{price}元/月\n"
        f"📍 {' | '.join(house_info)}\n"
        f"🕒 {update_info}\n"
        f"{image_section}"
        f"👉 詳細資訊：{detail_url}"
    )

def check_rentals():
    print(f"\n開始無情撈取591 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # target url
    url = "https://rent.591.com.tw/list?region=3&price=0$_15000$"
    
    # Request Headers
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "no-store",
        "Host": "rent.591.com.tw",
        "Cookie": "webp=1; T591_TOKEN=IHYP-kbJL-JjLlZ1yYLXq; _gcl_au=1.1.679501359.1746585024; __loc__=MzQuODAuMTE2Ljg2; T591_TOKEN=aq0shh5b0lh23dguu4ttvmo09k; __lt__cid=3b1f449c-e537-4a1f-8db2-dd0be53a6231; __lt__sid=bd8201cf-c0c22e18; PHPSESSID=n2ifqtf3hgdnovnu6tf5g0bqe0; 591_new_session=eyJpdiI6IjNSam9uWTNaN1hoeURGaGhCNmR3VWc9PSIsInZhbHVlIjoicmlKR1k0K1FKOVNMNEY5TDhiMmk2cFhXWE95UUxSdHZxaS9idWgrSlhXS3pmM0ZMN1hMQXA0NXVhUElYZDZVUUUya08zRDVmNmM2QWcvc2lyVTFMVklxNTVIaTVSMEhUMjZUcCt4b1RiUitNZ2xpdDB3cCtNZmNnMjRBT0ZuN0YiLCJtYWMiOiI4MDQ3YmE5ZTUxOWQ3Mzc2ODI3NWUyN2ZkOTUyZjY5MmMxYjZkMDAwNzVlZGY2NWY5N2UyMjY2NzVmOGZkMzYyIiwidGFnIjoiIn0%3D; __one_id__=01JTM98XQCDA8W4HGT9AMKPYNV; _fbp=fb.2.1746585024960.972964459539734502; rentPreventFraud=0; urlJumpIp=3"
    }
    
    try:
        print("send request...")
        print(f"target url: {url}")
        
        # send request
        response = requests.get(url=url, headers=headers, verify=False)
        response.raise_for_status()
        

        print(f"\nresponse status code: {response.status_code}")
        
        # 檢查是否被導向到登入頁面
        if "login" in response.url.lower() or "登入" in response.text[:200]:
            print("\n警告：被導向到登入頁面，可能需要更新 Cookie")
            return
        
        # parse html
        soup = BeautifulSoup(response.text, "html.parser")
        
        # get all items
        items = soup.find_all("div", class_="item")
        print(f"\nfind {len(items)} house items")
        
        found_count = 0
        
        for item in items:
            try:
                # 照片
                img = item.find("img", class_="common-img").get("data-src", "")
                
                # 標題
                title = item.find("a", class_="link").getText().strip()
                
                # URL
                detailUrl = item.find("a", class_="link").get("href", "")
                if not detailUrl.startswith("https:"):
                    detailUrl = "https:" + detailUrl
                
                # 價格
                price = extract_price(item)
                
                # 標籤資訊
                tags = []
                tag_div = item.find("div", class_="item-info-tag")
                if tag_div:
                    tags = [tag.getText().strip() for tag in tag_div.find_all("span", class_="tag")]
                
                # 房屋資訊
                house_info = []
                info_divs = item.find_all("div", class_="item-info-txt")
                for info_div in info_divs:
                    info_text = info_div.getText().strip()
                    if info_text:
                        house_info.append(info_text)
                
                # 更新時間和瀏覽次數
                update_info = ""
                role_div = item.find("div", class_="role-name")
                if role_div:
                    update_info = role_div.getText().strip()
                    print(f"\n找到房屋：{title}")
                    print(f"更新資訊：{update_info}")
                    
                    # 更新時間
                    minutes = parse_update_time(update_info)
                    if minutes is not None and minutes <= 120:  # 360分鐘
                        print(f"更新時間：{minutes}分鐘前")
                        print("符合2小時內更新條件！")
                        found_count += 1
                        
                        # create message
                        msg = create_line_message(title, price, house_info, update_info, detailUrl, img)
                        # send_line_message(msg)  #LINE
                        send_message(msg)  # Google Chat
                        
                        print("發送：")
                        print(msg)
                        print('-------------')
                
            except Exception as e:
                print(f"處理房屋資訊時發生錯誤：{e}")
                continue
        
        # 顯示總結
        if found_count > 0:
            print(f"\n總共找到並發送了 {found_count} 個符合條件的房源通知")
        else:
            print("\n沒有找到符合條件的新房源")
            
    except requests.exceptions.SSLError as e:
        print(f"SSL 錯誤：{e}")
    except requests.exceptions.ConnectionError as e:
        print(f"連線錯誤：{e}")
    except requests.exceptions.Timeout as e:
        print(f"請求超時：{e}")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP 錯誤：{e}")
    except requests.exceptions.RequestException as e:
        print(f"其他請求錯誤：{e}")
    except Exception as e:
        print(f"未預期的錯誤：{e}")

def main():
    print("啟動無情的爬房機器人...")
    print("每1小時執行一次")
    
    check_rentals()
    
    # 設定定時
    schedule.every(1).hours.do(check_rentals)
    
    # keep running
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()