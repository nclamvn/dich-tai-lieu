# 🚀 Translation Server - Hướng Dẫn Quản Lý

## 📌 LINKS TRUY CẬP

Server đang chạy ở port **8000** (cố định):

```
🌐 Giao diện Premium:  http://localhost:8000/ui/premium
📊 Dashboard API:      http://localhost:8000/api/dashboard  
📚 API Documentation:  http://localhost:8000/docs
```

---

## 🛠️ QUẢN LÝ SERVER

### Khởi động server (manual)
```bash
./start_server.sh
```

### Dừng server
```bash
./stop_server.sh
```

### Kiểm tra trạng thái
```bash
./status_server.sh
```

### Xem logs
```bash
tail -f logs/server.log
```

---

## 🔄 TỰ ĐỘNG KHỞI ĐỘNG KHI MAC BOOT

### Cài đặt auto-start
```bash
./install_autostart.sh
```

Sau khi cài đặt:
- ✅ Server tự động khởi động khi Mac boot
- ✅ Tự động restart nếu bị crash
- ✅ Luôn chạy ở port 8000

### Gỡ bỏ auto-start
```bash
./uninstall_autostart.sh
```

### Kiểm tra auto-start đang hoạt động
```bash
launchctl list | grep com.translator.server
```

### Xem logs của auto-start
```bash
tail -f logs/launchd.out.log  # Output logs
tail -f logs/launchd.err.log  # Error logs
```

---

## 🔒 ĐẢM BẢO PORT 8000 CHỈ CHO DỰ ÁN NÀY

### Phương án 1: Auto-start (Khuyên dùng)
Cài đặt auto-start như trên, launchd sẽ tự động quản lý port 8000.

### Phương án 2: Manual management
Script `start_server.sh` đã được cấu hình để:
1. Kiểm tra xem port 8000 có đang bị chiếm không
2. Nếu bị chiếm bởi process khác → hỏi có muốn kill không
3. Nếu đã là Translation Server → thông báo đang chạy

### Kiểm tra process nào đang dùng port 8000
```bash
lsof -i :8000
```

### Kill tất cả process trên port 8000
```bash
kill -9 $(lsof -ti:8000)
```

---

## 📁 CẤU TRÚC FILES

```
translator_project/
├── start_server.sh           # Khởi động server manual
├── stop_server.sh            # Dừng server
├── status_server.sh          # Kiểm tra trạng thái
├── install_autostart.sh      # Cài đặt tự động khởi động
├── uninstall_autostart.sh    # Gỡ bỏ tự động khởi động
├── com.translator.server.plist  # Launchd config file
├── logs/
│   ├── server.log           # Server logs (manual start)
│   ├── launchd.out.log      # Auto-start output logs
│   └── launchd.err.log      # Auto-start error logs
└── .server.pid              # Process ID file
```

---

## ⚙️ TROUBLESHOOTING

### Server không khởi động được
```bash
# Kiểm tra logs
cat logs/server.log

# Kiểm tra dependencies
pip install -r requirements.txt

# Kiểm tra port
lsof -i :8000
```

### Auto-start không hoạt động
```bash
# Kiểm tra service có được load không
launchctl list | grep translator

# Reload service
launchctl unload ~/Library/LaunchAgents/com.translator.server.plist
launchctl load ~/Library/LaunchAgents/com.translator.server.plist

# Kiểm tra error logs
cat logs/launchd.err.log
```

### Port 8000 bị chiếm bởi app khác
```bash
# Xem process nào đang dùng
lsof -i :8000

# Kill nó
kill -9 $(lsof -ti:8000)

# Hoặc dùng script
./start_server.sh  # Script sẽ tự hỏi có muốn kill không
```

---

## 💡 TIPS

1. **Development mode**: Dùng `./start_server.sh` (có auto-reload)
2. **Production mode**: Dùng `./install_autostart.sh` (stable, auto-restart)
3. **Xem logs realtime**: `tail -f logs/server.log`
4. **Restart server**: `./stop_server.sh && ./start_server.sh`

---

## 🔐 BẢO MẬT

Server đang chạy với `--host 0.0.0.0`, nghĩa là:
- ✅ Có thể truy cập từ LAN (http://YOUR_IP:8000)
- ⚠️ Nếu chỉ muốn local: đổi thành `127.0.0.1` trong script

Để đổi sang localhost-only:
```bash
# Edit start_server.sh hoặc com.translator.server.plist
# Đổi: --host 0.0.0.0
# Thành: --host 127.0.0.1
```
