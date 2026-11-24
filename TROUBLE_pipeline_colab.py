# @title 🎬 TROUBLE — PIPELINE MASTER v2.2 (ACE-Step 1.5 · Colab GPU T4)
# @markdown ⚡ **Entorno de ejecución → Cambiar tipo de entorno → GPU T4**
# @markdown 📁 **Sube tus imágenes (PNG/JPG/WEBP) al panel 📁 de la izquierda (carpeta `/content`) ANTES de ejecutar**
# @markdown ⏱️ 1.ª vez: ~15-25 min (instala ACE-Step 1.5 + descarga ~10 GB de modelos). Siguientes: ~3-6 min.
# @markdown 📦 Salida: `/content/trouble_prod/output/TROUBLE_COMPLETA.wav` + `TROUBLE_PREVIEW.mp4`
MODELO = "acestep-v15-turbo"  # @param ["acestep-v15-turbo", "acestep-v15-xl-turbo"]
DURACION_SEG = 186  # @param {type:"integer"}
SEED = 42  # @param {type:"integer"}
HACER_VIDEO = True  # @param {type:"boolean"}
SOLO_REHACER_VIDEO = False  # @param {type:"boolean"}
# @markdown `SOLO_REHACER_VIDEO`: no genera audio otra vez; reutiliza el último y solo rehace el vídeo.

# ──────────────────────────────────────────────────────────────────────────────
# Por qué está hecho así:
#  • El script viejo usaba la API de ACE-Step 1.5 (acestep.inference / AceStepHandler)
#    pero clonaba el repo de ACE-Step v1 → "No module named 'acestep.inference'".
#  • ACE-Step 1.5 exige Python 3.11-3.12 y Colab ya trae 3.13 → se instala en un
#    entorno aparte con uv (Python 3.12) y la generación corre en un subproceso.
#    El kernel de Colab no se toca: nada de reinstalar torch ni reiniciar sesión.
#  • El vídeo se hace con ffmpeg directamente (moviepy 2.x rompía .resize/.set_*).
# ──────────────────────────────────────────────────────────────────────────────
import os, sys, glob, json, math, re, shutil, subprocess, wave

EN_WINDOWS = os.name == "nt"
EN_COLAB = os.path.isdir("/content") and not EN_WINDOWS
LOCAL = os.path.join(os.path.expanduser("~"), "trouble_ai").replace("\\", "/")  # fuera de OneDrive
REPO = os.environ.get("TROUBLE_REPO", "/content/ACE-Step-1.5" if EN_COLAB else f"{LOCAL}/ACE-Step-1.5")
BASE = os.environ.get("TROUBLE_BASE", "/content/trouble_prod" if EN_COLAB else f"{LOCAL}/trouble_prod")
IMG_DIR = os.environ.get("TROUBLE_IMG_DIR", "/content" if EN_COLAB else f"{LOCAL}/imagenes")
os.makedirs(IMG_DIR, exist_ok=True)


def _buscar_ffmpeg():
    exe = os.environ.get("TROUBLE_FFMPEG") or shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "imageio-ffmpeg"], check=True)
        import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


FFMPEG = _buscar_ffmpeg()
VENV_PY = f"{REPO}/.venv/Scripts/python.exe" if EN_WINDOWS else f"{REPO}/.venv/bin/python"
RAW_WAV = f"{BASE}/audio/trouble_raw.wav"
OUT_WAV = f"{BASE}/output/TROUBLE_COMPLETA.wav"
OUT_MP4 = f"{BASE}/output/TROUBLE_PREVIEW.mp4"
for d in ("audio", "images_clean", "clips", "output", "lyrics"):
    os.makedirs(f"{BASE}/{d}", exist_ok=True)

print(f"🐍 Python del notebook: {sys.version.split()[0]}")


def sh(cmd, cwd=None, env=None, check=True, quiet=False):
    """Ejecuta un comando mostrando la salida en vivo. Si falla, enseña las últimas líneas reales."""
    if not quiet:
        print("$", " ".join(str(c) for c in cmd))
    p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, bufsize=1,
                         encoding="utf-8", errors="replace")
    tail = []
    for line in p.stdout:
        tail = (tail + [line])[-80:]
        if not quiet:
            print(line, end="")
    p.wait()
    if check and p.returncode != 0:
        raise RuntimeError(f"❌ Falló (código {p.returncode}): {cmd[0]}\n--- últimas líneas ---\n{''.join(tail)}")
    return p.returncode


def wav_seconds(path):
    with wave.open(path, "rb") as w:
        return w.getnframes() / float(w.getframerate())


# ──────────────────────────────────────────────────────────────────────────────
# 1. LETRA Y CAPTION
# ──────────────────────────────────────────────────────────────────────────────
# ACE-Step 1.5 admite como máximo 512 caracteres de caption: esta es la versión condensada
# del caption maestro (mismas reglas de voces, tempo e instrumentos).
CAPTION = (
    "Dark cinematic bilingual street rap duet: UK rap and Mexican Spanish rap, 144 BPM with heavy "
    "half-time 72 BPM feel, 4/4. Two male rappers trading verses, never overlapping. One: deep gritty "
    "raspy South London baritone, cold, sharp percussive cadence. Two: raspy playful Mexican street flow, "
    "bouncy syncopated, cheeky. String ostinato, sub-bass, distorted 808, brass horns, angelic choir, "
    "sinister atmosphere, spacious mix, funeral bell ending. No female vocals, no singing, no autotune."
)
assert len(CAPTION) <= 512, f"Caption demasiado largo: {len(CAPTION)} caracteres (máx. 512)"

LETRA_PARTE_1 = """[Intro - Double G | Bars 1-2]
¡No mames, cabrón! Fuck… here comes trouble,
Se prende la noche y el pulso se dobla.

[Intro - Atlas Rain | Bars 3-4]
What's happening? I'm back, back in trouble,
Cold step on the tarmac, no room for the double.

[Chorus 1A - Double G | Bars 5-8]
Trouble en la pista, traemos el fuego,
Doble el impacto cada vez que pego,
Triple la jugada, nadie nos compite,
El desmadre arranca y el bajo repite.

[Chorus 1B - Atlas Rain | Bars 9-12]
Cold steel steps when the city goes quiet,
Heavy half-time drum and the whole room riots,
Darkness in the eye, never folding, never bending,
Irresistible pressure till the night is ending.

[Verse 1B - Atlas Rain | Bars 13-16]  ← WITH CAP (snapback pink/lavender)
Bad days, mad ways, turning pressure into weight,
Silent in the shadows while they chatter on the gate,
Every scar a lesson that the cold nights taught,
Back on the mic with the fire that I bought.

[Verse 1A - Double G | Bars 17-20]
Pasamontañas firme, la mirada al frente,
La calle habla claro, se nota en la gente,
De Morelia al bloque, el ritmo va al cien,
Risa de lado cuando caen de sien.

[Chorus 2A - Double G | Bars 21-24]  ← JAPANESE RESTAURANT, NO CAP
Trouble en la mesa, copa roja y control,
Doble el estilo cuando sube el calor,
Triple la jugada, nadie nos compite,
El desmadre sigue y el bajo repite."""

LETRA_PARTE_2 = """[Verse 3 - Atlas Rain | Bars 25-28]  ← WET STREETS, NO CAP
No crew? No problem, stand tall on my own,
Truth on the table where the real ones are known,
Late-night grit and a steady command,
Every step heavy on the wet concrete land.

[Back-to-Back | Bars 29-32]
[Atlas Rain - Bars 29-30]
Black mask, bad past, never lose face,
Clock ticks loud in a cold dark place.

[Double G - Bars 31-32]  ← JAPANESE RESTAURANT
Cállate a la verga con tu cuento de actor,
Aquí manda el pulso y el que sube el calor.

[Bridge - Atlas Rain | Bars 33-36]  ← CONFRONTATION
Bad blood, mad mud, settled in the rain,
Keep my composure through the pressure and the strain.
Cold steel steps when the city goes quiet,
Heavy half-time drum and the whole room riots.

[Chorus 3B - Atlas Rain | Bars 37-38]
Darkness in the eye, never folding, never bending,
Irresistible pressure till the night is ending.

[Bridge - Double G | Bars 39-40]  ← JAPANESE RESTAURANT
Pura rata, pura farsa, se les cae el telón,
Mi gente bien puesta, firme el corazón.

[Chorus 3A - Double G | Bars 41-42]
Trouble en la noche, traemos el fuego,
Doble el impacto cada vez que pego,
Triple la jugada, nadie nos compite,
El desmadre sigue y el bajo repite.
¡Ya volvieron los reyes, hijos de puta!

[Outro - Atlas Rain | Bars 41-42]  ← SIMULTANEOUS, VISUAL SYMMETRY
You thought I'd stay gone? Nah, bruv…"""


def limpiar_letra(texto):
    """Quita las notas de escena (← ...) y los números de compás, que el modelo cantaría o malinterpretaría."""
    lineas = []
    for linea in texto.splitlines():
        linea = re.sub(r"\s*←.*$", "", linea)
        linea = re.sub(r"\s*[-|]\s*Bars?\s*[\d\-–]+", "", linea)
        lineas.append(linea.rstrip())
    return "\n".join(lineas).strip()


# La canción completa se genera en UNA sola pasada (ACE-Step 1.5 llega a 600 s):
# así no hay corte ni cambio de beat entre la parte 1 y la 2.
LETRA = limpiar_letra(LETRA_PARTE_1) + "\n\n" + limpiar_letra(LETRA_PARTE_2)
assert len(LETRA) <= 4096, f"Letra demasiado larga: {len(LETRA)} caracteres (máx. 4096)"
with open(f"{BASE}/caption.txt", "w", encoding="utf-8") as f:
    f.write(CAPTION)
with open(f"{BASE}/lyrics/letra_modelo.txt", "w", encoding="utf-8") as f:
    f.write(LETRA)
print(f"📝 Caption {len(CAPTION)}/512 · Letra {len(LETRA)}/4096 caracteres")

# ──────────────────────────────────────────────────────────────────────────────
# 2. GPU + INSTALACIÓN DE ACE-STEP 1.5 (entorno Python 3.12 aislado)
# ──────────────────────────────────────────────────────────────────────────────
GEN_SCRIPT = r'''
import inspect, json, os, shutil, sys, time
job = json.load(open(sys.argv[1], encoding="utf-8"))
sys.path.insert(0, job["repo"])
import torch
from acestep.handler import AceStepHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music

def solo_validos(fn, kw):
    sig = inspect.signature(fn).parameters
    if any(p.kind == p.VAR_KEYWORD for p in sig.values()):
        return kw
    fuera = [k for k in kw if k not in sig]
    if fuera:
        print("   (ignorados por esta versión:", ", ".join(fuera) + ")")
    return {k: v for k, v in kw.items() if k in sig}

vram = torch.cuda.get_device_properties(0).total_memory / 1e9
print(f"🎮 {torch.cuda.get_device_name(0)} · {vram:.1f} GB · torch {torch.__version__}", flush=True)

h = AceStepHandler()
init_kw = dict(project_root=job["repo"], config_path=job["model"], device="cuda",
               offload_to_cpu=vram < 20)
if vram < 8:                       # GPUs pequeñas (p. ej. 4 GB): el DiT también se aparca en RAM
    init_kw["offload_dit_to_cpu"] = True
if ("xl" in job["model"] and vram < 20) or vram < 8:
    try:
        import torchao  # noqa: F401  (la cuantización int8 lo necesita)
        init_kw["quantization"] = "int8_weight_only"
    except ImportError:
        print("   (sin torchao: se carga sin cuantizar)", flush=True)
print("🔄 Cargando modelo (la 1.ª vez descarga ~10 GB)...", flush=True)
t0 = time.time()
status, ok = h.initialize_service(**solo_validos(h.initialize_service, init_kw))
print(status, flush=True)
if not ok:
    sys.exit(2)
print(f"✅ Modelo listo en {time.time() - t0:.0f}s", flush=True)

turbo = "turbo" in job["model"]
params = GenerationParams(**solo_validos(GenerationParams, dict(
    task_type="text2music",
    caption=job["caption"],
    lyrics=job["lyrics"],
    duration=float(job["duration"]),
    bpm=144,
    inference_steps=8 if turbo else 50,
    shift=3.0,
    seed=job["seed"],
    thinking=False,          # sin modelo de lenguaje: la letra va tal cual
    use_cot_metas=False,
    use_cot_caption=False,
    use_cot_lyrics=False,
    use_cot_language=False,
)))
config = GenerationConfig(**solo_validos(GenerationConfig, dict(
    batch_size=1, use_random_seed=False, seeds=[job["seed"]], audio_format="wav")))

print(f"🎵 Generando {job['duration']} s de audio...", flush=True)
t0 = time.time()
try:
    res = generate_music(h, None, params, config, save_dir=job["save_dir"])
except torch.cuda.OutOfMemoryError:
    print("❌ Sin memoria de GPU. Usa MODELO = acestep-v15-turbo o baja DURACION_SEG.", flush=True)
    sys.exit(4)
if not res.success or not res.audios:
    print("❌ Error de generación:", res.error, flush=True)
    sys.exit(3)
shutil.copy2(res.audios[0]["path"], job["out"])
print(f"✅ Audio generado en {time.time() - t0:.0f}s → {job['out']}", flush=True)
'''


def gpu_ok():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            print(f"🎮 GPU detectada: {r.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    return False


def venv_env(**extra):
    """Entorno limpio para el Python 3.12: sin las rutas del Python 3.13 de Colab."""
    quitar = ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONWARNINGS", "MPLBACKEND",
              "JPY_PARENT_PID", "CLICOLOR_FORCE")
    env = {k: v for k, v in os.environ.items() if k not in quitar}
    env.update(UV_PYTHON="3.12", UV_LINK_MODE="copy", VIRTUAL_ENV=f"{REPO}/.venv",
               PYTHONIOENCODING="utf-8", PYTHONUTF8="1", MPLBACKEND="Agg", **extra)
    return env


CHECK_VENV = (
    "import torch\n"
    "print('torch', torch.__version__, 'cuda', torch.version.cuda)\n"
    "assert torch.cuda.is_available(), 'TORCH_SIN_CUDA'\n"
    "torch.zeros(2, device='cuda').add_(1)  # prueba real en la GPU\n"
    "import acestep.inference, acestep.handler\n"
    "print('IMPORT_OK')\n"
)

# nombre de módulo → nombre del paquete pip cuando no coinciden
PIP_NOMBRES = {"cv2": "opencv-python-headless", "PIL": "pillow", "yaml": "pyyaml", "sklearn": "scikit-learn",
               "skimage": "scikit-image", "soundfile": "soundfile", "google": "protobuf", "Crypto": "pycryptodome"}


def probar_venv():
    if not os.path.exists(VENV_PY):
        return False, "no existe el entorno"
    r = subprocess.run([VENV_PY, "-c", CHECK_VENV], cwd=REPO, env=venv_env(),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    salida = (r.stdout or "") + (r.stderr or "")
    return r.returncode == 0 and "IMPORT_OK" in salida, salida


def uv_pip(*args):
    sh([sys.executable, "-m", "uv", "pip", "install", "--python", VENV_PY, *args], cwd=REPO, env=venv_env())


_TORCH_INTENTO = 0


def cuda_del_driver():
    """Versión de CUDA que soporta el driver de la GPU (p. ej. 12.4), leída de nvidia-smi."""
    try:
        out = subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout
        m = re.search(r"CUDA Version:\s*([\d.]+)", out)
        return float(m.group(1)) if m else None
    except (FileNotFoundError, ValueError):
        return None


def reparar(error):
    """Arregla automáticamente los fallos típicos. Devuelve True si intentó algún arreglo."""
    falta = re.findall(r"No module named '([\w\.]+)'", error)
    if falta:
        mod = falta[-1].split(".")[0]
        if mod in ("acestep", "torch"):
            return False
        paquete = PIP_NOMBRES.get(mod, mod.replace("_", "-"))
        print(f"🔧 Falta el módulo '{mod}' → instalando {paquete}")
        uv_pip(paquete)
        return True
    if any(s in error for s in ("TORCH_SIN_CUDA", "no kernel image", "CUDA driver", "libcuda",
                                "cudaGetDeviceCount", "CUDA error", "too old")):
        global _TORCH_INTENTO
        cuda_drv = cuda_del_driver()
        # versiones de torch publicadas para cada CUDA, de la más nueva a la más vieja
        opciones = [(12.8, "cu128", "2.7.1", "0.22.1"), (12.6, "cu126", "2.7.1", "0.22.1"),
                    (12.4, "cu124", "2.6.0", "0.21.0"), (12.1, "cu121", "2.5.1", "0.20.1")]
        validas = [o for o in opciones if cuda_drv is None or o[0] <= cuda_drv + 1e-6]
        if _TORCH_INTENTO >= len(validas):
            return False
        _, idx, tv, vv = validas[_TORCH_INTENTO]
        _TORCH_INTENTO += 1
        print(f"🔧 torch no funciona con la GPU (driver CUDA {cuda_drv}) → instalando torch {tv}+{idx}")
        uv_pip("--reinstall", f"torch=={tv}", f"torchvision=={vv}", f"torchaudio=={tv}",
               "--index-url", f"https://download.pytorch.org/whl/{idx}")
        if tv < "2.7":   # igual que el instalador oficial de ACE-Step para torch antiguo
            uv_pip("--reinstall", "torchao==0.11.0")
        return True
    if ("libsndfile" in error or "sndfile" in error) and not EN_WINDOWS:
        sh(["apt-get", "install", "-y", "-qq", "libsndfile1"])
        return True
    return False


def instalar_ace_step():
    if not os.path.isdir(f"{REPO}/acestep"):
        shutil.rmtree(REPO, ignore_errors=True)
        sh(["git", "clone", "--depth", "1", "https://github.com/ace-step/ACE-Step-1.5.git", REPO])
    ok, salida = probar_venv()
    if ok:
        print("✅ ACE-Step 1.5 ya instalado")
        return
    print("\n📦 Instalando ACE-Step 1.5 con uv + Python 3.12 (unos minutos)...")
    sh([sys.executable, "-m", "pip", "install", "-q", "-U", "uv"])
    sh([sys.executable, "-m", "uv", "sync", "--python", "3.12"], cwd=REPO, env=venv_env())
    for intento in range(1, 9):
        ok, salida = probar_venv()
        if ok:
            print("✅ ACE-Step 1.5 listo")
            return
        print(f"\n⚠️ Verificación {intento}: falló. Error real:\n{salida[-2500:]}")
        if not reparar(salida):
            break
    raise RuntimeError("❌ ACE-Step 1.5 no arranca. Copia TODO este recuadro y pégalo en el chat.\n"
                       f"Driver CUDA: {cuda_del_driver()}\n"
                       f"──── ERROR REAL ────\n{salida[-3000:]}")


def generar_audio():
    job = dict(repo=REPO, model=MODELO, caption=CAPTION, lyrics=LETRA,
               duration=int(DURACION_SEG), seed=int(SEED), out=RAW_WAV,
               save_dir=f"{BASE}/audio/_tmp")
    os.makedirs(job["save_dir"], exist_ok=True)
    with open(f"{BASE}/job.json", "w", encoding="utf-8") as f:
        json.dump(job, f, ensure_ascii=False)
    with open(f"{BASE}/gen_trouble.py", "w", encoding="utf-8") as f:
        f.write(GEN_SCRIPT)
    env = venv_env(PYTHONUNBUFFERED="1", TOKENIZERS_PARALLELISM="false")
    for intento in range(4):
        try:
            sh([VENV_PY, f"{BASE}/gen_trouble.py", f"{BASE}/job.json"], cwd=REPO, env=env)
            return
        except RuntimeError as e:
            if intento == 3 or not reparar(str(e)):
                raise
            print("🔁 Arreglado; reintentando la generación...")


# ──────────────────────────────────────────────────────────────────────────────
# 3. MASTER DEL AUDIO
# ──────────────────────────────────────────────────────────────────────────────
def masterizar():
    print("\n🎚️ Normalizando a -14 LUFS...")
    sh([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", RAW_WAV,
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "pcm_s16le", OUT_WAV], quiet=True)
    print(f"✅ {OUT_WAV} — {wav_seconds(OUT_WAV):.1f}s")


# ──────────────────────────────────────────────────────────────────────────────
# 4. VÍDEO (ffmpeg: zoom lento por plano, un cambio de imagen cada compás a 72 BPM)
# ──────────────────────────────────────────────────────────────────────────────
def hacer_video():
    exts = ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.PNG", "*.JPG", "*.JPEG", "*.WEBP")
    raw = sorted({p for e in exts for p in glob.glob(os.path.join(IMG_DIR, e))})
    if not raw:
        print(f"⚠️ No hay imágenes en {IMG_DIR}. Súbelas al panel 📁 y vuelve a ejecutar con "
              "SOLO_REHACER_VIDEO = True (no regenera el audio).")
        return
    print(f"\n🖼️ Preparando {len(raw)} imágenes a 1920x1080...")
    for old in glob.glob(f"{BASE}/images_clean/*") + glob.glob(f"{BASE}/clips/*"):
        os.remove(old)
    clean = []
    for i, img in enumerate(raw):
        out = f"{BASE}/images_clean/scene_{i + 1:02d}.png"
        rc = sh([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", img, "-frames:v", "1",
                 "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1",
                 out], check=False, quiet=True)
        if rc == 0 and os.path.exists(out):
            clean.append(out)
        else:
            print(f"   ⚠️ Saltada (no se pudo leer): {os.path.basename(img)}")
    if not clean:
        print("⚠️ Ninguna imagen válida; no se hace vídeo.")
        return

    fps = 24
    dur_total = wav_seconds(OUT_WAV)
    plano = 4 * 60.0 / 72.0               # 1 compás a 72 BPM ≈ 3.33 s
    n = math.ceil(dur_total / plano)
    print(f"🎬 {n} planos de {plano:.2f}s para {dur_total:.1f}s de audio...")
    lista = []
    for k in range(n):
        frames = max(1, round(min(plano, dur_total - k * plano) * fps))
        clip = f"{BASE}/clips/clip_{k:03d}.mp4"
        zoom = (f"zoompan=z='min(1+0.0006*on,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d={frames}:s=1920x1080:fps={fps},format=yuv420p")
        sh([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", clean[k % len(clean)],
            "-vf", zoom, "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "20", "-r", str(fps), clip], quiet=True)
        lista.append(clip)
        if (k + 1) % 10 == 0 or k + 1 == n:
            print(f"   {k + 1}/{n} planos")
    with open(f"{BASE}/clips/lista.txt", "w", encoding="utf-8") as f:
        f.writelines(f"file '{c}'\n" for c in lista)
    sh([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
        "-i", f"{BASE}/clips/lista.txt", "-i", OUT_WAV, "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart",
        OUT_MP4], quiet=True)
    print(f"✅ VÍDEO: {OUT_MP4} ({os.path.getsize(OUT_MP4) / 1e6:.1f} MB)")


# ──────────────────────────────────────────────────────────────────────────────
# 5. EJECUCIÓN
# ──────────────────────────────────────────────────────────────────────────────
if SOLO_REHACER_VIDEO:
    if not os.path.exists(RAW_WAV):
        raise RuntimeError("❌ Aún no hay audio generado: pon SOLO_REHACER_VIDEO = False y ejecuta todo.")
else:
    if not gpu_ok():
        raise RuntimeError("❌ No hay GPU. Entorno de ejecución → Cambiar tipo de entorno → GPU T4 → Guardar, "
                           "y vuelve a ejecutar la celda.")
    if not 10 <= int(DURACION_SEG) <= 600:
        raise ValueError("DURACION_SEG debe estar entre 10 y 600")
    instalar_ace_step()
    generar_audio()

masterizar()
if HACER_VIDEO:
    hacer_video()

print("\n🎉 TROUBLE COMPLETO")
print(f"🎵 {OUT_WAV}")
if HACER_VIDEO and os.path.exists(OUT_MP4):
    print(f"🎬 {OUT_MP4}")
try:
    from IPython.display import Audio, display
    display(Audio(OUT_WAV))
except Exception:
    pass
