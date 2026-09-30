# 캐릭터를 등속으로 촬영해 WebP 낱장 시퀀스로 출력하는 블렌더 렌더 스크립트
#
# 사용법 (GUI 없이 실행)
#   blender -b -P turntable.py -- --out "…/char/pc" --frames 60 --camera move --pose sit
#   blender -b -P turntable.py -- --model "…/char.glb" --out "…" --camera move
#   blender -b -P turntable.py -- --out "…/char" --silhouette true --still true
#
# 핵심 — 회전·이동 키프레임 보간을 LINEAR 로 강제한다.
# 블렌더 기본값은 감속이 들어간 베지어 곡선이라, 그대로 두면
# 스크롤은 일정한데 캐릭터만 빨라졌다 느려진다. 가속·감속은 웹 코드가 처리한다.

import bpy
import sys
import os
import math
from mathutils import Vector


# ─────────────────────────────────────────────
def get_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []

    cfg = {
        "model":      None,      # .glb / .fbx / .obj. 없으면 임시 도형 생성
        "out":        "./out",
        "prefix":     "char_",
        "frames":     60,
        "width":      1600,
        "height":     900,
        "angle":      270.0,     # camera=fixed 일 때 오브젝트 회전 각도
        "orbit":      200.0,     # camera=move 일 때 카메라가 도는 각도
        "zoom":       2.35,      # 끝 지점 카메라 거리 배수 (시작은 이것의 0.42)
        "camera":     "fixed",   # fixed | move
        "pose":       "stand",   # stand | sit  (임시 도형에만 적용)
        "silhouette": False,     # 단색 실루엣 렌더
        "quality":    78,
        "samples":    48,
        "still":      False,
    }

    i = 0
    while i < len(argv):
        key = argv[i].lstrip("-")
        if key in cfg and i + 1 < len(argv):
            val, cur = argv[i + 1], cfg[key]
            if isinstance(cur, bool):
                cfg[key] = val.lower() in ("1", "true", "yes")
            elif isinstance(cur, int):
                cfg[key] = int(val)
            elif isinstance(cur, float):
                cfg[key] = float(val)
            else:
                cfg[key] = val
            i += 2
        else:
            i += 1
    return cfg


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials,
                  bpy.data.cameras, bpy.data.lights):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def make_mat(name, rgba, rough=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = rough
    return m


# ─────────────────────────────────────────────
# 임시 캐릭터 — 모델이 없을 때 파이프라인 검증 및 데모용
# 구와 타원체 조합. 서 있는 자세와 앉은 자세를 지원한다.
# ─────────────────────────────────────────────
def build_placeholder(pose="stand"):
    parts = []
    skin = make_mat("skin", (0.95, 0.92, 1.0, 1.0), 0.42)
    dark = make_mat("dark", (0.10, 0.06, 0.20, 1.0), 0.30)

    def ball(r, loc, scale=(1, 1, 1), rot=(0, 0, 0), mat=None, seg=48, ring=24):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=ring)
        o = bpy.context.object
        o.scale = scale
        o.rotation_euler = rot
        o.data.materials.append(mat or skin)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.shade_smooth()
        parts.append(o)
        return o

    if pose == "ball":
        # 가장 단순한 시안 — 구 하나. 회전이 보이도록 표면에 점 하나만 둔다.
        ball(1.5, (0, 0, 1.5), seg=64, ring=32)
        ball(0.26, (0.62, -1.18, 2.05), (1.0, 1.0, 1.0), mat=dark, seg=24, ring=12)
    elif pose == "sit":
        # 앉은 자세 — 몸통이 낮고 넓게, 다리가 앞으로
        ball(1.05, (0, 0, 0.92), (1.0, 0.86, 0.72))                  # 몸통
        ball(0.86, (0, 0, 2.05))                                     # 머리
        for s in (-1, 1):                                            # 무릎
            ball(0.46, (s * 0.46, -0.86, 0.46), (1.0, 1.5, 0.82))
        for s in (-1, 1):                                            # 팔
            ball(0.30, (s * 1.02, -0.22, 0.98), (0.8, 1.25, 1.0),
                 (0, math.radians(s * 12), 0))
        for s in (-1, 1):                                            # 눈
            ball(0.15, (s * 0.30, -0.76, 2.16), (1.0, 0.5, 1.25), mat=dark, seg=20, ring=10)
    else:
        ball(1.00, (0, 0, 0.95), (1.0, 0.92, 0.82))                  # 몸통
        ball(0.85, (0, 0, 2.30))                                     # 머리
        for s in (-1, 1):                                            # 지느러미
            ball(0.34, (s * 1.02, 0, 1.05), (0.5, 0.85, 1.25),
                 (0, math.radians(s * 16), 0))
        for s in (-1, 1):                                            # 눈
            ball(0.15, (s * 0.30, -0.74, 2.45), (1.0, 0.55, 1.25), mat=dark, seg=20, ring=10)

    return parts


def import_model(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    else:
        raise RuntimeError("지원하지 않는 형식: " + ext)
    return [o for o in bpy.context.scene.objects if o.type in ("MESH", "ARMATURE", "EMPTY")]


# ─────────────────────────────────────────────
def normalize(objs, target_height=3.0):
    meshes = [o for o in objs if o.type == "MESH"]
    if not meshes:
        return target_height

    xs, ys, zs = [], [], []
    for o in meshes:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            xs.append(w.x); ys.append(w.y); zs.append(w.z)

    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    h = max(zs) - min(zs) or 1.0
    s = target_height / h

    pivot = bpy.data.objects.new("PIVOT", None)
    bpy.context.collection.objects.link(pivot)
    for o in objs:
        if o.parent is None:
            o.parent = pivot
            o.matrix_parent_inverse = pivot.matrix_world.inverted()
    pivot.scale = (s, s, s)
    pivot.location = (-cx * s, -cy * s, -min(zs) * s)

    root = bpy.data.objects.new("ROOT", None)
    bpy.context.collection.objects.link(root)
    pivot.parent = root

    return target_height


# ─────────────────────────────────────────────
def setup_camera(height, w_px, h_px, cfg):
    """카메라를 축(CAM_PIVOT)에 묶어 둔다. camera=move 면 그 축을 돌린다."""
    far = height * cfg["zoom"]
    if h_px > w_px:
        far *= 1.22

    pivot = bpy.data.objects.new("CAM_PIVOT", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = (0, 0, height * 0.52)

    cam_data = bpy.data.cameras.new("CAM")
    cam_data.lens = 58
    cam = bpy.data.objects.new("CAM", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.parent = pivot

    target = bpy.data.objects.new("CAM_TARGET", None)
    bpy.context.collection.objects.link(target)
    target.location = (0, 0, height * 0.52)

    con = cam.constraints.new(type="TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"

    bpy.context.scene.camera = cam
    return cam, pivot, far


def setup_lights(height, silhouette=False):
    if silhouette:
        return
    d = height * 2.0

    def area(name, loc, energy, size, rot):
        ld = bpy.data.lights.new(name, type="AREA")
        ld.energy, ld.size = energy, size
        lo = bpy.data.objects.new(name, ld)
        bpy.context.collection.objects.link(lo)
        lo.location, lo.rotation_euler = loc, rot

    area("KEY",  (-d * 0.8, -d * 0.9, d * 1.15), 900, height * 2.2,
         (math.radians(52), 0, math.radians(-40)))
    area("FILL", (d * 1.0, -d * 0.5, height * 0.8), 300, height * 2.6,
         (math.radians(78), 0, math.radians(58)))
    area("RIM",  (0, d * 1.1, d * 1.0), 550, height * 1.8,
         (math.radians(-140), 0, 0))


def make_silhouette():
    """모든 재질을 평평한 어두운 발광체로 교체한다. 조명 없이 단색으로 찍힌다."""
    flat = bpy.data.materials.new("SILHOUETTE")
    flat.use_nodes = True
    nt = flat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = nt.nodes["Material Output"]
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.10, 0.06, 0.20, 1.0)
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])

    for o in bpy.context.scene.objects:
        if o.type == "MESH":
            o.data.materials.clear()
            o.data.materials.append(flat)


# ─────────────────────────────────────────────
def force_linear(obj):
    """4.4+ 는 Action 이 슬롯 구조라 action.fcurves 가 없다. 양쪽 모두 훑는다."""
    ad = obj.animation_data
    if not ad or not ad.action:
        return 0
    action = ad.action
    curves = []

    if hasattr(action, "fcurves"):
        curves = list(action.fcurves)
    else:
        for layer in getattr(action, "layers", []):
            for strip in getattr(layer, "strips", []):
                bags = getattr(strip, "channelbags", None)
                if bags is None:
                    slot = getattr(ad, "action_slot", None)
                    if slot is not None and hasattr(strip, "channelbag"):
                        bag = strip.channelbag(slot)
                        bags = [bag] if bag else []
                    else:
                        bags = []
                for bag in bags:
                    curves.extend(getattr(bag, "fcurves", []))

    n = 0
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
            kp.easing = "AUTO"
            n += 1
    return n


def animate(cfg, height, cam, cam_pivot, far):
    try:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    except Exception as e:
        print("[turntable] 기본 보간 설정 실패:", e)

    last = cfg["frames"]
    fixed = 0

    if cfg["camera"] == "move":
        # 카메라가 앞 가까이에서 뒤 멀리로 이동한다. 대상은 가만히 있다.
        near = far * 0.42
        cam.location = (0, -near, height * 0.10)
        cam.keyframe_insert(data_path="location", frame=1)
        cam.location = (0, -far, height * 0.58)
        cam.keyframe_insert(data_path="location", frame=last)

        cam_pivot.rotation_euler = (0, 0, 0)
        cam_pivot.keyframe_insert(data_path="rotation_euler", index=2, frame=1)
        cam_pivot.rotation_euler = (0, 0, math.radians(cfg["orbit"]))
        cam_pivot.keyframe_insert(data_path="rotation_euler", index=2, frame=last)

        fixed += force_linear(cam) + force_linear(cam_pivot)
    else:
        cam.location = (0, -far, height * 0.62)
        root = bpy.data.objects.get("ROOT")
        root.rotation_euler = (0, 0, 0)
        root.keyframe_insert(data_path="rotation_euler", index=2, frame=1)
        root.rotation_euler = (0, 0, math.radians(cfg["angle"]))
        root.keyframe_insert(data_path="rotation_euler", index=2, frame=last)
        fixed += force_linear(root)

    print("[turntable] LINEAR 적용 키프레임 =", fixed)


# ─────────────────────────────────────────────
def setup_render(cfg):
    scene = bpy.context.scene
    r = scene.render

    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            r.engine = engine
            break
        except TypeError:
            continue
    print("[turntable] engine =", r.engine)

    if "EEVEE" in r.engine:
        ee = getattr(scene, "eevee", None)
        if ee is not None:
            for attr in ("taa_render_samples", "samples"):
                if hasattr(ee, attr):
                    setattr(ee, attr, cfg["samples"])
                    break
    elif r.engine == "CYCLES":
        scene.cycles.samples = cfg["samples"]

    r.resolution_x = cfg["width"]
    r.resolution_y = cfg["height"]
    r.resolution_percentage = 100
    r.film_transparent = True          # 배경은 웹에서 깐다

    img = r.image_settings
    try:
        img.file_format = "WEBP"
        img.quality = cfg["quality"]
    except TypeError:
        print("[turntable] WEBP 미지원 — PNG 로 대체")
        img.file_format = "PNG"
    img.color_mode = "RGBA"

    scene.frame_start = 1
    scene.frame_end = cfg["frames"]

    out = cfg["out"].replace("\\", "/").rstrip("/")
    os.makedirs(out, exist_ok=True)
    r.filepath = out + "/" + cfg["prefix"]
    r.use_file_extension = True
    r.use_overwrite = True
    return scene


def main():
    cfg = get_args()
    print("[turntable] config =", cfg)

    clear_scene()

    if cfg["model"]:
        objs = import_model(cfg["model"])
        print("[turntable] 모델 임포트:", cfg["model"])
    else:
        objs = build_placeholder(cfg["pose"])
        print("[turntable] 임시 도형 생성 · pose =", cfg["pose"])

    height = normalize(objs, target_height=3.0)
    cam, cam_pivot, far = setup_camera(height, cfg["width"], cfg["height"], cfg)
    setup_lights(height, cfg["silhouette"])
    if cfg["silhouette"]:
        make_silhouette()
    animate(cfg, height, cam, cam_pivot, far)
    scene = setup_render(cfg)

    out = cfg["out"].replace("\\", "/").rstrip("/")
    if cfg["still"]:
        scene.frame_set(1)
        scene.render.filepath = out + "/" + cfg["prefix"].rstrip("_")
        bpy.ops.render.render(write_still=True)
        print("[turntable] 정지 컷 저장 완료")
    else:
        bpy.ops.render.render(animation=True)
        print("[turntable] 시퀀스 %d장 저장 완료 → %s" % (cfg["frames"], out))


if __name__ == "__main__":
    main()
