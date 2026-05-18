# PowerShell script to start both backend and frontend services

Write-Host "🚀 Starting Patch Resume Services..." -ForegroundColor Green

# Check if we're in the right directory
if (-not (Test-Path "backend/main.py")) {
    Write-Host "❌ Error: Please run this script from the patch-resume root directory" -ForegroundColor Red
    exit 1
}

# Start backend in background
Write-Host "🔧 Starting backend server..." -ForegroundColor Yellow
$backendProcess = Start-Process powershell -ArgumentList "-Command", "cd backend; python -m uvicorn main:app --reload --port 8000" -PassThru -WindowStyle Hidden

# Wait a moment for backend to start
Start-Sleep -Seconds 5

# Test backend health
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
    if ($response.status -eq "healthy") {
        Write-Host "✅ Backend started successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ Backend health check failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Backend is not responding. Check if it's running properly." -ForegroundColor Red
    exit 1
}

# Start frontend
Write-Host "🌐 Starting frontend server..." -ForegroundColor Yellow
$frontendProcess = Start-Process powershell -ArgumentList "-Command", "npm run dev" -PassThru -WindowStyle Hidden

Write-Host ""
Write-Host "🎉 Services are starting up!" -ForegroundColor Green
Write-Host "📡 Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "🌐 Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "📚 API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Yellow

# Wait for user input to stop
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    # Cleanup when script is interrupted
    Write-Host ""
    Write-Host "🛑 Stopping services..." -ForegroundColor Yellow
    
    if ($backendProcess -and !$backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force
        Write-Host "✅ Backend stopped" -ForegroundColor Green
    }
    
    if ($frontendProcess -and !$frontendProcess.HasExited) {
        Stop-Process -Id $frontendProcess.Id -Force
        Write-Host "✅ Frontend stopped" -ForegroundColor Green
    }
    
    Write-Host "👋 All services stopped" -ForegroundColor Green
}