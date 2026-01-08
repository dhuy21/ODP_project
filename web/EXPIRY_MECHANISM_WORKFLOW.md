# 🔄 Cơ Chế Expire Reservation - Workflow Chi Tiết

## 📋 Tổng Quan

Hệ thống có **2 cơ chế song song** để phát hiện và xử lý reservations expired:

1. **Background Task** (Server-side): Chạy tự động mỗi 30 giây
2. **Frontend Check** (Client-side): Gọi API mỗi 30 giây từ dashboard

---

## 🏗️ Kiến Trúc Tổng Thể

```
┌─────────────────────────────────────────────────────────────┐
│                    EXPIRY DETECTION SYSTEM                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │ Background Task   │         │ Frontend Check    │        │
│  │ (app.py)          │         │ (dashboard_home)  │        │
│  │ Every 30s         │         │ Every 30s         │        │
│  └────────┬──────────┘         └────────┬─────────┘        │
│           │                              │                    │
│           └──────────┬───────────────────┘                    │
│                      │                                        │
│           ┌──────────▼──────────┐                            │
│           │  Check Expired      │                            │
│           │  Reservations       │                            │
│           └──────────┬──────────┘                            │
│                      │                                        │
│           ┌──────────▼──────────┐                            │
│           │  Save Final Stats   │                            │
│           │  Update Status      │                            │
│           └──────────┬──────────┘                            │
│                      │                                        │
│           ┌──────────▼──────────┐                            │
│           │  Notify User        │                            │
│           │  Disconnect SSH     │                            │
│           └─────────────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Workflow Chi Tiết

### 1️⃣ **Background Task (Server-side)**

**File**: `app.py` → `check_expired_reservations_loop()`

**Chạy**: Mỗi 30 giây, tự động trong background thread

**Workflow**:

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Khởi động Background Thread                         │
│ - Thread được start khi app khởi động                       │
│ - Chạy vô hạn trong while True loop                         │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Check Docker Containers (mỗi 30s)                   │
│ - Gọi docker_service.check_expired_containers()              │
│ - Chạy: ./pool_manager.sh check-expired                     │
│ - Mục đích: Release containers đã hết hạn ở Docker level    │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Load All Users & Reservations                      │
│ - user_db.load_users()                                      │
│ - Lặp qua TẤT CẢ users trong database                       │
│ - Lặp qua TẤT CẢ reservations của mỗi user                  │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Check Each Reservation                              │
│ FOR EACH reservation:                                        │
│   IF status == 'active':                                     │
│     IF current_time > expires_at:                            │
│       → RESERVATION EXPIRED!                                │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Save Final Stats                                    │
│ - Gọi StatsService.get_reservation_stats()                  │
│ - Lấy CPU/RAM hiện tại của các nodes                        │
│ - user_db.save_reservation_final_stats()                    │
│ - Log: [STATS] Saved final stats for reservation...         │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Update Status to 'expired'                          │
│ - user_db.update_reservation_status(username, id, 'expired')│
│ - Ghi vào database ngay lập tức                             │
│ - Log: [EXPIRY] Marking reservation ... as expired          │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 7: Disconnect SSH Sessions                             │
│ - ssh_controller.disconnect_user_sessions(username)         │
│ - Đóng tất cả SSH connections của user                      │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 8: Log Completion                                      │
│ - Log: [EXPIRY CHECK] Completed at ...                      │
│ - Sleep 30 giây                                              │
│ - Lặp lại từ STEP 2                                         │
└─────────────────────────────────────────────────────────────┘
```

**Ví dụ từ log**:
```
[EXPIRY CHECK] Completed at 2026-01-07 18:23:33
[STATS] Saved final stats for reservation 06f42821...
[EXPIRY] Marked reservation 06f42821 as expired for huy
[EXPIRY CHECK] Completed at 2026-01-07 18:24:06
```

---

### 2️⃣ **Frontend Check (Client-side)**

**File**: `dashboard_home.js` → `initReservationCheck()`

**Chạy**: Mỗi 30 giây từ browser, chỉ khi user đang ở dashboard

**Workflow**:

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Page Load                                           │
│ - initReservationCheck() được gọi khi DOM ready             │
│ - Khởi tạo flags:                                            │
│   • hasShownExpiredNotification = false                      │
│   • isReloading = false                                      │
│   • checkInterval = null                                      │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Immediate Check (ngay khi load)                     │
│ - Gọi checkExpiredReservations() ngay lập tức               │
│ - Mục đích: Phát hiện reservation đã expired khi page mở   │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Set Interval (mỗi 30s)                              │
│ - setInterval(checkExpiredReservations, 30000)               │
│ - Lưu interval ID vào checkInterval                         │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Check Logic (mỗi lần interval chạy)                │
│ IF (isReloading || hasShownExpiredNotification):            │
│   → RETURN (không check nữa)                               │
│                                                              │
│ ELSE:                                                        │
│   → Gọi API: GET /check-my-reservations                     │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: API Response Processing                             │
│ Backend (vm_controller.check_my_reservations):              │
│   - Load reservations của user                              │
│   - Check từng reservation:                                 │
│     IF status == 'active' AND current_time > expires_at:    │
│       → Save final stats                                     │
│       → Update status to 'expired'                          │
│       → has_expired = true                                  │
│       → expired_count++                                     │
│                                                              │
│ Return: { has_expired: true/false, expired_count: N }       │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Frontend Response Handling                          │
│ IF data.has_expired && !hasShownExpiredNotification:       │
│   → hasShownExpiredNotification = true                      │
│   → isReloading = true                                      │
│   → clearInterval(checkInterval)  // Dừng check             │
│   → Hiển thị notification                                   │
│   → setTimeout(() => location.reload(), 3000)              │
└─────────────────────────────────────────────────────────────┘
```

**Ví dụ từ log**:
```
127.0.0.1 - - [07/Jan/2026 18:24:24] "GET /check-my-reservations HTTP/1.1" 200 -
127.0.0.1 - - [07/Jan/2026 18:25:01] "GET /check-my-reservations HTTP/1.1" 200 -
127.0.0.1 - - [07/Jan/2026 18:25:31] "GET /check-my-reservations HTTP/1.1" 200 -
```

---

### 3️⃣ **Reservation Detail Page Check**

**File**: `reservation_detail.js` → `initializeCountdown()`

**Chạy**: Mỗi 1 giây, chỉ khi user đang xem reservation detail

**Workflow**:

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Initialize Countdown                                │
│ - Lấy expires_at từ template                                │
│ - Khởi tạo flag: hasShownExpiredNotification = false        │
│ - Set interval mỗi 1 giây                                    │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Update Countdown (mỗi 1s)                           │
│ - Tính remaining = expires_at - current_time                │
│ - IF remaining <= 0:                                        │
│     → EXPIRED!                                              │
│   ELSE:                                                      │
│     → Hiển thị countdown: "Xh Ym Zs"                       │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Handle Expired                                      │
│ IF expired && !hasShownExpiredNotification:                │
│   → hasShownExpiredNotification = true                       │
│   → stopStatsUpdates()  // Dừng update stats                │
│   → clearInterval(countdownInterval)  // Dừng countdown     │
│   → Hiển thị notification                                   │
│   → Redirect sau 3 giây                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 Phân Tích Log Thực Tế

### Timeline từ log:

```
18:23:11 - User tạo reservation (06f42821-40e6-4fd2-a4f0-a1663a236883)
18:23:15 - Stats updates bắt đầu (mỗi 3s)
18:23:33 - Background task check (lần 1) - chưa expired
18:24:06 - Background task check (lần 2) - chưa expired
18:24:20 - User vào dashboard
18:24:23 - Background task phát hiện expired:
           [STATS] Saved final stats for reservation 06f42821...
           [EXPIRY] Marked reservation 06f42821 as expired for huy
18:24:24 - Frontend check phát hiện expired (sau 1 giây)
18:24:26 - Stats vẫn được fetch (nhưng sẽ trả về final_stats)
18:24:31 - Page reload (sau notification)
18:25:01 - Frontend check tiếp tục (nhưng reservation đã expired)
```

### Điểm Quan Trọng:

1. **Background task** phát hiện expired trước (18:24:23)
2. **Frontend check** phát hiện sau đó (18:24:24) - có thể do timing
3. **Stats updates** vẫn tiếp tục sau khi expired (18:24:26, 18:24:27)
   - Nhưng sẽ trả về `final_stats` thay vì real-time stats
   - Frontend sẽ dừng interval khi phát hiện status != 'active'

---

## ⚠️ Vấn Đề & Giải Pháp

### 1. **Race Condition**

**Vấn đề**: Background task và Frontend check có thể cùng update status

**Giải pháp**: 
- Background task có priority cao hơn
- Frontend check chỉ update khi chưa được update
- Status được check trước khi update: `if status == 'active'`

### 2. **Notification Vô Tận**

**Vấn đề**: Nhiều notifications xuất hiện liên tục

**Giải pháp**:
- Flag `hasShownExpiredNotification` để chỉ show 1 lần
- Dừng interval ngay khi phát hiện expired
- Reload page sau notification để reset state

### 3. **Stats Updates Sau Expired**

**Vấn đề**: Stats vẫn được fetch sau khi expired

**Giải pháp**:
- `get_container_stats()` trả về `final_stats` nếu status != 'active'
- Frontend dừng interval khi phát hiện expired
- `isStatsUpdateActive` flag để control updates

### 4. **Timeout Error**

**Vấn đề**: `pool_manager.sh check-expired` timeout sau 10 giây

**Log**:
```
Error checking expired containers: Command '['./pool_manager.sh', 'check-expired']' timed out after 10 seconds
```

**Giải pháp**: 
- Tăng timeout trong `docker_service.check_expired_containers()`
- Hoặc xử lý timeout gracefully (đã có try-except)

---

## 📊 So Sánh 2 Cơ Chế

| Tiêu Chí | Background Task | Frontend Check |
|----------|----------------|----------------|
| **Chạy ở đâu** | Server (Python thread) | Browser (JavaScript) |
| **Tần suất** | Mỗi 30 giây | Mỗi 30 giây |
| **Phạm vi** | TẤT CẢ users | Chỉ user hiện tại |
| **Khi nào chạy** | Luôn luôn | Chỉ khi user ở dashboard |
| **Priority** | Cao (chạy trước) | Thấp (backup) |
| **Notification** | Không (server-side) | Có (client-side) |
| **Disconnect SSH** | Có | Không |

---

## 🎯 Best Practices

1. **Background task là primary mechanism**: Luôn chạy và xử lý tất cả
2. **Frontend check là backup**: Chỉ để notify user nhanh hơn
3. **Status check trước update**: `if status == 'active'` để tránh duplicate
4. **Save stats trước update status**: Đảm bảo data không mất
5. **Flags để prevent loops**: `hasShownExpiredNotification`, `isReloading`

---

## 🔧 Cải Thiện Có Thể

1. **WebSocket notification**: Thay vì polling, dùng WebSocket để notify real-time
2. **Single source of truth**: Chỉ background task update status, frontend chỉ check
3. **Optimize database writes**: Batch updates thay vì update từng reservation
4. **Better error handling**: Retry mechanism cho failed updates
5. **Metrics & monitoring**: Track số lượng expired reservations, response time

---

## 📝 Kết Luận

Cơ chế expire hoạt động với **2 lớp bảo vệ**:
- **Background task**: Đảm bảo tất cả reservations được check và update
- **Frontend check**: Cung cấp UX tốt hơn với notification nhanh

Cả 2 cơ chế đều:
- Check mỗi 30 giây
- Save final stats trước khi update status
- Update status ngay lập tức khi phát hiện expired
- Có error handling và logging

