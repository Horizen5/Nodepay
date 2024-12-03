# 导入必要的库
import asyncio  # 异步IO库
import cloudscraper  # 用于绕过Cloudflare防护
import time
from loguru import logger  # 日志记录
from concurrent.futures import ThreadPoolExecutor  # 线程池
from curl_cffi import requests  # HTTP请求库
from colorama import Fore, Style  # 控制台颜色输出
from colorama import init as colorama_init
colorama_init(autoreset=True)  # 初始化颜色输出

# 程序横幅
BANNER = f"""
{Fore.CYAN}[+]=========================[+]
{Fore.CYAN}[+]  NODEPAY代理脚本 V2.2   [+]
{Fore.CYAN}[+]    挖矿 & 每日签到      [+]
{Fore.CYAN}[+]=========================[+]
"""

print(BANNER)

# 常量定义
PING_INTERVAL = 60  # Ping间隔时间(秒)
KEEP_ALIVE_INTERVAL = 300  # 保活间隔时间(秒)
DOMAIN_API = {  # API接口地址
    "SESSION": "http://api.nodepay.ai/api/auth/session",
    "PING": ["https://nw.nodepay.org/api/network/ping"]
}

# 连接状态枚举
CONNECTION_STATES = {
    "CONNECTED": 1,      # 已连接
    "DISCONNECTED": 2,   # 已断开
    "NONE_CONNECTION": 3 # 未连接
}

# 保活机制的全局变量
wakeup = None  # 定时器对象
isFirstStart = False  # 是否首次启动
isAlreadyAwake = False  # 是否已经唤醒
firstCall = None  # 首次调用时间
lastCall = None  # 最后调用时间
timer = None  # 计时器

def letsStart():
    """初始化并启动保活机制"""
    global wakeup, isFirstStart, isAlreadyAwake, firstCall, lastCall, timer

    if wakeup is None:
        isFirstStart = True
        isAlreadyAwake = True
        firstCall = time.time()
        lastCall = firstCall
        timer = KEEP_ALIVE_INTERVAL

        wakeup = asyncio.get_event_loop().call_later(timer, keepAlive)
        logger.info(">>> 保活机制已启动")

def keepAlive():
    """执行保活操作的函数"""
    global lastCall, timer, wakeup

    now = time.time()
    lastCall = now
    logger.info(f">>> 执行保活操作,时间: {now:.3f}")

    # 重新调度下一次保活
    wakeup = asyncio.get_event_loop().call_later(timer, keepAlive)

class AccountInfo:
    """账户信息类"""
    def __init__(self, token, proxies):
        self.token = token  # 账户令牌
        self.proxies = proxies  # 代理列表
        self.status_connect = CONNECTION_STATES["NONE_CONNECTION"]  # 连接状态
        self.account_data = {}  # 账户数据
        self.retries = 0  # 重试次数
        self.last_ping_status = 'Waiting...'  # 最后ping状态
        self.browser_id = {  # 浏览器标识信息
            'ping_count': 0,
            'successful_pings': 0,
            'score': 0,
            'start_time': time.time(),
            'last_ping_time': None
        }

    def reset(self):
        """重置账户状态"""
        self.status_connect = CONNECTION_STATES["NONE_CONNECTION"]
        self.account_data = {}
        self.retries = 3

# 创建cloudscraper实例
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

async def load_tokens():
    """从文件加载账户令牌"""
    try:
        with open('tokens.txt', 'r') as file:
            tokens = file.read().splitlines()
        return tokens
    except Exception as e:
        logger.error(f"加载令牌失败: {e}")
        raise SystemExit("由于加载令牌失败而退出")

async def call_api(url, data, account_info, proxy):
    """调用API接口"""
    headers = {
        "Authorization": f"Bearer {account_info.token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://app.nodepay.ai/",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "chrome-extension://lgmpfmgeabnnlemejacfljbmonaomfmm"
    }

    proxy_config = {
        "http": proxy,
        "https": proxy
    }

    try:
        response = scraper.post(url, json=data, headers=headers, proxies=proxy_config, timeout=60)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"API调用失败,令牌:{account_info.token},代理:{proxy}: {e}")
        raise ValueError(f"调用API {url} 失败")

    return response.json()

async def render_profile_info(account_info):
    """获取账户信息"""
    try:
        for proxy in account_info.proxies:
            try:
                response = await call_api(DOMAIN_API["SESSION"], {}, account_info, proxy)
                if response.get("code") == 0:
                    account_info.account_data = response["data"]
                    if account_info.account_data.get("uid"):
                        await start_ping(account_info)
                        return
                else:
                    logger.warning(f"会话失败,令牌:{account_info.token},代理:{proxy}")
            except Exception as e:
                logger.error(f"获取账户信息失败,令牌:{account_info.token},代理:{proxy}: {e}")

        logger.error(f"所有代理均失败,令牌:{account_info.token}")
    except Exception as e:
        logger.error(f"render_profile_info错误,令牌:{account_info.token}: {e}")

async def start_ping(account_info):
    """开始ping操作"""
    try:
        logger.info(f"开始ping,令牌:{account_info.token}")
        while True:
            for proxy in account_info.proxies:
                try:
                    await asyncio.sleep(PING_INTERVAL)
                    await ping(account_info, proxy)
                except Exception as e:
                    logger.error(f"Ping失败,令牌:{account_info.token},代理:{proxy}: {e}")
    except asyncio.CancelledError:
        logger.info(f"Ping任务已取消,令牌:{account_info.token}")
    except Exception as e:
        logger.error(f"start_ping错误,令牌:{account_info.token}: {e}")

async def ping(account_info, proxy):
    """执行ping请求"""
    for url in DOMAIN_API["PING"]:
        try:
            data = {
                "id": account_info.account_data.get("uid"),
                "browser_id": account_info.browser_id,
                "timestamp": int(time.time())
            }
            response = await call_api(url, data, account_info, proxy)
            if response["code"] == 0:
                logger.info(Fore.GREEN + f"Ping成功,令牌:{account_info.token},代理:{proxy}" + Style.RESET_ALL)
                return
        except Exception as e:
            logger.error(f"Ping失败,令牌:{account_info.token},URL:{url},代理:{proxy}: {e}")

def process_account(token, proxies):
    """处理单个账户"""
    account_info = AccountInfo(token, proxies)
    asyncio.run(render_profile_info(account_info))

async def main():
    """主函数"""
    letsStart()  # 启动保活机制
    tokens = await load_tokens()

    # 加载代理列表
    try:
        with open('local_proxies.txt', 'r') as file:
            proxies = file.read().splitlines()
    except Exception as e:
        logger.error(f"加载代理失败: {e}")
        raise SystemExit("由于加载代理失败而退出")

    # 使用线程池并发处理账户
    with ThreadPoolExecutor(max_workers=3000) as executor:
        futures = []
        for token in tokens:
            futures.append(executor.submit(process_account, token, proxies))

        for future in futures:
            future.result()

def dailyclaim():
    """执行每日签到"""
    try:
        with open('tokens.txt', 'r') as file:
            local_data = file.read().splitlines()
            for tokenlist in local_data:
                url = f"https://api.nodepay.org/api/mission/complete-mission?"
                headers = {
                    "Authorization": f"Bearer {tokenlist}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                    "Content-Type": "application/json",
                    "Origin": "https://app.nodepay.ai",
                    "Referer": "https://app.nodepay.ai/"
                }
                
                data = {
                    "mission_id":"1"
                }

                response = requests.post(url, headers=headers, json=data, impersonate="chrome110")
                
                if response.status_code != 200:
                    logger.error(f"请求失败,状态码: {response.status_code}")
                    continue

                logger.debug(f"响应内容: {response.content}")

                try:
                    is_success = response.json().get('success')
                    if is_success == True:
                        logger.info('领取奖励成功!')
                        logger.info(response.json())
                    else:
                        logger.info('奖励已领取或出现错误!')
                except ValueError as e:
                    logger.error(f"解析JSON响应失败: {e}")
    except requests.exceptions.RequestException as e:
        print(f"错误: {e}")

if __name__ == '__main__':
    try:
        dailyclaim()  # 执行每日签到
        asyncio.run(main())  # 运行主程序
    except (KeyboardInterrupt, SystemExit):
        logger.info("程序被用户终止")
