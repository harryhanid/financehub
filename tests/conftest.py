import os
import sys

# Add parent (Financehub root) to path so we can import app and app.modules
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app_dir = os.path.join(root_dir, "app")
sys.path.insert(0, app_dir)
sys.path.insert(0, root_dir)
