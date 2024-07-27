"""
$ yay -Sy chromedriver
$ conda install -yc conda-forge selenium
$ yay -S google-chrome
chromiumをインストールしたが、うまくいかなかった。
オプションやサービスの指定の仕方がわからなかった
"""

import os
import time
from typing import Optional
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from PIL import Image

CHROMEDRIVER_PATH = "/usr/bin/chromedriver"


def create_driver():
    """seleniumで扱うchromeドライバを生成する"""
    service = Service(CHROMEDRIVER_PATH)
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def get_content(url: str) -> str:
    """ブラウザを使ってJavaScriptで遅延ダウンロードされるページコンテンツを取得"""
    driver = create_driver()
    driver.get(url)
    time.sleep(3)  # jsの実行を待つ
    # print(driver.page_source)  # 取得したページを表示
    return driver.page_source


def find_jpg(soup: BeautifulSoup) -> list[str]:
    """ jpgで終わるhref属性を持つaタグを検索 """
    # jpg_links = soup.find_all("a", href=re.compile(r"\.jpg$"))
    jpg_links = soup.select("div.separator a[href$='jpg']")
    return [a["href"] for a in jpg_links]


def fetch_image(url: str) -> Optional[str]:
    """URLをfetchして画像として保存
    ファイル名を返す
    """
    resp = requests.get(url, timeout=30000)
    if resp.status_code != 200:  # コンテンツがなければ終了
        return None
    cwd = os.getcwd()
    filename = os.path.join(cwd, url.split("/")[-1])
    with open(filename, "wb") as f:
        f.write(resp.content)
    return filename


def download_images(links: list[str]):
    """渡されたURLリストのコンテンツをカレントディレクトリに保存する"""
    downloaded_imgs = []
    for link in links:
        img_file = fetch_image(link)
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


def main():
    # URLからHTMLを取得
    url = "https://mangakoma01.net/manga/tuishino-zi/di52hua"
    print(f"fetch content from {url}...")
    html_content = get_content(url)

    # BeautifulSoupオブジェクトを作成
    soup = BeautifulSoup(html_content, "html.parser")
    jpgs = find_jpg(soup)
    jpgs = jpgs[1:-1]  # 最初と最後のページはサムネ？が入るのでカット
    # print("download images: ", jpgs)

    # jpgファイルをカレントディレクトリに保存
    jpg_filepaths = download_images(jpgs)
    # print("donwloaded file paths: ", jpg_filepaths)

    # URL末尾の/以降を保存先のPDF名とする
    pdf_filename = f"{url.split('/')[-1]}.pdf"
    images_to_pdf(jpg_filepaths, pdf_filename)


if __name__ == "__main__":
    main()
