#!/bin/bash

# 小红书笔记提取工具 - 一键启动脚本（全自动）
# 适用于 macOS 和 Linux
# 自动完成：依赖检查 → 登录检查 → 启动Web界面

# ============================================================================
# 配置选项（开发者可修改）
# ============================================================================
# 是否过滤控制台中的PyTorch相关错误信息
# true: 过滤（默认，适合普通用户）
# false: 不过滤（适合开发者调试）
FILTER_CONSOLE_ERRORS=true
# ============================================================================

# 切换到脚本所在目录（确保相对路径正确）
cd "$(dirname "$0")"

echo "=========================================="
echo "  小红书笔记提取工具 - 一键启动"
echo "=========================================="
echo ""
echo "💡 提示: 按 Ctrl+C 可以停止服务"
echo ""

# ============================================
# 步骤1: 检查Python环境
# ============================================
echo "📋 [1/4] 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "⚠️  未找到Python3"
    echo ""
    echo "检测到系统未安装Python，可以选择："
    echo "1. 自动安装Python（推荐，使用Homebrew）"
    echo "2. 手动安装Python（访问 https://www.python.org/downloads/）"
    echo ""
    read -p "是否自动安装Python？(y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📦 正在检查Homebrew..."
        if ! command -v brew &> /dev/null; then
            echo "   未找到Homebrew，正在安装Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            
            if [ $? -ne 0 ]; then
                echo "❌ Homebrew安装失败，请手动安装Python"
                exit 1
            fi
            
            # 添加Homebrew到PATH（适用于Apple Silicon Mac）
            if [ -f "/opt/homebrew/bin/brew" ]; then
                eval "$(/opt/homebrew/bin/brew shellenv)"
            elif [ -f "/usr/local/bin/brew" ]; then
                eval "$(/usr/local/bin/brew shellenv)"
            fi
        fi
        
        echo "📦 正在使用Homebrew安装Python..."
        brew install python3
        
        if [ $? -ne 0 ]; then
            echo "❌ Python安装失败，请手动安装"
            echo "   访问 https://www.python.org/downloads/ 下载安装"
            exit 1
        fi
        
        # 重新检查Python
        if ! command -v python3 &> /dev/null; then
            echo "❌ Python安装后仍无法找到，请手动配置PATH"
            exit 1
        fi
        
        echo "✅ Python安装成功！"
        echo ""
    else
        echo "   请手动安装Python后重新运行此脚本"
        echo "   访问 https://www.python.org/downloads/ 下载安装"
        exit 1
    fi
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Python版本: $PYTHON_VERSION"
echo ""

# ============================================
# 步骤2: 检查并安装依赖
# ============================================
echo "📋 [2/4] 检查依赖..."
NEED_INSTALL=false

# 检查必要的包
if ! python3 -c "import playwright" 2>/dev/null; then
    echo "   ⚠️  未安装 playwright"
    NEED_INSTALL=true
fi

if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "   ⚠️  未安装 streamlit"
    NEED_INSTALL=true
fi

if ! python3 -c "import requests" 2>/dev/null; then
    echo "   ⚠️  未安装 requests"
    NEED_INSTALL=true
fi

if [ "$NEED_INSTALL" = true ]; then
    echo ""
    echo "📦 正在安装依赖包（这可能需要几分钟）..."
    pip3 install playwright requests beautifulsoup4 streamlit --quiet
    
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败，请检查网络连接"
        exit 1
    fi
    
    echo "✅ 依赖包安装完成"
    echo ""
    
    # 检查Playwright浏览器
    echo "🌐 检查Playwright浏览器..."
    if [ ! -d "$HOME/.cache/ms-playwright" ] || [ -z "$(ls -A $HOME/.cache/ms-playwright/chromium-* 2>/dev/null)" ]; then
        echo "   正在安装浏览器（这可能需要几分钟）..."
        python3 -m playwright install chromium --quiet
        
        if [ $? -ne 0 ]; then
            echo "❌ 浏览器安装失败"
            exit 1
        fi
    fi
    echo "✅ 浏览器已就绪"
    echo ""
else
    echo "✅ 所有依赖已安装"
    echo ""
fi

# ============================================
# 步骤3: 检查登录状态
# ============================================
echo "📋 [3/4] 检查登录状态..."
if [ ! -f "xhs_extractor_module/xhs_state.json" ]; then
    echo "   ⚠️  未检测到登录状态"
    echo ""
    echo "📝 需要先登录小红书账号："
    echo "   1. 浏览器将自动打开小红书登录页面"
    echo "   2. 请在浏览器中完成登录"
    echo "   3. 登录成功后，回到终端按回车键"
    echo ""
    read -p "   按回车键开始登录..." -r
    echo ""
    
    python3 -m xhs_extractor_module.xhs_login
    
    if [ $? -ne 0 ] || [ ! -f "xhs_extractor_module/xhs_state.json" ]; then
        echo ""
        echo "❌ 登录失败或未完成，请重试"
        exit 1
    fi
    
    # 验证登录状态是否有效
    echo ""
    echo "🔍 正在验证登录状态..."
    if python3 -m xhs_extractor_module.xhs_login --verify 2>/dev/null; then
        echo ""
        echo "✅ 登录成功！登录信息已验证有效"
        echo ""
    else
        echo ""
        echo "❌ 登录验证失败"
        echo "   刚才的登录操作可能不成功或者账号信息文件已损坏"
        echo ""
        echo "请选择："
        echo "1. 重新登录"
        echo "2. 退出脚本"
        echo ""
        read -p "请选择 (1/2): " -r
        echo ""
        
        if [[ $REPLY =~ ^[1一]$ ]]; then
            echo "📝 正在重新登录..."
            echo "   1. 浏览器将自动打开小红书登录页面"
            echo "   2. 请在浏览器中完成登录"
            echo "   3. 登录成功后，回到终端按回车键"
            echo ""
            read -p "   按回车键开始登录..." -r
            echo ""
            
            python3 -m xhs_extractor_module.xhs_login
            
            if [ $? -ne 0 ] || [ ! -f "xhs_extractor_module/xhs_state.json" ]; then
                echo ""
                echo "❌ 登录失败或未完成，请重试"
                exit 1
            fi
            
            # 再次验证登录状态
            echo ""
            echo "🔍 正在验证登录状态..."
            if python3 -m xhs_extractor_module.xhs_login --verify 2>/dev/null; then
                echo ""
                echo "✅ 登录成功！登录信息已验证有效"
                echo ""
            else
                echo ""
                echo "❌ 登录验证仍然失败，请检查网络连接或稍后重试"
                exit 1
            fi
        else
            echo "退出脚本"
            exit 1
        fi
    fi
else
    echo "   ✅ 检测到已有登录信息"
    echo ""
    echo "请选择："
    echo "1. 使用当前账号（继续使用已保存的登录信息）"
    echo "2. 切换账号（重新登录新账号）"
    echo ""
    read -p "请选择 (1/2，直接回车默认使用当前账号): " -r
    echo ""
    
    if [[ $REPLY =~ ^[2二]$ ]]; then
        echo "📝 正在切换账号..."
        echo "   1. 浏览器将自动打开小红书登录页面"
        echo "   2. 请在浏览器中完成登录"
        echo "   3. 登录成功后，回到终端按回车键"
        echo ""
        read -p "   按回车键开始登录..." -r
        echo ""
        
        python3 -m xhs_extractor_module.xhs_login
        
        if [ $? -ne 0 ] || [ ! -f "xhs_extractor_module/xhs_state.json" ]; then
            echo ""
            echo "❌ 登录失败或未完成，请重试"
            exit 1
        fi
        
        # 验证登录状态是否有效
        echo ""
        echo "🔍 正在验证登录状态..."
        if python3 -m xhs_extractor_module.xhs_login --verify 2>/dev/null; then
            echo ""
            echo "✅ 账号切换成功！登录信息已验证有效"
            echo ""
        else
            echo ""
            echo "❌ 登录验证失败"
            echo "   刚才的登录操作可能不成功或者账号信息文件已损坏"
            echo ""
            echo "请选择："
            echo "1. 重新登录"
            echo "2. 退出脚本"
            echo ""
            read -p "请选择 (1/2): " -r
            echo ""
            
            if [[ $REPLY =~ ^[1一]$ ]]; then
                echo "📝 正在重新登录..."
                echo "   1. 浏览器将自动打开小红书登录页面"
                echo "   2. 请在浏览器中完成登录"
                echo "   3. 登录成功后，回到终端按回车键"
                echo ""
                read -p "   按回车键开始登录..." -r
                echo ""
                
                python3 -m xhs_extractor_module.xhs_login
                
                if [ $? -ne 0 ] || [ ! -f "xhs_extractor_module/xhs_state.json" ]; then
                    echo ""
                    echo "❌ 登录失败或未完成，请重试"
                    exit 1
                fi
                
                # 再次验证登录状态
                echo ""
                echo "🔍 正在验证登录状态..."
                if python3 -m xhs_extractor_module.xhs_login --verify 2>/dev/null; then
                    echo ""
                    echo "✅ 登录成功！登录信息已验证有效"
                    echo ""
                else
                    echo ""
                    echo "❌ 登录验证仍然失败，请检查网络连接或稍后重试"
                    exit 1
                fi
            else
                echo "退出脚本"
                exit 1
            fi
        fi
    else
        # 验证当前账号的登录状态是否有效
        echo "🔍 正在验证当前账号的登录状态..."
        if python3 -m xhs_extractor_module.xhs_login --verify 2>/dev/null; then
            echo ""
            echo "✅ 登录信息已验证有效，继续启动"
            echo ""
        else
            echo ""
            echo "❌ 登录验证失败"
            echo "   保存的登录信息可能已过期或已损坏"
            echo ""
            echo "请选择："
            echo "1. 重新登录"
            echo "2. 退出脚本"
            echo ""
            read -p "请选择 (1/2): " -r
            echo ""
            
            if [[ $REPLY =~ ^[1一]$ ]]; then
                echo "📝 正在重新登录..."
                echo "   1. 浏览器将自动打开小红书登录页面"
                echo "   2. 请在浏览器中完成登录"
                echo "   3. 登录成功后，回到终端按回车键"
                echo ""
                read -p "   按回车键开始登录..." -r
                echo ""
                
                python3 -m xhs_extractor_module.xhs_login
                
                if [ $? -ne 0 ] || [ ! -f "xhs_extractor_module/xhs_state.json" ]; then
                    echo ""
                    echo "❌ 登录失败或未完成，请重试"
                    exit 1
                fi
                
                # 再次验证登录状态
                echo ""
                echo "🔍 正在验证登录状态..."
                if python3 -m xhs_extractor_module.xhs_login --verify 2>/dev/null; then
                    echo ""
                    echo "✅ 登录成功！登录信息已验证有效"
                    echo ""
                else
                    echo ""
                    echo "❌ 登录验证仍然失败，请检查网络连接或稍后重试"
                    exit 1
                fi
            else
                echo "退出脚本"
                exit 1
            fi
        fi
    fi
fi

# ============================================
# 步骤4: 启动Web界面
# ============================================
echo "📋 [4/4] 启动Web界面..."
echo ""
echo "🚀 正在启动..."
echo "   浏览器将自动打开，如果没有自动打开，请访问: http://localhost:8501"
echo ""
echo "💡 提示: 按 Ctrl+C 可以停止服务"
echo ""

# 启动Streamlit
if [ "$FILTER_CONSOLE_ERRORS" = "true" ]; then
    # 过滤PyTorch相关的非致命错误（默认模式）
    streamlit run xhs_extractor_module/web_app.py 2>&1 | grep -v "torch.classes" | grep -v "streamlit.watcher" | grep -v "RuntimeError: Tried to instantiate class" | grep -v "RuntimeError: no running event loop" | grep -v "Examining the path of torch.classes" || true
else
    # 不过滤，显示所有输出（开发者模式）
    streamlit run xhs_extractor_module/web_app.py
fi

