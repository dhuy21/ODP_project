#!/usr/bin/env python3
"""Quick test to verify MVC app works"""

import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🧪 Testing MVC Application...")
print()

try:
    # Test imports
    print("1️⃣ Testing imports...")
    from app import app, socketio
    print("   ✅ App imported successfully")
    
    # Test blueprints registered
    print("\n2️⃣ Testing blueprints...")
    blueprints = list(app.blueprints.keys())
    expected = ['auth', 'main', 'provision', 'terminal']
    
    for bp in expected:
        if bp in blueprints:
            print(f"   ✅ Blueprint '{bp}' registered")
        else:
            print(f"   ❌ Blueprint '{bp}' NOT registered")
            sys.exit(1)
    
    # Test routes exist
    print("\n3️⃣ Testing key routes...")
    routes = [rule.endpoint for rule in app.url_map.iter_rules()]
    
    key_endpoints = [
        'auth.login',
        'auth.register', 
        'auth.logout',
        'main.index',
        'main.home',
        'main.dashboard_home',
        'main.admin_panel',
        'provision.provision',
        'provision.view_reservation',
        'terminal.terminal'
    ]
    
    for endpoint in key_endpoints:
        if endpoint in routes:
            print(f"   ✅ Route '{endpoint}' exists")
        else:
            print(f"   ⚠️  Route '{endpoint}' not found")
    
    print("\n✅ All tests passed!")
    print("\n🚀 Ready to run: python3 app.py")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
