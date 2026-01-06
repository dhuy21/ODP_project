# ODP Platform - MVC Architecture

## 📁 Cấu Trúc Dự Án

```
web/
├── app.py                 # Old monolithic version (backup)
├── app_mvc.py            # NEW: Main application entry point (MVC)
├── config/               # Configuration
│   ├── __init__.py
│   └── config.py        # App configuration (SECRET_KEY, paths, etc.)
├── models/              # Data models
│   ├── __init__.py
│   ├── user.py          # User & UserDatabase
│   ├── vm.py            # VM & Reservation models
│   └── ssh_session.py   # SSH Session model
├── views/               # Templates (Flask uses templates/)
│   └── templates/       # HTML templates
├── controllers/         # Business logic
│   ├── __init__.py
│   ├── auth_controller.py       # Authentication logic
│   ├── dashboard_controller.py  # Dashboard logic
│   ├── vm_controller.py         # VM provisioning logic
│   └── ssh_controller.py        # SSH terminal logic
├── services/            # External services
│   ├── __init__.py
│   ├── docker_service.py    # Docker pool management
│   ├── ssh_service.py       # SSH connection management
│   └── ansible_service.py   # Ansible automation
├── routes/              # URL routing
│   ├── __init__.py
│   ├── auth_routes.py       # /login, /register, /logout
│   ├── main_routes.py       # /, /home, /admin/*
│   ├── provision_routes.py  # /provision, /release, /reservation/*
│   ├── terminal_routes.py   # /terminal/*
│   └── socketio_handlers.py # WebSocket handlers
├── middlewares/         # Middleware functions
│   ├── __init__.py
│   └── auth.py          # @login_required, @admin_required
├── static/              # Static files (CSS, JS)
└── templates/           # HTML templates

## 🏗️ MVC Pattern Explanation

### Models (models/)
- **Chức năng**: Quản lý dữ liệu và business entities
- **Các lớp**:
  - `User`, `UserDatabase`: Quản lý người dùng
  - `VM`, `Reservation`: Quản lý máy ảo và đặt chỗ
  - `SSHSession`: Quản lý phiên SSH

### Views (templates/)
- **Chức năng**: Hiển thị giao diện người dùng
- **Templates**: HTML files với Jinja2 syntax
- **Static**: CSS, JavaScript files

### Controllers (controller/)
- **Chức năng**: Xử lý logic nghiệp vụ, kết nối Model và View
- **Các controller**:
  - `AuthController`: Xử lý đăng nhập/đăng ký
  - `DashboardController`: Xử lý dashboard và admin panel
  - `VMController`: Xử lý provisioning VM
  - `SSHController`: Xử lý SSH terminal connections

### Services (services/)
- **Chức năng**: Tương tác với external systems
- **Các service**:
  - `DockerService`: Giao tiếp với Docker pool
  - `SSHService`: Quản lý SSH connections
  - `AnsibleService`: Chạy Ansible playbooks

### Routes (routes/)
- **Chức năng**: Định tuyến URL đến controllers
- **Blueprints**:
  - `auth_bp`: Authentication routes
  - `main_bp`: Main application routes
  - `provision_bp`: Provisioning routes
  - `terminal_bp`: Terminal routes

## 🚀 Sử Dụng

### Chạy phiên bản MVC mới:
```bash
cd web
python3 app_mvc.py
```

### Hoặc với file cũ (để so sánh):
```bash
python3 app.py
```

## ✨ Ưu Điểm của MVC

1. **Separation of Concerns**: Mỗi phần có trách nhiệm riêng
2. **Maintainability**: Dễ bảo trì và cập nhật
3. **Scalability**: Dễ mở rộng với features mới
4. **Testability**: Dễ viết unit tests cho từng component
5. **Reusability**: Services và controllers có thể tái sử dụng

## 🔄 So Sánh với Monolithic

### Trước (Monolithic - app.py):
- ❌ 1000+ dòng code trong 1 file
- ❌ Logic lẫn lộn giữa routes, business logic, và data access
- ❌ Khó bảo trì và debug
- ❌ Khó test riêng từng phần

### Sau (MVC - app_mvc.py):
- ✅ Code được tách thành nhiều modules nhỏ
- ✅ Mỗi component có trách nhiệm rõ ràng
- ✅ Dễ tìm và sửa bugs
- ✅ Có thể test từng layer riêng biệt

## 📊 Flow Diagram

```
Request → Routes → Controller → Service → External System
              ↓         ↓           ↓
           Templates  Models    (Docker/SSH/Ansible)
              ↓         ↓
           Response ← View
```

## 🔧 Thêm Feature Mới

### Ví dụ: Thêm tính năng "Export Reports"

1. **Model** (`models/report.py`):
```python
class Report:
    def __init__(self, user, data):
        self.user = user
        self.data = data
```

2. **Service** (`services/report_service.py`):
```python
class ReportService:
    def generate_report(self, user):
        # Logic to generate report
        pass
```

3. **Controller** (`controller/report_controller.py`):
```python
class ReportController:
    def export_report(self):
        report = self.report_service.generate_report(user)
        return render_template('report.html', report=report)
```

4. **Route** (`routes/report_routes.py`):
```python
@report_bp.route('/report/export')
@login_required
def export_report():
    return report_controller.export_report()
```

5. **Register in app_mvc.py**:
```python
app.register_blueprint(report_bp)
```

## 📝 Notes

- File `app.py` cũ được giữ lại để tham khảo
- Tất cả chức năng đều giữ nguyên, chỉ tổ chức lại code
- Background tasks vẫn hoạt động bình thường
- SocketIO handlers được tổ chức riêng
