# 概要
以下のサイトで公開されている無料の漫画をPDF化します。

## 対応サイト
- https://mangakoma.org
- https://mangakoma01.net
- https://mangakoma.onl/manga

## 使用方法

```shell-session
$ python raw_downloader.py https://mangakoma.org/{漫画のURL}
```

{漫画のURL} に与えるURLは漫画の中のどの話数でも構いません。話数選択のセレクトボックスから自動で1話から全話数のURLを取得し、1話に対して1ファイルを作成します。

### usage:

`raw_downloader.py [-h] [-v] [-o OUTPUT] [-s SKIP] [-d DRIVER] url`

https://mangakoma.org/ などの漫画をPDFとしてダウンロードします。

### positional arguments:
  url                   取得元URL。話数はどの話数からでも良い。話数セレクトボックスから得られるすべての話数を1話から順に取得する。

### options:

```
-h, --help            show this help message and exit
-v, --version         show program's version number and exit
-o OUTPUT, --output OUTPUT
                    出力先ディレクトリ。(default: カレントディレクトリ)
-s SKIP, --skip SKIP  スキップする話数。例として、5を指定すると6話からダウンロードする。(default: 0)
-d DRIVER, --driver DRIVER
                    chrome driver path(default: /usr/bin/chromedriver)
```

## インストール

### `raw_downloader.py`のインストール

githubからクローンして、requirements.txtにあるPythonモジュールをインストールします。

```
$ git clone https://github.com/u1and0/raw_downloader.git
$ pip install -r requirements.txt
```

### Chrome driverのインストール
ヘッドレスブラウザを使ってJavaScriptを操作する必要がある[^1]ので、ChromeDriverのインストールが必須です。

[^1]: これらのページは画像の読み込みなどにJavaScriptを使う仕組みのようです。そのため、ヘッドレスブラウザを使って実際のページを開くときのように模擬しないと画像の読み込みや話数の取得に失敗します。

OS毎の方法でchrome driverをインストールします。

また、インストール前にインストールするchrome driverのバージョンを確認してください。

[https://googlechromelabs.github.io/chrome-for-testing/](https://googlechromelabs.github.io/chrome-for-testing/)

#### wgetで取得する場合

```
$ wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/120.0.6099.71/linux64/chromedriver-linux64.zip
$ unzip chromedriver-linux64.zip
$ chmod 755 chromedriver-linux64
$ sudo mv chromedriver-linux64 /usr/local/bin/
$ rm chromedriver-linux64.zip
```

#### Archlinuxの場合

```shell-session
$ yay -Sy chromedriver
$ conda install -yc conda-forge selenium
$ yay -S google-chrome
```


## エラー


### エラー内容

```
selenium.common.exceptions.WebDriverException: Message: unknown error: session delet
ed because of page crash
from unknown error: cannot determine loading status
from tab crashed
  (Session info: chrome-headless-shell=127.0.6533.99)
Stacktrace:
#0 0x5b53a3b016aa <unknown>
#1 0x5b53a37d2441 <unknown>
```

### 解決法
時間を置いてやり直してください。
複数回失敗するようでしたら、/tmpのchromium関連のディレクトリを削除してください。

```
$ rm -rf /tmp/.org.chromium.Chromium.*
```
