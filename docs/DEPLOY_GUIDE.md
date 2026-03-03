# 项目打包与部署指南 (Mac Mini M2 - 本机部署)

本文档将指导你如何在同一台 Mac Mini M2 上完成项目的打包、安装与部署，并最终通过域名绑定微信公众号。

由于开发环境与部署环境为同一台机器，我们可以省去文件传输步骤，但为了保证服务稳定，建议采用**环境隔离**的方式进行部署。

## 1. 打包项目 (Packaging)

首先生成项目的发布包 (Wheel)，这可以确保部署的是一个干净、版本固定的快照。

### 前置要求
确保系统已安装 Python 3。如果 `pip` 命令不可用，推荐使用 Homebrew 安装 Python：
```bash
brew install python
```
*注：Homebrew 安装的 Python 会自带 `pip`，通常可以通过 `python3 -m pip` 调用。*

确保安装了 `build` 工具：
```bash
python3 -m pip install build
```

### 执行打包
在项目根目录下运行：
```bash
5
```
执行完成后，`dist/` 目录下会生成：
- `game_claim_helper-1.0.0-py3-none-any.whl` (Wheel包)
- `game_claim_helper-1.0.0.tar.gz` (源码包)

---

## 2. 环境准备

如果你的开发机已经安装了 Redis 和 MySQL，可跳过此步。

### 安装基础服务
推荐使用 Homebrew 安装：
```bash
# 安装 Redis
brew install redis
brew services start redis

# 安装 MySQL (或者使用 Docker)
brew install mysql
brew services start mysql
```

### 创建数据库
确保数据库已创建：
```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS game_claim_helper CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

---

## 3. 部署安装

建议在单独的目录下运行生产服务，避免与开发目录混淆。

### 创建部署目录与虚拟环境
```bash
# 创建部署目录
mkdir -p ~/deploy/game_claim_helper
cd ~/deploy/game_claim_helper

# 创建生产环境专用的虚拟环境
python3 -m venv venv
source venv/bin/activate

# 激活后，你的命令行前缀应显示 (venv)
# 此时可以直接使用 pip (它指向虚拟环境内的pip)
# 如果仍然报错，请继续使用 python3 -m pip
```

### 安装项目
直接安装刚才打包生成的 `.whl` 文件（请将路径替换为你实际的开发目录路径）：
```bash
# 假设开发目录在 ~/codeRepository/game_claim_helper
python3 -m pip install --force-reinstall ~/codeRepository/game_claim_helper/dist/game_claim_helper-1.0.0-py3-none-any.whl

# 安装生产服务器
python3 -m pip install "uvicorn[standard]" gunicorn
```

### 准备配置文件
1. **环境变量文件**: 将开发目录的 `.env` 复制过来，或新建一个：
   ```bash
   cp ~/codeRepository/game_claim_helper/.env ~/deploy/game_claim_helper/.env
   ```
   *注意检查 `.env` 中的配置是否适用于生产环境（如关闭调试模式）。*

2. **Gunicorn 配置文件**: 复制 Gunicorn 配置：
   ```bash
   cp ~/codeRepository/game_claim_helper/gunicorn_conf.py ~/deploy/game_claim_helper/
   ```

---

## 4. 启动服务 (Gunicorn + Uvicorn)

### 手动测试启动
在部署目录下 (`~/deploy/game_claim_helper`) 运行：
```bash
# main:app 指的是 main.py 中的 app 对象
# 注意：安装 wheel 后，main 模块可能不在当前目录，需要确保 gunicorn 能找到它
# 如果是通过 wheel 安装的，通常可以直接引用包名，或者确保 main.py 被正确打包
# 本项目中 main.py 在根目录，可能需要调整调用方式或直接指定 pythonpath
```
*修正说明*：由于 `main.py` 在项目根目录，标准打包可能不会将其作为顶层模块安装到 site-packages 中（除非在 setup.py 中特别配置）。
**更简单的做法**：直接将 `main.py` 复制到部署目录，或者在 `gunicorn` 命令中指定 `PYTHONPATH`。

**推荐方式**：直接运行安装后的包（如果 `setup.py` 配置了 entry_points）或：
```bash
# 将 main.py 也复制到部署目录
cp ~/codeRepository/game_claim_helper/main.py ~/deploy/game_claim_helper/

# 启动
gunicorn -c gunicorn_conf.py main:app
```

### 设置开机自启 (Launchd)
创建一个 plist 文件 `~/Library/LaunchAgents/com.gameclaim.helper.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gameclaim.helper</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USER_NAME/deploy/game_claim_helper/venv/bin/gunicorn</string>
        <string>-c</string>
        <string>/Users/YOUR_USER_NAME/deploy/game_claim_helper/gunicorn_conf.py</string>
        <string>main:app</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USER_NAME/deploy/game_claim_helper</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/game_claim.out</string>
    <key>StandardErrorPath</key>
    <string>/tmp/game_claim.err</string>
</dict>
</plist>
```
*请将 `YOUR_USER_NAME` 替换为你的实际用户名 (chen)。*

加载并启动：
```bash
launchctl load ~/Library/LaunchAgents/com.gameclaim.helper.plist
launchctl start com.gameclaim.helper
```

---

## 5. 域名绑定与 Nginx 反向代理

为了让微信服务器能访问到你的本地服务，你需要一个公网域名 (`yxbot.online`) 并解析到你的 Mac Mini。

### 5.1 网络环境准备 (公网访问)
如果你的 Mac Mini 位于家庭网络（非云服务器），要实现外网访问，通常需要以下步骤：

1.  **获取公网 IP**: 确保你的光猫处于“桥接模式”，并由路由器进行拨号，且运营商分配给你的是公网 IPv4 地址。
2.  **DDNS (动态域名解析)**: 因为家用宽带的公网 IP 经常变动，你需要配置 DDNS。
    *   推荐在路由器后台配置 DDNS（如使用花生壳、DNSPod、阿里云等服务），将域名 `yxbot.online` 动态解析到你家里的公网 IP。
3.  **端口映射 (Port Forwarding)**:
    *   在路由器后台找到“端口转发”或“虚拟服务器”设置。
    *   将外部端口（建议 80 或 443，但家用宽带通常封锁了 80/443/8080，你可能需要使用非常规端口，如 8000-9000）映射到 Mac Mini 的内网 IP 和 Nginx 端口（例如 80）。
    *   **注意**: 微信公众号服务器配置**只支持 80 和 443 端口**。如果你的宽带无法使用 80/443，你可能需要使用**内网穿透工具**（如 frp, ngrok, cpolar）来获得一个可用的 80/443 访问入口。

### 5.2 安装 Nginx
```bash
brew install nginx
```

### 5.3 配置 Nginx (可选)
如果直接运行在 80 端口，则不需要 Nginx 反向代理。但如果需要 HTTPS 或其他高级功能，可以使用 Nginx。

如果使用 Nginx，请确保 Nginx 监听 80/443，并将流量转发到应用的端口（注意：应用现在配置为监听 80，如果与 Nginx 冲突，请修改应用端口或 Nginx 配置）。

**推荐方式**：直接使用 root 权限运行应用监听 80 端口（无需 Nginx）：
```bash
sudo python3 -m uvicorn main:app --host 0.0.0.0 --port 80
```

### 5.4 验证外网访问
在手机上关闭 Wi-Fi，使用 4G/5G 网络访问 `http://yxbot.online/health` (如果你成功解决了 80 端口问题)。如果返回 `{"status": "healthy"}` 说明外网访问配置成功。

---

## 6. 微信公众号对接配置

1. 登录 [微信公众平台](https://mp.weixin.qq.com)。
2. 进入 **设置与开发** -> **基本配置** -> **服务器配置**。
3. 填写信息：
   - **URL**: `http://yxbot.online/wechat/callback` (注意：必须是 80 或 443 端口，不支持带端口号的 URL)
   - **Token**: 必须与 `.env` 中的 `WECHAT_OFFICIAL_TOKEN` 一致。
   - **EncodingAESKey**: 必须与 `.env` 中的 `WECHAT_OFFICIAL_AES_KEY` 一致。
4. 提交验证并启用。

此时，你的 Mac Mini 即作为服务器运行着该服务。
