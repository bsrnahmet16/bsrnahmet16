import bpy, math, sys
from mathutils import Vector

kind = "solo"
if "--" in sys.argv:
    args = sys.argv[sys.argv.index("--")+1:]
    if args: kind = args[0]
ASSETS = {
 "Melipo":"assets/Melipo_3D_rigged.glb",
 "Pofi":"assets/Pofi_3D_rigged.glb",
 "Zipzi":"assets/Zipzi_3D_rigged.glb",
 "Luma":"assets/Luma_3D_rigged.glb",
}
bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.frame_start=1; scene.frame_end=120; scene.render.fps=30
scene.render.engine="BLENDER_EEVEE"; scene.eevee.taa_render_samples=8
scene.eevee.use_gtao=True; scene.eevee.gtao_distance=3; scene.eevee.gtao_factor=1.15
scene.render.resolution_x=1280; scene.render.resolution_y=720; scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"; scene.render.filepath=f"frames/{kind}_"
scene.world.color=(0.055,0.095,0.14)
scene.view_settings.look="AgX - Base Contrast"; scene.view_settings.exposure=-0.30

def mat(name,color,rough=.78,metal=0):
 m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
 b=m.node_tree.nodes.get("Principled BSDF"); b.inputs["Base Color"].default_value=(*color,1); b.inputs["Roughness"].default_value=rough; b.inputs["Metallic"].default_value=metal
 return m
def look(obj,p): obj.rotation_euler=(Vector(p)-obj.location).to_track_quat("-Z","Y").to_euler()
def cube(name,loc,scale,color,bevel=.12):
 bpy.ops.mesh.primitive_cube_add(location=loc); o=bpy.context.object; o.name=name; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if bevel:
  mod=o.modifiers.new("Soft edges","BEVEL"); mod.width=bevel; mod.segments=3
 o.data.materials.append(mat(name+"Mat",color)); return o
def sphere(name,loc,scale,color):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=loc); o=bpy.context.object; o.name=name; o.scale=scale; o.data.materials.append(mat(name+"Mat",color)); return o
def cyl(name,loc,radius,depth,color,rot=(0,0,0)):
 bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=radius,depth=depth,location=loc,rotation=rot); o=bpy.context.object;o.name=name;o.data.materials.append(mat(name+"Mat",color));return o
def text_obj(body,loc,size=1.35):
 bpy.ops.object.text_add(location=loc,rotation=(math.radians(90),0,0)); o=bpy.context.object; o.data.body=body;o.data.align_x="CENTER";o.data.align_y="CENTER";o.data.size=size;o.data.extrude=.045;o.data.bevel_depth=.018
 o.data.materials.append(mat("LetterMat",(0.97,0.78,0.12),.58)); return o

# ground and environment
if kind=="solo":
 cube("Grass",(0,1,-.18),(11,9,.18),(0.16,.38,.20),.08)
 for x,y,s in [(-6,3,1.1),(-4,5,.85),(4,5,1),(6,3,.9)]:
  cyl("Trunk",(x,y,1.0*s),.28*s,2.0*s,(.25,.11,.045))
  sphere("Crown",(x,y,2.7*s),(1.3*s,1.1*s,1.3*s),(.12,.34,.16))
 for x in [-7,-5,4.8,6.5]:
  sphere("Flower",(x,0,.18),(.18,.18,.18),(.62,.25,.46))
elif kind=="object":
 cube("Grass",(0,2,-.22),(11,9,.22),(.18,.39,.20),.08)
 cube("Road",(0,0,-.02),(11,3.2,.08),(.14,.16,.18),.05)
 for x in range(-8,9,3): cube("Stripe",(x,-.1,.08),(.75,.08,.018),(.92,.83,.48),.02)
 # recognizable rounded toy car
 cube("CarBody",(2.0,.3,.72),(1.85,.72,.48),(.18,.42,.68),.28)
 cube("CarCabin",(2.0,.3,1.30),(1.05,.62,.42),(.28,.58,.78),.22)
 for x in [1.0,3.0]:
  for y in [-.45,.95]: cyl("Wheel",(x,y,.48),.30,.20,(.045,.05,.055),rot=(math.radians(90),0,0))
else:
 cube("Meadow",(0,2,-.18),(11,9,.18),(.17,.37,.21),.08)
 for x,y in [(-7,3),(7,3),(-6,6),(6,6)]:
  cyl("Trunk",(x,y,1),.25,2,(.26,.12,.05)); sphere("Crown",(x,y,2.7),(1.2,1.0,1.3),(.13,.33,.17))

# soft sun disk
sphere("Sun",(-6,5,7),(1.0,1.0,1.0),(.95,.68,.24))

# camera
cam_y=-13.8 if kind!="group" else -15.8
bpy.ops.object.camera_add(location=(0,cam_y,3.7)); cam=bpy.context.object; cam.data.lens=50; look(cam,(0,0,2)); scene.camera=cam
# balanced lights
for typ,loc,energy,color,size in [
 ("AREA",(-5,-6,9),850,(1.0,.88,.74),7),
 ("AREA",(6,-3,6),560,(.68,.80,.94),6),
 ("AREA",(0,4,8),600,(1.0,.75,.58),5)]:
 bpy.ops.object.light_add(type=typ,location=loc); l=bpy.context.object;l.data.energy=energy;l.data.color=color;l.data.size=size;look(l,(0,0,2))

def bbox(objs):
 pts=[]
 for o in objs:
  if o.type=="MESH": pts += [o.matrix_world@Vector(c) for c in o.bound_box]
 xs=[p.x for p in pts];ys=[p.y for p in pts];zs=[p.z for p in pts]
 return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)
def add_character(label,x):
 before=set(bpy.data.objects); acts=set(bpy.data.actions)
 bpy.ops.import_scene.gltf(filepath=ASSETS[label])
 imported=[o for o in bpy.data.objects if o not in before]; newacts=[a for a in bpy.data.actions if a not in acts]
 root=bpy.data.objects.new(label+"_ROOT",None);bpy.context.collection.objects.link(root)
 for o in imported:
  if o.parent is None:o.parent=root
 mnx,mxx,mny,mxy,mnz,mxz=bbox(imported); sc=3.55/max(mxz-mnz,.001)
 root.scale=(sc,sc,sc);root.location=(x-(mnx+mxx)*.5*sc,-(mny+mxy)*.5*sc,-mnz*sc)
 for arm in [o for o in imported if o.type=="ARMATURE"]:
  pref=None
  tokens=("Agree_Gesture","Walking","Running","baselayer") if kind=="group" else ("Walking","Agree_Gesture","Running","baselayer")
  for token in tokens:
   pref=next((a for a in newacts if token.lower() in a.name.lower()),None)
   if pref:break
  if pref:
   arm.animation_data_create();arm.animation_data.action=pref
   for fc in pref.fcurves:
    if not any(m.type=="CYCLES" for m in fc.modifiers):fc.modifiers.new(type="CYCLES")
  if arm.pose and "headfront" in arm.pose.bones:
   try:
    drv=arm.pose.bones["headfront"].driver_add("scale",1).driver;drv.expression="1.0+0.006*sin(frame*0.45)"
   except TypeError:pass

if kind=="solo":
 add_character("Melipo",-1.7); text_obj("A  a",(2.6,.15,2.5),1.55)
elif kind=="object":
 add_character("Pofi",-2.7); text_obj("A  a",(0,2.7,4.8),1.25)
else:
 for label,x in zip(("Melipo","Pofi","Zipzi","Luma"),(-4.2,-1.4,1.4,4.2)): add_character(label,x)
 text_obj("A  a",(0,2.6,5.0),1.20)

cam.keyframe_insert(data_path="location",frame=1); cam.location.y=cam_y+.18;cam.keyframe_insert(data_path="location",frame=60);cam.location.y=cam_y;cam.keyframe_insert(data_path="location",frame=120)
for fc in cam.animation_data.action.fcurves:
 for kp in fc.keyframe_points:kp.interpolation="BEZIER"
bpy.ops.wm.save_as_mainfile(filepath=f"a_{kind}_canary.blend")
bpy.ops.render.render(animation=True)
