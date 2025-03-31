import bpy
from mathutils import Vector
from .utils import create_bone, delete_bones, calculate_bone_count


class AutoRigProperties(bpy.types.PropertyGroup):
    generate_hands: bpy.props.BoolProperty(
        name="Generate Hands",
        default=True,
        description="Generate hand bones with fingers",
        update=lambda self, context: self.update_bone_count()
    )

    generate_feet: bpy.props.BoolProperty(
        name="Generate Feet",
        default=True,
        description="Generate foot bones with toes",
        update=lambda self, context: self.update_bone_count()
    )

    bone_detail: bpy.props.IntProperty(
        name="Detail Level",
        min=3, max=6,
        default=4,
        description="Number of spine segments",
        update=lambda self, context: self.update_bone_count()
    )

    bone_count: bpy.props.IntProperty(
        name="Estimated Bones",
        default=0,
        description="Estimated total number of bones"
    )

    def update_bone_count(self):
        try:
            self.bone_count = calculate_bone_count(self)
        except Exception as e:
            print(f"Error calculating bone count: {str(e)}")


class AR_OT_GenerateRig(bpy.types.Operator):
    bl_idname = "ar.generate_rig"
    bl_label = "Generate Rig"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

            props = context.scene.ar_props
            create_rig(props)
            self.report({'INFO'}, f"Rig generated with {props.bone_count} bones")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to generate rig: {str(e)}")
            return {'CANCELLED'}
        return {'FINISHED'}


class AR_OT_ResizeRig(bpy.types.Operator):
    bl_idname = "ar.resize_rig"
    bl_label = "Resize to Mesh"

    def execute(self, context):
        try:
            rig = bpy.data.objects.get("AutoRig")
            mesh = context.active_object

            if not rig:
                self.report({'ERROR'}, "No AutoRig found - generate one first")
                return {'CANCELLED'}

            if not mesh or mesh.type != 'MESH':
                self.report({'ERROR'}, "Select a mesh object first")
                return {'CANCELLED'}

            bbox = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
            height = max(v.z for v in bbox) - min(v.z for v in bbox)

            if height <= 0:
                self.report({'ERROR'}, "Invalid mesh dimensions")
                return {'CANCELLED'}

            scale_factor = height / 2.5
            rig.scale = (scale_factor, scale_factor, scale_factor)
            bpy.ops.object.transform_apply(scale=True)

            self.report({'INFO'}, f"Rig scaled by {scale_factor:.2f}x")
        except Exception as e:
            self.report({'ERROR'}, f"Resize failed: {str(e)}")
            return {'CANCELLED'}
        return {'FINISHED'}


class AR_OT_BindMesh(bpy.types.Operator):
    bl_idname = "ar.bind_mesh"
    bl_label = "Bind Mesh"

    def execute(self, context):
        try:
            rig = bpy.data.objects.get("AutoRig")
            mesh = context.active_object

            if not rig:
                self.report({'ERROR'}, "Generate a rig first")
                return {'CANCELLED'}

            if not mesh or mesh.type != 'MESH':
                self.report({'ERROR'}, "Select a mesh object first")
                return {'CANCELLED'}

            # Select the rig and make it active
            bpy.ops.object.select_all(action='DESELECT')
            mesh.select_set(True)
            rig.select_set(True)
            context.view_layer.objects.active = rig

            # Parent with automatic weights
            bpy.ops.object.parent_set(type='ARMATURE_AUTO')

            # Reselect the mesh as active
            context.view_layer.objects.active = mesh
            self.report({'INFO'}, f"Successfully bound {mesh.name} to rig")

        except Exception as e:
            self.report({'ERROR'}, f"Binding failed: {str(e)}")
            return {'CANCELLED'}
        return {'FINISHED'}


class AR_OT_UnbindMesh(bpy.types.Operator):
    bl_idname = "ar.unbind_mesh"
    bl_label = "Unbind Mesh"

    def execute(self, context):
        try:
            removed = 0
            for obj in context.selected_objects:
                if obj.type == 'MESH':
                    for mod in obj.modifiers:
                        if mod.type == 'ARMATURE':
                            obj.modifiers.remove(mod)
                            removed += 1
            if removed == 0:
                self.report({'WARNING'}, "No armature modifiers found")
            else:
                self.report({'INFO'}, f"Removed {removed} armature modifiers")
        except Exception as e:
            self.report({'ERROR'}, f"Unbind failed: {str(e)}")
            return {'CANCELLED'}
        return {'FINISHED'}


def create_rig(props):
    try:
        # Clean existing rig
        if "AutoRig" in bpy.data.objects:
            old_rig = bpy.data.objects["AutoRig"]
            old_rig.select_set(True)
            bpy.ops.object.delete()

        # Create new armature
        bpy.ops.object.armature_add(enter_editmode=True)
        armature = bpy.context.object
        armature.name = "AutoRig"
        delete_bones(armature)

        # Core bones
        root = create_bone(armature, "Root", (0, 0, 0), (0, 0, 0.1))
        pelvis = create_bone(armature, "Pelvis", (0, 0, 0.1), (0, 0, 0.5), root)

        # Spine system
        spine_bones = create_spine(armature, pelvis, props.bone_detail)

        # Limbs
        create_limbs(armature, pelvis, props)

        bpy.ops.object.mode_set(mode='OBJECT')
        return armature

    except Exception as e:
        bpy.ops.object.mode_set(mode='OBJECT')
        raise RuntimeError(f"Rig creation failed: {str(e)}") from e


def create_spine(armature, parent, detail):
    try:
        detail = max(min(int(detail), 6), 3)  # Clamp value
        positions = [(0, 0, parent.tail.z + i * 0.3) for i in range(detail + 1)]

        spine_bones = []
        for i in range(len(positions) - 1):
            bone_name = f"Spine_{i:02d}"
            bone = create_bone(armature, bone_name,
                               Vector(positions[i]),
                               Vector(positions[i + 1]),
                               spine_bones[-1] if spine_bones else parent)
            spine_bones.append(bone)

        # Neck & Head
        neck = create_bone(armature, "Neck",
                           spine_bones[-1].tail,
                           spine_bones[-1].tail + Vector((0, 0, 0.2)),
                           spine_bones[-1])

        create_bone(armature, "Head",
                    neck.tail,
                    neck.tail + Vector((0, 0, 0.3)),
                    neck)

        return spine_bones
    except IndexError:
        raise RuntimeError("Failed to create spine - invalid bone positions")
    except Exception as e:
        raise RuntimeError(f"Spine creation failed: {str(e)}") from e


def create_limbs(armature, pelvis, props):
    try:
        for side in ['L', 'R']:
            create_arm(armature, pelvis, side, props)
            create_leg(armature, pelvis, side, props)
    except Exception as e:
        raise RuntimeError(f"Limb creation failed: {str(e)}") from e


def create_arm(armature, pelvis, side, props):
    try:
        sign = -1 if side == 'L' else 1

        # Find last spine bone dynamically
        spine_bones = [b for b in armature.data.edit_bones if b.name.startswith("Spine_")]
        if not spine_bones:
            raise RuntimeError("No spine bones found for arm attachment")

        last_spine = sorted(spine_bones, key=lambda x: x.name)[-1]

        # Clavicle
        clavicle = create_bone(armature, f"Clavicle_{side}",
                               last_spine.tail + Vector((sign * 0.2, 0, 0)),
                               last_spine.tail + Vector((sign * 0.4, 0, 0)),
                               last_spine)

        # Arm chain
        upper_arm = create_bone(armature, f"UpperArm_{side}",
                                clavicle.tail,
                                clavicle.tail + Vector((sign * 0.3, 0, -0.2)),
                                clavicle)

        lower_arm = create_bone(armature, f"LowerArm_{side}",
                                upper_arm.tail,
                                upper_arm.tail + Vector((sign * 0.3, 0, -0.2)),
                                upper_arm)

        if props.generate_hands:
            create_hand(armature, lower_arm, side)

    except Exception as e:
        raise RuntimeError(f"Arm creation failed: {str(e)}") from e


def create_hand(armature, parent, side):
    try:
        wrist = create_bone(armature, f"Wrist_{side}",
                            parent.tail,
                            parent.tail + Vector((0, 0, -0.1)),
                            parent)

        # Fingers
        for i in range(5):
            finger_bones = []
            for j in range(3):
                pos = wrist.tail + Vector((i * 0.1 - 0.2, 0, -j * 0.1))
                bone = create_bone(armature, f"Finger_{side}_{i}_{j}",
                                   pos,
                                   pos + Vector((0.1, 0, -0.1)),
                                   finger_bones[-1] if finger_bones else wrist)
                finger_bones.append(bone)
    except Exception as e:
        raise RuntimeError(f"Hand creation failed: {str(e)}") from e


def create_leg(armature, pelvis, side, props):
    try:
        sign = -1 if side == 'L' else 1
        hip_pos = Vector((sign * 0.2, 0, pelvis.tail.z))

        hip = create_bone(armature, f"Hip_{side}",
                          hip_pos,
                          hip_pos + Vector((sign * 0.1, 0, -0.2)),
                          pelvis)

        thigh = create_bone(armature, f"Thigh_{side}",
                            hip.tail,
                            hip.tail + Vector((0, 0, -0.5)),
                            hip)

        calf = create_bone(armature, f"Calf_{side}",
                           thigh.tail,
                           thigh.tail + Vector((0, 0, -0.5)),
                           thigh)

        if props.generate_feet:
            create_foot(armature, calf, side)

    except Exception as e:
        raise RuntimeError(f"Leg creation failed: {str(e)}") from e


def create_foot(armature, parent, side):
    try:
        foot = create_bone(armature, f"Foot_{side}",
                           parent.tail,
                           parent.tail + Vector((0.1, 0, -0.1)),
                           parent)

        # Toes
        for i in range(5):
            toe_start = foot.tail + Vector((i * 0.05 - 0.1, 0, 0))
            create_bone(armature, f"Toe_{side}_{i}",
                        toe_start,
                        toe_start + Vector((0.05, 0, -0.1)),
                        foot)
    except Exception as e:
        raise RuntimeError(f"Foot creation failed: {str(e)}") from e


def register():
    bpy.utils.register_class(AutoRigProperties)
    bpy.utils.register_class(AR_OT_GenerateRig)
    bpy.utils.register_class(AR_OT_ResizeRig)
    bpy.utils.register_class(AR_OT_BindMesh)
    bpy.utils.register_class(AR_OT_UnbindMesh)
    bpy.types.Scene.ar_props = bpy.props.PointerProperty(type=AutoRigProperties)


def unregister():
    bpy.utils.unregister_class(AR_OT_UnbindMesh)
    bpy.utils.unregister_class(AR_OT_BindMesh)
    bpy.utils.unregister_class(AR_OT_ResizeRig)
    bpy.utils.unregister_class(AR_OT_GenerateRig)
    bpy.utils.unregister_class(AutoRigProperties)
    del bpy.types.Scene.ar_props