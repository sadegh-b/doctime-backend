# مسیر فایل: tests/test_security_access.ps1
$base = "http://127.0.0.1:8000/api/v1"

Write-Host "--- Testing Security: Accessing other patient's data ---" -ForegroundColor Cyan

# فرض کن ما دو تا بیمار داریم. بیمار ۱ نوبت رزرو کرده.
# آیا بیمار ۲ با توکن خودش می‌تونه لیست نوبت‌های بیمار ۱ رو ببینه؟
# یا نوبت اون رو کنسل کنه؟

# این تست باید با خطای 403 یا 404 مواجه بشه.
try {
    # تلاش برای دیدن نوبتی که متعلق به ما نیست (مثلاً ID شماره 1)
    $fakeAccess = Invoke-RestMethod -Uri "$base/appointments/1" -Method Get -Headers $patientHeaders
    Write-Host "SECURITY HOLE: Accessed other patient's appointment!" -ForegroundColor Red
}
catch {
    Write-Host "Success: Security block working. (Expected)" -ForegroundColor Green
}
