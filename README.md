
## 更新
- 每个账户只能连接 3 个代理。
- 目前最好的操作方式是创建多个账户。
- 脚本支持多账户操作，只需将 `np_tokens.txt` 文件中的每一行填入一个账户的 token。
- 确保你的账户获得 **Proof of Humanhood** 徽章。
- 在这里注册：[https://app.nodepay.ai/](https://app.nodepay.ai)

![image](https://github.com/user-attachments/assets/6b77e7e9-7fcc-4de0-b026-ca3d1a40146e)

## 获取所需信息

1. 打开链接并登录 [https://app.nodepay.ai/](https://app.nodepay.ai/register?ref=Od15EPpf6UBd5qR)
2. 按 F12 打开控制台（或使用 Ctrl + Shift + i 来检查页面）
3. 在控制台输入 `localStorage.getItem('np_token');`
4. 控制台打印出的文本就是你的 NP_TOKEN，复制并粘贴到 `np_token.txt` 文件中。
5. 将你的代理放入 `proxy.txt` 文件中，例如：`http://username:pass@ip:port`

## 1. 运行代码的步骤
```bash
git clone https://github.com/Horizen5/Nodepay.git
cd Nodepay
```

## 2.创建虚拟环境
windows
```bash
python -m venv env
.\env\Scripts\activate

```
linux
```bash
python3 -m venv venv
cd venv/bin
source activate
cd ../..
```
## 3. 安装依赖
```bash
pip install -r requirements.txt
```
## 4. 运行脚本
```bash
python3 main.py

