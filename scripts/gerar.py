#!/usr/bin/env python3
"""Gera os SVGs do perfil.

Os cartoes fixos saem iguais toda vez (aleatoriedade com semente). So a floresta
depende de dados: le o calendario de contribuicoes pela API do GitHub, por isso
a Action roda este script todo dia. Sem GITHUB_TOKEN a floresta e pulada e o
arquivo que ja existe fica como esta.

Fonte: subconjunto da Cascadia Mono (SIL OFL, ver fontes/OFL.txt) renomeado
pra HunterMono. Cada SVG embute so os caracteres que usa.
"""
import base64
import io
import json
import math
import os
import random
import sys
import urllib.request
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "assets"
FONTES = Path(__file__).resolve().parent / "fontes"
USUARIO = os.environ.get("PERFIL", "NetoPissolato")

# Paleta: base grafite neutra; o verde do Gon entra so como acento
BG0 = "#0a0b0d"
BG1 = "#111317"
BG2 = "#181b21"
LINHA = "#272b33"
VERDE = "#3ecf8e"
VERDE_ESC = "#1d6f4b"
AURA = "#6be3a8"
MENTA = "#e7ebef"
TEXTO = "#f1f3f5"
SUAVE = "#9aa3ad"
APAGADO = "#5f6772"
OURO = "#e8b64c"
AGUA = "#8cc8ff"
VAGALUME = "#ffd66b"
CINZA = "#8b949e"  # legivel em tema claro e escuro

AVANCO = 1200 / 2048  # largura de um caractere da Cascadia Mono, em em


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def largura(texto, tam, ls=0):
    return len(texto) * (tam * AVANCO + ls)


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
        (ASSETS / nome).write_text(self.svg(), encoding="utf-8")
        print(f"  {nome}  {len(self.svg()) // 1024} KB")


FILTROS = (
    '<filter id="brilho" x="-50%" y="-50%" width="200%" height="200%">'
    '<feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/>'
    '<feMergeNode in="SourceGraphic"/></feMerge></filter>'
    '<filter id="nevoa" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="28"/></filter>'
    '<filter id="nevoa-p" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="10"/></filter>'
)


def moldura(t, rx=22):
    t.defs.append(f'<clipPath id="card"><rect width="{t.w}" height="{t.h}" rx="{rx}"/></clipPath>')


def capim(rnd, x0, x1, base, hmin, hmax, cor, passo=6, grupos=10, classe="balanca"):
    """Linha de capim com grupos que balancam em tempos diferentes."""
    folhas = []
    x = x0
    while x < x1:
        h = rnd.uniform(hmin, hmax)
        w = rnd.uniform(1.6, 2.8)
        dobra = rnd.uniform(-5, 5)
        folhas.append(
            f"M{x - w:.1f} {base}Q{x - w + dobra * .3:.1f} {base - h * .5:.1f} {x + dobra:.1f} {base - h:.1f}"
            f"Q{x + w + dobra * .3:.1f} {base - h * .5:.1f} {x + w:.1f} {base}Z"
        )
        x += rnd.uniform(passo * .6, passo * 1.4)
    tam = max(1, len(folhas) // grupos)
    saida = []
    for i in range(0, len(folhas), tam):
        dur = rnd.uniform(4.5, 7.5)
        atraso = rnd.uniform(0, 5)
        saida.append(
            f'<g class="{classe}" style="animation-duration:{dur:.1f}s;animation-delay:-{atraso:.1f}s">'
            f'<path fill="{cor}" d="{"".join(folhas[i:i + tam])}"/></g>'
        )
    return "".join(saida)


CSS_BALANCA = (
    ".balanca{transform-box:fill-box;transform-origin:50% 100%;"
    "animation:balanca 6s ease-in-out infinite alternate}"
    "@keyframes balanca{from{transform:skewX(-4deg)}to{transform:skewX(4deg)}}"
)


# ---------------------------------------------------------------- cabecalho
def cabecalho():
    rnd = random.Random(405)
    t = Tela(1200, 400, "José Pissolato — Hunter de código",
             "Cabeçalho animado: aura Nen verde em volta do crachá 405 do Exame Hunter.")
    moldura(t, 24)
    t.defs.append(
        f'<radialGradient id="fundo" cx="76%" cy="46%" r="80%"><stop offset="0" stop-color="{BG2}"/>'
        f'<stop offset=".55" stop-color="{BG1}"/><stop offset="1" stop-color="{BG0}"/></radialGradient>'
        f'<linearGradient id="anel" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{AURA}"/>'
        f'<stop offset=".5" stop-color="{VERDE}"/><stop offset="1" stop-color="{VERDE_ESC}"/></linearGradient>'
        f'<pattern id="pontos" width="28" height="28" patternUnits="userSpaceOnUse">'
        f'<circle cx="2" cy="2" r="1" fill="{LINHA}"/></pattern>'
        '<path id="arco-cima" d="M848 200a72 72 0 0 1 144 0"/>'
        '<path id="arco-baixo" d="M844 200a76 76 0 0 0 152 0"/>'
        + FILTROS
    )
    t.css.append(
        CSS_BALANCA
        + ".pulsa{transform-box:fill-box;transform-origin:center;animation:pulsa 4s ease-in-out infinite}"
        "@keyframes pulsa{0%,100%{transform:scale(.94);opacity:.16}50%{transform:scale(1.07);opacity:.3}}"
        ".lingua{transform-box:fill-box;transform-origin:center bottom;animation:lingua 2.8s ease-out infinite}"
        "@keyframes lingua{0%{transform:translateY(0) scale(1,1);opacity:0}15%{opacity:.28}"
        "100%{transform:translateY(-120px) scale(.35,1.5);opacity:0}}"
        ".sobe{animation:sobe 5s linear infinite}"
        "@keyframes sobe{0%{transform:translateY(0);opacity:0}15%{opacity:1}100%{transform:translateY(-210px);opacity:0}}"
        ".flutua{animation:flutua 6s ease-in-out infinite}"
        "@keyframes flutua{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}"
        ".gira{transform-box:view-box;transform-origin:920px 200px;animation:gira 60s linear infinite}"
        "@keyframes gira{to{transform:rotate(360deg)}}"
        ".cursor{animation:pisca 1s steps(1) infinite}"
        "@keyframes pisca{50%{opacity:0}}"
    )
    t.add('<g clip-path="url(#card)">',
          f'<rect width="1200" height="400" fill="url(#fundo)"/>',
          '<rect width="1200" height="400" fill="url(#pontos)" opacity=".5"/>')

    # aura em volta do cracha
    t.add(f'<ellipse class="pulsa" cx="920" cy="190" rx="170" ry="185" fill="{VERDE}" filter="url(#nevoa)" opacity=".5"/>',
          f'<ellipse class="pulsa" style="animation-delay:-2s" cx="920" cy="175" rx="120" ry="150" fill="{AURA}" '
          f'filter="url(#nevoa)" opacity=".35"/>')
    for i in range(6):
        x = 920 + rnd.uniform(-95, 95)
        y = 150 + rnd.uniform(-10, 60)
        t.add(f'<ellipse class="lingua" style="animation-delay:-{rnd.uniform(0, 2.8):.2f}s;animation-duration:{rnd.uniform(2.3, 3.4):.2f}s" '
              f'cx="{x:.0f}" cy="{y:.0f}" rx="{rnd.uniform(18, 34):.0f}" ry="{rnd.uniform(34, 60):.0f}" '
              f'fill="{rnd.choice([VERDE, AURA])}" filter="url(#nevoa-p)"/>')
    for i in range(16):
        x = 920 + rnd.uniform(-150, 150)
        y = rnd.uniform(300, 380)
        t.add(f'<circle class="sobe" style="animation-delay:-{rnd.uniform(0, 5):.2f}s;animation-duration:{rnd.uniform(3.8, 6.5):.2f}s" '
              f'cx="{x:.0f}" cy="{y:.0f}" r="{rnd.uniform(1.2, 3):.1f}" fill="{rnd.choice([TEXTO, SUAVE, VERDE])}"/>')

    # cracha 405
    marcas = "".join(
        f'<line x1="{920 + 104 * math.cos(a):.1f}" y1="{200 + 104 * math.sin(a):.1f}" '
        f'x2="{920 + (97 if i % 5 else 92) * math.cos(a):.1f}" y2="{200 + (97 if i % 5 else 92) * math.sin(a):.1f}"/>'
        for i in range(60) for a in [i * math.tau / 60]
    )
    t.usa("EXAME HUNTER · CANDIDATO", 700)
    t.usa("405", 700)
    t.add('<g class="flutua">',
          f'<circle cx="920" cy="200" r="114" fill="{BG0}" stroke="url(#anel)" stroke-width="3"/>',
          f'<g class="gira" stroke="{SUAVE}" stroke-width="1.4" opacity=".35">{marcas}</g>',
          f'<circle cx="920" cy="200" r="88" fill="{BG1}" stroke="{LINHA}" stroke-width="1.5"/>',
          f'<text font-size="13" font-weight="700" letter-spacing="4" fill="{VERDE}">'
          f'<textPath href="#arco-cima" startOffset="50%" text-anchor="middle">EXAME HUNTER</textPath></text>',
          f'<text font-size="13" font-weight="700" letter-spacing="4" fill="{APAGADO}">'
          f'<textPath href="#arco-baixo" startOffset="50%" text-anchor="middle">· CANDIDATO ·</textPath></text>',
          f'<text x="920" y="232" font-size="92" font-weight="700" fill="{TEXTO}" text-anchor="middle" '
          f'filter="url(#brilho)">405</text>',
          '</g>')

    # texto
    t.add(f'<text x="72" y="112" font-size="15" font-weight="700" letter-spacing="4" fill="{VERDE}">'
          f'▸ HUNTER DE CÓDIGO<tspan fill="{APAGADO}"> · BRASIL</tspan></text>')
    t.usa("▸ HUNTER DE CÓDIGO · BRASIL", 700)
    t.txt(72, 190, "JOSÉ PISSOLATO", 66, 700, TEXTO, ls=2, extra='filter="url(#brilho)"')
    t.txt(74, 234, "dev full-stack · desktop · web · bots · IA", 20, 400, SUAVE)

    # jan-ken em loop: cada pedaco aparece e fica ate o fim do ciclo
    t.add(f'<rect x="72" y="276" width="566" height="50" rx="14" fill="{BG0}" fill-opacity=".75" stroke="{LINHA}"/>')
    x0, y, tam = 96, 308, 18
    cw = tam * AVANCO
    pedacos = [("$", VERDE, 700, 0), (" saisho wa guu,", SUAVE, 400, 6), (" jan...", SUAVE, 400, 22),
               (" ken...", SUAVE, 400, 36), (" DEPLOY!", AURA, 700, 50)]
    col = 0
    cursor_pos = []
    for i, (texto, cor, peso, entra) in enumerate(pedacos):
        nome = f"jk{i}"
        t.css.append(f".{nome}{{animation:{nome} 10s steps(1) infinite}}"
                     f"@keyframes {nome}{{0%{{opacity:{1 if entra == 0 else 0}}}{max(entra, 0.01)}%{{opacity:1}}92%{{opacity:0}}}}")
        extra = f'class="{nome}"' + (' filter="url(#brilho)"' if texto.strip() == "DEPLOY!" else "")
        recuo = len(texto) - len(texto.lstrip())
        t.txt(x0 + (col + recuo) * cw, y, texto.lstrip(), tam, peso, cor, extra=extra)
        col += len(texto)
        cursor_pos.append((entra, x0 + col * cw + 3))
    quadros = "".join(f"{max(e, 0.01)}%{{transform:translateX({x - cursor_pos[0][1]:.1f}px)}}" for e, x in cursor_pos)
    t.css.append(f".anda{{animation:anda 10s steps(1) infinite}}@keyframes anda{{0%{{transform:translateX(0)}}{quadros}92%{{transform:translateX(0)}}}}")
    t.add(f'<g class="anda"><rect class="cursor" x="{cursor_pos[0][1]:.1f}" y="292" width="10" height="20" fill="{VERDE}"/></g>')

    # capim da Ilha Baleia
    t.add(capim(rnd, -10, 1210, 402, 18, 46, "#121419", passo=5, grupos=12),
          capim(rnd, -10, 1210, 402, 8, 26, "#171a20", passo=6, grupos=12))

    # cantos de mira
    for x, y, sx, sy in [(20, 20, 1, 1), (1180, 20, -1, 1), (20, 380, 1, -1), (1180, 380, -1, -1)]:
        t.add(f'<path d="M{x} {y + 18 * sy}V{y}H{x + 18 * sx}" fill="none" stroke="{SUAVE}" stroke-width="2" opacity=".4"/>')
    t.add('</g>', f'<rect x=".75" y=".75" width="1198.5" height="398.5" rx="24" fill="none" stroke="{LINHA}" stroke-width="1.5"/>')
    return t


# ---------------------------------------------------------------- licenca
def licenca():
    rnd = random.Random(1998)
    t = Tela(600, 360, "Hunter License de José Pissolato",
             "Licença Hunter: José I. Pissolato Neto, Hunter de Código, tipo de Nen Reforço, emitida em 20/05/2019.")
    moldura(t)
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
        ".pulsa{transform-box:fill-box;transform-origin:center;animation:pulsa 4s ease-in-out infinite}"
        "@keyframes pulsa{0%,100%{transform:scale(.9);opacity:.15}50%{transform:scale(1.1);opacity:.32}}"
        ".gira{transform-box:fill-box;transform-origin:center;animation:gira 24s linear infinite}"
        "@keyframes gira{to{transform:rotate(360deg)}}"
        ".vivo{animation:vivo 2s ease-in-out infinite}@keyframes vivo{50%{opacity:.35}}"
    )
    t.add('<g clip-path="url(#card)">', '<rect width="600" height="360" fill="url(#fundo)"/>')
    # guilloche
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

    # foto: silhueta com aura
    t.add(f'<rect x="40" y="96" width="136" height="172" rx="14" fill="{BG0}"/>',
          '<g clip-path="url(#foto)">',
          f'<ellipse class="pulsa" cx="108" cy="190" rx="62" ry="80" fill="{VERDE}" filter="url(#nevoa-p)" opacity=".5"/>',
          f'<circle cx="108" cy="166" r="30" fill="url(#pessoa)"/>',
          f'<path d="M48 272c4-40 28-62 60-62s56 22 60 62z" fill="url(#pessoa)"/>',
          '</g>',
          f'<rect x="40" y="96" width="136" height="172" rx="14" fill="none" stroke="{LINHA}" stroke-width="1.5"/>')

    campos = [(200, 112, "NOME", "José I. Pissolato Neto", TEXTO),
              (200, 168, "CLASSE", "Hunter de Código", TEXTO),
              (200, 224, "TIPO DE NEN", "Reforço", AURA), (380, 224, "EMITIDA EM", "20.05.2019", TEXTO),
              (200, 280, "ORIGEM", "Brasil", TEXTO)]
    for x, y, rot, val, cor in campos:
        t.txt(x, y, rot, 12, 700, SUAVE, ls=2, extra='opacity=".75"')
        t.txt(x, y + 24, val, 19, 700, cor)
    t.txt(380, 280, "ESTADO", 12, 700, SUAVE, ls=2, extra='opacity=".75"')
    t.add(f'<circle class="vivo" cx="386" cy="298" r="5" fill="{AURA}"/>')
    t.txt(398, 304, "ativa", 19, 700, TEXTO)

    # codigo de barras
    x = 40
    barras = []
    while x < 176:
        w = rnd.choice([1, 1, 2, 3])
        barras.append(f'<rect x="{x}" y="288" width="{w}" height="30" fill="{SUAVE}" opacity=".7"/>')
        x += w + rnd.choice([1, 2, 2, 3])
    t.add(*barras)
    t.txt(40, 340, "github.com/NetoPissolato", 12, 400, APAGADO)
    t.txt(560, 340, "acesso a 90% dos países", 12, 400, APAGADO, anchor="end")
    t.add('</g>', f'<rect x=".75" y=".75" width="598.5" height="358.5" rx="22" fill="none" stroke="{OURO}" stroke-opacity=".45" stroke-width="1.5"/>')
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
    moldura(t)
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

    t.add('<g clip-path="url(#card)">', '<rect width="600" height="360" fill="url(#fundo)"/>')
    t.txt(40, 50, "TESTE DA ÁGUA", 20, 700, TEXTO, ls=4)
    t.add(f'<text x="560" y="50" font-size="14" font-weight="700" text-anchor="end" fill="{SUAVE}">'
          f'resultado: <tspan fill="{AURA}">REFORÇO</tspan></text>')
    t.usa("resultado: REFORÇO", 700)

    for k in (1 / 3, 2 / 3, 1):
        t.add(f'<polygon points="{poly(R * k)}" fill="none" stroke="{LINHA}" stroke-width="{1.6 if k == 1 else 1}"/>')
    for i in range(6):
        x, y = pt(i, R)
        t.add(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{LINHA}"/>')

    valores = " ".join(f"{pt(i, R * n)[0]:.1f},{pt(i, R * n)[1]:.1f}" for i, (_, _, n) in enumerate(NEN))
    t.add('<g class="radar">',
          f'<polygon points="{valores}" fill="{VERDE}" fill-opacity=".1" filter="url(#nevoa-p)"/>',
          f'<polygon points="{valores}" fill="{VERDE}" fill-opacity=".1" stroke="{VERDE}" stroke-width="1.8" stroke-linejoin="round"/>',
          *[f'<circle cx="{pt(i, R * n)[0]:.1f}" cy="{pt(i, R * n)[1]:.1f}" r="{5 if i == 0 else 3.5}" '
            f'fill="{AURA if i == 0 else VERDE}"/>' for i, (_, _, n) in enumerate(NEN)],
          '</g>')

    # rotulos
    for i, (tipo, hab, _) in enumerate(NEN):
        x, y = pt(i, R)
        cor = AURA if i == 0 else TEXTO
        if i == 0:
            t.txt(x, y - 30, tipo, 15, 700, cor, anchor="middle", ls=1, extra='filter="url(#brilho)"')
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
          f'<g class="agua"><ellipse cx="{cx + 3}" cy="{cy - 26}" rx="8" ry="3" fill="{VERDE}" '
          f'transform="rotate(-14 {cx + 3} {cy - 26})"/></g>',
          f'<path d="M{cx - 19} {cy - 24}l4 48h30l4-48" fill="none" stroke="{TEXTO}" stroke-opacity=".6" stroke-width="2" '
          f'stroke-linejoin="round"/>',
          f'<circle class="gota" cx="{cx - 21}" cy="{cy - 22}" r="2.4" fill="{AGUA}"/>',
          f'<circle class="gota" style="animation-delay:.5s" cx="{cx + 21}" cy="{cy - 22}" r="2.4" fill="{AGUA}"/>')
    t.add('</g>', f'<rect x=".75" y=".75" width="598.5" height="358.5" rx="22" fill="none" stroke="{LINHA}" stroke-width="1.5"/>')
    return t


# ---------------------------------------------------------------- arcos
ICONES = {
    "tela": 'M-17 -13h34v22h-34zM-7 15h14M0 9v6',
    "memoria": 'M-12 -10a5 5 0 1 0 0.1 0M12 -10a5 5 0 1 0 0.1 0M0 11a5 5 0 1 0 0.1 0M-8 -7L-3 7M8 -7L3 7M-7 -10H7',
    "carro": 'M-19 6v-6l5 -9h20l7 9h6v6zM-11 6a4 4 0 1 0 0.1 0M11 6a4 4 0 1 0 0.1 0',
}


def arco(n, titulo, linhas, chips, estado, icone, link=None):
    rnd = random.Random(n)
    t = Tela(400, 250, f"Arco {n:02d}: {titulo}", " ".join(linhas))
    moldura(t, 20)
    t.defs.append(
        f'<linearGradient id="fundo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG2}"/>'
        f'<stop offset="1" stop-color="{BG0}"/></linearGradient>'
        f'<linearGradient id="borda" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{AURA}"/>'
        f'<stop offset="1" stop-color="{VERDE}"/></linearGradient>'
        + FILTROS
    )
    dur = 7 + n
    t.css.append(
        f".corre{{animation:corre {dur}s linear infinite}}@keyframes corre{{to{{stroke-dashoffset:-100}}}}"
        ".vivo{animation:vivo 2s ease-in-out infinite}@keyframes vivo{50%{opacity:.3}}"
    )
    t.add('<g clip-path="url(#card)">', '<rect width="400" height="250" fill="url(#fundo)"/>')
    t.txt(378, 92, f"{n:02d}", 96, 700, TEXTO, anchor="end", extra='opacity=".05"')
    t.add(f'<rect x="28" y="28" width="52" height="52" rx="14" fill="{BG0}" stroke="{LINHA}"/>',
          f'<path transform="translate(54 54)" d="{ICONES[icone]}" fill="none" stroke="{VERDE}" stroke-width="2.2" '
          f'stroke-linecap="round" stroke-linejoin="round"/>')
    if icone == "tela":
        t.add(f'<path transform="translate(54 54)" d="M22 -9a9 9 0 0 1 0 12M26 -13a15 15 0 0 1 0 20" fill="none" '
              f'stroke="{VERDE}" stroke-width="2" stroke-linecap="round" class="vivo"/>')
    t.txt(96, 48, f"ARCO {n:02d}", 12, 700, VERDE, ls=3)
    t.txt(96, 76, titulo, 22, 700, TEXTO)
    for i, linha in enumerate(linhas):
        t.txt(28, 120 + i * 22, linha, 15, 400, SUAVE)
    x, y = 28, 162
    for c in chips:
        w = largura(c, 12) + 22
        if x + w > 372:
            x, y = 28, y + 32
        t.add(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="24" rx="12" fill="{BG0}" stroke="{LINHA}"/>')
        t.txt(x + 11, y + 16, c, 12, 400, MENTA)
        x += w + 8
    t.add(f'<circle class="vivo" cx="33" cy="222" r="4.5" fill="{AURA}"/>')
    t.txt(46, 227, estado, 13, 400, SUAVE)
    if link:
        t.txt(372, 227, link, 13, 700, VERDE, anchor="end")
    t.add('</g>',
          f'<rect x=".75" y=".75" width="398.5" height="248.5" rx="20" fill="none" stroke="{LINHA}" stroke-width="1.5"/>',
          f'<rect class="corre" x=".75" y=".75" width="398.5" height="248.5" rx="20" fill="none" stroke="url(#borda)" '
          f'stroke-width="1.5" pathLength="100" stroke-dasharray="10 90" stroke-linecap="round" opacity=".8"/>')
    return t


def titulo_secao(texto, sub):
    t = Tela(1200, 64, texto, sub)
    t.defs.append(f'<linearGradient id="some" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CINZA}" stop-opacity=".5"/>'
                  f'<stop offset="1" stop-color="{CINZA}" stop-opacity="0"/></linearGradient>')
    t.add(f'<rect x="2" y="18" width="5" height="26" rx="2.5" fill="{VERDE}"/>')
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
    t = Tela(1200, 320, "Treino diário: contribuições do último ano",
             f"{total} contribuições no último ano. Sequência atual de {atual} dias, recorde de {recorde}. "
             "Cada folha de capim é um dia; quanto mais contribuições, mais alta a folha.")
    moldura(t)
    base = 262
    t.defs.append(
        f'<linearGradient id="ceu" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG0}"/>'
        f'<stop offset="1" stop-color="{BG2}"/></linearGradient>'
        f'<linearGradient id="chao" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG1}"/>'
        f'<stop offset="1" stop-color="{BG0}"/></linearGradient>'
        + "".join(
            f'<linearGradient id="f{i}" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{VERDE_ESC}"/>'
            f'<stop offset="1" stop-color="{c}"/></linearGradient>' for i, c in enumerate([VERDE_ESC, VERDE, AURA]))
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
    t.add('<g clip-path="url(#card)">', '<rect width="1200" height="320" fill="url(#ceu)"/>')
    for _ in range(80):
        t.add(f'<circle class="brilha" style="animation-delay:-{rnd.uniform(0, 3):.1f}s" cx="{rnd.uniform(0, 1200):.0f}" '
              f'cy="{rnd.uniform(8, 200):.0f}" r="{rnd.uniform(.5, 1.4):.1f}" fill="{TEXTO}" opacity=".6"/>')
    t.add(f'<circle cx="1096" cy="74" r="60" fill="#fff1cc" filter="url(#nevoa)" opacity=".18"/>',
          '<circle cx="1096" cy="74" r="26" fill="#f4efe2"/>',
          '<circle cx="1087" cy="67" r="5" fill="#d8d0bd" opacity=".6"/><circle cx="1104" cy="84" r="3.5" fill="#d8d0bd" opacity=".6"/>')

    maximo = max(1, max(c for _, c in dias))
    n = len(dias)
    x0, x1 = 40, 1160
    passo = (x1 - x0) / max(1, n - 1)
    folhas, altas = [], []
    for i, (d, c) in enumerate(dias):
        x = x0 + i * passo
        dobra = rnd.uniform(-4, 4)
        w = 1.5
        if c:
            k = math.sqrt(c / maximo)
            h = 22 + 90 * k
            g = 2 if k > .66 else 1 if k > .33 else 0
            if k > .66:
                altas.append((x + dobra, base - h))
        else:
            h, g = rnd.uniform(5, 14), None
        path = (f"M{x - w:.1f} {base}Q{x - w + dobra * .3:.1f} {base - h * .5:.1f} {x + dobra:.1f} {base - h:.1f}"
                f"Q{x + w + dobra * .3:.1f} {base - h * .5:.1f} {x + w:.1f} {base}Z")
        folhas.append((path, g))
    grupo = 24
    for i in range(0, n, grupo):
        pedaco = folhas[i:i + grupo]
        mortas = "".join(p for p, g in pedaco if g is None)
        vivas = {k: "".join(p for p, g in pedaco if g == k) for k in (0, 1, 2)}
        t.add(f'<g class="balanca" style="animation-duration:{rnd.uniform(4.5, 7.5):.1f}s;animation-delay:-{rnd.uniform(0, 5):.1f}s">',
              f'<path fill="#232a27" d="{mortas}"/>' if mortas else "",
              *[f'<path fill="url(#f{k})" d="{p}"{BRILHO if k == 2 else ""}/>' for k, p in vivas.items() if p],
              '</g>')
    for x, y in altas:
        t.add(f'<circle class="faisca" style="animation-delay:-{rnd.uniform(0, 3.5):.1f}s" cx="{x:.1f}" cy="{y - 4:.1f}" r="2" fill="{VAGALUME}"/>')
    for _ in range(12):
        t.add(f'<circle class="vaga" style="animation-delay:-{rnd.uniform(0, 9):.1f}s;animation-duration:{rnd.uniform(7, 12):.1f}s" '
              f'cx="{rnd.uniform(60, 1140):.0f}" cy="{rnd.uniform(150, 245):.0f}" r="2.2" fill="{VAGALUME}" filter="url(#brilho)"/>')

    t.add(f'<rect x="0" y="{base}" width="1200" height="{320 - base}" fill="url(#chao)"/>',
          f'<line x1="0" y1="{base}" x2="1200" y2="{base}" stroke="{LINHA}" stroke-width="1.5"/>')
    for i, (d, _) in enumerate(dias):
        if d.day == 1:
            x = x0 + i * passo
            t.add(f'<line x1="{x:.1f}" y1="{base + 4}" x2="{x:.1f}" y2="{base + 10}" stroke="{APAGADO}"/>')
            t.txt(x + 4, base + 24, MESES[d.month - 1], 12, 400, APAGADO)
    t.txt(1160, 306, "cada folha é um dia · a altura é o quanto treinei", 12, 400, APAGADO, anchor="end")

    t.txt(40, 50, "TREINO DIÁRIO", 14, 700, SUAVE, ls=4)
    num = str(total)
    t.txt(40, 102, num, 48, 700, TEXTO, extra='filter="url(#brilho)"')
    t.txt(40 + largura(num, 48) + 14, 100, "contribuições no último ano", 17, 400, SUAVE)
    dia_melhor = f"{melhor[0].day:02d}/{melhor[0].month:02d}"
    t.txt(40, 132, f"sequência atual {atual} · recorde {recorde} · melhor dia {melhor[1]} ({dia_melhor})", 14, 400, SUAVE)
    t.add('</g>', f'<rect x=".75" y=".75" width="1198.5" height="318.5" rx="22" fill="none" stroke="{LINHA}" stroke-width="1.5"/>')
    return t


# ----------------------------------------------------------------
def main():
    print("gerando:")
    cabecalho().salvar("cabecalho.svg")
    licenca().salvar("licenca.svg")
    nen().salvar("nen.svg")
    titulo_secao("ARCOS", "o que eu tô construindo").salvar("secao-arcos.svg")
    arco(1, "SPACERCORD", ["Compartilhe a tela escolhendo quais", "programas levam áudio junto."],
         ["Electron", "C++ nativo", "WebRTC", "LiveKit"], "v0.21.1 lançada", "tela", "releases →").salvar("arco-1.svg")
    arco(2, "JARVIS", ["Memória de código persistente pra", "agentes de IA. Sabe onde tudo está."],
         ["Node.js", "MCP", "tree-sitter", "SQLite"], "em uso todo dia", "memoria").salvar("arco-2.svg")
    arco(3, "ERP CONCESSIONÁRIA", ["Gestão completa de concessionária:", "API, painel web e deploy em VPS."],
         ["FastAPI", "Next.js", "PostgreSQL", "Docker"], "Docker + Nginx em VPS", "carro").salvar("arco-3.svg")

    dados = contribuicoes()
    if dados is None:
        print("  floresta.svg  pulada (sem GITHUB_TOKEN)")
    else:
        floresta(*dados).salvar("floresta.svg")


if __name__ == "__main__":
    sys.exit(main())
