# Test all sample products and log results
$API = "https://autocategory.cucham.com/api/classify"

$samples = @(
    @{ title = 'Pass ip13 prm 256g fullbox'; desc = 'pin 88, may zin, con bh den t6/2025, khong kem hop'; price = 12500000; expected = 2 },
    @{ title = 'Ban laptop gaming Asus TUF F15 RTX 3060'; desc = 'Ram 16GB, SSD 512, moi 99%, con bao hanh Asus'; price = 18000000; expected = 5 },
    @{ title = 'Xe SH 150i ABS 2022 can pass gap'; desc = 'xe chuan chinh, odo 8k, khong dam dung, gia thuong luong'; price = 68000000; expected = 24 },
    @{ title = 'Cho thue phong tro gan DH Bach Khoa HN, 18m2'; desc = 'gio tu do, co WC rieng, dien nuoc theo gia nha nuoc'; price = 3500000; expected = 42 },
    @{ title = 'Ban meo Anh long ngan 3 thang tuoi'; desc = 'da tiem phong, tay giun, kem giay to, mau xam xanh'; price = 4000000; expected = 51 },
    @{ title = 'Tuyen nhan vien ban hang online tai nha'; desc = 'thoi gian linh hoat, hoa hong 15-20%, khong can kinh nghiem'; price = $null; expected = 45 },
    @{ title = 'Cho tang ban hoc cu, tu den lay'; desc = 'ban con dung duoc, hoi xuoc, khu vuc Cau Giay'; price = 0; expected = 38 },
    @{ title = 'Toyota Vios 2019 so tu dong mau trang'; desc = 'xe gia dinh di ky, full option, khong taxi, gia fix cung'; price = 425000000; expected = 25 },
    @{ title = 'Giay Nike Air Force 1 rep 1:1 full box'; desc = 'size 42, moi 99%, di 2 lan, khong loi'; price = 350000; expected = 28 },
    @{ title = 'iPad Pro M2 11 inch 128GB WiFi gray'; desc = 'like new, con bao hanh Apple den 2025, kem bao da'; price = 18500000; expected = 3 },
    @{ title = 'Ao thun nam cotton 100% form rong unisex'; desc = 'vai mem min, thoang mat, nhieu mau, freesize 50-75kg'; price = 120000; expected = 27 },
    @{ title = 'Ban nha 3 tang mat tien duong Le Loi Q1'; desc = '4x15m, so hong chinh chu, vi tri dep, gia thuong luong'; price = 12500000000; expected = 41 },
    @{ title = 'Tim viec lam them buoi toi khu vuc HN'; desc = 'nam 25t, co xe may, chap nhan moi cong viec, khong quan bar'; price = $null; expected = 44 },
    @{ title = 'Loa JBL Flip 6 chinh hang con BH 10 thang'; desc = 'mau do, zin nguyen seal, moi mua thua can ban lai'; price = 2300000; expected = 90 },
    @{ title = 'Balo laptop The North Face Borealis 28L'; desc = 'hang real, mau den, chong nuoc, fit laptop 15.6 inch'; price = 1800000; expected = 67 },
    @{ title = 'Cho Corgi 4 thang tuoi duc tiem du 3 mui'; desc = 'thuan chung, giay VKA, bo me nhap Thai, rat khoe'; price = 8500000; expected = 50 },
    @{ title = 'Nuoc hoa Dior Sauvage EDT 100ml tester'; desc = 'hang xach tay Phap, con 85%, mui thom lau, nam tinh'; price = 1650000; expected = 68 },
    @{ title = 'Xe dap dia hinh Giant ATX 26 inch do den'; desc = 'phanh dia, baga sau, zin 95%, dung it, gia tot'; price = 3200000; expected = 76 },
    @{ title = 'PS5 slim digital moi seal 100% bao hanh SSVN'; desc = 'full box nguyen seal chua kich hoat, ship toan quoc'; price = 12900000; expected = 4 },
    @{ title = 'Macbook Air M2 2023 16GB 256GB Space Gray'; desc = 'nhu moi, dan skin, dung 6 thang, con AppleCare+'; price = 25500000; expected = 5 }
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Testing $($samples.Count) samples..." -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$correct = 0
$total = $samples.Count
$results = @()

for ($i = 0; $i -lt $samples.Count; $i++) {
    $s = $samples[$i]
    $num = $i + 1
    
    Write-Host "[$num/$total] Testing: $($s.title)" -ForegroundColor Yellow
    
    $body = @{
        title = $s.title
        description = $s.desc
        price = $s.price
        image_urls = @()
        fast = $false
    } | ConvertTo-Json -Compress
    
    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $r = Invoke-RestMethod -Uri $API -Method POST -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -TimeoutSec 30
        $sw.Stop()
        
        $predicted = $r.rerank.category_id
        $confidence = $r.rerank.confidence
        $decision = $r.decision
        $elapsed = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        
        $match = $predicted -eq $s.expected
        if ($match) { $correct++ }
        
        $status = if ($match) { "PASS" } else { "FAIL" }
        $statusColor = if ($match) { "Green" } else { "Red" }
        
        Write-Host "  $status | Predicted: $predicted | Expected: $($s.expected) | Conf: $([math]::Round($confidence*100))% | Time: ${elapsed}s | Decision: $decision" -ForegroundColor $statusColor
        
        $results += [PSCustomObject]@{
            Sample = "$num. $($s.title)"
            Expected = $s.expected
            Predicted = $predicted
            Match = $match
            Confidence = [math]::Round($confidence, 4)
            Time = $elapsed
            Decision = $decision
            CategoryName = $r.selected_category.name
        }
        
    } catch {
        Write-Host "  ERROR | $($_.Exception.Message)" -ForegroundColor Red
        $results += [PSCustomObject]@{
            Sample = "$num. $($s.title)"
            Expected = $s.expected
            Predicted = "ERROR"
            Match = $false
            Confidence = 0
            Time = 0
            Decision = "error"
            CategoryName = "N/A"
        }
    }
    
    Start-Sleep -Milliseconds 500
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Correct: $correct / $total ($([math]::Round($correct/$total*100, 1))%)" -ForegroundColor $(if ($correct/$total -ge 0.9) { "Green" } else { "Yellow" })
Write-Host "Failed: $($total - $correct)" -ForegroundColor $(if ($correct -eq $total) { "Green" } else { "Red" })

Write-Host "`nDetailed Results:" -ForegroundColor Cyan
$results | Format-Table -AutoSize

$csvPath = "D:\Ads\AutoCategory\autocategory\test_results_$(Get-Date -Format 'yyyyMMdd_HHmmss').csv"
$results | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
Write-Host "`nResults exported to: $csvPath" -ForegroundColor Green
