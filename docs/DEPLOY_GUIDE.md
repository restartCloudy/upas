# UPAS GitHub Pages 部署指南

## 📋 前置条件

1. GitHub账号
2. 服务器（用于提供API数据）
3. 基本的Git操作知识

## 🚀 部署步骤

### 第一步：创建GitHub仓库

1. 登录GitHub，点击右上角 **+** → **New repository**
2. 仓库名称填写 `upas`
3. 选择 **Public**（GitHub Pages免费版需要公开仓库）
4. 点击 **Create repository**

### 第二步：推送代码到GitHub

在你的服务器上执行：

```bash
cd /root/.openclaw/workspace/upas

# 初始化Git仓库
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: UPAS v1.0"

# 添加远程仓库（替换为你的用户名）
git remote add origin https://github.com/你的用户名/upas.git

# 推送代码
git branch -M main
git push -u origin main
```

### 第三步：启用GitHub Pages

1. 打开你的GitHub仓库页面
2. 点击 **Settings** → **Pages**
3. **Source** 选择 **GitHub Actions**
4. 等待部署完成（约1-2分钟）
5. 访问 `https://你的用户名.github.io/upas/`

### 第四步：启动API服务器

在你的服务器上启动数据接口：

```bash
cd /root/.openclaw/workspace/upas

# 后台启动API服务器
nohup python3 tools/api_server.py --port 8080 > api_server.log 2>&1 &

# 查看日志
tail -f api_server.log
```

### 第五步：配置防火墙（如果需要）

确保服务器防火墙允许8080端口：

```bash
# Ubuntu/Debian
sudo ufw allow 8080

# CentOS
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

## 🌐 访问方式

### 1. GitHub Pages（前端）
```
https://你的用户名.github.io/upas/
```

### 2. 你的服务器（API）
```
http://你的服务器IP:8080/api/patterns
http://你的服务器IP:8080/api/expectancy
http://你的服务器IP:8080/api/status
```

## 📱 使用GitHub Pages查看数据

1. 打开 `https://你的用户名.github.io/upas/`
2. 在"服务器配置"区域输入你的服务器地址：
   ```
   http://你的服务器IP:8080
   ```
3. 点击"连接服务器"
4. 数据将从你的服务器实时加载到前端界面

## 🔧 故障排查

### GitHub Pages 404
- 确认仓库是Public
- 确认Settings → Pages中选择了GitHub Actions
- 等待Actions工作流完成（查看Actions标签页）

### 无法连接服务器
- 确认API服务器已启动：`ps aux | grep api_server`
- 确认端口开放：`netstat -tlnp | grep 8080`
- 确认防火墙允许：`sudo ufw status`
- 确认服务器IP正确

### CORS错误
- API服务器已配置CORS支持，无需额外设置
- 如果仍有问题，检查浏览器控制台错误信息

## 📝 更新数据

当UPAS系统发现新形态后，GitHub Pages会自动显示最新数据：

1. 在服务器运行UPAS发现新形态
2. API服务器会自动读取最新数据
3. 刷新GitHub Pages页面即可看到更新

## 🔄 自动部署

每次推送代码到main分支，GitHub Actions会自动重新部署：

```bash
git add .
git commit -m "更新说明"
git push origin main
```

部署状态可以在仓库的 **Actions** 标签页查看。

## 📞 支持

如有问题，请提交Issue到GitHub仓库。

---

**注意**: GitHub Pages只托管前端静态页面，数据需要通过你的服务器API提供。