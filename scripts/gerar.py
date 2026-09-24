#!/usr/bin/env python3
"""Gera os SVGs do perfil.

Os cartoes fixos saem iguais toda vez (aleatoriedade com semente). A floresta
depende do calendario de contribuicoes e a licenca usa o avatar atual, os dois
lidos do GitHub, por isso a Action roda este script todo dia. Sem GITHUB_TOKEN a
floresta e pulada e o arquivo que ja existe fica como esta.

Fonte: subconjunto da Cascadia Mono (SIL OFL, ver fontes/OFL.txt) renomeado
pra HunterMono. Cada SVG embute so os caracteres que usa.
Imagens: scripts/imagens, embutidas em base64 (SVG em <img> nao busca nada de fora).
"""
import base64
import hashlib
import io
import json
import math
import os
import random
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "assets"
AQUI = Path(__file__).resolve().parent
FONTES = AQUI / "fontes"
IMAGENS = AQUI / "imagens"
USUARIO = os.environ.get("PERFIL", "NetoPissolato")

# Paleta: grafite neutro, ambar do Jajanken e do friso da jaqueta como acento.
# O verde fica com as imagens do Gon e com o capim.
BG0 = "#0a0b0d"
BG1 = "#111317"
BG2 = "#181b21"
LINHA = "#272b33"
ACENTO = "#ffab40"
ACENTO_ESC = "#b8641a"
BRASA = "#ffd27a"
CLARO = "#e7ebef"
TEXTO = "#f1f3f5"
SUAVE = "#9aa3ad"
APAGADO = "#5f6772"
OURO = "#f0c060"
GRAMA = "#3fbf7f"
GRAMA_ESC = "#1d6f4b"
GRAMA_CLARA = "#9be8b8"
AGUA = "#8cc8ff"
VAGALUME = "#ffd66b"
CINZA = "#8b949e"  # legivel em tema claro e escuro

AVANCO = 1200 / 2048  # largura de um caractere da Cascadia Mono, em em


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def largura(texto, tam, ls=0):
    return len(texto) * (tam * AVANCO + ls)


def quebrar(texto, tam, maximo):
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if largura(teste, tam) > maximo and atual:
            linhas.append(atual)
            atual = palavra
        else:
            atual = teste
    return linhas + [atual]


def imagem(nome):
    tipo = {"webp": "image/webp", "png": "image/png", "jpg": "image/jpeg"}[nome.rsplit(".", 1)[1]]
    return f"data:{tipo};base64," + base64.b64encode((IMAGENS / nome).read_bytes()).decode()


def avatar():
    try:
        with urllib.request.urlopen(f"https://github.com/{USUARIO}.png?size=320", timeout=20) as r:
            tipo = r.headers.get_content_type()
            return f"data:{tipo};base64," + base64.b64encode(r.read()).decode()
    except Exception as e:  # sem rede: a licenca sai com silhueta
        print(f"  avatar indisponivel ({e})")
        return None


_cache_fonte = {}


def subconjunto(peso, chars):
    from fontTools.ttLib import TTFont
    from fontTools import subset

    chave = (peso, "".join(sorted(chars)))
    if chave in _cache_fonte:
        return _cache_fonte[chave]
    fonte = TTFont(FONTES / f"huntermono-{peso}.woff2")
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.hinting = False
    opts.layout_features = ["kern"]
    opts.name_IDs = ["*"]
    s = subset.Subsetter(opts)
    s.populate(text="".join(chars))
    s.subset(fonte)
    buf = io.BytesIO()
    fonte.save(buf)
    dados = base64.b64encode(buf.getvalue()).decode()
    _cache_fonte[chave] = dados
    return dados


class Tela:
    def __init__(self, w, h, titulo, desc):
        self.w, self.h = w, h
        self.titulo, self.desc = titulo, desc
        self.defs, self.css, self.corpo = [], [], []
        self.usados = {400: set(), 700: set()}

    def usa(self, texto, peso=400):
        self.usados[peso].update(texto)

    def txt(self, x, y, texto, tam, peso=400, cor=TEXTO, anchor=None, ls=0, extra=""):
        self.usa(texto, peso)
        a = f' text-anchor="{anchor}"' if anchor else ""
        l = f' letter-spacing="{ls}"' if ls else ""
        self.corpo.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{tam}" font-weight="{peso}" '
            f'fill="{cor}"{a}{l} {extra}>{esc(texto)}</text>'
        )

    def add(self, *partes):
        self.corpo.extend(partes)

    def svg(self):
        faces = "".join(
            "@font-face{font-family:'HunterMono';font-weight:%d;"
            "src:url(data:font/woff2;base64,%s) format('woff2')}" % (p, subconjunto(p, c))
            for p, c in self.usados.items()
            if c
        )
        css = faces + "text{font-family:'HunterMono',ui-monospace,Menlo,Consolas,monospace}" + "".join(self.css)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="t d">'
            f'<title id="t">{esc(self.titulo)}</title><desc id="d">{esc(self.desc)}</desc>'
            f'<defs><style>{css}</style>{"".join(self.defs)}</defs>{"".join(self.corpo)}</svg>'
        )

    def salvar(self, nome):
        ASSETS.mkdir(exist_ok=True)
        conteudo = self.svg()
        (ASSETS / nome).write_text(conteudo, encoding="utf-8")
        print(f"  {nome}  {len(conteudo) // 1024} KB")


FILTROS = (
    '<filter id="brilho" x="-50%" y="-50%" width="200%" height="200%">'
    '<feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/>'
    '<feMergeNode in="SourceGraphic"/></feMerge></filter>'
    '<filter id="nevoa" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="28"/></filter>'
    '<filter id="nevoa-p" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="10"/></filter>'
)


def base(t, rx=22, fundo=None):
    """Clip arredondado, fundo e abre o grupo recortado. Fechar com fechar()."""
    t.defs.append(f'<clipPath id="card"><rect width="{t.w}" height="{t.h}" rx="{rx}"/></clipPath>')
    t.add('<g clip-path="url(#card)">', f'<rect width="{t.w}" height="{t.h}" fill="{fundo or BG1}"/>')


def fechar(t, rx=22, borda=LINHA, opacidade=1):
    t.add('</g>', f'<rect x=".75" y=".75" width="{t.w - 1.5}" height="{t.h - 1.5}" rx="{rx}" fill="none" '
                  f'stroke="{borda}" stroke-opacity="{opacidade}" stroke-width="1.5"/>')


def capim(rnd, x0, x1, chao, hmin, hmax, cor, passo=6, grupos=10):
    folhas = []
    x = x0
    while x < x1:
        h = rnd.uniform(hmin, hmax)
        w = rnd.uniform(1.6, 2.8)
        dobra = rnd.uniform(-5, 5)
        folhas.append(f"M{x - w:.1f} {chao}Q{x - w + dobra * .3:.1f} {chao - h * .5:.1f} {x + dobra:.1f} {chao - h:.1f}"
                      f"Q{x + w + dobra * .3:.1f} {chao - h * .5:.1f} {x + w:.1f} {chao}Z")
        x += rnd.uniform(passo * .6, passo * 1.4)
    tam = max(1, len(folhas) // grupos)
    return "".join(
        f'<g class="balanca" style="animation-duration:{rnd.uniform(4.5, 7.5):.1f}s;animation-delay:-{rnd.uniform(0, 5):.1f}s">'
        f'<path fill="{cor}" d="{"".join(folhas[i:i + tam])}"/></g>'
        for i in range(0, len(folhas), tam))


CSS_BALANCA = (
    ".balanca{transform-box:fill-box;transform-origin:50% 100%;"
    "animation:balanca 6s ease-in-out infinite alternate}"
    "@keyframes balanca{from{transform:skewX(-4deg)}to{transform:skewX(4deg)}}"
)
CSS_VIVO = ".vivo{animation:vivo 2s ease-in-out infinite}@keyframes vivo{50%{opacity:.3}}"


def pontos(t):
    t.defs.append(f'<pattern id="pontos" width="28" height="28" patternUnits="userSpaceOnUse">'
                  f'<circle cx="2" cy="2" r="1" fill="{LINHA}"/></pattern>')
    t.add(f'<rect width="{t.w}" height="{t.h}" fill="url(#pontos)" opacity=".45"/>')


# ---------------------------------------------------------------- cabecalho
CICLO = 10  # segundos do jan-ken; o clarao do punho bate com o DEPLOY!
DEPLOY_EM = 50  # % do ciclo


def cabecalho():
    rnd = random.Random(405)
    t = Tela(1200, 400, "José Pissolato — Hunter de código",
             "Gon carregando o Jajanken ao lado do nome. O terminal digita saisho wa guu, jan, ken, DEPLOY "
             "e o punho do Gon brilha no DEPLOY.")
    # imagem do Gon: 1100x648, punho em (367, 222) no arquivo
    esc_img, ix, iy = 470 / 648, 505, -18
    pw, ph = 1100 * esc_img, 648 * esc_img
    px, py = ix + 367 * esc_img, iy + 222 * esc_img
    t.defs.append(
        f'<radialGradient id="fundo" cx="72%" cy="40%" r="75%"><stop offset="0" stop-color="#1d1a17"/>'
        f'<stop offset=".6" stop-color="{BG1}"/><stop offset="1" stop-color="{BG0}"/></radialGradient>'
        f'<linearGradient id="some" gradientUnits="userSpaceOnUse" x1="{ix + 50}" y1="0" x2="{ix + 220}" y2="0">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff"/></linearGradient>'
        f'<mask id="mascara"><rect width="1200" height="400" fill="url(#some)"/></mask>'
        f'<radialGradient id="clarao"><stop offset="0" stop-color="#fff"/><stop offset=".25" stop-color="{BRASA}"/>'
        f'<stop offset=".6" stop-color="{ACENTO}" stop-opacity=".35"/><stop offset="1" stop-color="{ACENTO}" stop-opacity="0"/>'
        '</radialGradient>'
        + FILTROS
    )
    a = DEPLOY_EM
    t.css.append(
        CSS_BALANCA
        + ".pulsa{transform-box:fill-box;transform-origin:center;animation:pulsa 4s ease-in-out infinite}"
        "@keyframes pulsa{0%,100%{transform:scale(.92);opacity:.18}50%{transform:scale(1.08);opacity:.32}}"
        ".sobe{animation:sobe 5s linear infinite}"
        "@keyframes sobe{0%{transform:translateY(0);opacity:0}15%{opacity:1}100%{transform:translateY(-220px);opacity:0}}"
        f".clarao{{transform-box:fill-box;transform-origin:center;mix-blend-mode:screen;animation:clarao {CICLO}s ease-out infinite}}"
        f"@keyframes clarao{{0%,{a - 1}%{{transform:scale(.5);opacity:0}}{a}%{{transform:scale(1.35);opacity:1}}"
        f"{a + 8}%{{transform:scale(1);opacity:.45}}90%{{transform:scale(.95);opacity:.3}}100%{{transform:scale(.5);opacity:0}}}}"
        ".cursor{animation:pisca 1s steps(1) infinite}@keyframes pisca{50%{opacity:0}}"
    )
    base(t, 24, "url(#fundo)")
    pontos(t)

    # brasa atras do punho e particulas subindo
    t.add(f'<ellipse class="pulsa" cx="{px:.0f}" cy="{py + 20:.0f}" rx="210" ry="190" fill="{ACENTO}" filter="url(#nevoa)"/>')
    for _ in range(18):
        t.add(f'<circle class="sobe" style="animation-delay:-{rnd.uniform(0, 5):.2f}s;animation-duration:{rnd.uniform(3.8, 6.5):.2f}s" '
              f'cx="{rnd.uniform(640, 1180):.0f}" cy="{rnd.uniform(300, 400):.0f}" r="{rnd.uniform(1.2, 2.8):.1f}" '
              f'fill="{rnd.choice([BRASA, ACENTO, TEXTO])}"/>')

    t.add(f'<image href="{imagem("gon-jajanken.webp")}" x="{ix}" y="{iy}" width="{pw:.0f}" height="{ph:.0f}" mask="url(#mascara)"/>',
          f'<circle class="clarao" cx="{px:.0f}" cy="{py:.0f}" r="95" fill="url(#clarao)"/>')

    # texto
    t.add(f'<text x="72" y="112" font-size="15" font-weight="700" letter-spacing="4" fill="{ACENTO}">'
          f'▸ HUNTER DE CÓDIGO<tspan fill="{APAGADO}"> · BRASIL</tspan></text>')
    t.usa("▸ HUNTER DE CÓDIGO · BRASIL", 700)
    t.txt(72, 190, "JOSÉ PISSOLATO", 66, 700, TEXTO, ls=2)
    t.txt(74, 234, "dev full-stack · desktop · web · bots · IA", 20, 400, SUAVE)

    # jan-ken em loop: cada pedaco aparece e fica ate o fim do ciclo
    t.add(f'<rect x="72" y="276" width="566" height="50" rx="14" fill="{BG0}" fill-opacity=".8" stroke="{LINHA}"/>')
    x0, y, tam = 96, 308, 18
    cw = tam * AVANCO
    pedacos = [("$", ACENTO, 700, 0), (" saisho wa guu,", SUAVE, 400, 6), (" jan...", SUAVE, 400, 22),
               (" ken...", SUAVE, 400, 36), (" DEPLOY!", BRASA, 700, DEPLOY_EM)]
    col = 0
    cursor_pos = []
    for i, (texto, cor, peso, entra) in enumerate(pedacos):
        nome = f"jk{i}"
        t.css.append(f".{nome}{{animation:{nome} {CICLO}s steps(1) infinite}}"
                     f"@keyframes {nome}{{0%{{opacity:{1 if entra == 0 else 0}}}{max(entra, 0.01)}%{{opacity:1}}92%{{opacity:0}}}}")
        extra = f'class="{nome}"' + (' filter="url(#brilho)"' if "DEPLOY" in texto else "")
        recuo = len(texto) - len(texto.lstrip())  # SVG engole espaco no comeco do <text>
        t.txt(x0 + (col + recuo) * cw, y, texto.lstrip(), tam, peso, cor, extra=extra)
        col += len(texto)
        cursor_pos.append((entra, x0 + col * cw + 3))
    quadros = "".join(f"{max(e, 0.01)}%{{transform:translateX({x - cursor_pos[0][1]:.1f}px)}}" for e, x in cursor_pos)
    t.css.append(f".anda{{animation:anda {CICLO}s steps(1) infinite}}"
                 f"@keyframes anda{{0%{{transform:translateX(0)}}{quadros}92%{{transform:translateX(0)}}}}")
    t.add(f'<g class="anda"><rect class="cursor" x="{cursor_pos[0][1]:.1f}" y="292" width="10" height="20" fill="{ACENTO}"/></g>')

    t.add(capim(rnd, -10, 1210, 402, 16, 40, "#121419", passo=5, grupos=12),
          capim(rnd, -10, 1210, 402, 8, 24, "#171a20", passo=6, grupos=12))
    for x, y, sx, sy in [(20, 20, 1, 1), (1180, 20, -1, 1), (20, 380, 1, -1), (1180, 380, -1, -1)]:
        t.add(f'<path d="M{x} {y + 18 * sy}V{y}H{x + 18 * sx}" fill="none" stroke="{SUAVE}" stroke-width="2" opacity=".4"/>')
    fechar(t, 24)
    return t


# ---------------------------------------------------------------- licenca
def licenca(foto):
    rnd = random.Random(1998)
    t = Tela(600, 360, "Hunter License de José Pissolato",
             "Licença Hunter: José I. Pissolato Neto, Hunter de Código, tipo de Nen Reforço, emitida em 20/05/2019.")
    t.defs.append(
        f'<linearGradient id="fundo" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BG2}"/>'
        f'<stop offset="1" stop-color="{BG0}"/></linearGradient>'
        '<linearGradient id="holo" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        f'<stop offset=".45" stop-color="#fff" stop-opacity=".07"/><stop offset=".55" stop-color="{OURO}" stop-opacity=".12"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="pessoa" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{SUAVE}"/>'
        f'<stop offset="1" stop-color="{SUAVE}" stop-opacity=".12"/></linearGradient>'
        '<clipPath id="foto"><rect x="40" y="96" width="136" height="172" rx="14"/></clipPath>'
        + FILTROS
    )
    t.css.append(
        ".holo{animation:holo 7s ease-in-out infinite}"
        "@keyframes holo{0%{transform:translateX(-260px) skewX(-18deg)}55%,100%{transform:translateX(900px) skewX(-18deg)}}"
        ".gira{transform-box:fill-box;transform-origin:center;animation:gira 24s linear infinite}"
        "@keyframes gira{to{transform:rotate(360deg)}}" + CSS_VIVO
    )
    base(t, 22, "url(#fundo)")
    for k in range(12):
        pts = " ".join(f"{x},{70 + k * 24 + 9 * math.sin(x / 38 + k * .9):.1f}" for x in range(0, 604, 8))
        t.add(f'<polyline points="{pts}" fill="none" stroke="{TEXTO}" stroke-opacity=".035" stroke-width="1"/>')
    t.add('<rect class="holo" x="0" y="-40" width="170" height="440" fill="url(#holo)"/>')

    t.txt(40, 56, "HUNTER LICENSE", 20, 700, OURO, ls=5)
    t.txt(506, 56, "Nº 0405", 14, 700, OURO, anchor="end", extra='opacity=".85"')
    hexa = lambda cx, cy, r, rot=0: " ".join(
        f"{cx + r * math.cos(math.radians(60 * i + rot)):.1f},{cy + r * math.sin(math.radians(60 * i + rot)):.1f}" for i in range(6))
    t.add(f'<g class="gira"><polygon points="{hexa(546, 50, 20, 30)}" fill="none" stroke="{OURO}" stroke-width="1.8"/>'
          f'<polygon points="{hexa(546, 50, 11)}" fill="none" stroke="{OURO}" stroke-width="1.2" opacity=".7"/></g>'
          f'<circle cx="546" cy="50" r="2.6" fill="{OURO}"/>',
          f'<line x1="40" y1="74" x2="560" y2="74" stroke="{OURO}" stroke-opacity=".35"/>')

    t.add(f'<rect x="40" y="96" width="136" height="172" rx="14" fill="{BG0}"/>', '<g clip-path="url(#foto)">')
    if foto:
        t.add(f'<image href="{foto}" x="22" y="96" width="172" height="172" preserveAspectRatio="xMidYMid slice"/>')
    else:
        t.add('<circle cx="108" cy="166" r="30" fill="url(#pessoa)"/>',
              '<path d="M48 272c4-40 28-62 60-62s56 22 60 62z" fill="url(#pessoa)"/>')
    t.add('</g>', f'<rect x="40" y="96" width="136" height="172" rx="14" fill="none" stroke="{OURO}" stroke-opacity=".35" stroke-width="1.5"/>')

    campos = [(200, 112, "NOME", "José I. Pissolato Neto", TEXTO),
              (200, 168, "CLASSE", "Hunter de Código", TEXTO),
              (200, 224, "TIPO DE NEN", "Reforço", ACENTO), (380, 224, "EMITIDA EM", "20.05.2019", TEXTO),
              (200, 280, "ORIGEM", "Brasil", TEXTO)]
    for x, y, rot, val, cor in campos:
        t.txt(x, y, rot, 12, 700, SUAVE, ls=2, extra='opacity=".75"')
        t.txt(x, y + 24, val, 19, 700, cor)
    t.txt(380, 280, "ESTADO", 12, 700, SUAVE, ls=2, extra='opacity=".75"')
    t.add(f'<circle class="vivo" cx="386" cy="298" r="5" fill="{ACENTO}"/>')
    t.txt(398, 304, "ativa", 19, 700, TEXTO)

    x = 40
    while x < 176:
        w = rnd.choice([1, 1, 2, 3])
        t.add(f'<rect x="{x}" y="288" width="{w}" height="30" fill="{SUAVE}" opacity=".7"/>')
        x += w + rnd.choice([1, 2, 2, 3])
    t.txt(40, 340, "github.com/NetoPissolato", 12, 400, APAGADO)
    t.txt(560, 340, "acesso a 90% dos países", 12, 400, APAGADO, anchor="end")
    fechar(t, 22, OURO, .45)
    return t


# ---------------------------------------------------------------- teste da agua
NEN = [  # (tipo, habilidade, nivel) no sentido horario a partir do topo, como no hexagono do anime
    ("REFORÇO", "backend · Python", .95),
    ("TRANSFORMAÇÃO", "front · Next.js", .72),
    ("MATERIALIZAÇÃO", "desktop · C++", .85),
    ("ESPECIALIZAÇÃO", "IA · MCP", .78),
    ("MANIPULAÇÃO", "bots · automação", .9),
    ("EMISSÃO", "tempo real · WebRTC", .8),
]


def nen():
    t = Tela(600, 360, "Teste da água: tipo de Nen",
             "Hexágono do Nen usado como mapa de habilidades. Reforço é backend, Transformação é front-end, "
             "Materialização é desktop, Especialização é IA, Manipulação é bots, Emissão é tempo real. "
             "No copo, a água sobe e transborda: resultado Reforço.")
    cx, cy, R = 300, 214, 94
    t.defs.append(
        f'<radialGradient id="fundo" cx="50%" cy="58%" r="70%"><stop offset="0" stop-color="{BG2}"/>'
        f'<stop offset="1" stop-color="{BG0}"/></radialGradient>'
        f'<clipPath id="copo"><path d="M{cx - 19} {cy - 24}h38l-4 48h-30z"/></clipPath>'
        + FILTROS
    )
    t.css.append(
        f".radar{{transform-box:view-box;transform-origin:{cx}px {cy}px;animation:radar 4s ease-in-out infinite}}"
        "@keyframes radar{0%,100%{transform:scale(.96)}50%{transform:scale(1.03)}}"
        ".agua{animation:agua 7s ease-in-out infinite}"
        "@keyframes agua{0%{transform:translateY(30px)}55%,88%{transform:translateY(-3px)}100%{transform:translateY(30px)}}"
        ".gota{animation:gota 7s ease-in infinite}"
        "@keyframes gota{0%,55%{transform:translateY(0);opacity:0}58%{opacity:1}75%{transform:translateY(46px);opacity:0}"
        "100%{opacity:0}}"
    )
    ang = [math.radians(-90 + 60 * i) for i in range(6)]
    pt = lambda i, r: (cx + r * math.cos(ang[i]), cy + r * math.sin(ang[i]))
    poly = lambda r: " ".join(f"{pt(i, r)[0]:.1f},{pt(i, r)[1]:.1f}" for i in range(6))

    base(t, 22, "url(#fundo)")
    t.txt(40, 50, "TESTE DA ÁGUA", 20, 700, TEXTO, ls=4)
    t.add(f'<text x="560" y="50" font-size="14" font-weight="700" text-anchor="end" fill="{SUAVE}">'
          f'resultado: <tspan fill="{ACENTO}">REFORÇO</tspan></text>')
    t.usa("resultado: REFORÇO", 700)
    for k in (1 / 3, 2 / 3, 1):
        t.add(f'<polygon points="{poly(R * k)}" fill="none" stroke="{LINHA}" stroke-width="{1.6 if k == 1 else 1}"/>')
    for i in range(6):
        x, y = pt(i, R)
        t.add(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{LINHA}"/>')

    valores = " ".join(f"{pt(i, R * n)[0]:.1f},{pt(i, R * n)[1]:.1f}" for i, (_, _, n) in enumerate(NEN))
    t.add('<g class="radar">',
          f'<polygon points="{valores}" fill="{ACENTO}" fill-opacity=".12" filter="url(#nevoa-p)"/>',
          f'<polygon points="{valores}" fill="{ACENTO}" fill-opacity=".1" stroke="{ACENTO}" stroke-width="1.8" stroke-linejoin="round"/>',
          *[f'<circle cx="{pt(i, R * n)[0]:.1f}" cy="{pt(i, R * n)[1]:.1f}" r="{5 if i == 0 else 3.5}" '
            f'fill="{BRASA if i == 0 else ACENTO}"/>' for i, (_, _, n) in enumerate(NEN)],
          '</g>')
    for i, (tipo, hab, _) in enumerate(NEN):
        x, y = pt(i, R)
        cor = ACENTO if i == 0 else TEXTO
        if i == 0:
            t.txt(x, y - 30, tipo, 15, 700, cor, anchor="middle", ls=1)
            t.txt(x, y - 13, hab, 13, 400, SUAVE, anchor="middle")
        elif i == 3:
            t.txt(x, y + 24, tipo, 15, 700, cor, anchor="middle", ls=1)
            t.txt(x, y + 41, hab, 13, 400, SUAVE, anchor="middle")
        else:
            dx = 14 if x > cx else -14
            anc = "start" if x > cx else "end"
            t.txt(x + dx, y - 3, tipo, 15, 700, cor, anchor=anc, ls=1)
            t.txt(x + dx, y + 15, hab, 13, 400, SUAVE, anchor=anc)

    # copo com folha: a agua sobe e transborda (sinal de Reforco)
    t.add(f'<path d="M{cx - 19} {cy - 24}h38l-4 48h-30z" fill="{BG0}" fill-opacity=".85"/>',
          '<g clip-path="url(#copo)"><g class="agua">',
          f'<rect x="{cx - 24}" y="{cy - 24}" width="48" height="60" fill="{AGUA}" fill-opacity=".4"/>',
          f'<rect x="{cx - 24}" y="{cy - 24}" width="48" height="2" fill="#d8ecff" fill-opacity=".9"/>',
          '</g></g>',
          f'<g class="agua"><ellipse cx="{cx + 3}" cy="{cy - 26}" rx="8" ry="3" fill="{GRAMA}" '
          f'transform="rotate(-14 {cx + 3} {cy - 26})"/></g>',
          f'<path d="M{cx - 19} {cy - 24}l4 48h30l4-48" fill="none" stroke="{TEXTO}" stroke-opacity=".6" stroke-width="2" '
          f'stroke-linejoin="round"/>',
          f'<circle class="gota" cx="{cx - 21}" cy="{cy - 22}" r="2.4" fill="{AGUA}"/>',
          f'<circle class="gota" style="animation-delay:.5s" cx="{cx + 21}" cy="{cy - 22}" r="2.4" fill="{AGUA}"/>')
    fechar(t)
    return t


# ---------------------------------------------------------------- arcos
ICONES = {
    "memoria": 'M-12 -10a5 5 0 1 0 0.1 0M12 -10a5 5 0 1 0 0.1 0M0 11a5 5 0 1 0 0.1 0M-8 -7L-3 7M8 -7L3 7M-7 -10H7',
    "carro": 'M-19 6v-6l5 -9h20l7 9h6v6zM-11 6a4 4 0 1 0 0.1 0M11 6a4 4 0 1 0 0.1 0',
}


def chips(t, x0, y, itens, tam, limite):
    x = x0
    for c in itens:
        w = largura(c, tam) + tam * 2
        if x + w > limite:
            x, y = x0, y + tam * 2.8
        t.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{tam * 2.1:.1f}" rx="{tam * 1.05:.1f}" '
              f'fill="{BG0}" stroke="{LINHA}"/>')
        t.txt(x + tam, y + tam * 1.42, c, tam, 400, CLARO)
        x += w + 10
    return y


def borda_corrente(t, rx, dur):
    t.defs.append(f'<linearGradient id="borda" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BRASA}"/>'
                  f'<stop offset="1" stop-color="{ACENTO}"/></linearGradient>')
    t.css.append(f".corre{{animation:corre {dur}s linear infinite}}@keyframes corre{{to{{stroke-dashoffset:-100}}}}")
    t.add(f'<rect class="corre" x=".75" y=".75" width="{t.w - 1.5}" height="{t.h - 1.5}" rx="{rx}" fill="none" '
          f'stroke="url(#borda)" stroke-width="1.5" pathLength="100" stroke-dasharray="8 92" stroke-linecap="round" opacity=".85"/>')


def arco_destaque():
    rnd = random.Random(1)
    t = Tela(1200, 270, "Arco 01: Spacercord",
             "Projeto em destaque. Spacercord: compartilhe a tela com os amigos escolhendo exatamente quais "
             "programas levam áudio junto. Electron, C++ nativo, WebRTC e LiveKit. Versão 0.21.1.")
    t.defs.append(
        f'<linearGradient id="fundo" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BG2}"/>'
        f'<stop offset="1" stop-color="{BG0}"/></linearGradient>'
        + FILTROS
    )
    t.css.append(CSS_VIVO + ".barra{transform-box:fill-box;transform-origin:50% 100%;animation:barra 1.2s ease-in-out infinite alternate}"
                 "@keyframes barra{from{transform:scaleY(.15)}to{transform:scaleY(1)}}")
    base(t, 22, "url(#fundo)")

    # marca do Spacercord num circulo com anel ambar
    t.add(f'<circle cx="130" cy="135" r="86" fill="{ACENTO}" filter="url(#nevoa)" opacity=".12"/>',
          f'<circle cx="130" cy="135" r="72" fill="{BG0}" stroke="{ACENTO}" stroke-opacity=".6" stroke-width="2"/>',
          f'<image href="{imagem("spacercord.png")}" x="82" y="97" width="96" height="75"/>')

    t.txt(250, 68, "ARCO 01 · PROJETO EM DESTAQUE", 13, 700, ACENTO, ls=3)
    t.txt(250, 108, "SPACERCORD", 36, 700, TEXTO, ls=1)
    for i, linha in enumerate(quebrar("Compartilhe a tela com os amigos escolhendo exatamente quais programas levam áudio junto.", 18, 560)):
        t.txt(250, 146 + i * 26, linha, 18, 400, SUAVE)
    chips(t, 250, 196, ["Electron", "C++ nativo", "WebRTC", "LiveKit", "Node.js"], 14, 840)

    # equalizador: um canal de audio por programa
    x0, chao = 900, 150
    for i in range(16):
        h = rnd.uniform(30, 90)
        t.add(f'<rect class="barra" style="animation-delay:-{rnd.uniform(0, 1.2):.2f}s;animation-duration:{rnd.uniform(.6, 1.4):.2f}s" '
              f'x="{x0 + i * 16}" y="{chao - h:.0f}" width="9" height="{h:.0f}" rx="3" '
              f'fill="{ACENTO if i % 4 else BRASA}" opacity="{.35 + (i % 4) * .15:.2f}"/>')
    t.add(f'<rect x="900" y="176" width="252" height="48" rx="14" fill="{ACENTO}" fill-opacity=".1" stroke="{ACENTO}" stroke-opacity=".7"/>')
    t.txt(1026, 207, "baixar a v0.21.1 →", 16, 700, BRASA, anchor="middle")
    borda_corrente(t, 22, 9)
    fechar(t)
    return t


def arco(n, titulo, texto, itens, estado, icone):
    t = Tela(600, 290, f"Arco {n:02d}: {titulo}", texto)
    t.defs.append(f'<linearGradient id="fundo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG2}"/>'
                  f'<stop offset="1" stop-color="{BG0}"/></linearGradient>')
    t.css.append(CSS_VIVO)
    base(t, 22, "url(#fundo)")
    t.txt(572, 118, f"{n:02d}", 120, 700, TEXTO, anchor="end", extra='opacity=".04"')
    t.add(f'<rect x="36" y="36" width="64" height="64" rx="18" fill="{BG0}" stroke="{LINHA}"/>',
          f'<path transform="translate(68 68) scale(1.25)" d="{ICONES[icone]}" fill="none" stroke="{ACENTO}" stroke-width="2" '
          f'stroke-linecap="round" stroke-linejoin="round"/>')
    t.txt(120, 60, f"ARCO {n:02d}", 14, 700, ACENTO, ls=3)
    t.txt(120, 92, titulo, 28, 700, TEXTO)
    for i, linha in enumerate(quebrar(texto, 19, 528)):
        t.txt(36, 144 + i * 27, linha, 19, 400, SUAVE)
    chips(t, 36, 190, itens, 15, 564)
    t.add(f'<circle class="vivo" cx="42" cy="258" r="5" fill="{ACENTO}"/>')
    t.txt(56, 264, estado, 16, 400, SUAVE)
    borda_corrente(t, 22, 7 + n)
    fechar(t)
    return t


def titulo_secao(texto, sub):
    t = Tela(1200, 64, texto, sub)
    t.defs.append(f'<linearGradient id="some" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CINZA}" stop-opacity=".5"/>'
                  f'<stop offset="1" stop-color="{CINZA}" stop-opacity="0"/></linearGradient>')
    t.add(f'<rect x="2" y="18" width="5" height="26" rx="2.5" fill="{ACENTO}"/>')
    t.txt(20, 40, texto, 26, 700, CINZA, ls=6)
    x = 20 + largura(texto, 26, 6) + 16
    t.txt(x, 40, sub, 15, 400, CINZA)
    x += largura(sub, 15) + 20
    t.add(f'<rect x="{x:.0f}" y="34" width="{1196 - x:.0f}" height="2" fill="url(#some)"/>')
    return t


# ---------------------------------------------------------------- floresta
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def contribuicoes():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return None
    q = {"query": "query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{"
                  "totalContributions weeks{contributionDays{date contributionCount}}}}}}",
         "variables": {"u": USUARIO}}
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps(q).encode(),
                                 headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                                          "User-Agent": "perfil-hunter"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    cal = d["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    dias = [(date.fromisoformat(x["date"]), x["contributionCount"])
            for w in cal["weeks"] for x in w["contributionDays"]]
    return cal["totalContributions"], dias


def sequencias(dias):
    ate = dias[:-1] if dias and dias[-1][1] == 0 else dias  # hoje ainda sem commit nao quebra a sequencia
    atual = 0
    for _, c in reversed(ate):
        if not c:
            break
        atual += 1
    recorde = corrida = 0
    for _, c in dias:
        corrida = corrida + 1 if c else 0
        recorde = max(recorde, corrida)
    return atual, recorde


BRILHO = ' filter="url(#brilho)"'


def floresta(total, dias):
    rnd = random.Random(7)
    atual, recorde = sequencias(dias)
    melhor = max(dias, key=lambda d: d[1])
    W, H, chao = 1200, 340, 290
    t = Tela(W, H, "Treino diário: contribuições do último ano",
             f"Gon pescando ao lado do gráfico. {total} contribuições no último ano, sequência atual de {atual} dias, "
             f"recorde de {recorde}. Cada folha de capim é um dia; quanto mais contribuições, mais alta a folha.")
    # imagem espelhada 884x491, ocupa a esquerda e some antes do grafico
    ih = H
    iw = 884 * ih / 491
    t.defs.append(
        f'<linearGradient id="ceu" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG0}"/>'
        f'<stop offset="1" stop-color="{BG2}"/></linearGradient>'
        f'<linearGradient id="chao" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG1}"/>'
        f'<stop offset="1" stop-color="{BG0}"/></linearGradient>'
        f'<linearGradient id="some" gradientUnits="userSpaceOnUse" x1="{iw - 380:.0f}" y1="0" x2="{iw:.0f}" y2="0">'
        '<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<mask id="mascara"><rect width="{W}" height="{H}" fill="url(#some)"/></mask>'
        + "".join(
            f'<linearGradient id="f{i}" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{GRAMA_ESC}"/>'
            f'<stop offset="1" stop-color="{c}"/></linearGradient>' for i, c in enumerate([GRAMA_ESC, GRAMA, GRAMA_CLARA]))
        + FILTROS
    )
    t.css.append(
        CSS_BALANCA
        + ".brilha{animation:brilha 3s ease-in-out infinite}@keyframes brilha{50%{opacity:.25}}"
        ".vaga{animation:vaga 9s ease-in-out infinite}"
        "@keyframes vaga{0%,100%{transform:translate(0,0);opacity:.2}30%{opacity:1}50%{transform:translate(18px,-14px)}"
        "70%{opacity:.9}80%{transform:translate(-10px,-24px)}}"
        ".faisca{animation:faisca 3.5s ease-out infinite}"
        "@keyframes faisca{0%{transform:translateY(0);opacity:0}20%{opacity:1}100%{transform:translateY(-40px);opacity:0}}"
    )
    base(t, 22, "url(#ceu)")
    for _ in range(60):
        t.add(f'<circle class="brilha" style="animation-delay:-{rnd.uniform(0, 3):.1f}s" cx="{rnd.uniform(560, 1200):.0f}" '
              f'cy="{rnd.uniform(8, 200):.0f}" r="{rnd.uniform(.5, 1.3):.1f}" fill="{TEXTO}" opacity=".55"/>')
    t.add(f'<image href="{imagem("gon-pescando.webp")}" x="0" y="0" width="{iw:.0f}" height="{ih}" '
          f'preserveAspectRatio="xMinYMid slice" mask="url(#mascara)"/>',
          f'<rect width="{iw:.0f}" height="{ih}" fill="{BG0}" opacity=".18" mask="url(#mascara)"/>')

    x0, x1 = 640, 1160
    maximo = max(1, max(c for _, c in dias))
    n = len(dias)
    passo = (x1 - x0) / max(1, n - 1)
    folhas, altas = [], []
    for i, (d, c) in enumerate(dias):
        x = x0 + i * passo
        dobra = rnd.uniform(-3, 3)
        w = 1.1
        if c:
            k = math.sqrt(c / maximo)
            h = 20 + 100 * k
            g = 2 if k > .66 else 1 if k > .33 else 0
            if k > .66:
                altas.append((x + dobra, chao - h))
        else:
            h, g = rnd.uniform(4, 12), None
        folhas.append((f"M{x - w:.1f} {chao}Q{x - w + dobra * .3:.1f} {chao - h * .5:.1f} {x + dobra:.1f} {chao - h:.1f}"
                       f"Q{x + w + dobra * .3:.1f} {chao - h * .5:.1f} {x + w:.1f} {chao}Z", g))
    for i in range(0, n, 24):
        pedaco = folhas[i:i + 24]
        mortas = "".join(p for p, g in pedaco if g is None)
        vivas = {k: "".join(p for p, g in pedaco if g == k) for k in (0, 1, 2)}
        t.add(f'<g class="balanca" style="animation-duration:{rnd.uniform(4.5, 7.5):.1f}s;animation-delay:-{rnd.uniform(0, 5):.1f}s">',
              f'<path fill="#232a27" d="{mortas}"/>' if mortas else "",
              *[f'<path fill="url(#f{k})" d="{p}"{BRILHO if k == 2 else ""}/>' for k, p in vivas.items() if p],
              '</g>')
    for x, y in altas:
        t.add(f'<circle class="faisca" style="animation-delay:-{rnd.uniform(0, 3.5):.1f}s" cx="{x:.1f}" cy="{y - 4:.1f}" r="2" fill="{VAGALUME}"/>')
    for _ in range(9):
        t.add(f'<circle class="vaga" style="animation-delay:-{rnd.uniform(0, 9):.1f}s;animation-duration:{rnd.uniform(7, 12):.1f}s" '
              f'cx="{rnd.uniform(660, 1140):.0f}" cy="{rnd.uniform(190, 270):.0f}" r="2.2" fill="{VAGALUME}"{BRILHO}/>')

    t.add(f'<rect x="{x0 - 20}" y="{chao}" width="{W - x0 + 20}" height="{H - chao}" fill="url(#chao)"/>',
          f'<line x1="{x0 - 20}" y1="{chao}" x2="{W}" y2="{chao}" stroke="{LINHA}" stroke-width="1.5"/>')
    for i, (d, _) in enumerate(dias):
        if d.day == 1:
            x = x0 + i * passo
            t.add(f'<line x1="{x:.1f}" y1="{chao + 4}" x2="{x:.1f}" y2="{chao + 9}" stroke="{APAGADO}"/>')
            t.txt(x + 3, chao + 22, MESES[d.month - 1], 12, 400, APAGADO)
    t.txt(x1, H - 10, "cada folha é um dia", 11, 400, APAGADO, anchor="end")

    t.txt(x0, 56, "TREINO DIÁRIO", 14, 700, ACENTO, ls=4)
    num = str(total)
    t.txt(x0, 108, num, 48, 700, TEXTO)
    t.txt(x0 + largura(num, 48) + 14, 106, "contribuições no último ano", 17, 400, SUAVE)
    dia_melhor = f"{melhor[0].day:02d}/{melhor[0].month:02d}"
    t.txt(x0, 138, f"sequência atual {atual} · recorde {recorde} · melhor dia {melhor[1]} ({dia_melhor})", 14, 400, SUAVE)
    fechar(t)
    return t


# ---------------------------------------------------------------- rodape
def rodape():
    t = Tela(1200, 240, "Valeu pela visita!", "Gon fazendo sinal de paz, aparecendo pela borda de baixo.")
    t.defs.append(
        f'<radialGradient id="fundo" cx="80%" cy="100%" r="70%"><stop offset="0" stop-color="#201c17"/>'
        f'<stop offset="1" stop-color="{BG1}"/></radialGradient>' + FILTROS)
    t.css.append(".espia{animation:espia 5s ease-in-out infinite}"
                 "@keyframes espia{0%,100%{transform:translateY(8px)}50%{transform:translateY(0)}}")
    base(t, 22, "url(#fundo)")
    pontos(t)
    # 620x383, corte reto embaixo encostado na borda
    h = 226
    w = 620 * h / 383
    t.add(f'<ellipse cx="{1200 - 70 - w / 2:.0f}" cy="240" rx="260" ry="150" fill="{ACENTO}" filter="url(#nevoa)" opacity=".16"/>',
          f'<g class="espia"><image href="{imagem("gon-paz.webp")}" x="{1200 - 70 - w:.0f}" y="{240 - h + 2}" '
          f'width="{w:.0f}" height="{h}"/></g>')
    t.txt(72, 98, "VALEU PELA VISITA!", 38, 700, TEXTO, ls=2)
    t.txt(74, 136, "se curtiu algum projeto, deixa uma estrela", 18, 400, SUAVE)
    t.add(f'<text x="74" y="186" font-size="14" font-weight="700" letter-spacing="3" fill="{ACENTO}">'
          f'saisho wa guu · jan · ken<tspan fill="{APAGADO}" font-weight="400" letter-spacing="0">'
          f' — até a próxima caçada</tspan></text>')
    t.usa("saisho wa guu · jan · ken", 700)
    t.usa(" — até a próxima caçada", 400)
    fechar(t)
    return t


def carimbar_readme():
    """Poe ?v=<hash do conteudo> em cada imagem do README. O GitHub guarda imagem
    em cache por 5 min pela URL; com o hash, imagem que mudou ganha URL nova na hora."""
    readme = RAIZ / "README.md"
    texto = readme.read_text(encoding="utf-8")

    def carimbo(m):
        arq = ASSETS / f"{m.group(1)}.svg"
        if not arq.exists():
            return m.group(0)
        return f"assets/{m.group(1)}.svg?v={hashlib.sha1(arq.read_bytes()).hexdigest()[:8]}"

    novo = re.sub(r"assets/([\w-]+)\.svg(?:\?v=\w+)?", carimbo, texto)
    if novo != texto:
        readme.write_text(novo, encoding="utf-8")
        print("  README.md  carimbado")


# ----------------------------------------------------------------
def main():
    print("gerando:")
    cabecalho().salvar("cabecalho.svg")
    licenca(avatar()).salvar("licenca.svg")
    nen().salvar("nen.svg")
    titulo_secao("ARCOS", "o que eu tô construindo").salvar("secao-arcos.svg")
    arco_destaque().salvar("arco-1.svg")
    arco(2, "JARVIS", "Memória de código persistente pra agentes de IA. Sabe onde cada coisa está no projeto.",
         ["Node.js", "MCP", "tree-sitter", "SQLite"], "em uso todo dia", "memoria").salvar("arco-2.svg")
    arco(3, "ERP CONCESSIONÁRIA", "Gestão completa de concessionária: API, painel web e deploy em VPS.",
         ["FastAPI", "Next.js", "PostgreSQL", "Docker"], "Docker + Nginx em VPS", "carro").salvar("arco-3.svg")
    rodape().salvar("rodape.svg")

    dados = contribuicoes()
    if dados is None:
        print("  floresta.svg  pulada (sem GITHUB_TOKEN)")
    else:
        floresta(*dados).salvar("floresta.svg")
    carimbar_readme()


if __name__ == "__main__":
    sys.exit(main())
