import bpy, math
from mathutils import Vector

FRAMES=150
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.frame_start=1; scene.frame_end=FRAMES; scene.render.fps=30
scene.render.engine='BLENDER_EEVEE'; scene.eevee.taa_render_samples=16
scene.eevee.use_gtao=True; scene.eevee.gtao_distance=3; scene.eevee.gtao_factor=1.25
scene.render.resolution_x=1280; scene.render.resolution_y=720; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.filepath='frames/premium_car_'
scene.view_settings.look='AgX - Medium High Contrast'; scene.view_settings.exposure=-0.65

def material(name,color,rough=.65,metal=0.0):
 m=bpy.data.materials.new(name); m.use_nodes=True
 b=m.node_tree.nodes.get('Principled BSDF'); b.inputs['Base Color'].default_value=(*color,1)
 b.inputs['Roughness'].default_value=rough; b.inputs['Metallic'].default_value=metal
 return m
def look(obj,point): obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()
def cube(name,loc,scale,mat,bevel=.05):
 bpy.ops.mesh.primitive_cube_add(location=loc); o=bpy.context.object; o.name=name; o.scale=scale
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if bevel:
  m=o.modifiers.new('Soft edges','BEVEL');m.width=bevel;m.segments=3
 o.data.materials.append(mat); return o
def sphere(name,loc,scale,mat):
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;o.data.materials.append(mat);return o
def cylinder(name,loc,radius,depth,mat):
 bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=radius,depth=depth,location=loc);o=bpy.context.object;o.name=name;o.data.materials.append(mat);return o

# Photographic meadow light/background.
world=bpy.data.worlds.new('Meadow World');scene.world=world;world.use_nodes=True
nodes=world.node_tree.nodes;links=world.node_tree.links;nodes.clear()
out=nodes.new('ShaderNodeOutputWorld');bg=nodes.new('ShaderNodeBackground');env=nodes.new('ShaderNodeTexEnvironment')
env.image=bpy.data.images.load('assets/meadow_4k.exr');bg.inputs['Strength'].default_value=.30
links.new(env.outputs['Color'],bg.inputs['Color']);links.new(bg.outputs['Background'],out.inputs['Surface'])

grass=material('Grass',(0.075,.22,.085),.92); asphalt=material('Asphalt',(.045,.055,.065),.88)
cream=material('Road markings',(.93,.82,.50),.62); stone=material('Kerb',(.35,.37,.36),.82)
trunk=material('Bark',(.20,.075,.025),.92); leaf1=material('Leaves deep',(.045,.20,.07),.82);leaf2=material('Leaves warm',(.11,.31,.085),.8)
pink=material('Flowers',(.62,.16,.34),.58); white=material('White flowers',(.88,.82,.66),.7)

ground=cube('Textured meadow',(0,3,-.20),(15,13,.20),grass,.08)
ground.data.materials.clear()
gm=bpy.data.materials.new('Procedural grass');gm.use_nodes=True;n=gm.node_tree.nodes;l=gm.node_tree.links
bs=n.get('Principled BSDF');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=7;noise.inputs['Detail'].default_value=5;noise.inputs['Roughness'].default_value=.75
ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.018,.075,.02,1);ramp.color_ramp.elements[1].color=(.14,.34,.07,1)
bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.12
l.new(noise.outputs['Fac'],ramp.inputs['Fac']);l.new(ramp.outputs['Color'],bs.inputs['Base Color']);l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal']);bs.inputs['Roughness'].default_value=.9
ground.data.materials.append(gm)
cube('Curving road',(0,1,-.03),(15,3.0,.08),asphalt,.18)
for x in range(-13,14,3): cube('Road dash',(x,1,.07),(.75,.065,.015),cream,.02)
for x in (-15,15): cube('Kerb',(x,1,.02),(.08,3.2,.12),stone,.03)

for x,y,s in [(-8,6,1.15),(-5,8,.85),(6,7,1.0),(9,5,.9)]:
 cylinder('Tree trunk',(x,y,1.1*s),.24*s,2.2*s,trunk)
 for dx,dy,dz,ss,ma in [(-.55,0,2.3,.82,leaf1),(.45,.12,2.45,.9,leaf2),(0,-.18,3.0,.75,leaf1)]: sphere('Tree crown',(x+dx*s,y+dy*s,dz*s),(ss*s,ss*.82*s,ss*s),ma)
for i,x in enumerate([-10,-8,-6,5.5,7.2,9.2,11]):
 y=4.3+(i%2)*1.1;sphere('Shrub',(x,y,.55),(.65,.52,.55),leaf1 if i%2 else leaf2)
 for j in range(3): sphere('Flower',(x-.32+j*.30,y-.35,.72+j*.08),(.10,.10,.10),pink if (i+j)%2 else white)

def bbox(objs):
 pts=[]
 for o in objs:
  if o.type=='MESH': pts.extend(o.matrix_world@Vector(c) for c in o.bound_box)
 xs=[p.x for p in pts];ys=[p.y for p in pts];zs=[p.z for p in pts]
 return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)
def import_rig(path,name,height,loc):
 before=set(bpy.data.objects); actions=set(bpy.data.actions);bpy.ops.import_scene.gltf(filepath=path)
 objs=[o for o in bpy.data.objects if o not in before];acts=[a for a in bpy.data.actions if a not in actions]
 root=bpy.data.objects.new(name+'_ROOT',None);bpy.context.collection.objects.link(root)
 for o in objs:
  if o.parent is None:o.parent=root
 mnx,mxx,mny,mxy,mnz,mxz=bbox(objs);sc=height/max(mxz-mnz,.001)
 root.scale=(sc,sc,sc);root.location=(loc[0]-(mnx+mxx)*.5*sc,loc[1]-(mny+mxy)*.5*sc,loc[2]-mnz*sc)
 for arm in [o for o in objs if o.type=='ARMATURE']:
  act=next((a for a in acts if 'walking' in a.name.lower()),None) or (acts[0] if acts else None)
  if act:
   arm.animation_data_create();arm.animation_data.action=act
   for fc in act.fcurves:
    if not any(m.type=='CYCLES' for m in fc.modifiers):fc.modifiers.new(type='CYCLES')
 return root

pofi=import_rig('assets/Pofi_3D_rigged.glb','Pofi',3.65,(-3.8,-.15,.08));pofi.rotation_euler[2]=math.radians(-7)

# Authored CC0 vehicle mesh and materials.
before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath='assets/sedan.glb');carobjs=[o for o in bpy.data.objects if o not in before]
car=bpy.data.objects.new('CAR_ROOT',None);bpy.context.collection.objects.link(car)
for o in carobjs:
 if o.parent is None:o.parent=car
mnx,mxx,mny,mxy,mnz,mxz=bbox(carobjs);sc=3.7/max(mxx-mnx,.001)
car.scale=(sc,sc,sc);car.location=(1.9-(mnx+mxx)*.5*sc,.80-(mny+mxy)*.5*sc,.05-mnz*sc);car.rotation_euler[2]=math.radians(6)
car.keyframe_insert('location',frame=1);car.location.x=2.25;car.keyframe_insert('location',frame=150)

def add_text(body,loc,size,color,extrude,bevel):
 bpy.ops.object.text_add(location=loc,rotation=(math.radians(90),0,0));o=bpy.context.object
 o.data.body=body;o.data.align_x='CENTER';o.data.align_y='CENTER';o.data.size=size;o.data.extrude=extrude;o.data.bevel_depth=bevel;o.data.bevel_resolution=5;o.data.materials.append(color);return o
outline=material('Letter deep blue',(.015,.07,.16),.35); face=material('Letter warm cream',(.98,.70,.08),.30)
back=add_text('A   a',(0,3.10,4.42),1.68,outline,.115,.055);front=add_text('A   a',(0,3.02,4.42),1.55,face,.075,.035)
for o in (back,front):
 o.scale=(0,0,0);o.keyframe_insert('scale',frame=1);o.keyframe_insert('scale',frame=24)
 o.scale=(1,1,1);o.keyframe_insert('scale',frame=33);o.keyframe_insert('scale',frame=126)
 o.scale=(0,0,0);o.keyframe_insert('scale',frame=136)
 for fc in o.animation_data.action.fcurves:
  for kp in fc.keyframe_points:kp.interpolation='BEZIER'

bpy.ops.object.empty_add(location=(0,1.1,1.65));focus=bpy.context.object
bpy.ops.object.camera_add(location=(0,-13.2,3.45));cam=bpy.context.object;cam.data.lens=53;look(cam,(0,1.1,1.75));scene.camera=cam
cam.data.dof.use_dof=True;cam.data.dof.focus_object=focus;cam.data.dof.aperture_fstop=7.0
cam.keyframe_insert('location',frame=1);cam.location=(.28,-12.75,3.32);cam.keyframe_insert('location',frame=150)
for fc in cam.animation_data.action.fcurves:
 for kp in fc.keyframe_points:kp.interpolation='BEZIER'
for loc,energy,color,size in [((-5,-4,9),950,(1.0,.82,.64),6),((6,-2,6),650,(.62,.76,1.0),5),((0,7,8),800,(1.0,.65,.44),4)]:
 bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=energy;light.data.color=color;light.data.size=size;look(light,(0,1,1.6))

bpy.ops.wm.save_as_mainfile(filepath='a_premium_car_canary.blend')
bpy.ops.render.render(animation=True)
