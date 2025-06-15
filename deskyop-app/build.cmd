@echo off
echo Building FeedVox AI Desktop Application...
echo.

echo [1/3] Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo [2/3] Installing dependencies...
call npm install

echo [3/3] Building application...
call npm run dist:win

echo.
echo Build complete! Check the dist folder for the executable.
pause 