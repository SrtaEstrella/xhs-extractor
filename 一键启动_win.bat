@echo off
setlocal enabledelayedexpansion
REM 小红书笔记提取工具 - 一键启动脚本（全自动）
REM Windows版本
REM 自动完成：依赖检查 → 登录检查 → 启动Web界面

REM ============================================================================
REM 配置选项（开发者可修改）
REM ============================================================================
REM 是否过滤控制台中的PyTorch相关错误信息
REM true: 过滤（默认，适合普通用户）
REM false: 不过滤（适合开发者调试）
set FILTER_CONSOLE_ERRORS=true
REM ============================================================================

REM 切换到脚本所在目录（确保相对路径正确）
cd /d "%~dp0"

echo ==========================================
echo   小红书笔记提取工具 - 一键启动
echo ==========================================
echo.
echo [提示] 提示: 按 Ctrl+C 可以停止服务
echo.

REM ============================================
REM 步骤1: 检查Python环境
REM ============================================
echo [1/4] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [提示] 未找到Python
    echo.
    echo 检测到系统未安装Python，可以选择：
    echo 1. 自动下载并安装Python（推荐）
    echo 2. 手动安装Python（访问 https://www.python.org/downloads/）
    echo.
    set /p INSTALL_PYTHON="是否自动安装Python？(y/n): "
    
    if /i "%INSTALL_PYTHON%"=="y" (
        echo.
        echo [下载] 正在下载Python安装包...
        echo 这可能需要几分钟，请耐心等待...
        echo.
        
        REM 创建临时目录
        set TEMP_DIR=%TEMP%\xhs_python_install
        if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"
        
        REM 下载Python安装包（最新稳定版）
        REM 使用PowerShell下载
        powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe' -OutFile '%TEMP_DIR%\python-installer.exe'"
        
        if not exist "%TEMP_DIR%\python-installer.exe" (
            echo [错误] Python安装包下载失败
            echo 请手动访问 https://www.python.org/downloads/ 下载安装
            pause
            exit /b 1
        )
        
        echo [安装] 正在安装Python...
        echo 安装过程中请勾选 "Add Python to PATH" 选项
        echo.
        
        REM 静默安装Python（自动添加到PATH）
        "%TEMP_DIR%\python-installer.exe" /quiet InstallAllUsers=1 PrependPath=1
        
        if errorlevel 1 (
            echo [错误] Python安装失败
            echo 请手动运行安装程序: %TEMP_DIR%\python-installer.exe
            pause
            exit /b 1
        )
        
        REM 刷新环境变量
        call refreshenv >nul 2>&1
        
        REM 重新检查Python
        python --version >nul 2>&1
        if errorlevel 1 (
            echo [提示] Python已安装，但需要重新打开终端
            echo 请关闭此窗口，重新运行一键启动脚本
            pause
            exit /b 1
        )
        
        echo [成功] Python安装成功！
        echo.
        
        REM 清理临时文件
        del "%TEMP_DIR%\python-installer.exe" >nul 2>&1
        rmdir "%TEMP_DIR%" >nul 2>&1
    ) else (
        echo.
        echo 请手动安装Python后重新运行此脚本
        echo 访问 https://www.python.org/downloads/ 下载安装
        pause
        exit /b 1
    )
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [成功] Python版本: %PYTHON_VERSION%
echo.

REM ============================================
REM 步骤2: 检查并安装依赖
REM ============================================
echo [2/4] 检查依赖...
set NEED_INSTALL=0

python -c "import playwright" >nul 2>&1
if errorlevel 1 (
    echo    [提示] 未安装 playwright
    set NEED_INSTALL=1
)

python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo    [提示] 未安装 streamlit
    set NEED_INSTALL=1
)

python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo    [提示] 未安装 requests
    set NEED_INSTALL=1
)

if %NEED_INSTALL%==1 (
    echo.
    echo [安装] 正在安装依赖包（这可能需要几分钟）...
    python -m pip install playwright requests beautifulsoup4 streamlit --quiet
    
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
    
    echo [成功] 依赖包安装完成
    echo.
    
    REM 检查Playwright浏览器
    echo [检查] 检查Playwright浏览器...
    python -m playwright install chromium
    
    if errorlevel 1 (
        echo [错误] 浏览器安装失败
        pause
        exit /b 1
    )
    echo [成功] 浏览器已就绪
    echo.
) else (
    echo [成功] 所有依赖已安装
    echo.
)

REM ============================================
REM 步骤3: 检查登录状态
REM ============================================
echo [3/4] 检查登录状态...
if not exist "xhs_extractor_module\browser_data" (
    echo    [提示] 未检测到登录状态
    echo.
    echo [说明] 需要先登录小红书账号：
    echo    1. 浏览器将自动打开小红书登录页面
    echo    2. 请在浏览器中完成登录
    echo    3. 登录成功后，回到终端按回车键
    echo.
    pause
    
    python -m xhs_extractor_module.xhs_login
    
    if errorlevel 1 (
        echo.
        echo [错误] 登录失败，请重试
        pause
        exit /b 1
    )
    
    if not exist "xhs_extractor_module\browser_data" (
        echo.
        echo [错误] 登录未完成，请重试
        pause
        exit /b 1
    )
    
    REM 验证登录状态是否有效
    echo.
    echo [验证] 正在验证登录状态...
    python -m xhs_extractor_module.xhs_login --verify 2>nul
    if errorlevel 1 (
        echo.
        echo [错误] 登录验证失败
        echo    刚才的登录操作可能不成功或者账号信息文件已损坏
        echo.
        echo 请选择：
        echo 1. 重新登录
        echo 2. 退出脚本
        echo.
        set /p RETRY_CHOICE="请选择 (1/2): " < con
        
        if /i "!RETRY_CHOICE!"=="1" (
            echo.
            echo [说明] 正在重新登录...
            echo    1. 浏览器将自动打开小红书登录页面
            echo    2. 请在浏览器中完成登录
            echo    3. 登录成功后，回到终端按回车键
            echo.
            pause
            
            python -m xhs_extractor_module.xhs_login
            
            if errorlevel 1 (
                echo.
                echo [错误] 登录失败，请重试
                pause
                exit /b 1
            )
            
            if not exist "xhs_extractor_module\browser_data" (
                echo.
                echo [错误] 登录未完成，请重试
                pause
                exit /b 1
            )
            
            REM 再次验证登录状态
            echo.
            echo [验证] 正在验证登录状态...
            python -m xhs_extractor_module.xhs_login --verify 2>nul
            if errorlevel 1 (
                echo.
                echo [错误] 登录验证仍然失败，请检查网络连接或稍后重试
                pause
                exit /b 1
            )
            
            echo.
            echo [成功] 登录成功！登录信息已验证有效
            echo.
        ) else (
            echo.
            echo 退出脚本
            pause
            exit /b 1
        )
    ) else (
        echo.
        echo [成功] 登录成功！登录信息已验证有效
        echo.
    )
) else (
    echo    [成功] 检测到已有登录信息，验证中...

    python -m xhs_extractor_module.xhs_login --verify 2>nul
    if errorlevel 1 (
        echo    [提示] 登录状态已过期，需要重新登录
        echo.
        echo    1. 浏览器将自动打开小红书登录页面
        echo    2. 请在浏览器中完成登录
        echo    3. 登录成功后，回到终端按回车键
        echo.
        pause

        python -m xhs_extractor_module.xhs_login

        if errorlevel 1 (
            echo.
            echo [错误] 登录失败，请重试
            pause
            exit /b 1
        )

        echo.
        echo [成功] 登录成功！登录信息已验证有效
        echo.
    ) else (
        echo    [成功] 登录信息已验证有效
        echo.
        echo [启动] 正在启动浏览器和工具界面...
        echo    浏览器将打开两个标签页：小红书 + 工具界面
        echo    按 Ctrl+C 或关闭终端即可退出
        echo.
        echo.
        echo [启动] 正在打开小红书...
        start /b python -m xhs_extractor_module.xhs_login --browse
        echo [启动] 正在启动 Web 界面...
        streamlit run xhs_extractor_module/web_app.py --server.headless true
    )
)