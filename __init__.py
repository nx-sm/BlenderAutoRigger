bl_info = {
    "name": "Auto Rigger",
    "author": "Sergio Matsak",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Auto Rigger",
    "description": "Simple auto-rigging solution with UI controls for low-mid humanoid models",
    "category": "Rigging",
}

import bpy
from . import auto_rigger, ui

def register():
    auto_rigger.register()
    ui.register()

def unregister():
    ui.unregister()
    auto_rigger.unregister()

if __name__ == "__main__":
    register()