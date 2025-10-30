@echo off
chcp 65001 >nul
echo ========================================
echo  字符统计与字体瘦身工具 - 打包脚本
echo ========================================
echo.

REM 检查是否安装了 PyInstaller
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 PyInstaller，正在安装...
    pip install pyinstaller
    if errorlevel 1 (
        echo [失败] PyInstaller 安装失败，请手动运行: pip install pyinstaller
        pause
        exit /b 1
    )
    echo [成功] PyInstaller 安装完成！
    echo.
)

echo [信息] 开始打包程序...
echo.

REM 删除旧的构建文件
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "字符统计与字体瘦身工具.spec" del /q "字符统计与字体瘦身工具.spec"

REM 执行打包
pyinstaller --onefile --windowed ^
    --name "字符统计与字体瘦身工具" ^
    --hidden-import=fontTools.subset ^
    --hidden-import=fontTools.ttLib ^
    --hidden-import=fontTools.ttLib.ttCollection ^
    wc.py

if errorlevel 1 (
    echo.
    echo [失败] 打包过程出错！
    pause
    exit /b 1
)

echo.
echo ========================================
echo  打包完成！
echo ========================================
echo.
echo 生成的文件位置：
echo   dist\字符统计与字体瘦身工具.exe
echo.
echo 您可以将该 exe 文件复制到任何位置使用。
echo.

REM 询问是否清理临时文件
set /p cleanup="是否删除临时文件（build文件夹）？[Y/N]: "
if /i "%cleanup%"=="Y" (
    rmdir /s /q build
    del /q "字符统计与字体瘦身工具.spec"
    echo [完成] 临时文件已清理。
)

echo.
pause