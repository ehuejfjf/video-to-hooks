"""Generate concept homepage mockups for church outreach.

Each mockup is a single self-contained HTML file (no external assets) so it can be
opened offline, screenshotted, or hosted anywhere. Facts come from each church's own
website or the Methodist Church in Singapore directory (checked Nov 2026). Anything
not confirmed is shown as a visible [to confirm] tag.
"""
import html
from pathlib import Path

OUT = Path(__file__).parent / "mockups"

TBC = '<span class="tbc">to confirm</span>'

CHURCHES = [
    {
        "slug": "hakka-mc",
        "name": "Hakka Methodist Church",
        "zh": "",
        "short": "HKMC",
        "accent": "#9a3b26", "accent2": "#f3e3d6",
        "tagline": "Holding up the cross of Christ since 1966.",
        "intro": "A church family worshipping in Hakka, Mandarin and English, at the foot of the cross on Evelyn Road.",
        "services": [
            ("Saturday", "5:00 PM", "Hakka Service", "客家崇拜"),
            ("Sunday", "9:00 AM", "Mandarin Service", "华语崇拜"),
            ("Sunday", "11:00 AM", "English Service", ""),
            ("Weekly", TBC, "Youth Service", ""),
        ],
        "address": "1B Evelyn Road, Singapore 309298",
        "phone": "6256 2225",
        "email": "admin@hakkamc.org.sg",
        "ministries": ["Sunday School", "Youth", "Discipleship &amp; Nurture", "Missions", "Social Concerns", "Worship &amp; Music"],
        "news": [
            ("Livestream", "Our Saturday 5PM Hakka service is streamed live every week.", "Watch"),
            ("Our story", "Celebrating 70+ years: watch the anniversary documentary.", "Watch"),
            ("Upcoming", "Christmas services and events " + TBC, "See dates"),
        ],
        "socials": ["Facebook", "YouTube", "Telegram " + TBC],
    },
    {
        "slug": "geylang-chinese-mc",
        "name": "Geylang Chinese Methodist Church",
        "zh": "卫理公会芽笼堂",
        "short": "GCMC",
        "accent": "#1f5f8b", "accent2": "#dceaf4",
        "tagline": "A home for every nation in Geylang, since 1905.",
        "intro": "Locals, Malaysians, mainland Chinese, Vietnamese, Thais and Indonesians worship together here. We also stand alongside the students of Geylang Methodist School (Secondary).",
        "services": [
            ("Sunday", "9:00 AM", "Mandarin Worship", "华语崇拜"),
            ("Sunday", "9:00 AM", "English Worship", "英语崇拜"),
            ("Sunday", "11:00 AM", "Hokkien Worship", "厦语崇拜"),
        ],
        "address": "Geylang Methodist School (Secondary), 2 Geylang East Central, Singapore 389705 " + TBC,
        "phone": "6748 5413",
        "email": "gcmc-admin@gcmc.org.sg",
        "ministries": ["Tuition for students", "Character building", "Student welfare", "Migrant fellowship", "Discipleship", "Missions"],
        "news": [
            ("Welcome", "New to GCMC? Here's what a Sunday looks like.", "Plan a visit"),
            ("Community", "Volunteer with our school tuition programme.", "Get involved"),
            ("Upcoming", "Christmas worship " + TBC, "See dates"),
        ],
        "socials": ["Facebook", "YouTube " + TBC, "Telegram " + TBC],
    },
    {
        "slug": "toa-payoh-chinese-mc",
        "name": "Toa Payoh Chinese Methodist Church",
        "zh": "",
        "short": "TPCMC",
        "accent": "#2f6b3f", "accent2": "#e0efe3",
        "tagline": "领人归主 · 作主门徒 — Bringing people to Christ, making disciples.",
        "intro": "Serving Toa Payoh and Bishan since 1973, in Mandarin, Hokkien and bilingual worship.",
        "services": [
            ("Sunday", "9:00 AM", "Mandarin Worship", "华语崇拜"),
            ("Sunday", "9:00 AM", "Hokkien Worship", "福建崇拜"),
            ("Sunday", "11:00 AM", "New Life Service (bilingual)", "新生命崇拜"),
        ],
        "address": "480 Lorong 2 Toa Payoh, Singapore 319641",
        "phone": "6353 3284",
        "email": "church_office@tpcmc.org.sg",
        "ministries": ["Seniors' Fellowship 乐龄团契", "Evangelism", "Missions", "Community care", "Discipleship", "Fellowship"],
        "news": [
            ("Christmas", "Christmas Day outreach, 25 Dec 2026. Bring a friend! 圣诞节布道会", "Details"),
            ("Church Camp 2027", "Our biennial church camp. Registration opened in October.", "Register"),
            ("Weekly bulletin", "Download this week's order of service 秩序单.", "Download"),
        ],
        "socials": ["Facebook", "YouTube", "Telegram " + TBC],
    },
    {
        "slug": "hinghwa-mc",
        "name": "Hinghwa Methodist Church",
        "zh": "卫理公会天道堂",
        "short": "HMC",
        "accent": "#6b3fa0", "accent2": "#ece3f6",
        "tagline": "Jesus is central to everything we do. Since 1911.",
        "intro": "In the heart of Lavender, worshipping in English, Mandarin and Hinghwa, and serving our neighbours through tuition and senior care.",
        "services": [
            ("Saturday", "5:00 PM", "Connect@5 (English)", "Level 4 Sanctuary"),
            ("Sunday", TBC, "Chinese Service", "华语崇拜"),
            ("Sunday", TBC, "Hinghwa Service", "兴化音崇拜"),
        ],
        "address": "93 Kitchener Road, Singapore 208510",
        "phone": "6298 3955",
        "email": "administrator@hinghwamc.org.sg",
        "ministries": ["Hi Connect kids (3–12)", "Pacesetters", "Neighbourhood Tuition Centre", "Glory Fellowship 荣美团契", "Silver Buddies 活跃乐龄", "EAT fellowship dinner"],
        "news": [
            ("Family Service", "First Saturday of every month: all ages worship together, with Holy Communion.", "Learn more"),
            ("EAT", "Fourth Saturday: stay for a catered fellowship dinner after Connect@5.", "Join us"),
            ("New here?", "Come as you are. No registration needed, about 90 minutes.", "Plan a visit"),
        ],
        "socials": ["Facebook", "YouTube " + TBC, "Telegram " + TBC],
    },
    {
        "slug": "bedok-mc",
        "name": "Bedok Methodist Church",
        "zh": "",
        "short": "BMC",
        "accent": "#b5651d", "accent2": "#f6e7d6",
        "tagline": "80 years of faith in the East.",
        "intro": "A community in Bedok worshipping in English and Chinese, with traditional and contemporary services every Sunday.",
        "services": [
            ("Sunday", "8:30 AM", "English (Traditional)", ""),
            ("Sunday", "10:00 AM", "Chinese Service", "华语崇拜"),
            ("Sunday", "11:30 AM", "English (Contemporary)", ""),
        ],
        "address": "86 Bedok Road, Singapore 469371",
        "phone": "6448 4215",
        "email": "office@bmc.org.sg",
        "ministries": ["Disciple Groups", "Children", "Youth", "Online Services", "Kindergarten", "Prayer Support"],
        "news": [
            ("BMC80", "Celebrating 80 years: stories, events and thanksgiving.", "Explore"),
            ("Sermon series", "Catch up on our current sermon series online.", "Listen"),
            ("Christmas", "Christmas services " + TBC, "See dates"),
        ],
        "socials": ["Facebook", "Instagram", "YouTube"],
    },
]

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{--a:ACCENT;--a2:ACCENT2;--ink:#1d1d1f;--mute:#5b5b62;--line:#e6e2dc;--bg:#fbfaf7}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue","PingFang SC","Microsoft YaHei",sans-serif;color:var(--ink);background:var(--bg);line-height:1.55}
a{color:inherit;text-decoration:none}
.concept{background:#111;color:#ddd;font-size:12px;text-align:center;padding:6px 12px}
.wrap{max-width:1100px;margin:0 auto;padding:0 20px}
header{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
header .wrap{display:flex;align-items:center;justify-content:space-between;height:68px;gap:16px}
.brand{display:flex;align-items:center;gap:10px;font-weight:700}
.mark{width:36px;height:36px;border-radius:10px;background:var(--a);display:grid;place-items:center}
.mark:before{content:"";width:4px;height:20px;background:#fff;border-radius:2px;box-shadow:0 0 0 0 #fff}
.mark{position:relative}.mark:after{content:"";position:absolute;width:14px;height:4px;background:#fff;border-radius:2px;top:13px}
.brand small{display:block;font-weight:500;color:var(--mute);font-size:12px}
nav{display:flex;gap:22px;font-size:14px;color:var(--mute)}
.btn{display:inline-block;white-space:nowrap;background:var(--a);color:#fff;padding:11px 18px;border-radius:999px;font-weight:600;font-size:14px}
.btn.ghost{background:transparent;color:var(--a);border:1.5px solid var(--a)}
.hero{background:linear-gradient(135deg,var(--a) 0%,color-mix(in srgb,var(--a) 70%,#000) 100%);color:#fff;padding:64px 0 72px;position:relative;overflow:hidden}
.hero:after{content:"";position:absolute;right:-120px;top:-120px;width:420px;height:420px;border-radius:50%;background:rgba(255,255,255,.07)}
.hero .wrap{display:grid;grid-template-columns:1.25fr 1fr;gap:40px;align-items:center;position:relative;z-index:1}
.eyebrow{font-size:13px;letter-spacing:.12em;text-transform:uppercase;opacity:.8}
.hero h1{font-size:44px;line-height:1.12;margin:10px 0 14px;letter-spacing:-.01em}
.hero p{font-size:17px;opacity:.92;max-width:520px}
.hero .ctas{margin-top:26px;display:flex;gap:12px;flex-wrap:wrap}
.hero .btn{background:#fff;color:var(--a)}
.hero .btn.ghost{background:transparent;color:#fff;border-color:rgba(255,255,255,.7)}
.times{background:#fff;color:var(--ink);border-radius:18px;padding:22px;box-shadow:0 20px 50px rgba(0,0,0,.18)}
.times h3{font-size:15px;margin-bottom:12px;display:flex;justify-content:space-between}
.times h3 span{color:var(--mute);font-weight:500;font-size:13px}
.t{display:grid;grid-template-columns:88px 1fr;gap:10px;padding:11px 0;border-top:1px solid var(--line)}
.t b{font-size:15px;color:var(--a)}.t small{display:block;color:var(--mute);font-size:12px}
.t div:last-child{font-weight:600;font-size:14px}
.times .addr{margin-top:12px;font-size:13px;color:var(--mute)}
section{padding:64px 0}
h2{font-size:28px;letter-spacing:-.01em;margin-bottom:8px}
.lead{color:var(--mute);margin-bottom:28px;max-width:640px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.card{background:#fff;border:1px solid var(--line);border-radius:16px;padding:22px}
.card .tag{display:inline-block;font-size:12px;font-weight:600;color:var(--a);background:var(--a2);padding:3px 10px;border-radius:999px;margin-bottom:12px}
.card p{font-size:15px;margin-bottom:14px}
.card a{font-weight:600;color:var(--a);font-size:14px}
.visit{background:var(--a2)}
.visit .wrap{display:grid;grid-template-columns:1fr 1fr;gap:36px;align-items:start}
.steps{display:grid;gap:12px}
.step{display:flex;gap:14px;background:#fff;border-radius:14px;padding:16px}
.step i{font-style:normal;width:30px;height:30px;border-radius:50%;background:var(--a);color:#fff;display:grid;place-items:center;font-weight:700;flex:none}
.step b{display:block}.step span{color:var(--mute);font-size:14px}
.map{background:#fff;border-radius:16px;height:100%;min-height:260px;display:grid;place-items:center;text-align:center;padding:24px;border:1px dashed color-mix(in srgb,var(--a) 40%,#fff)}
.map b{display:block;font-size:17px;margin:8px 0}
.pin{width:44px;height:44px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);background:var(--a);margin:0 auto}
.chips{display:flex;flex-wrap:wrap;gap:10px}
.chip{background:#fff;border:1px solid var(--line);border-radius:999px;padding:10px 16px;font-size:14px;font-weight:500}
.give{display:grid;grid-template-columns:1.2fr 1fr;gap:24px;align-items:center;background:#fff;border:1px solid var(--line);border-radius:20px;padding:32px}
.qr{width:150px;height:150px;border-radius:12px;margin-left:auto;background:repeating-conic-gradient(var(--ink) 0 25%,#fff 0 50%) 0 0/22px 22px;border:10px solid #fff;outline:1px solid var(--line);position:relative}
.qr:after{content:"PayNow";position:absolute;inset:auto 0 -34px 0;text-align:center;font-size:12px;font-weight:700;color:var(--a)}
footer{background:#17171a;color:#bbb;padding:44px 0;font-size:14px}
footer .wrap{display:grid;grid-template-columns:1.4fr 1fr 1fr;gap:28px}
footer b{color:#fff;display:block;margin-bottom:8px}
.tbc{display:inline-block;font-size:11px;font-weight:700;background:#ffe9a8;color:#6b4e00;padding:1px 7px;border-radius:6px;vertical-align:middle;letter-spacing:.02em}
@media(max-width:820px){
 nav{display:none}
 .brand{font-size:14px;line-height:1.25}.brand small{font-size:11px}
 header .btn{padding:9px 14px;font-size:13px}
 .hero{padding:40px 0 48px}.hero h1{font-size:32px}
 .hero .wrap,.visit .wrap,.give,footer .wrap{grid-template-columns:1fr}
 .grid3{grid-template-columns:1fr}
 .qr{margin:0 auto 30px}
 section{padding:44px 0}
}
"""


def page(c):
    e = lambda s: s  # content is authored here; html already escaped where needed
    times = "".join(
        f'<div class="t"><div><b>{t}</b><small>{d}</small></div><div>{n}<small>{zh}</small></div></div>'
        for d, t, n, zh in c["services"]
    )
    news = "".join(
        f'<div class="card"><span class="tag">{h}</span><p>{p}</p><a href="#">{l} →</a></div>' for h, p, l in c["news"]
    )
    mins = "".join(f'<span class="chip">{m}</span>' for m in c["ministries"])
    socials = " · ".join(c["socials"])
    zh = f'<small>{c["zh"]}</small>' if c["zh"] else f'<small>{c["short"]}</small>'
    css = CSS.replace("ACCENT2", c["accent2"]).replace("ACCENT", c["accent"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(c['name'])} — homepage concept</title><style>{css}</style></head>
<body>
<div class="concept">Concept redesign prepared for {html.escape(c['name'])}. Not the official website. Yellow tags mark details to confirm.</div>
<header><div class="wrap">
 <a class="brand" href="#"><span class="mark"></span><span>{c['name']}{zh}</span></a>
 <nav><a href="#visit">Plan a visit</a><a href="#services">Services</a><a href="#ministries">Ministries</a><a href="#news">Happenings</a><a href="#give">Give</a></nav>
 <a class="btn" href="#visit">I'm new</a>
</div></header>

<div class="hero"><div class="wrap">
 <div>
  <div class="eyebrow">Welcome · 欢迎</div>
  <h1>{c['tagline']}</h1>
  <p>{c['intro']}</p>
  <div class="ctas"><a class="btn" href="#visit">Plan your visit</a><a class="btn ghost" href="#news">Watch online</a></div>
 </div>
 <div class="times" id="services">
  <h3>Join us this weekend <span>Service times</span></h3>
  {times}
  <div class="addr">📍 {c['address']}</div>
 </div>
</div></div>

<section id="news"><div class="wrap">
 <h2>Happening at {c['short']}</h2>
 <p class="lead">What's coming up, kept up to date by our volunteers in minutes from a phone.</p>
 <div class="grid3">{news}</div>
</div></section>

<section class="visit" id="visit"><div class="wrap">
 <div>
  <h2>Planning your first visit?</h2>
  <p class="lead">Come as you are. Here's what to expect.</p>
  <div class="steps">
   <div class="step"><i>1</i><div><b>Pick a service</b><span>Choose the language and time that suits you best.</span></div></div>
   <div class="step"><i>2</i><div><b>Getting here</b><span>Nearest MRT, bus and parking details {TBC}</span></div></div>
   <div class="step"><i>3</i><div><b>Say hello</b><span>Our welcome team will help you find a seat, and the kids' programme if you need it.</span></div></div>
  </div>
 </div>
 <div class="map"><div><div class="pin"></div><b>{c['name']}</b><span>{c['address']}</span><br><br><a class="btn ghost" href="#">Open in Google Maps</a></div></div>
</div></section>

<section id="ministries"><div class="wrap">
 <h2>Find your place</h2>
 <p class="lead">There's a community for every age and season of life.</p>
 <div class="chips">{mins}</div>
</div></section>

<section id="give" style="padding-top:0"><div class="wrap">
 <div class="give">
  <div><h2>Give online</h2><p class="lead" style="margin-bottom:16px">Support the work of the church with PayNow or bank transfer. Details {TBC}</p><a class="btn" href="#">Ways to give</a></div>
  <div class="qr" aria-label="PayNow QR placeholder"></div>
 </div>
</div></section>

<footer><div class="wrap">
 <div><b>{c['name']}</b>{c['address']}<br>Tel {c['phone']} · {c['email']}</div>
 <div><b>Stay connected</b>{socials}</div>
 <div><b>Quick links</b>Bulletin · Sermons · Contact · Data protection</div>
</div></footer>
</body></html>"""


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for c in CHURCHES:
        d = OUT / c["slug"]
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(page(c))
        print("wrote", d / "index.html")
