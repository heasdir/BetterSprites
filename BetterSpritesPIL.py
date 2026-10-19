import math
import os
import random
from PIL import Image

# ---------------------------------------------------------------- helpers
def remap(value, fromLow, fromHigh, toLow, toHigh):
    return (value - fromLow) * (toHigh - toLow) / (fromHigh - fromLow) + toLow

def avg_deviation(numlist):
    if not numlist:
        return 0, 0
    total = sum(numlist)
    avg = total / len(numlist)
    var = sum((n - avg) ** 2 for n in numlist) / len(numlist)
    return avg, math.sqrt(var)

# ---------------------------------------------------------------- catalog
def get_sprites(setselect="human"):
    folder = f"imgparts/{setselect}"
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Part set '{setselect}' not found at {folder}")
    file_list = [f for f in os.listdir(folder) if f.lower().endswith(".png")]

    part_directional, part_non_directional = [], []
    for fn in file_list:
        base = fn[:-4]
        if base.endswith("-l") or base.endswith("-r"):
            if base.endswith("-l"):
                part_directional.append(base[:-2])
        else:
            part_non_directional.append(base)

    categories = ['engine', 'gun', 'turret', 'perimeter', 'cockpit',
                  'body', 'core', 'greeble', 'other']

    part_dir_dict = {k: [] for k in categories}
    part_uni_dict = {k: [] for k in categories}

    def categorize(base, bucket):
        full = f"{folder}/{base}"
        for cat in categories[:-1]:
            if base.endswith(cat):
                bucket[cat].append(full)
                return
        bucket['other'].append(full)

    for b in part_directional:
        categorize(b, part_dir_dict)
    for b in part_non_directional:
        categorize(b, part_uni_dict)

    return part_dir_dict, part_uni_dict

# ---------------------------------------------------------------- part loading
def pick_part_dir(partDir):
    lpath = partDir + "-l.png"
    rpath = partDir + "-r.png"
    has_l = os.path.exists(lpath)
    has_r = os.path.exists(rpath)
    if has_l and has_r:
        return [Image.open(lpath).convert("RGBA"), Image.open(rpath).convert("RGBA")]
    if has_l:
        img = Image.open(lpath).convert("RGBA")
        return [img, img.copy()]
    if has_r:
        img = Image.open(rpath).convert("RGBA")
        return [img, img.copy()]
    raise FileNotFoundError(f"No directional sprite for {partDir}")

def _load_uni(path):
    img = Image.open(path).convert("RGBA")
    return [img, img.copy()]

# ---------------------------------------------------------------- sorting
def sort_bounds(newboundmin, newboundmax, sortby='x'):
    mode_sel = 0 if sortby.casefold() == 'x' else 1
    for i in range(len(newboundmin)):
        for j in range(i + 1, len(newboundmin)):
            if newboundmin[i][mode_sel] < newboundmin[j][mode_sel]:
                newboundmin[i], newboundmin[j] = newboundmin[j], newboundmin[i]
                newboundmax[i], newboundmax[j] = newboundmax[j], newboundmax[i]
    return newboundmin, newboundmax

# ---------------------------------------------------------------- placement
def get_part_pos(partlist, newboundmin, newboundmax, mode, part, part_size,
                 uniMode, stray=[[1, 1], [1, 1]], core_img=None,
                 part_type='', placemode='symmetric'):
    mode_sel = 0 if mode.casefold() == 'x' else 1

    if part_type in ('center', 'gun', 'engine'):
        newboundmin, newboundmax = sort_bounds(newboundmin, newboundmax, mode)
    if part_type in ('engine',):
        newboundmin.reverse()
        newboundmax.reverse()

    valid_part = False
    rposmin = rposmax = 0
    m = 0
    h = 0

    while not valid_part:
        h += 1
        m = random.randrange(len(newboundmin))
        if part_type in ('gun', 'engine', 'center'):
            m = random.randrange(1, max(2, round(len(newboundmin) / 2)))

        for n in partlist:
            if mode_sel == 0:
                rposmin = round(newboundmin[m][0] * stray[0][0])
                rposmax = round(newboundmax[m][0] * stray[0][1])
                canvasmin = abs(part_size[0][mode_sel] / 2)
                if placemode == 'asym':
                    canvasmin = abs(part_size[0][mode_sel])
                canvasmax = core_img.size[0] - part_size[0][mode_sel] * 0.5
            else:
                rposmin = round(newboundmin[m][mode_sel] * stray[1][0])
                rposmax = round(newboundmax[m][mode_sel] * stray[1][1])
                canvasmin = abs(part_size[0][mode_sel])
                canvasmax = core_img.size[1] - part_size[0][mode_sel] * 0.5

            rposmin = max(rposmin, canvasmin)
            rposmax = min(rposmax, canvasmax)

            if rposmin < rposmax:
                valid_part = True
                break
            else:
                if not uniMode:
                    part = pick_part_dir(n)
                else:
                    part = _load_uni(n + ".png")
                part_size = [p.size for p in part]

        if not valid_part:
            nscale = 0.9
            for _ in range(max(1, part_size[0][mode_sel] - 1)):
                new_size = [max(1, math.ceil(part[0].size[0] * nscale)),
                            max(1, math.ceil(part[0].size[1] * nscale))]
                part = [p.resize(new_size, Image.LANCZOS) for p in part]
                part_size = [p.size for p in part]

                rposmin = round(newboundmin[m][mode_sel])
                rposmax = round(newboundmax[m][mode_sel])
                canvasmin = abs(part_size[0][mode_sel] / 2)
                canvasmax = core_img.size[mode_sel] - part_size[0][mode_sel] * 0.5
                rposmin = max(rposmin, canvasmin)
                rposmax = min(rposmax, canvasmax)
                if rposmin > rposmax:
                    nscale -= 0.1
                    if nscale <= 0.05:
                        break
                else:
                    valid_part = True
                    break

        if valid_part:
            break
        if h >= 50:
            part = [Image.new('RGBA', (1, 1)) for _ in range(2)]
            part_size = [p.size for p in part]
            rposmin, rposmax = 0, 0
            break

    return part, part_size, rposmin, rposmax

def place_parts(core_img, part_list, count, symmetric=True, center=False,
                part_type='random', boundmin=None, boundmax=None,
                dir_chance=0.5, weightX=0.3, scaleRange=(1, 1),
                pattern=None, clustermode=False, bounddict=None,
                inputdictonly=False):
    if boundmin is None: boundmin = [0, 0]
    if boundmax is None: boundmax = [0, 0]
    if bounddict is None: bounddict = {}

    width, height = core_img.size
    centW, centH = round(width / 2), round(height / 2)
    count = int(round(count))

    part_dir_dict, part_uni_dict = part_list

    if part_type == 'random':
        have = False
        tries = 0
        while not have and tries < 50:
            tries += 1
            part_type = random.choice(list(part_dir_dict.keys()))
            have = (len(part_dir_dict[part_type]) > 0 or len(part_uni_dict[part_type]) > 0)
        if not have:
            return core_img, bounddict, []

    partlistdir_raw = list(part_dir_dict.get(part_type, []))
    partlistuni_raw = list(part_uni_dict.get(part_type, []))

    if not partlistdir_raw and not partlistuni_raw:
        return core_img, bounddict, []

    if center:
        dir_chance = 0

    partlistdir = []
    for p in partlistdir_raw:
        try:
            with Image.open(p + "-l.png") as img:
                partlistdir.append((img.size[1], p))
        except FileNotFoundError:
            pass
    partlistdir = [p[1] for p in sorted(partlistdir, key=lambda x: x[0], reverse=True)]

    partlistuni = []
    for p in partlistuni_raw:
        try:
            with Image.open(p + ".png") as img:
                partlistuni.append((img.size[1], p))
        except FileNotFoundError:
            pass
    partlistuni = [p[1] for p in sorted(partlistuni, key=lambda x: x[0], reverse=True)]

    random.shuffle(partlistdir)
    random.shuffle(partlistuni)

    uniMode = False
    Dirbool = random.random() <= dir_chance
    if Dirbool and partlistdir:
        part = pick_part_dir(partlistdir[0])
    elif partlistuni:
        part = _load_uni(partlistuni[0] + ".png")
        uniMode = True
    elif partlistdir:
        part = pick_part_dir(partlistdir[0])
    else:
        return core_img, bounddict, []

    scale_rand = random.uniform(scaleRange[0], scaleRange[1])
    if part_type == "greeble":
        scale_rand = random.uniform(scaleRange[0] / 5, scaleRange[1] / 2)

    rescale = True
    safety = 0
    while rescale and safety < 200:
        safety += 1
        new_size = [max(1, round(part[0].size[0] * scale_rand)),
                    max(1, round(part[0].size[1] * scale_rand))]
        part = [p.resize(new_size, Image.LANCZOS) for p in part]
        part_size = [p.size for p in part]
        too_big = False
        for ps in part_size:
            if ps[0] > centW or ps[1] > centH:
                too_big = True
                break
        if too_big:
            scale_rand -= 0.1
            if scale_rand <= 0.05:
                break
        else:
            rescale = False

    if boundmax == [0, 0] and not clustermode:
        if part_type == 'gun':
            boundmin = [0, part_size[0][1] + 5]
            boundmax = [width * 0.2, height * 0.2 + part_size[0][1]]
        elif part_type == 'engine':
            boundmin = [part_size[0][0], centH * 0.7 - part_size[0][1]]
            boundmax = [centW * 0.75, height]
        elif part_type == 'turret':
            boundmin = [centW * 0.24, centH * 0.24]
            boundmax = [centW * 0.525, centH * 0.525]
        else:
            boundmin = [part_size[0][0], part_size[0][1]]
            boundmax = [centW * 0.75, height]
    elif boundmax == [0, 0]:
        boundmax = [width, height]

    newboundmin, newboundmax = [], []
    if bounddict:
        newboundmin = list(bounddict.get('min', []))
        newboundmax = list(bounddict.get('max', []))

    hardpoint = []
    staticcount = count
    i = 0

    if symmetric and not center:
        while count > 1:
            if len(newboundmin) == 0 or not clustermode:
                rXmin = round(centW)
                rXmax = round(boundmax[0] + 1 - part_size[0][0] / 2)
                if rXmax < rXmin:
                    rXmax = rXmin
                randX = round(random.triangular(rXmin, rXmax, rXmin)) if rXmax > rXmin else rXmin
                rYmin = round(boundmin[1])
                rYmax = round(boundmax[1] + 1 - part_size[0][1] / 2)
                if rYmax <= rYmin:
                    rYmax = rYmin + 1
                randY = random.randrange(rYmin, rYmax)
            else:
                partlistany = partlistuni if uniMode else partlistdir
                src_min = bounddict['min'] if inputdictonly and bounddict else newboundmin
                src_max = bounddict['max'] if inputdictonly and bounddict else newboundmax
                part, part_size, rXmin, rXmax = get_part_pos(
                    partlistany, src_min, src_max, 'x', part, part_size,
                    uniMode, core_img=core_img, part_type=part_type)
                rXmin = max(centW + part_size[0][0] / 2, rXmin)
                randX = round(random.triangular(rXmin, rXmax)) if rXmax > rXmin else round(rXmin)

                part, part_size, rYmin, rYmax = get_part_pos(
                    partlistany, src_min, src_max, 'y', part, part_size,
                    uniMode, core_img=core_img)
                randY = round(random.triangular(rYmin, rYmax)) if rYmax > rYmin else round(rYmin)

            randX = int(max(round(part_size[0][0] / 2), min(width - round(part_size[0][0] / 2), randX)))
            randY = int(max(round(part_size[0][1] / 2), min(height - round(part_size[0][1] / 2), randY)))

            posX = randX - round(part_size[0][0] / 2)
            posY = randY - round(part_size[0][1] / 2)
            core_img.paste(part[1], (posX, posY), part[1])
            newboundmin.append([posX, posY])

            nposX = randX + round(part_size[0][0] / 2)
            nposY = randY + round(part_size[0][1] / 2)
            newboundmax.append([nposX, nposY])

            symX = width - round(part_size[1][0] / 2) - randX + 1
            core_img.paste(part[0], (symX - round(part_size[1][0] / 2), posY), part[0])

            if part_type in ('gun', 'turret'):
                hardpoint.append([randX - centW, posY - centH])
                hardpoint.append([symX - round(part_size[1][0] / 2) - centW, posY - centH])
            elif part_type == 'engine':
                hardpoint.append([randX - centW, nposY - centH])
                hardpoint.append([symX - round(part_size[1][0] / 2) - centW, nposY - centH])

            count -= 2
            i += 2

        if count == 1:
            randX = centW
            if len(newboundmin) == 0 or not clustermode:
                rYmin = round(boundmin[1])
                rYmax = round(boundmax[1] + 1)
                if rYmax <= rYmin:
                    rYmax = rYmin + 1
                randY = random.randrange(rYmin, rYmax)
            else:
                npart_type = 'center' if part_type == 'cockpit' else part_type
                part, part_size, rYmin, rYmax = get_part_pos(
                    partlistuni, newboundmin, newboundmax, 'y', part,
                    part_size, uniMode=True, core_img=core_img,
                    part_type=npart_type)
                randY = random.randrange(int(rYmin), int(rYmax) + 1) if rYmax > rYmin else int(rYmin)

            posX = randX - round(part_size[0][0] / 2)
            posY = randY - round(part_size[0][1] / 2)
            core_img.paste(part[0], (posX, posY), part[0])

            newboundmin.append([posX, posY])
            newboundmax.append([randX + round(part_size[0][0] / 2),
                                randY + round(part_size[0][1] / 2)])

            if part_type in ('gun', 'turret'):
                hardpoint.append([0, posY - centH])
            elif part_type == 'engine':
                hardpoint.append([0, randY + round(part_size[0][1] / 2) - centH])
            count -= 1

    elif center:
        loop = 0
        while count > 0:
            if pattern is not None and loop < len(pattern):
                randX = pattern[loop][0] * part_size[0][0]
                randY = pattern[loop][1] * part_size[0][1]
            else:
                randX = 0
                if len(newboundmin) == 0 or not clustermode:
                    rYmin = round(boundmin[1] + part_size[0][1] / 2)
                    rYmax = round(boundmax[1] + 1 - part_size[0][1] / 2)
                    if rYmax <= rYmin:
                        rYmax = rYmin + 1
                    randY = random.randrange(rYmin, rYmax)
                else:
                    part, part_size, rYmin, rYmax = get_part_pos(
                        partlistuni, newboundmin, newboundmax, 'y', part,
                        part_size, uniMode=True, core_img=core_img)
                    randY = random.randrange(int(rYmin), int(rYmax) + 1) if rYmax > rYmin else int(rYmin)

            posX = randX - round(part_size[0][0] / 2)
            posY = randY - round(part_size[0][1] / 2)
            core_img.paste(part[0], (posX + centW, posY), part[0])

            newboundmin.append([posX, posY])
            newboundmax.append([randX + round(part_size[0][0] / 2) + centW,
                                randY + round(part_size[0][1] / 2)])
            count -= 1
            loop += 1

    else:
        while count > 0:
            if len(newboundmin) == 0 or not clustermode:
                rXmin = round(centW)
                rXmax = round(boundmax[0] + 1 - part_size[0][0] / 2)
                if rXmax < rXmin:
                    rXmax = rXmin
                randX = round(random.triangular(rXmin, rXmax, rXmin)) if rXmax > rXmin else rXmin
                rYmin = round(boundmin[1])
                rYmax = round(boundmax[1] + 1 - part_size[0][1] / 2)
                if rYmax <= rYmin:
                    rYmax = rYmin + 1
                randY = random.randrange(rYmin, rYmax)
            else:
                partlistany = partlistuni if uniMode else partlistdir
                part, part_size, rXmin, rXmax = get_part_pos(
                    partlistany, newboundmin, newboundmax, 'x', part,
                    part_size, uniMode, core_img=core_img,
                    part_type=part_type, placemode='asym')
                randX = round(random.triangular(rXmin, rXmax)) if rXmax > rXmin else round(rXmin)

                part, part_size, rYmin, rYmax = get_part_pos(
                    partlistany, newboundmin, newboundmax, 'y', part,
                    part_size, uniMode, core_img=core_img)
                randY = round(random.triangular(rYmin, rYmax)) if rYmax > rYmin else round(rYmin)

            posX = randX - round(part_size[0][0] / 2)
            posY = randY - round(part_size[0][1] / 2)
            side_sel = 1 if posX >= centW else 0
            core_img.paste(part[side_sel], (posX, posY), part[side_sel])

            newboundmin.append([posX, posY])
            newboundmax.append([randX + round(part_size[0][0] / 2),
                                randY + round(part_size[0][1] / 2)])

            if part_type in ('gun', 'turret'):
                hardpoint.append([(randX / 2) - centW, posY - centH])
            elif part_type == 'engine':
                hardpoint.append([(randX / 2) - centW,
                                  randY + round(part_size[0][1] / 2) - centH])
            count -= 1

    bounddict = {'min': newboundmin.copy(), 'max': newboundmax.copy()}
    return core_img, bounddict, hardpoint

def generate_sprite(faction, category="Heavy Warship", width=0, height=0,
                    part_list=None, gun=0, turret=0, enginesp=0):
    if part_list is None:
        raise ValueError("part_list is required")

    stacktype = 2
    symmode = True
    if faction is not None and hasattr(faction, "shipsymmode"):
        symmode = faction.shipsymmode

    if width == 0 or height == 0:
        if category in ("Drone", "Fighter"):
            width = random.randrange(80, 100, 2);  height = random.randrange(80, 100, 2)
        elif category == "Interceptor":
            width = random.randrange(100, 120, 2); height = random.randrange(100, 120, 2)
        elif category in ("Light Warship", "Light Freighter"):
            width = random.randrange(120, 200, 2); height = random.randrange(120, 200, 2)
        elif category == "Medium Warship":
            width = random.randrange(170, 260, 2); height = random.randrange(170, 260, 2)
        elif category in ("Heavy Warship", "Heavy Freighter"):
            width = random.randrange(200, 420, 2); height = random.randrange(260, 420, 2)
        elif category == "Transport":
            width = random.randrange(120, 260, 2); height = random.randrange(120, 260, 2)

    if category in ("Drone", "Fighter", "Interceptor", "Light Warship", "Light Freighter"):
        stacktype = 3

    engine = max(1, round(enginesp / 100))
    centW, centH = round(width / 2), round(height / 2)
    gpoints, tpoints, epoints = [], [], []
    pcs = (width * height) / (260.0 * 260.0)
    new_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))

    if stacktype == 1:
        new_img, bd, _ = place_parts(new_img, part_list, count=4, part_type='engine')
        new_img, bd, _ = place_parts(new_img, part_list, count=1, part_type='core', bounddict=bd)
        new_img, bd, _ = place_parts(new_img, part_list, count=4, part_type='gun', bounddict=bd)
        new_img, bd, _ = place_parts(new_img, part_list, count=8, part_type='perimeter', bounddict=bd)
        new_img, bd, _ = place_parts(new_img, part_list, count=32, part_type='body', bounddict=bd)
        new_img, bd, _ = place_parts(new_img, part_list, count=16, part_type='body', bounddict=bd)
        new_img, bd, _ = place_parts(new_img, part_list, count=8, part_type='body', bounddict=bd)
        new_img, bd, _ = place_parts(new_img, part_list, count=16, part_type='greeble', bounddict=bd)
        new_img, bd, _ = place_parts(new_img, part_list, count=16, part_type='greeble', bounddict=bd)
        new_img, bd, _ = place_parts(new_img, part_list, count=1, part_type='turret', bounddict=bd)
        new_img, bd, tpoints = place_parts(new_img, part_list, count=6, part_type='turret', bounddict=bd)
        new_img, bd, _ = place_parts(new_img, part_list, count=1, part_type='cockpit', bounddict=bd)

    elif stacktype == 2:
        new_img, bdc, _ = place_parts(new_img, part_list, count=1, part_type='core', boundmin=[0, centH], boundmax=[0, centH])
        new_img, bdb, _ = place_parts(new_img, part_list, count=64 * pcs, part_type='body', bounddict=bdc, clustermode=True, symmetric=symmode)
        new_img, bd,  _ = place_parts(new_img, part_list, count=8 * pcs, part_type='body', bounddict=bdc, clustermode=True, symmetric=symmode)
        new_img, bdg, gpoints = place_parts(new_img, part_list, count=gun, part_type='gun', bounddict=bdb, clustermode=True, symmetric=symmode)
        new_img, bde, epoints = place_parts(new_img, part_list, count=engine, part_type='engine', bounddict=bdb, clustermode=True, symmetric=symmode)
        new_img, bd,  _ = place_parts(new_img, part_list, count=8 * pcs, part_type='perimeter', bounddict=bdb, clustermode=True, symmetric=symmode)
        new_img, bd,  _ = place_parts(new_img, part_list, count=8 * pcs, part_type='body', bounddict=bdb, clustermode=True, symmetric=symmode)
        new_img, bd,  _ = place_parts(new_img, part_list, count=max(0, round(8 * pcs)), part_type='greeble', bounddict=bdb, clustermode=True, symmetric=symmode)
        new_img, bd, tpoints = place_parts(new_img, part_list, count=turret, part_type='turret', bounddict=bdb, clustermode=True, symmetric=symmode)
        new_img, bd, _ = place_parts(new_img, part_list, count=1, part_type='cockpit', bounddict=bd, clustermode=True, symmetric=symmode)

    elif stacktype == 3:
        new_img, bdc, _ = place_parts(new_img, part_list, count=1, part_type='core', boundmin=[0, centH], boundmax=[0, centH])
        new_img, bdb, _ = place_parts(new_img, part_list, count=4, part_type='body', bounddict=bdc, clustermode=True, symmetric=symmode)
        new_img, bdg, gpoints = place_parts(new_img, part_list, count=gun, part_type='gun', bounddict=bdb, clustermode=True, symmetric=symmode)
        new_img, bde, epoints = place_parts(new_img, part_list, count=engine, part_type='engine', bounddict=bdb, clustermode=True, symmetric=symmode)
        new_img, bd,  _ = place_parts(new_img, part_list, count=2, part_type='perimeter', bounddict=bdb, clustermode=True, symmetric=symmode)
        new_img, bd,  _ = place_parts(new_img, part_list, count=4, part_type='body', bounddict=bdb, clustermode=True)
        new_img, bd, tpoints = place_parts(new_img, part_list, count=turret, part_type='turret', bounddict=bdb, clustermode=True, symmetric=symmode)
        new_img, bd, _ = place_parts(new_img, part_list, count=1, part_type='cockpit', bounddict=bd, clustermode=True, symmetric=symmode)

    elif stacktype == 99:
        new_img, bdc, _ = place_parts(new_img, part_list, count=1, part_type='core')
        new_img, bdb, _ = place_parts(new_img, part_list, count=2, part_type='body', bounddict=bdc, clustermode=True)

    border = Image.new('RGBA', (width + 2, height + 2), (0, 0, 0, 0))
    border.paste(new_img, (1, 1), new_img)
    return border, gpoints, tpoints, epoints

def call_generate_sprite(faction, category, name, gun, turret, width=0, height=0, enginesp=0):
    if getattr(faction, "devmode", False):
        random.seed(faction.devmodeseed)
    part_list = get_sprites(setselect=faction.partset)
    sprite, gpoints, tpoints, epoints = generate_sprite(faction, category, gun=gun, turret=turret, part_list=part_list, width=width, height=height, enginesp=enginesp)
    out_dir = f'images/ship/{faction.name}'
    os.makedirs(out_dir, exist_ok=True)
    sprite.save(f'{out_dir}/{name}.png')
    return ([p[0] for p in gpoints], [p[1] for p in gpoints], 
            [p[0] for p in tpoints], [p[1] for p in tpoints], 
            [p[0] for p in epoints], [p[1] for p in epoints])

# ---------------------------------------------------------------- Pydroid entry
if __name__ == "__main__":
    # 1. FORCE true randomness using hardware entropy
    random.seed(os.urandom(16))
    
    # 2. Randomly choose ONE faction for this entire run
    faction_set = random.choice(["human", "indus a", "curve b"])
    
    # 3. Randomly choose the total amount for this run (5 to 13)
    NUM_SHIPS = random.randint(5, 13)
    
    OUT_DIR = "generatedsprites"
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Run started! Faction: '{faction_set}' | Generating {NUM_SHIPS} ships...")
    
    # 4. Load the parts once for this faction
    try:
        parts = get_sprites(setselect=faction_set)
    except FileNotFoundError:
        print(f"ERROR: Folder 'imgparts/{faction_set}' not found.")
        exit()

    # 5. Generate the batch
    for n in range(NUM_SHIPS):
        # Randomly pick a category and stats for each ship
        cat = random.choice(["Drone", "Fighter", "Interceptor", 
                             "Light Warship", "Medium Warship", "Heavy Warship", "Transport"])
        guns = random.randint(1, 4)
        turrets = random.randint(0, 3)
        engine = random.randint(100, 400)

        # Generate sprite
        sprite, g, t, e = generate_sprite(None, category=cat, part_list=parts, gun=guns, turret=turrets, enginesp=engine)
        
        # 6. Save with unique filename (includes the faction)
        safe_faction = faction_set.replace(' ', '_')
        base_name = f"{cat.replace(' ', '')}_{n+1}_{safe_faction}"
        custom_ship_name = base_name
        
        counter = 1
        while os.path.exists(f"{OUT_DIR}/{custom_ship_name}.png"):
            custom_ship_name = f"{base_name}_{counter}"
            counter += 1
            
        path = f"{OUT_DIR}/{custom_ship_name}.png"
        sprite.save(path)
        print(f"[{n+1}/{NUM_SHIPS}] {cat} -> {path}")

    print("Done.")