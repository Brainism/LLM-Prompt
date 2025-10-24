@echo off
call .venv\Scripts\activate

REM 1) Ensure output dirs
if not exist submission mkdir submission

REM 2) Copy required artifacts into submission/temp
if exist submission\temp rmdir /s /q submission\temp
mkdir submission\temp

REM 2a) Papers (pdf) - leave to user to create paper PDF in root or paper\paper.pdf
if exist paper\paper.pdf (
  copy /Y paper\paper.pdf submission\temp\paper.pdf
) else (
  echo WARNING: paper\paper.pdf not found. Ensure you created final PDF at paper\paper.pdf
)

REM 2b) Figures (use high-res)
if exist figs_highres (
  xcopy /E /I /Y "figs_highres" submission\temp\figs_highres >nul
) else if exist figs (
  xcopy /E /I /Y "figs" submission\temp\figs >nul
) else (
  echo WARNING: No figures found in figs_highres or figs.
)

REM 2c) Tables and reproducibility notes
if exist docs\paper\tables xcopy /E /I /Y "docs\paper\tables" submission\temp\tables >nul
if exist docs\paper\appendix xcopy /E /I /Y "docs\paper\appendix" submission\temp\appendix >nul
if exist analysis_outputs xcopy /E /I /Y "analysis_outputs" submission\temp\analysis_outputs >nul

REM 3) Create zip (using PowerShell inside cmd)
set ZIPNAME=final_package.zip
if exist submission\%ZIPNAME% del /f /q submission\%ZIPNAME%
powershell -Command "Compress-Archive -Path 'submission\\temp\\*' -DestinationPath 'submission\\%ZIPNAME%' -Force"
if errorlevel 1 (
  echo ERROR: Failed to create zip. Ensure PowerShell is available.
  exit /b 1
)

REM 4) Generate SHA256 checksums for every file in zip root (using certutil) and a checksums.txt
echo Generating checksums...
if exist submission\checksums.txt del /f /q submission\checksums.txt
for %%F in (submission\temp\*) do (
  rem only top-level files; better to compute for zip file itself
)

REM checksum for zip itself
certutil -hashfile submission\%ZIPNAME% SHA256 > submission\checksums.txt

echo Packaging complete: submission\%ZIPNAME%
echo Checksum saved to submission\checksums.txt
pause