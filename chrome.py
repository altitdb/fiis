import os
import re
import shutil
import zipfile
import requests
import subprocess
from winreg import ConnectRegistry, HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE, OpenKey, QueryValueEx

# Configurações (Mantendo seu diretório 'webdriver')
DRIVER_DIR = "webdriver"
DRIVER_PATH = os.path.join(DRIVER_DIR, "chromedriver.exe")
TEMP_ZIP = "chromedriver.zip"

def get_chrome_version():
    """Obtém a versão do Chrome instalado no Windows via Registro."""
    paths = [
        (HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon"),
        (HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Google\Update\Clients\{8A69D345-D564-463c-AFF1-A69D9E530F96}"),
        (HKEY_LOCAL_MACHINE, r"SOFTWARE\Google\Update\Clients\{8A69D345-D564-463c-AFF1-A69D9E530F96}")
    ]
    for root, path in paths:
        try:
            registry = ConnectRegistry(None, root)
            key = OpenKey(registry, path)
            version, _ = QueryValueEx(key, "version" if "BLBeacon" in path else "pv")
            return version
        except Exception:
            continue
    return None

def get_current_chromedriver_version():
    """Obtém a versão do chromedriver.exe atual na pasta."""
    if not os.path.exists(DRIVER_PATH):
        return None
    try:
        output = subprocess.check_output([DRIVER_PATH, "--version"], stderr=subprocess.STDOUT).decode("utf-8")
        version = re.search(r"chromedriver\s+([\d.]+)", output.lower()).group(1)
        return version
    except Exception:
        return None

def get_latest_chromedriver_url(chrome_version):
    """Busca a URL de download para o Major específico usando a API de Milestones."""
    major_version = chrome_version.split('.')[0] if chrome_version else None
    
    # API que contém a última versão de cada "Milestone" (Major)
    api_url = "https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone-with-downloads.json"
    
    try:
        response = requests.get(api_url)
        data = response.json()
        milestones = data.get("milestones", {})
        
        if major_version and major_version in milestones:
            v_data = milestones[major_version]
            downloads = v_data.get("downloads", {}).get("chromedriver", [])
            for dl in downloads:
                if dl.get("platform") == "win64":
                    return dl.get("url"), v_data.get("version")
        
        # Se não encontrar o Milestone específico, tenta a Stable Global como último recurso
        print(f"Aviso: Milestone {major_version} não encontrado. Buscando última estável global...")
        fallback_url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
        res_fallback = requests.get(fallback_url)
        stable_data = res_fallback.json().get("channels", {}).get("Stable", {})
        downloads = stable_data.get("downloads", {}).get("chromedriver", [])
        for dl in downloads:
            if dl.get("platform") == "win64":
                return dl.get("url"), stable_data.get("version")
                
    except Exception as e:
        print(f"Erro ao consultar API: {e}")
    
    return None, None

def update_chromedriver():
    if not os.path.exists(DRIVER_DIR):
        os.makedirs(DRIVER_DIR)

    chrome_v = get_chrome_version()
    current_v = get_current_chromedriver_version()
    
    chrome_major = chrome_v.split('.')[0] if chrome_v else None
    current_major = current_v.split('.')[0] if current_v else None

    print(f"Chrome Instalado: {chrome_v or 'Não detectado'} (Major: {chrome_major})")
    print(f"Driver Local: {current_v or 'NÃO ENCONTRADO'} (Major: {current_major})")

    # Atualiza se: Driver não existe OU Major do Driver é diferente do Major do Chrome
    if current_major != chrome_major or current_v is None:
        print(f"Buscando a versão mais recente disponível para o Major {chrome_major}...")
        
        latest_url, latest_v = get_latest_chromedriver_url(chrome_v)
        if not latest_v:
            print("ERRO: Não foi possível obter dados da API.")
            return

        print(f"Versão encontrada para download: {latest_v}")
        try:
            res = requests.get(latest_url)
            with open(TEMP_ZIP, "wb") as f:
                f.write(res.content)

            with zipfile.ZipFile(TEMP_ZIP, "r") as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith("chromedriver.exe"):
                        with zip_ref.open(file) as source, open(DRIVER_PATH, "wb") as target:
                            shutil.copyfileobj(source, target)
            
            print(f">>> ChromeDriver atualizado/instalado com sucesso (Versão {latest_v})!")
        except Exception as e:
            print(f"ERRO durante download/extração: {e}")
        finally:
            if os.path.exists(TEMP_ZIP):
                os.remove(TEMP_ZIP)
    else:
        print(f"O ChromeDriver existente (Major {current_major}) já atende ao Chrome (Major {chrome_major}).")

if __name__ == "__main__":
    update_chromedriver()
