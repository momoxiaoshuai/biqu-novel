#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import urllib.parse
import sys
import requests
import copy
import os
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from colorama import init, Fore, Style
from tqdm import tqdm

# 初始化colorama
init(autoreset=True)

# 界面样式常量
TITLE_STYLE = Fore.CYAN + Style.BRIGHT
INFO_STYLE = Fore.GREEN
ERROR_STYLE = Fore.RED
INPUT_STYLE = Fore.YELLOW
DIVIDER = "=" * 50

HEADERS = {
    "authority": "www.biqg.cc",
    "accept": "application/json",
    "accept-language": "zh,en;q=0.9,zh-CN;q=0.8",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "x-requested-with": "XMLHttpRequest",
}

BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
DOWNLOAD_PATH = os.path.join(BASE_DIR, "bookstore")

class NovelDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.lock = Lock()
        self.progress_callback = None
        self.total_chapters = 0
        self.current_progress = 0
        self.is_cancelled = False  # 添加取消标志
        
    def cancel_download(self):
        self.is_cancelled = True
        
    def set_progress_callback(self, callback):
        self.progress_callback = callback
        
    def get_hm_cookie(self, url):
        try:
            self.session.get(url=url, timeout=10)
            return self.session
        except requests.RequestException as e:
            print(f"{ERROR_STYLE}获取Cookie失败: {e}")
            return None

    def search(self, key_word):
        new_header = copy.deepcopy(HEADERS)
        new_header["referer"] = urllib.parse.quote(
            f"https://www.biqg.cc/s?q={key_word}", safe="/&=:?"
        )

        hm_url = urllib.parse.quote(
            f"https://www.biqg.cc/user/hm.html?q={key_word}", safe="/&=:?"
        )
        
        if not self.get_hm_cookie(hm_url):
            return []

        params = {"q": key_word}
        try:
            response = self.session.get(
                "https://www.biqg.cc/user/search.html",
                params=params,
                headers=new_header,
                timeout=10,
            )
            return response.json()
        except Exception as e:
            print(f"{ERROR_STYLE}搜索{key_word}时失败: {e}")
            return []

    def download_chapter(self, args):
        if self.is_cancelled:  # 检查是否已取消
            return None, None, None
            
        tag, href, index = args
        title = tag.text.strip()
        url = f"https://www.biqg.cc{href}"
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.is_cancelled:  # 检查是否已取消
                    return None, None, None
                    
                response = self.session.get(url, timeout=10)
                soup = BeautifulSoup(response.content, "html.parser")
                text = soup.find(id="chaptercontent")
                
                if not text:
                    raise ValueError("未找到章节内容")
                
                content = [f"\n\n{title}\n\n"]
                content.extend(f"{i}\n" for i in text.get_text().split("　　")[1:-2])
                
                with self.lock:
                    if self.is_cancelled:  # 检查是否已取消
                        return None, None, None
                    self.current_progress += 1
                    if self.progress_callback:
                        self.progress_callback(self.current_progress, self.total_chapters)
                    else:
                        self.progress_bar.update(1)
                
                return index, title, "".join(content)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"\n下载章节 {title} 失败: {e}")
                    return index, title, f"\n\n{title}\n\n下载失败: {str(e)}\n\n"
                time.sleep(1)

    def download_novel(self, url, novel_name, author):
        self.is_cancelled = False  # 重置取消标志
        if not os.path.exists(DOWNLOAD_PATH):
            os.makedirs(DOWNLOAD_PATH, exist_ok=True)
            
        path_name = f"{novel_name}___{author}"
        result_file_path = os.path.join(DOWNLOAD_PATH, f"{path_name}.txt")

        try:
            print(f"{INFO_STYLE}开始下载《{novel_name}》...")
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, "html.parser")
            chapters = []
            index = 0

            # 收集所有章节
            for tag in soup.select("div[class='listmain'] dl dd a"):
                href = tag["href"]
                if href == "javascript:dd_show()":
                    for hide_tag in soup.select("span[class='dd_hide'] dd a"):
                        chapters.append((hide_tag, hide_tag["href"], index))
                        index += 1
                else:
                    chapters.append((tag, href, index))
                    index += 1

            self.total_chapters = len(chapters)
            self.current_progress = 0

            # 如果没有GUI回调，创建终端进度条
            if not self.progress_callback:
                self.progress_bar = tqdm(total=self.total_chapters, 
                                       desc=f"下载《{novel_name}》", 
                                       unit="章", ncols=80)

            # 并发下载
            chapter_contents = {}
            max_workers = min(20, len(chapters))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_chapter = {
                    executor.submit(self.download_chapter, args): args 
                    for args in chapters
                }
                
                for future in as_completed(future_to_chapter):
                    if self.is_cancelled:
                        executor.shutdown(wait=False)
                        return False
                        
                    index, title, content = future.result()
                    if index is not None:  # 只保存未取消的章节
                        chapter_contents[index] = content

            if self.is_cancelled:
                return False

            # 写入文件
            with open(result_file_path, "w", encoding="utf-8") as f:
                f.write(f"《{novel_name}》\n作者：{author}\n\n")
                for i in range(len(chapter_contents)):
                    f.write(chapter_contents[i])

            # 只在使用终端进度条时关闭它
            if not self.progress_callback and hasattr(self, 'progress_bar'):
                self.progress_bar.close()

            print(f"{INFO_STYLE}《{novel_name}》下载完成！")
            print(f"{INFO_STYLE}保存至: {result_file_path}")
            return True

        except Exception as e:
            print(f"{ERROR_STYLE}下载失败: {e}")
            return False

def display_welcome():
    welcome_text = """
    ══════════════════════════════════════
               笔趣阁小说下载器             
    ══════════════════════════════════════
    """
    print(f"{TITLE_STYLE}{welcome_text}")

def display_menu():
    print(f"{TITLE_STYLE}{DIVIDER}")
    print(f"{INFO_STYLE}操作说明:")
    print(f"{INFO_STYLE}1. 输入小说名称搜索")
    print(f"{INFO_STYLE}2. 直接回车退出程序")
    print(f"{TITLE_STYLE}{DIVIDER}")

def main():
    downloader = NovelDownloader()
    display_welcome()
    
    while True:
        display_menu()
        keyword = input(f"{INPUT_STYLE}请输入笔趣阁小说名: {Style.RESET_ALL}").strip()
        if not keyword:
            print(f"{INFO_STYLE}感谢使用，再见！")
            break

        data_list = downloader.search(keyword)
        if not data_list or data_list == 1:
            print(f"{ERROR_STYLE}未找到相关小说，请重试...")
            continue

        # 显示搜索结果
        print(f"\n{TITLE_STYLE}搜索结果:")
        print(f"{TITLE_STYLE}{DIVIDER}")
        for i, item in enumerate(data_list, 1):
            print(f"{INFO_STYLE}{i}. 《{item['articlename']}》 作者：{item['author']}")
        print(f"{TITLE_STYLE}{DIVIDER}")
        
        while True:
            choice = input(f"{INPUT_STYLE}请选择要下载的小说编号(直接回车返回搜索): {Style.RESET_ALL}").strip()
            if not choice:
                break
                
            try:
                num = int(choice)
                if 1 <= num <= len(data_list):
                    item = data_list[num-1]
                    url = f"https://www.biqg.cc{item['url_list']}"
                    downloader.download_novel(url, item['articlename'], item['author'])
                    break
                else:
                    print(f"{ERROR_STYLE}请输入有效的序号!")
            except ValueError:
                print(f"{ERROR_STYLE}请输入数字!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{INFO_STYLE}程序已终止")
    except Exception as e:
        print(f"\n{ERROR_STYLE}程序出错: {e}")