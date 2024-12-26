@echo off

:: Step 1: 启动 service.py 服务
echo Activating Conda environment "changdi"...
call conda activate changdi
echo Starting service...
::start python E:\script\Text_select_captcha\service.py

:: Step 2: 执行 main.py，根据参数进行并发预定
:: 设置变量
set username=%USERNAME%
set password=%PASSWORD%
set arena=张江校区网球场
::set date=<YYYY-MM-DD>
:: Step 2: 计算两天后的日期，使用 PowerShell 获取
for /f %%i in ('powershell -Command "(Get-Date).AddDays(2).ToString(\"yyyy-MM-dd\")"') do set date=%%i

:: 显示预定日期
echo the reservation date is %date%

:: 设置需要预定的时间段，以空格分隔，如果有多个时间，可以并发执行
set times=09:00 
::set times=15:00 16:00 17:00
:: 示例：set times=08:00 10:00 14:00

:: 遍历所有预定时间，并使用 start 命令实现并发执行，限制同时只能有两个进程
::set date=<YYYY-MM-DD>
:: Step 2: 计算两天后的日期，使用 PowerShell 获取
for /f %%i in ('powershell -Command "(Get-Date).AddDays(2).ToString(\"yyyy-MM-dd\")"') do set date=%%i

:: 显示预定日期
echo the reservation date is %date%
for %%t in (%times%) do (
    echo Making reservation for %%t...
    start python E:\script\Text_select_captcha\main.py --username %username% --password %password% --reservation-arena %arena% --reservation-date %date% --reservation-time %%t
    echo start python E:\script\Text_select_captcha\main.py --username %username% --password %password% --reservation-arena %arena% --reservation-date %date% --reservation-time %%t
)

:: 所有任务已启动
echo All reservation tasks started.
exit
