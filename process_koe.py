import os
import shutil
import subprocess
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --- 設定 ---
# スクレイピング対象のURL
PAGE_URL = "https://ia601002.us.archive.org/view_archive.php?archive=/25/items/sayonara-wo-oshiete-2001-CDROM/%E3%81%95%E3%82%88%E3%81%AA%E3%82%89%E3%82%92%E6%95%99%E3%81%88%E3%81%A6%EF%BD%9Ecomment%20te%20dire%20adieu%EF%BD%9E%20%282001%20CD-ROM%20ver.%29.zip"
# ダウンロード先のベースURL
DOWNLOAD_BASE_URL = "https://archive.org"

# 一時作業ディレクトリ
KOE_DIR = "koe_files"
WAV_DIR = "wav_files"
# 実行ファイルがWAVを出力すると推測されるディレクトリ
EXTRACT_DIR = "koewav" 
# 実行ファイル名
UNPACKER_EXE = "koeunpac.exe"

# --- 1. ディレクトリの準備 ---
print(f"Creating directories: {KOE_DIR}, {WAV_DIR}")
os.makedirs(KOE_DIR, exist_ok=True)
os.makedirs(WAV_DIR, exist_ok=True)
# 実行ファイルが出力するディレクトリをクリーンアップ
if os.path.exists(EXTRACT_DIR):
    shutil.rmtree(EXTRACT_DIR)

# --- 2. .KOEファイルのスクレイピングとダウンロード ---
print(f"Scraping {PAGE_URL} for .KOE files...")
try:
    response = requests.get(PAGE_URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    koe_links = []
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and href.upper().endswith('.KOE'):
            # 相対URLを絶対URLに変換
            full_url = urljoin(DOWNLOAD_BASE_URL, href)
            koe_links.append(full_url)

    if not koe_links:
        print("No .KOE files found on the page.")
        exit(0) # エラーではなく正常終了

    print(f"Found {len(koe_links)} .KOE files. Downloading...")

    for url in koe_links:
        filename = url.split('/')[-1]
        filepath = os.path.join(KOE_DIR, filename)
        
        print(f"Downloading {url} -> {filepath}")
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

except requests.RequestException as e:
    print(f"Error during scraping or downloading: {e}")
    exit(1)

# --- 3. .KOEファイルから.WAVへの変換 (★エラー修正箇所) ---
print(f"Running {UNPACKER_EXE} on directory {KOE_DIR}...")
try:
    # 修正点:
    # 1. shell=True を削除し、Pythonにプロセス起動を直接管理させます。
    # 2. 実行ファイル名と引数をリスト形式 [UNPACKER_EXE, KOE_DIR] で渡します。
    #    (UNPACKER_EXE は "koeunpac.exe" という文字列です)
    
    print(f"Executing: {UNPACKER_EXE} {KOE_DIR}")
    
    # Pythonが "koeunpac.exe" をカレントディレクトリから探し、
    # "koe_files" を引数として実行します。
    subprocess.run([UNPACKER_EXE, KOE_DIR], check=True) 

except subprocess.CalledProcessError as e:
    # 実行ファイルがエラー(0以外)を返した場合
    print(f"Error running {UNPACKER_EXE}: {e}")
    print(f"Return code: {e.returncode}")
    # stdout/stderrはキャプチャ指定していない場合 None になりますが、念のため
    print(f"Stdout (if any): {e.stdout}") 
    print(f"Stderr (if any): {e.stderr}")
    exit(1)
except FileNotFoundError:
    # "koeunpac.exe" が見つからなかった場合
    print(f"Error: {UNPACKER_EXE} not found in repository root.")
    print("Please ensure koeunpac.exe is in the root directory.")
    exit(1)
except Exception as e:
    # その他の予期せぬエラー
    print(f"An unexpected error occurred during subprocess execution: {e}")
    exit(1)

# --- 4. .WAVファイルの移動 ---
print(f"Moving extracted files from {EXTRACT_DIR} to {WAV_DIR}...")
if not os.path.exists(EXTRACT_DIR):
    print(f"Error: Expected output directory '{EXTRACT_DIR}' not found.")
    print("The unpacker might have failed or extracts to a different location.")
    exit(1)

wav_files_found = 0
for filename in os.listdir(EXTRACT_DIR):
    if filename.upper().endswith('.WAV'):
        src_path = os.path.join(EXTRACT_DIR, filename)
        dest_path = os.path.join(WAV_DIR, filename)
        shutil.move(src_path, dest_path)
        wav_files_found += 1

if wav_files_found == 0:
    print(f"Warning: No .WAV files were found in {EXTRACT_DIR}.")
else:
    print(f"Successfully moved {wav_files_found} .WAV files.")

print("Process complete.")
