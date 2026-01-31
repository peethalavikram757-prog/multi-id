from flask import Flask, render_template, request, jsonify
from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired, FeedbackRequired, PleaseWaitFewMinutes, LoginRequired
import threading, time, random, os, gc

app = Flask(__name__)
app.secret_key = "sujal_hawk_final_fixed_2025"

state = {"running": False, "sent": 0, "logs": ["PANEL READY - START DABAO"], "start_time": None, "primary_ok": True, "in_warmup": False}
cfg = {
    "primary": {"sessionid": "", "thread_id": 0},
    "backups": [],
    "messages": [],
    "delay": 30,
    "warmup_duration": 600
}

DEVICES = [
    {"phone_manufacturer": "Google", "phone_model": "Pixel 8 Pro", "android_version": 15, "android_release": "15.0.0", "app_version": "323.0.0.46.109"},
    {"phone_manufacturer": "Samsung", "phone_model": "SM-S928B", "android_version": 15, "android_release": "15.0.0", "app_version": "324.0.0.41.110"},
    {"phone_manufacturer": "OnePlus", "phone_model": "PJZ110", "android_version": 15, "android_release": "15.0.0", "app_version": "322.0.0.40.108"},
    {"phone_manufacturer": "Xiaomi", "phone_model": "23127PN0CC", "android_version": 15, "android_release": "15.0.0", "app_version": "325.0.0.42.111"},
]

def log(m):
    state["logs"].append(f"[{time.strftime('%H:%M:%S')}] {m}")
    if len(state["logs"]) > 500: state["logs"] = state["logs"][-500:]
    gc.collect()

def vary_msg(msg):
    emojis = ['🔥', '💀', '😈', '🚀', '😂', '🤣', '😍', '❤️', '👍', '👀', '🗿']
    if random.random() > 0.4:
        msg += " " + random.choice(emojis) + random.choice(emojis)
    if random.random() > 0.5:
        msg = msg.upper() if random.random() > 0.5 else msg.lower()
    if random.random() > 0.6:
        msg = "  " + msg + "  "
    return msg

def spam(cl, tid, msg):
    try:
        cl.direct_send(msg, thread_ids=[tid])
        return True
    except Exception as e:
        log(f"SEND FAIL → {str(e)[:60]}")
        return False

def warmup(cl):
    log(f"WARMUP STARTED ({cfg['warmup_duration']//60} min)")
    state["in_warmup"] = True
    start = time.time()
    while time.time() - start < cfg["warmup_duration"] and state["running"]:
        action = random.choice(["viewing stories", "liking posts", "reading DMs", "scrolling feed"])
        log(f"WARMUP: Simulating {action}...")
        time.sleep(random.uniform(10, 60))
    state["in_warmup"] = False
    log("WARMUP COMPLETE - SPAM SHURU")

def get_primary():
    acc = cfg["primary"]
    cl = Client()
    cl.delay_range = [8, 30]
    dev = random.choice(DEVICES)
    cl.set_device(dev)
    cl.set_user_agent(f"Instagram {dev['app_version']} Android (34/15.0.0; 480dpi; 1080x2340; {dev['phone_manufacturer']}; {dev['phone_model']}; raven; raven; en_US)")
    try:
        cl.login_by_sessionid(acc["sessionid"])
        log("PRIMARY LOGIN SUCCESS")
        state["primary_ok"] = True
        return cl
    except LoginRequired:
        log("PRIMARY SESSION EXPIRED — TRYING BACKUP")
        state["primary_ok"] = False
    except Exception as e:
        log(f"PRIMARY LOGIN FAILED → {str(e)[:80]} — TRYING BACKUP")
        state["primary_ok"] = False
    return None

def get_backup():
    for acc in cfg["backups"]:
        cl = Client()
        cl.delay_range = [8, 30]
        dev = random.choice(DEVICES)
        cl.set_device(dev)
        cl.set_user_agent(f"Instagram {dev['app_version']} Android (34/15.0.0; 480dpi; 1080x2340; {dev['phone_manufacturer']}; {dev['phone_model']}; raven; raven; en_US)")
        try:
            cl.login_by_sessionid(acc["sessionid"])
            log("BACKUP LOGIN SUCCESS")
            return cl
        except:
            continue
    log("NO WORKING BACKUP LEFT — STOPPING")
    state["running"] = False
    return None

def loop():
    cl = get_primary()
    if cl:
        warmup(cl)

    while state["running"]:
        cl = None
        if state["primary_ok"]:
            cl = get_primary()
        if not cl:
            cl = get_backup()
        if not cl:
            break

        try:
            msg = random.choice(cfg["messages"])
            msg = vary_msg(msg)
            if spam(cl, cfg["primary"]["thread_id"], msg):
                state["sent"] += 1
                log(f"SENT #{state['sent']} → {msg[:40]}")
            time.sleep(cfg["delay"] + random.uniform(-2, 3))
        except Exception as e:
            log(f"ERROR → {str(e)[:60]}")
            time.sleep(15)
            cl = None

        # Primary recovery check every 10 min
        if int(time.time()) % 600 == 0:
            get_primary()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    global state
    state["running"] = False
    time.sleep(1)
    state = {"running": True, "sent": 0, "logs": ["STARTED - WAIT FOR LOGIN"], "start_time": time.time(), "primary_ok": True}

    cfg["primary"] = {"sessionid": request.form["primary_sessionid"].strip(), "thread_id": int(request.form["thread_id"])}
    backups_raw = request.form["backups"].strip().split("\n")
    cfg["backups"] = []
    for line in backups_raw:
        if line.strip():
            sessionid, thread_id = line.split(":")
            cfg["backups"].append({"sessionid": sessionid.strip(), "thread_id": int(thread_id.strip())})

    cfg["messages"] = [m.strip() for m in request.form["messages"].split("\n") if m.strip()]
    cfg["delay"] = float(request.form.get("spam_delay", "30"))
    cfg["warmup_duration"] = int(request.form.get("warmup_duration", "600"))

    threading.Thread(target=loop, daemon=True).start()
    log(f"STARTED - PRIMARY + BACKUPS (Warmup: {cfg['warmup_duration']//60} min)")

    return jsonify({"ok": True})

@app.route("/stop")
def stop():
    state["running"] = False
    log("STOPPED")
    return jsonify({"ok": True})

@app.route("/status")
def status():
    uptime = "00:00:00"
    if state.get("start_time"):
        t = int(time.time() - state["start_time"])
        h, r = divmod(t, 3600)
        m, s = divmod(r, 60)
        uptime = f"{h:02d}:{m:02d}:{s:02d}"
    return jsonify({"running": state["running"], "sent": state["sent"], "uptime": uptime, "logs": state["logs"][-100:]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
