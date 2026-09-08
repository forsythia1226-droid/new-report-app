@echo off
REM ---------------------------------------------------------------------------
REM Windows 작업 스케줄러에 등록해서 쓰는 48시간 보관 정책 정리 배치 파일.
REM 앱 접속 여부와 무관하게 지정한 시각에 만료 데이터를 삭제한다.
REM
REM 등록 (관리자 PowerShell에서 1회 실행, 매시 정각 반복):
REM   schtasks /create /tn "IssueReportPurge" /tr "\"%~f0\"" /sc hourly /st 00:00
REM
REM 확인 / 즉시 실행 / 삭제:
REM   schtasks /query /tn "IssueReportPurge"
REM   schtasks /run   /tn "IssueReportPurge"
REM   schtasks /delete /tn "IssueReportPurge" /f
REM ---------------------------------------------------------------------------

cd /d "%~dp0"
python purge_job.py --log-file purge.log
exit /b %ERRORLEVEL%
