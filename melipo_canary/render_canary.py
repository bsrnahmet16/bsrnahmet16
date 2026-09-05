import bpy
import math
from mathutils import Vector

FILES = [
    ("Melipo", "assets/Melipo_3D_rigged.glb", -4.2),
    ("Pofi", "assets/Pofi_3D_rigged.glb", -1.4),
    ("Zipzi", "assets/Zipzi_3D_rigged.glb", 1.4),
    ("Luma", "assets/Luma_3D_rigged.glb", 4.2),
]

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.actions, bpy.data.materials, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
    pass

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 300
scene.render.fps = 30
scene.render.engine = "BLENDER_EEVEE"
scene.eevee.use_gtao = True
scene.eevee.gtao_distance = 3
scene.eevee.gtao_factor = 1.25
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = "frames/frame_"
scene.world.color = (0.025, 0.055, 0.11)

def look_at(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()

def add_material(name, color, roughness=0.65):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat

# Ground
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
ground = bpy.context.object
ground.data.materials.append(add_material("Ground", (0.07, 0.16, 0.25), 0.82))

# Soft backdrop
bpy.ops.mesh.primitive_plane_add(size=35, location=(0, 5.5, 8), rotation=(math.radians(90), 0, 0))
back = bpy.context.object
back.data.materials.append(add_material("Backdrop", (0.04, 0.13, 0.24), 0.9))

# Camera
bpy.ops.object.camera_add(location=(0, -18.5, 4.2))
camera = bpy.context.object
camera.data.lens = 52
look_at(camera, (0, 0, 2.15))
scene.camera = camera

# Lighting
bpy.ops.object.light_add(type="AREA", location=(-5, -7, 9))
key = bpy.context.object
key.data.energy = 1250
key.data.shape = "DISK"
key.data.size = 7
look_at(key, (0, 0, 2))

bpy.ops.object.light_add(type="AREA", location=(6, -3, 6))
fill = bpy.context.object
fill.data.energy = 850
fill.data.color = (0.42, 0.68, 1.0)
fill.data.size = 6
look_at(fill, (0, 0, 2))

bpy.ops.object.light_add(type="AREA", location=(0, 4, 8))
rim = bpy.context.object
rim.data.energy = 1100
rim.data.color = (1.0, 0.55, 0.25)
rim.data.size = 5
look_at(rim, (0, 0, 2.5))

def bbox_world(objects):
    pts = []
    for obj in objects:
        if obj.type == "MESH":
            pts.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)

for index, (label, filepath, target_x) in enumerate(FILES):
    before_objects = set(bpy.data.objects)
    before_actions = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=filepath)
    imported = [o for o in bpy.data.objects if o not in before_objects]
    new_actions = [a for a in bpy.data.actions if a not in before_actions]

    root = bpy.data.objects.new(label + "_ROOT", None)
    bpy.context.collection.objects.link(root)
    for obj in imported:
        if obj.parent is None:
            obj.parent = root

    mnx, mxx, mny, mxy, mnz, mxz = bbox_world(imported)
    height = max(mxz - mnz, 0.001)
    scale = 3.45 / height
    root.scale = (scale, scale, scale)
    root.location.x = target_x - ((mnx + mxx) * 0.5 * scale)
    root.location.y = -((mny + mxy) * 0.5 * scale)
    root.location.z = -mnz * scale

    armatures = [o for o in imported if o.type == "ARMATURE"]
    for arm in armatures:
        preferred = None
        for token in ("Agree_Gesture", "Walking", "Running", "baselayer"):
            preferred = next((a for a in new_actions if token.lower() in a.name.lower()), None)
            if preferred:
                break
        if preferred:
            arm.animation_data_create()
            arm.animation_data.action = preferred
            for fc in preferred.fcurves:
                if not any(m.type == "CYCLES" for m in fc.modifiers):
                    fc.modifiers.new(type="CYCLES")

        # Very small facial pulse through the available front-head control.
        # This is deliberately subtle because the GLBs have no mouth morph targets.
        if arm.pose and "headfront" in arm.pose.bones:
            pb = arm.pose.bones["headfront"]
            try:
                drv = pb.driver_add("scale", 1).driver
                drv.expression = "1.0 + 0.004*sin(frame*0.42)"
            except TypeError:
                pass

# Gentle camera breathing, not a pan/zoom-only fake motion.
camera.keyframe_insert(data_path="location", frame=1)
camera.location.y = -18.15
camera.keyframe_insert(data_path="location", frame=150)
camera.location.y = -18.5
camera.keyframe_insert(data_path="location", frame=300)
for fc in camera.animation_data.action.fcurves:
    for kp in fc.keyframe_points:
        kp.interpolation = "BEZIER"

scene.view_settings.look = "Medium High Contrast"
scene.render.film_transparent = False
bpy.ops.wm.save_as_mainfile(filepath="melipo_canary.blend")
bpy.ops.render.render(animation=True)
