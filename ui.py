import bpy
from .auto_rigger import AutoRigProperties


class AR_PT_MainPanel(bpy.types.Panel):
    bl_label = "Auto Rigger"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Auto Rigger"

    def draw(self, context):
        layout = self.layout
        props = context.scene.ar_props

        # Settings Section
        box = layout.box()
        box.label(text="Rig Settings", icon='SETTINGS')

        row = box.row()
        row.prop(props, "generate_hands", toggle=True)
        row.prop(props, "generate_feet", toggle=True)

        row = box.row()
        row.prop(props, "bone_detail")
        row.label(text=f"Estimated Bones: {props.bone_count}")

        # Generation Controls
        layout.separator()
        layout.operator("ar.generate_rig", icon='ARMATURE_DATA')
        layout.operator("ar.resize_rig", icon='FULLSCREEN_ENTER')

        # Binding Controls
        layout.separator()
        layout.label(text="Mesh Binding", icon='MODIFIER')
        row = layout.row()
        row.operator("ar.bind_mesh", icon='LINKED')
        row.operator("ar.unbind_mesh", icon='UNLINKED')


def register():
    bpy.utils.register_class(AR_PT_MainPanel)


def unregister():
    bpy.utils.unregister_class(AR_PT_MainPanel)