#!/usr/bin/env python3
"""
Mangakoma downloader

https://mangakoma.org/ または https://mangakoma01.net/ の漫画をPDFとしてダウンロードします。

Usage:
    $ python raw_downloader.py [-h] [-v] [-o OUTPUT] [-s SKIP] [-d DRIVER] url
    $ python raw_downloader.py --output=/path/of/output --skip=5\
    --driver=/usr/bin/chromedriver https://mangakoma.org/manga/title/di-1hua

Options:
    url: 取得元URL。話数はどの話数からでも良い。話数セレクトボックスから得られるすべての話数を1話から順に取得する。
    --output: 出力先ディレクトリ。(default: カレントディレクトリ)
    --skip: スキップする話数。例として、5を指定すると6話からダウンロードする。(default: 0)
    --driver: chrome driver path(default: /usr/bin/chromedriver)

Install:
$ pipenv install -r requirements.txt
$ yay -Sy chromedriver google-chrome
"""

import os
import shutil
import time
from typing import Optional, Union
import tempfile
import argparse
import string
import random
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image, UnidentifiedImageError

VERSION = "v0.3.2"


def fetch_image(url: str, save_dir: str) -> Optional[str]:
    """URLをfetchして画像として保存
    ファイル名を返す
    """
    resp = requests.get(url, timeout=30000)
    if resp.status_code != 200:  # コンテンツがなければ終了
        return None
    # ランダムなファイル名を決める
    letters = string.ascii_letters + string.digits
    filename = "".join(random.choices(letters, k=32))
    # ファイルを保存
    filepath = os.path.join(save_dir, filename)
    with open(filepath, "wb") as f:
        f.write(resp.content)
    return filepath


def download_images(links: list[str], save_dir: str) -> list[str]:
    """渡されたURLリストのコンテンツを一時保管のディレクトリに保存する
    一時保管ディレクトリ上のファイルパスのリストを返す
    """
    downloaded_img_paths = []
    for link in links:
        img_file = fetch_image(link, save_dir)
        if img_file:  # コンテンツが見つかればファイル名をリストに追加
            downloaded_img_paths.append(img_file)
            print(img_file)
    return downloaded_img_paths


def images_to_pdf(files: list[str], pdf_filepath: str):
    """jpgファイルのリストを指定されたパスのPDFファイルに保存する"""
    images = []
    for img in files:
        try:
            image = Image.open(img)
            images.append(image)
        except (IOError, SyntaxError, UnidentifiedImageError) as e:
            print(f"このファイルは画像ファイルではありません {e}")
            continue

    # 画像を一つのPDFファイルに結合
    images[0].save(pdf_filepath, save_all=True, append_images=images[1:])
    for file in files:
        os.remove(file)


class Mangakoma01NetDownloader:

    def __init__(self, chromedriver_path: str = "/usr/bin/chromedriver"):
        """ダウンローダーの初期化
        chromedriverのパスを設定する
        """
        self.chromedriver_path = chromedriver_path
        self.selector = {"name": "nPL_list"}

    def download(self, url: str, out_dir: str, skip_file_num: int = 0):
        """
        1. セレクトボックスから取得先URLをすべて取得する
        2. 1話ずつ_fetch_content_create_pdf()へ渡す
        3. 画像取得してPDF化する
        """
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
        all_story_urls = self._get_story_urls(soup)
        print("story urls: ", all_story_urls)

        urls = reversed(all_story_urls) if skip_file_num == 0 else reversed(
            all_story_urls[:skip_file_num])
        for url in urls:  # 古い話から順に取得したいためreversed
            self._fetch_content_create_pdf(url, out_dir)

    def create_driver(self) -> webdriver.Chrome:
        """seleniumで扱うchromeドライバを生成する"""
        # chromedriver_path が見つからなければ終了
        if not os.path.isfile(self.chromedriver_path):
            raise FileNotFoundError(self.chromedriver_path)
        service = Service(self.chromedriver_path)
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        return webdriver.Chrome(service=service, options=options)

    def _get_story_urls(self, soup: BeautifulSoup) -> list[str]:
        """optionのリストから全話数のURLを取得する"""
        nPL_list = soup.find("select", self.selector)
        options = nPL_list.select("option")
        return [option["value"] for option in options]

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
        jpgs_href = self._find_jpg_source(soup)
        jpgs_href = self._cut(jpgs_href)
        print("download images: ", jpgs_href)

        tempdir = tempfile.mkdtemp()
        try:
            # jpgファイルをカレントディレクトリに保存
            jpg_filepaths = download_images(jpgs_href, tempdir)
            print("donwloaded file paths: ", jpg_filepaths)
            if len(jpg_filepaths) < 1:
                raise ValueError("None of download file")

            # 話数を示すURL
            # https://mangakoma.onl/manga/dan-john-no-naka-no-hito/chapter-38
            # のようなURLの末尾の/以降を保存先のPDF名とする
            name = url.rsplit('/', maxsplit=1)[-1]  # URL末尾の名前
            pdf_filename = f"{out_dir}/{name}.pdf"
            images_to_pdf(jpg_filepaths, pdf_filename)
        finally:
            print(f"save completed {pdf_filename}")
            # ダウンロード後に一時ディレクトリを削除する
            shutil.rmtree(tempdir)

    @classmethod
    def _find_jpg_source(cls, soup: BeautifulSoup) -> list[str]:
        """ jpgで終わるhref属性を持つaタグを検索
        オーバーライドして別のクラスでも使いたいが、
        selfとしてインスタンスを使うことがないのでclassmethodとしている。
        """
        # jpg_links = soup.find_all("a", href=re.compile(r"\.jpg$"))
        jpg_links = soup.select("div.separator a")
        sources = [a["href"] for a in jpg_links]
        return sources

    @classmethod
    def _cut(cls, pages):
        """最初と最後に挿入される場合がある挿絵を削除する"""
        return pages[1:-1]

    def _get_content(self, url: str) -> str:
        """ブラウザを使ってJavaScriptで遅延ダウンロードされるページコンテンツを取得"""
        with self.create_driver() as driver:
            driver.get(url)
            time.sleep(3)  # jsの実行を待つ
            # print(driver.page_source)  # 取得したページを表示
            pages = driver.page_source
        return pages


class MangakomaOrgDownloader(Mangakoma01NetDownloader):

    def __init__(self, chromedriver_path: str = "/usr/bin/chromedriver"):
        super().__init__(chromedriver_path)
        self.selector = {"class": "select-chapter"}

    @classmethod
    def _find_jpg_source(cls, soup: BeautifulSoup) -> list[str]:
        """ jpgで終わるhref属性を持つaタグを検索 """
        jpg_links = soup.select("div.page-chapter")
        # print("jpg_links:", jpg_links)
        sources = [div.find("img")["src"] for div in jpg_links]
        return sources

    @classmethod
    def _cut(cls, pages):
        """最初と最後に挿入される場合がある挿絵を削除する"""
        return pages[1:]


class MangakomaOnlDownloader(MangakomaOrgDownloader):

    def __init__(self, chromedriver_path: str = "/usr/bin/chromedriver"):
        """https://mangakoma.onl/manga からJPGをダウンロードしてPDF化するクラス"""
        super().__init__(chromedriver_path)

    @classmethod
    def _find_jpg_source(cls, soup: BeautifulSoup) -> list[str]:
        """ jpgで終わるhref属性を持つaタグを検索 """
        jpg_links = soup.select("div.page-chapter")
        # print("jpg_links:", jpg_links)
        sources = [div.find("img")["src"] for div in jpg_links]
        return sources

    @classmethod
    def _cut(cls, pages):
        """最初と最後に挿入される場合がある挿絵を削除する"""
        return pages

    def _get_content(self, url: str) -> str:
        """ブラウザを使ってJavaScriptで遅延ダウンロードされるページコンテンツを取得する。
        url一覧を取得するために、select.select-chapterをクリックして、
        モーダルを表示してからページ一覧を取得する。
        """
        selector = "select.select-chapter"
        with self.create_driver() as driver:
            driver.get(url)
            time.sleep(3)  # jsの実行を待つ

            # ページの読み込みを待って、(タイムアウト10秒)
            select_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            # セレクトボックスをクリックして
            select_element.click()
            # ページ一覧URLのモーダルを表示したHTMLを返す
            html = driver.page_source
        return html

    def _get_story_urls(self, soup: BeautifulSoup) -> list[str]:
        """optionのリストから全話数のURLを取得する"""
        options = soup.select("select.select-chapter option")
        if len(options) > 1:
            return [option["value"] for option in options]

        # チャプター選択がモーダルで動的に表示される場合
        # クリックされて表示したchapter listを探す
        chapter_list = soup.find(
            "div",
            {"class": "modal-body chapter-list chapter"},
        )

        if not chapter_list:
            raise ValueError(f"invalid chapter_list : {chapter_list}")
        print("[DEBUG] chapter_list", chapter_list)
        atags = chapter_list.select("a")
        return [a["href"] for a in atags]


def parse() -> argparse.Namespace:
    """コマンドライン引数の解釈"""
    parser = argparse.ArgumentParser(
        description="https://mangakoma.org/ の漫画をPDFとしてダウンロードします。")
    parser.add_argument(
        "url",
        type=str,
        help="取得元URL。話数はどの話数からでも良い。話数セレクトボックスから得られるすべての話数を1話から順に取得する。",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=os.getcwd(),
        help="出力先ディレクトリ。(default: カレントディレクトリ)",
    )
    parser.add_argument(
        "-s",
        "--skip",
        type=int,
        default=0,
        help="スキップする話数。例として、5を指定すると6話からダウンロードする。(default: 0)",
    )
    parser.add_argument(
        "-d",
        "--driver",
        type=str,
        default="/usr/bin/chromedriver",
        help="chrome driver path(default: /usr/bin/chromedriver)",
    )
    return parser.parse_args()


def main():
    # コマンドライン引数の解釈
    args = parse()
    # ダウンローダーの初期化
    raw: Union[MangakomaOrgDownloader, Mangakoma01NetDownloader, None] = None
    if args.url.startswith("https://mangakoma.org/"):
        raw = MangakomaOrgDownloader(args.driver)
    elif args.url.startswith("https://mangakoma01.net/"):
        raw = Mangakoma01NetDownloader(args.driver)
    elif args.url.startswith("https://mangakoma.onl/manga/"):
        raw = MangakomaOnlDownloader(args.driver)
    else:
        raise ValueError(f"Invalid URL {args.url}")
    # PDFのダウンロード
    raw.download(args.url, args.output, args.skip)


if __name__ == "__main__":
    main()
