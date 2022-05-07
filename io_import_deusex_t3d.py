# This Python file uses the following encoding: utf-8

import bpy
import mathutils as mu
import re

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty
from bpy.types import Operator

bl_info = {
    "name": "DeusEx T3D Import",
    "description": "Imports a DeusEx T3D file",
    "author": "Petr S.",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "File > Import",
    "support": "COMMUNITY",
    "category": "Import-Export"
    }

    
class ImportT3dData(Operator, ImportHelper):
    """Import a DeusEx T3D scene file into Blender"""
    bl_idname = "import_deusex_t3d.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import DeusEx T3D Data"

    # ImportHelper mixin class uses this
    filename_ext = ".t3d"

    filter_glob: StringProperty(
            default="*.t3d",
            options={'HIDDEN'},
            maxlen=255,  # Max internal buffer length, longer would be clamped.
            )

    def execute(self, context):
        return


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(
        ImportT3dData.bl_idname,
        text="DeusEx Game Level (*.t3d)")


classes = [
    ImportT3dData
]


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
