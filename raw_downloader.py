#!/usr/bin/env python3
"""
Usage:
$ python raw_downloader.py

スキップする話数、出力ディレクトリを調整する。

Install:
$ yay -Sy chromedriver
$ conda install -yc conda-forge selenium
$ yay -S google-chrome

chromiumをインストールしたが、うまくいかなかった。
オプションやサービスの指定の仕方がわからなかった
"""

import os
import time
from typing import Optional
import tempfile
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from PIL import Image


def find_jpg_source(soup: BeautifulSoup) -> list[str]:
    """ jpgで終わるhref属性を持つaタグを検索 """
    # jpg_links = soup.find_all("a", href=re.compile(r"\.jpg$"))
    jpg_links = soup.select("div.separator a")
    return [a["href"] for a in jpg_links]


def fetch_image(url: str, save_dir: str) -> Optional[str]:
    """URLをfetchして画像として保存
    ファイル名を返す
    """
    resp = requests.get(url, timeout=30000)
    if resp.status_code != 200:  # コンテンツがなければ終了
        return None
    filename = os.path.join(save_dir, url.split("/")[-1])
    with open(filename, "wb") as f:
        f.write(resp.content)
    return filename


def download_images(links: list[str]) -> list[str]:
    """渡されたURLリストのコンテンツをカレントディレクトリに保存する"""
    downloaded_imgs = []
    tempdir = tempfile.mkdtemp()
    for link in links:
        img_file = fetch_image(link, tempdir)
        if img_file:  # コンテンツが見つかればファイル名をリストに追加
            downloaded_imgs.append(img_file)
            print(img_file)
    return downloaded_imgs


def images_to_pdf(files: list[str], pdf_filepath: str):
    """jpgファイルのリストを指定されたパスのPDFファイルに保存する"""
    images = [Image.open(img) for img in files]
    images[0].save(pdf_filepath, save_all=True, append_images=images[1:])
    for file in files:
        os.remove(file)


def get_story_urls(content: BeautifulSoup) -> list[str]:
    """optionのリストから全話数のURLを取得する"""
    # nPL_list = content.select("select[name='nPL_list']")[0]
    nPL_list = content.find("select", {"name": "nPL_list"})
    options = nPL_list.select("option")
    return [option["value"] for option in options]


class RawDownloader:

    def __init__(self, chromedriver_path: str = "/usr/bin/chromedriver"):
        self.chromedriver_path = chromedriver_path

    def download(self, url: str, out_dir: str, skip_file_num: int = 0):
        try:
            # out_dir が見つからなければディレクトリ作成
            os.makedirs(out_dir, exist_ok=False)
        except FileExistsError:
            pass  # ディレクトリがすでにあったら何もしない

        skip_file_num *= -1
        print(f"fetch story from {url}...")
        html_content = self._get_content(url)

        # BeautifulSoupオブジェクトを作成
        soup = BeautifulSoup(html_content, "html.parser")
        all_story_urls = get_story_urls(soup)
        print("story urls: ", all_story_urls)

        urls = reversed(all_story_urls) if skip_file_num == 0 else reversed(
            all_story_urls[:skip_file_num])
        for url in urls:  # 古い話から順に取得したいためreversed
            self._fetch_content_create_pdf(url, out_dir)

    def create_driver(self) -> webdriver.Chrome:
        # seleniumで扱うchromeドライバを生成する
        # chromedriver_path が見つからなければ終了
        if not os.path.isfile(self.chromedriver_path):
            raise FileNotFoundError(self.chromedriver_path)
        service = Service(self.chromedriver_path)
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        return webdriver.Chrome(service=service, options=options)

    def _fetch_content_create_pdf(self, url: str, out_dir: str):
        """
        1. URLからHTMLを取得し
        2. 画像のダウンロード
        3. PDFの作成を行う
        """
        # URLからHTMLを取得
        print(f"fetch content from {url}...")
        html_content = self._get_content(url)

        # BeautifulSoupオブジェクトを作成
        soup = BeautifulSoup(html_content, "html.parser")
        jpgs_href = find_jpg_source(soup)
        jpgs_href = jpgs_href[1:-1]  # 最初と最後のページはサムネ？が入るのでカット
        # print("download images: ", jpgs)

        # jpgファイルをカレントディレクトリに保存
        jpg_filepaths = download_images(jpgs_href)
        # print("donwloaded file paths: ", jpg_filepaths)

        # URL末尾の/以降を保存先のPDF名とする
        name = url.rsplit('/', maxsplit=1)[-1]  # URL末尾の名前
        pdf_filename = f"{out_dir}/{name}.pdf"
        images_to_pdf(jpg_filepaths, pdf_filename)

    def _get_content(self, url: str) -> str:
        """ブラウザを使ってJavaScriptで遅延ダウンロードされるページコンテンツを取得"""
        driver = self.create_driver()
        driver.get(url)
        time.sleep(3)  # jsの実行を待つ
        # print(driver.page_source)  # 取得したページを表示
        return driver.page_source


if __name__ == "__main__":
    # SKIPPED = -134  # すでにダウンロード済みで、スキップする話数
    raw = RawDownloader()
    out_dir = "/mnt/e/Users/U1and0/Documents/PDF/呪術廻戦"
    # 全話のURLを取得するためのURL, どの話数でもいい
    url = "https://mangakoma01.net/manga/zhou-shu-hui-zhana004/di1hua"
    raw.download(url, out_dir)
