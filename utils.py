import bpy
from mathutils import Vector

def create_bone(armature, name, head, tail, parent=None, roll=0):
    bone = armature.data.edit_bones.new(name)
    bone.head = head
    bone.tail = tail
    bone.roll = roll
    if parent:
        bone.parent = parent
    return bone

def delete_bones(armature):
    for bone in armature.data.edit_bones:
        armature.data.edit_bones.remove(bone)

def calculate_bone_count(props):
    base = 20  # Core bones
    spine = props.bone_detail
    limbs = 16  # 8 per side
    hands = 30 if props.generate_hands else 0  # 15 per hand
    feet = 10 if props.generate_feet else 0    # 5 per foot
    return base + spine + limbs + hands + feet