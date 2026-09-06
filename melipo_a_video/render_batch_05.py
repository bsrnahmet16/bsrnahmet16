import bpy, math, sys
from mathutils import Vector

SCENE=int(sys.argv[sys.argv.index("--")+1]) if "--" in sys.argv else 1
DURATIONS={13:5.700,14:5.330,15:5.170}
FRAMES=round(DURATIONS[SCENE]*30)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.frame_start=1; scene.frame_end=FRAMES; scene.render.fps=30
scene.render.engine='BLENDER_EEVEE'; scene.eevee.taa_render_samples=16
scene.eevee.use_gtao=True; scene.eevee.gtao_distance=3; scene.eevee.gtao_factor=1.25
scene.render.resolution_x=1920; scene.render.resolution_y=1080; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.filepath=f'frames/scene_{SCENE:02d}_'
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
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;o.data.materials.append(mat)
 for p in o.data.polygons:p.use_smooth=True
 return o
def cylinder(name,loc,radius,depth,mat):
 bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=radius,depth=depth,location=loc);o=bpy.context.object;o.name=name;o.data.materials.append(mat);return o

# Stable physical daylight sky (no external-texture fallback colour).
world=bpy.data.worlds.new('Meadow World');scene.world=world;world.use_nodes=True
nodes=world.node_tree.nodes;links=world.node_tree.links;nodes.clear()
out=nodes.new('ShaderNodeOutputWorld');bg=nodes.new('ShaderNodeBackground');sky=nodes.new('ShaderNodeTexSky')
sky.sky_type='NISHITA';sky.sun_elevation=math.radians(42);sky.sun_rotation=math.radians(135);sky.altitude=.15;sky.air_density=.72;sky.dust_density=.65;sky.ozone_density=.85
bg.inputs['Strength'].default_value=.50
links.new(sky.outputs['Color'],bg.inputs['Color']);links.new(bg.outputs['Background'],out.inputs['Surface'])

grass=material('Grass',(0.075,.22,.085),.92); asphalt=material('Asphalt',(.045,.055,.065),.88)
cream=material('Road markings',(.93,.82,.50),.62); stone=material('Kerb',(.35,.37,.36),.82)
trunk=material('Bark',(.20,.075,.025),.92); leaf1=material('Leaves deep',(.045,.20,.07),.82);leaf2=material('Leaves warm',(.11,.31,.085),.8)
pink=material('Flowers',(.62,.16,.34),.58); white=material('White flowers',(.88,.82,.66),.7)
hill1=material('Distant hills',(.08,.30,.18),.9);hill2=material('Sunlit hills',(.18,.42,.20),.88);cloud=material('Soft clouds',(.92,.96,1.0),.72)

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
# Midground depth: layered hills and softly modelled clouds.
for x,z,s,ma in [(-8,.35,3.8,hill1),(-3,.15,3.2,hill2),(3,.28,4.0,hill1),(9,.10,3.4,hill2)]: sphere('Hill',(x,10,z),(s,1.4,s*.55),ma)
for x,z,s in [(-6,5.7,1.0),(1,6.2,.85),(7,5.5,1.15)]:
 for dx,dz,ss in [(-.8,0,.72),(0,.18,1.0),(.85,-.03,.66)]: sphere('Cloud',(x+dx*s,9.4,z+dz*s),(1.25*ss*s,.30,.62*ss*s),cloud)

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
  # Use only animations embedded in the canonical GLB.  The two teaching
  # shots gesture; the closing chorus of this batch is slightly more lively.
  wanted='running' if SCENE==13 else 'agree'
  act=next((a for a in acts if wanted in a.name.lower()),None) or (acts[0] if acts else None)
  if act:
   arm.animation_data_create();arm.animation_data.action=act
   if SCENE in (14,15):
    # The canonical Agree_Gesture spans about 13 seconds.  Compress its full
    # motion into this five-second teaching shot so both arms complete the
    # gesture instead of showing only the quiet opening pose.
    lo,hi=act.frame_range
    span=max(1.0,hi-lo);factor=max(1.0,FRAMES-1)/span
    for fc in act.fcurves:
     for kp in fc.keyframe_points:
      kp.co.x=1+(kp.co.x-lo)*factor
      kp.handle_left.x=1+(kp.handle_left.x-lo)*factor
      kp.handle_right.x=1+(kp.handle_right.x-lo)*factor
   for fc in act.fcurves:
    if not any(m.type=='CYCLES' for m in fc.modifiers):fc.modifiers.new(type='CYCLES')
   # The supplied body rig has no separate mouth shape keys.  Its headfront
   # bone is therefore driven by a very small vowel pulse.  The deformation
   # is deliberately bounded so the canonical face cannot drift.
   mouth=arm.pose.bones.get('headfront')
   if mouth:
    for f in range(10,FRAMES,14):
     mouth.scale=(1,1,1);mouth.keyframe_insert('scale',frame=max(1,f-3))
     mouth.scale=(1.0,.94,1.08) if SCENE==15 else (1.0,.975,1.04);mouth.keyframe_insert('scale',frame=f)
     mouth.scale=(1,1,1);mouth.keyframe_insert('scale',frame=min(FRAMES,f+4))
 return root

pofi_loc={13:(-2.55,-.05,-.46),14:(-2.55,-.05,-.46),15:(-2.55,-.05,-.46)}[SCENE]
pofi=import_rig('assets/Melipo_3D_rigged.glb','Melipo',5.25,pofi_loc);pofi.rotation_euler[2]=math.radians(-5)
if SCENE==13:
 # The verified word cue begins at 67.58 s; reveal the single canonical bear
 # 0.45 s earlier, at 67.13 s, and keep it visible through the scene boundary.
 reveal=max(1,round((67.13-65.70)*30));base_scale=tuple(pofi.scale)
 pofi.scale=(0,0,0);pofi.keyframe_insert('scale',frame=1);pofi.keyframe_insert('scale',frame=max(1,reveal-4))
 pofi.scale=base_scale;pofi.keyframe_insert('scale',frame=reveal);pofi.keyframe_insert('scale',frame=FRAMES)
pofi.keyframe_insert('location',frame=1)
pofi.location.x += .22
pofi.keyframe_insert('location',frame=max(2,FRAMES//2))
pofi.location.x -= .10
pofi.keyframe_insert('location',frame=FRAMES)
for fc in pofi.animation_data.action.fcurves:
 for kp in fc.keyframe_points: kp.interpolation='BEZIER'

# Original rounded 3D children's car: separate glossy body, glass, lights and wheels.
car=bpy.data.objects.new('CAR_ROOT',None);bpy.context.collection.objects.link(car)
blue=material('Car pearl blue',(.025,.24,.62),.20,.18);blue.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value=.55
glass=material('Windows',(.025,.12,.22),.10,.15);rubber=material('Tyres',(.012,.015,.018),.86);chrome=material('Chrome',(.48,.53,.58),.18,.88)
lamp=material('Warm headlights',(1.0,.72,.22),.18);red=material('Rear lamps',(.72,.025,.018),.25)
def uvpart(name,loc,scale,ma,parent=car):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(ma);o.parent=parent
 for p in o.data.polygons:p.use_smooth=True
 return o
body=uvpart('Rounded car body',(2.0,.72,.72),(2.15,.92,.57),blue)
hood=uvpart('Rounded hood',(2.92,.48,.94),(1.05,.82,.36),blue)
cab=uvpart('Cabin',(1.52,.82,1.32),(1.20,.76,.64),blue)
wind=uvpart('Front windscreen',(2.19,.12,1.46),(.70,.035,.40),glass)
rearwind=uvpart('Rear windscreen',(.86,.30,1.44),(.42,.035,.34),glass)
# Camera-facing side windows and door details make the vehicle immediately legible.
side_front=uvpart('Side front window',(1.94,-.055,1.43),(.48,.035,.36),glass)
side_rear=uvpart('Side rear window',(1.05,-.055,1.43),(.37,.035,.34),glass)
cube('Front door inset',(2.05,-.195,.91),(.58,.025,.40),blue,.12).parent=car
cube('Rear door inset',(1.02,-.195,.91),(.40,.025,.38),blue,.12).parent=car
cube('Front handle',(2.26,-.235,1.04),(.12,.025,.035),chrome,.025).parent=car
cube('Rear handle',(1.15,-.235,1.04),(.10,.025,.035),chrome,.025).parent=car
for x in (1.0,2.95):
 for y in (-.02,1.47):
  bpy.ops.mesh.primitive_torus_add(major_radius=.38,minor_radius=.14,major_segments=40,minor_segments=12,location=(x,y,.48),rotation=(math.radians(90),0,0));w=bpy.context.object;w.name='Tyre';w.data.materials.append(rubber);w.parent=car
  cylinder('Hub',(x,y,.48),.19,.10,chrome).rotation_euler[0]=math.radians(90);bpy.context.object.parent=car
for y in (.17,1.27): uvpart('Headlight',(3.82,y,.86),(.12,.15,.15),lamp)
cube('Front bumper',(3.78,.72,.54),(.11,.76,.09),chrome,.08).parent=car
car.rotation_euler[2]=math.radians(-2);car.keyframe_insert('location',frame=1);car.location.x=.20;car.keyframe_insert('location',frame=150)

def add_text(body,loc,size,color,extrude,bevel):
 bpy.ops.object.text_add(location=loc,rotation=(math.radians(90),0,0));o=bpy.context.object
 o.data.body=body;o.data.align_x='CENTER';o.data.align_y='CENTER';o.data.size=size;o.data.extrude=extrude;o.data.bevel_depth=bevel;o.data.bevel_resolution=5;o.data.materials.append(color);return o
outline=material('Letter deep blue',(.015,.07,.16),.35); face=material('Letter warm cream',(.98,.70,.08),.30)
back=add_text('A   a',(0,3.10,3.82),2.25,outline,.135,.065);front=add_text('A   a',(0,3.02,3.82),2.08,face,.088,.042)
for o in (back,front):
 if False:
  o.scale=(0,0,0);o.keyframe_insert('scale',frame=1);o.keyframe_insert('scale',frame=FRAMES)
 elif False:
  reveal=max(1,round(3.20*30))
  o.scale=(0,0,0);o.keyframe_insert('scale',frame=1);o.keyframe_insert('scale',frame=reveal-8)
  o.scale=(1,1,1);o.keyframe_insert('scale',frame=reveal);o.keyframe_insert('scale',frame=FRAMES)
 else:
  o.scale=(1,1,1);o.keyframe_insert('scale',frame=1)
  if SCENE in (14,15):
   # Readable teaching beats follow the sung A accents.
   for f in (18,58,100):
    o.scale=(1,1,1);o.keyframe_insert('scale',frame=max(1,f-5))
    o.scale=(1.12,1.12,1.12);o.keyframe_insert('scale',frame=f)
    o.scale=(1,1,1);o.keyframe_insert('scale',frame=min(FRAMES,f+6))
  o.scale=(1,1,1);o.keyframe_insert('scale',frame=FRAMES)
 for fc in o.animation_data.action.fcurves:
  for kp in fc.keyframe_points:kp.interpolation='BEZIER'

bpy.ops.object.empty_add(location=(0,1.1,1.65));focus=bpy.context.object
bpy.ops.object.camera_add(location=(0,-14.4,3.70));cam=bpy.context.object;cam.data.lens=50;look(cam,(0,1.1,1.75));scene.camera=cam
cam.data.dof.use_dof=True;cam.data.dof.focus_object=focus;cam.data.dof.aperture_fstop=7.0
cam.keyframe_insert('location',frame=1);cam.location=(.10,-14.1,3.62);cam.keyframe_insert('location',frame=150)
for fc in cam.animation_data.action.fcurves:
 for kp in fc.keyframe_points:kp.interpolation='BEZIER'
for loc,energy,color,size in [((-5,-4,9),950,(1.0,.82,.64),6),((6,-2,6),650,(.62,.76,1.0),5),((0,7,8),800,(1.0,.65,.44),4)]:
 bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=energy;light.data.color=color;light.data.size=size;look(light,(0,1,1.6))

# Small premium 3D bee for scene 3; it appears 0.45 s before the word "arı".
bee=bpy.data.objects.new('BEE_ROOT',None);bpy.context.collection.objects.link(bee)
bee.location=(1.25,.05,2.75)
bee_yellow=material('Bee gold',(1.0,.50,.025),.34); bee_dark=material('Bee dark',(.025,.018,.012),.60)
wing_mat=material('Bee wings',(.72,.90,1.0),.18); wing_mat.blend_method='BLEND'
body=sphere('Bee body',(0,0,0),(0.34,.24,.24),bee_yellow); body.parent=bee
for x in (-.13,.12):
 band=cylinder('Bee stripe',(x,0,0),.245,.09,bee_dark);band.rotation_euler[1]=math.radians(90);band.parent=bee
head=sphere('Bee head',(-.35,0,.03),(.20,.20,.20),bee_dark);head.parent=bee
for side in (-1,1):
 wing=sphere('Bee wing',(0,.18*side,.22),(.28,.08,.16),wing_mat);wing.parent=bee
 wing.rotation_euler[0]=math.radians(24*side);wing.keyframe_insert('rotation_euler',frame=1,index=0)
 wing.rotation_euler[0]=math.radians(-24*side);wing.keyframe_insert('rotation_euler',frame=5,index=0)
 for fc in wing.animation_data.action.fcurves: fc.modifiers.new(type='CYCLES')
if SCENE==4:
 reveal=1
 bee.scale=(0,0,0);bee.keyframe_insert('scale',frame=1);bee.keyframe_insert('scale',frame=reveal-5)
 bee.scale=(1,1,1);bee.keyframe_insert('scale',frame=reveal)
 bee.keyframe_insert('location',frame=reveal);bee.location=(1.65,.05,3.05);bee.keyframe_insert('location',frame=FRAMES)
else:
 bee.scale=(0,0,0);bee.keyframe_insert('scale',frame=1);bee.keyframe_insert('scale',frame=FRAMES)

# Hybrid premium plate: retain the canonical animated GLB character and exact
# Blender typography, while replacing the rejected procedural scenery/car.
def is_under(obj,root):
 p=obj
 while p:
  if p==root:return True
  p=p.parent
 return False
for obj in bpy.data.objects:
 if obj.type=='MESH' and not is_under(obj,pofi) and not is_under(obj,bee): obj.hide_render=True

# Soft semi-transparent contact shadow anchors Pofi to the photographed ground.
shadow_mat=bpy.data.materials.new('Pofi contact shadow'); shadow_mat.use_nodes=True
sb=shadow_mat.node_tree.nodes.get('Principled BSDF')
sb.inputs['Base Color'].default_value=(.012,.016,.020,1)
sb.inputs['Roughness'].default_value=1.0
sb.inputs['Alpha'].default_value=.28
shadow_mat.blend_method='BLEND'; shadow_mat.use_screen_refraction=True
bpy.ops.mesh.primitive_circle_add(vertices=64,radius=1.0,fill_type='NGON',location=(pofi_loc[0],.02,-.43),rotation=(math.radians(90),0,0))
contact=bpy.context.object; contact.name='Pofi soft contact shadow'
contact.scale=(.66,.15,1); contact.data.materials.append(shadow_mat)
scene.render.film_transparent=True
# Pixel-exact compositor background: fills the complete 1280x720 frame without
# perspective distortion, mirroring or uncovered black borders.
scene.use_nodes=True
cn=scene.node_tree.nodes; cl=scene.node_tree.links; cn.clear()
rl=cn.new('CompositorNodeRLayers')
bgimg=cn.new('CompositorNodeImage')
bgimg.image=bpy.data.images.load('assets/premium_car_background_v1.png' if SCENE in (5,6) else 'assets/premium_meadow_background_v1.png')
scale=cn.new('CompositorNodeScale'); scale.space='RENDER_SIZE'; scale.frame_method='CROP'
over=cn.new('CompositorNodeAlphaOver'); over.inputs[0].default_value=1.0
comp=cn.new('CompositorNodeComposite')
cl.new(bgimg.outputs['Image'],scale.inputs['Image'])
cl.new(scale.outputs['Image'],over.inputs[1])
cl.new(rl.outputs['Image'],over.inputs[2])
cl.new(over.outputs['Image'],comp.inputs['Image'])

bpy.ops.wm.save_as_mainfile(filepath=f'a_scene_{SCENE:02d}.blend')
bpy.ops.render.render(animation=True)
