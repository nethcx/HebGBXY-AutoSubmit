import tkinter as tk
from tkinter import scrolledtext
import requests
from bs4 import BeautifulSoup
import re
import json
import time
from datetime import datetime
import threading

def submit_data():
    SESSION = session_entry.get()
    url = url_entry.get()

    headers = {
        "Cookie": f"SESSION={SESSION}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Referer": "https://www.hebgb.gov.cn/student/class_myClassList.do?type=1&menu=myclass",
    }

    thread = threading.Thread(target=process_requests, args=(SESSION, url, headers))
    thread.start()

def process_requests(SESSION, url, headers):
    try:
        response = requests.get(url, headers=headers)
        response.encoding = "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")

        records = []

        for div in soup.select("div.hoz_course_row"):
            onclick_btn = div.select_one("input.hover_btn")
            if not onclick_btn or "onclick" not in onclick_btn.attrs:
                continue
            match_id = re.search(r"addUrl\((\d+)\)", onclick_btn["onclick"])
            if not match_id:
                continue
            video_id = int(match_id.group(1))

            course_link = div.select_one("a[href*='course_detail.do']")
            match_course = re.search(r"courseId=(\d+)", course_link["href"]) if course_link else None
            if not match_course:
                continue
            course_id = int(match_course.group(1))

            time_span = div.select_one("span:contains('分钟')")
            duration = 1800  # 默认设置为 1800 秒
            if time_span:
                match_time = re.search(r"(\d+)\s*分钟", time_span.text)
                if match_time:
                    duration = int(match_time.group(1)) * 60

            records.append({
                "id": video_id,
                "study_course": course_id,
                "duration": duration
            })

        common_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Cookie": f"SESSION={SESSION}",
        }

        for record in records:
            id_ = record["id"]
            course = record["study_course"]
            duration = record["duration"]
            timestamp = str(int(time.time() * 1000))

            play_url = f"https://www.hebgb.gov.cn/portal/study_play.do?id={id_}"
            play_headers = {
                **common_headers,
                "Referer": "https://www.hebgb.gov.cn/portal/index.do",
            }
            play_resp = requests.get(play_url, headers=play_headers)
            if play_resp.status_code != 200:
                output_text.insert(tk.END, f"[✗] 无法访问课程页面 id={id_}，状态码：{play_resp.status_code}\n")
                output_text.yview(tk.END)
                return

            output_text.insert(tk.END, f"课程页面 id={id_}\n")
            output_text.yview(tk.END)

            manifest_url = f"https://www.hebgb.gov.cn/portal/getManifest.do?id={course}&is_gkk=false&_={timestamp}"
            manifest_headers = {
                **common_headers,
                "Referer": play_url,
                "X-Requested-With": "XMLHttpRequest",
            }
            manifest_resp = requests.get(manifest_url, headers=manifest_headers)
            if manifest_resp.status_code != 200:
                output_text.insert(tk.END, f"[✗] 无法获取资源清单 course={course}，状态码：{manifest_resp.status_code}\n")
                output_text.yview(tk.END)
                return

            output_text.insert(tk.END, f"资源清单 course={course}\n")
            output_text.yview(tk.END)

            # 第三步：提交学习记录
            now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            serialize_sco = {
                "res01": {
                    "lesson_location": duration,
                    "session_time": duration,
                    "last_learn_time": now_time
                },
                "last_study_sco": "res01"
            }
            post_data = {
                "id": str(id_),
                "serializeSco": json.dumps(serialize_sco, separators=(',', ':')),
                "duration": str(duration),
                "study_course": str(course)
            }
            post_headers = {
                **common_headers,
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": play_url,
                "Origin": "https://www.hebgb.gov.cn",
            }
            post_url = "https://www.hebgb.gov.cn/portal/seekNew.do"
            post_resp = requests.post(post_url, headers=post_headers, data=post_data)

            output_text.insert(tk.END, f"提交记录 ID={id_}, 课程={course}，状态码：{post_resp.status_code}\n")
            output_text.insert(tk.END, "返回内容：\n" + post_resp.text + "\n")
            output_text.yview(tk.END)

            # 可选延迟，避免请求过快被封
            time.sleep(0.5)
    except Exception as e:
        output_text.insert(tk.END, f"请求发生异常: {str(e)}\n")
        output_text.yview(tk.END)

root = tk.Tk()
root.title("河北网络干部学院")

session_label = tk.Label(root, text="SESSION")
session_label.pack(pady=5)
session_entry = tk.Entry(root, width=40)
session_entry.pack(pady=5)

url_label = tk.Label(root, text="URL")
url_label.pack(pady=5)
url_entry = tk.Entry(root, width=40)
url_entry.pack(pady=5)

submit_button = tk.Button(root, text="提交", command=submit_data)
submit_button.pack(pady=20)

output_text = scrolledtext.ScrolledText(root, width=80, height=20)
output_text.pack(padx=10, pady=10)

root.mainloop()
