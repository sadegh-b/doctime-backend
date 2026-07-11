$ErrorActionPreference = "Stop"

$base = "http://127.0.0.1:8000/api/v1"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor DarkGray
    Write-Host $Message -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor DarkGray
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Print-Json {
    param([Parameter(ValueFromPipeline = $true)] $InputObject)
    $InputObject | ConvertTo-Json -Depth 10
}

function Get-ErrorBody {
    param([Parameter(Mandatory = $true)] $ErrorRecord)

    if ($ErrorRecord.ErrorDetails -and -not [string]::IsNullOrWhiteSpace($ErrorRecord.ErrorDetails.Message)) {
        return $ErrorRecord.ErrorDetails.Message
    }

    if ($ErrorRecord.Exception -and -not [string]::IsNullOrWhiteSpace($ErrorRecord.Exception.Message)) {
        $fallbackMessage = $ErrorRecord.Exception.Message
    }
    else {
        $fallbackMessage = "Unknown error"
    }

    try {
        $response = $ErrorRecord.Exception.Response
        if ($null -eq $response) {
            return $fallbackMessage
        }

        $stream = $response.GetResponseStream()
        if ($null -eq $stream) {
            return $fallbackMessage
        }

        $reader = New-Object System.IO.StreamReader($stream)
        try {
            $body = $reader.ReadToEnd()
        }
        finally {
            $reader.Dispose()
        }

        if ([string]::IsNullOrWhiteSpace($body)) {
            return $fallbackMessage
        }

        return $body
    }
    catch {
        return $fallbackMessage
    }
}

function Require-AccessToken {
    param(
        [Parameter(Mandatory = $true)] $LoginResponse,
        [Parameter(Mandatory = $true)] [string] $UserLabel
    )

    if (-not $LoginResponse.access_token) {
        throw "$UserLabel login succeeded but access_token is missing."
    }

    return $LoginResponse.access_token
}

Write-Step "Step 1 - Register doctor"

$doctorPhone = "0912$(Get-Random -Minimum 1000000 -Maximum 9999999)"
$doctorEmail = "doctor_$doctorPhone@test.com"
$doctorPassword = "123456"

$doctorRegisterBody = @{
    name     = "Dr Test Auto"
    email    = $doctorEmail
    phone    = $doctorPhone
    password = $doctorPassword
    role     = "doctor"
} | ConvertTo-Json

try {
    $doctorRegister = Invoke-RestMethod -Uri "$base/auth/register" -Method Post -ContentType "application/json" -Body $doctorRegisterBody
    Write-Success "Doctor registered successfully"
    $doctorRegister | Print-Json
}
catch {
    Write-Fail "Doctor registration failed"
    Write-Host (Get-ErrorBody -ErrorRecord $_) -ForegroundColor Yellow
    exit 1
}

Write-Step "Step 2 - Login doctor"

$doctorLoginBody = @{
    phone    = $doctorPhone
    password = $doctorPassword
} | ConvertTo-Json

try {
    $doctorLogin = Invoke-RestMethod -Uri "$base/auth/login" -Method Post -ContentType "application/json" -Body $doctorLoginBody
    $doctorToken = Require-AccessToken -LoginResponse $doctorLogin -UserLabel "Doctor"
    $doctorHeaders = @{ Authorization = "Bearer $doctorToken" }

    Write-Success "Doctor login successful"
    $doctorLogin | Print-Json
}
catch {
    Write-Fail "Doctor login failed"
    Write-Host (Get-ErrorBody -ErrorRecord $_) -ForegroundColor Yellow
    exit 1
}

Write-Step "Step 3 - Create doctor profile"

$doctorProfileBody = @{
    specialty        = "Cardiology"
    experience_years = 8
    consultation_fee = 250000
    bio              = "Automated test doctor profile"
    city             = "Tehran"
    address          = "Test Address"
} | ConvertTo-Json

try {
    $doctorProfile = Invoke-RestMethod -Uri "$base/doctors" -Method Post -Headers $doctorHeaders -ContentType "application/json" -Body $doctorProfileBody
    Write-Success "Doctor profile created successfully"
    $doctorProfile | Print-Json
}
catch {
    Write-Fail "Doctor profile creation failed"
    Write-Host (Get-ErrorBody -ErrorRecord $_) -ForegroundColor Yellow
    exit 1
}

Write-Step "Step 4 - Create doctor availability"

$today = Get-Date
$targetDate = $today.AddDays(1).ToString("yyyy-MM-dd")

$availabilityBody = @{
    date             = $targetDate
    start_time       = "10:00"
    end_time         = "12:00"
    duration_minutes = 15
} | ConvertTo-Json

try {
    $availability = Invoke-RestMethod -Uri "$base/availability" -Method Post -Headers $doctorHeaders -ContentType "application/json" -Body $availabilityBody
    Write-Success "Availability created successfully"
    $availability | Print-Json
}
catch {
    Write-Fail "Availability creation failed"
    Write-Host (Get-ErrorBody -ErrorRecord $_) -ForegroundColor Yellow
    exit 1
}

Write-Step "Step 5 - Validate availability and extract first slot id"

$slotId = $null

if (-not $availability.success) {
    Write-Fail "Availability response indicates failure"
    $availability | Print-Json
    exit 1
}

if (-not $availability.items -or $availability.items.Count -eq 0) {
    Write-Fail "Availability response does not contain created slots"
    $availability | Print-Json
    exit 1
}

if ($availability.count -ne 8) {
    Write-Fail "Expected 8 slots, but got $($availability.count)"
    $availability | Print-Json
    exit 1
}

$slotId = $availability.items[0].id

if (-not $slotId) {
    Write-Fail "Could not extract slot id from availability response"
    $availability | Print-Json
    exit 1
}

Write-Success "Slot id extracted successfully: $slotId"

Write-Step "Step 5.1 - Validate slot time boundaries"

$expectedSlots = @(
    @{ start = "10:00:00"; end = "10:15:00" },
    @{ start = "10:15:00"; end = "10:30:00" },
    @{ start = "10:30:00"; end = "10:45:00" },
    @{ start = "10:45:00"; end = "11:00:00" },
    @{ start = "11:00:00"; end = "11:15:00" },
    @{ start = "11:15:00"; end = "11:30:00" },
    @{ start = "11:30:00"; end = "11:45:00" },
    @{ start = "11:45:00"; end = "12:00:00" }
)

for ($i = 0; $i -lt $expectedSlots.Count; $i++) {
    $actual = $availability.items[$i]
    $expected = $expectedSlots[$i]

    if ($actual.start_time -ne $expected.start -or $actual.end_time -ne $expected.end) {
        Write-Fail "Slot #$($i + 1) mismatch. Expected $($expected.start)-$($expected.end), got $($actual.start_time)-$($actual.end_time)"
        $availability | Print-Json
        exit 1
    }
}

Write-Success "All generated slots have correct 15-minute boundaries"

Write-Step "Step 6 - Register patient"

$patientPhone = "0935$(Get-Random -Minimum 1000000 -Maximum 9999999)"
$patientEmail = "patient_$patientPhone@test.com"
$patientPassword = "123456"

$patientRegisterBody = @{
    name     = "Patient Test Auto"
    email    = $patientEmail
    phone    = $patientPhone
    password = $patientPassword
    role     = "patient"
} | ConvertTo-Json

try {
    $patientRegister = Invoke-RestMethod -Uri "$base/auth/register" -Method Post -ContentType "application/json" -Body $patientRegisterBody
    Write-Success "Patient registered successfully"
    $patientRegister | Print-Json
}
catch {
    Write-Fail "Patient registration failed"
    Write-Host (Get-ErrorBody -ErrorRecord $_) -ForegroundColor Yellow
    exit 1
}

Write-Step "Step 7 - Login patient"

$patientLoginBody = @{
    phone    = $patientPhone
    password = $patientPassword
} | ConvertTo-Json

try {
    $patientLogin = Invoke-RestMethod -Uri "$base/auth/login" -Method Post -ContentType "application/json" -Body $patientLoginBody
    $patientToken = Require-AccessToken -LoginResponse $patientLogin -UserLabel "Patient"
    $patientHeaders = @{ Authorization = "Bearer $patientToken" }

    Write-Success "Patient login successful"
    $patientLogin | Print-Json
}
catch {
    Write-Fail "Patient login failed"
    Write-Host (Get-ErrorBody -ErrorRecord $_) -ForegroundColor Yellow
    exit 1
}

Write-Step "Step 8 - Book appointment with fresh slot"

try {
    $booking = Invoke-RestMethod -Uri "$base/appointments/book/$slotId" -Method Post -Headers $patientHeaders
    Write-Success "Appointment booking successful"
    $booking | Print-Json
}
catch {
    Write-Fail "Appointment booking failed"
    Write-Host (Get-ErrorBody -ErrorRecord $_) -ForegroundColor Yellow
    exit 1
}

Write-Step "Step 9 - Fetch patient appointments"

try {
    $myAppointments = Invoke-RestMethod -Uri "$base/appointments/me" -Method Get -Headers $patientHeaders
    Write-Success "Fetched patient appointments successfully"
    $myAppointments | Print-Json
}
catch {
    Write-Fail "Fetching patient appointments failed"
    Write-Host (Get-ErrorBody -ErrorRecord $_) -ForegroundColor Yellow
    exit 1
}

Write-Step "Step 10 - Try duplicate booking for same slot"

try {
    $duplicateBooking = Invoke-RestMethod -Uri "$base/appointments/book/$slotId" -Method Post -Headers $patientHeaders
    Write-Fail "Duplicate booking unexpectedly succeeded"
    $duplicateBooking | Print-Json
    exit 1
}
catch {
    Write-Success "Duplicate booking was correctly rejected"
    Write-Host (Get-ErrorBody -ErrorRecord $_) -ForegroundColor Yellow
}

Write-Step "Step 11 - Test summary"

Write-Host "Doctor phone: $doctorPhone" -ForegroundColor Magenta
Write-Host "Doctor email: $doctorEmail" -ForegroundColor Magenta
Write-Host "Patient phone: $patientPhone" -ForegroundColor Magenta
Write-Host "Patient email: $patientEmail" -ForegroundColor Magenta
Write-Host "Target date: $targetDate" -ForegroundColor Magenta
Write-Host "Booked slot id: $slotId" -ForegroundColor Magenta

Write-Success "Full self-contained E2E booking flow completed"
