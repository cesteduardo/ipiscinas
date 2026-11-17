#!/usr/bin/env python3
"""iPiscinas · gerador do site estático.

Baixa os dados reais da API pública do iPiscinas (lojas, piscinas, blog) e
monta as páginas em HTML puro na raiz do projeto.

    python3 _fonte/build.py            # usa o cache de _fonte/cache quando existe
    python3 _fonte/build.py --fresco   # baixa tudo de novo da API

CSS e JS ficam em assets/ e são editados direto.
"""
import concurrent.futures as cf
import html
import json
import re
import shutil
import sys
import unicodedata
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "_fonte" / "cache"
API = "https://api.ipiscinas.com.br/api"
SITE = "https://www.ipiscinas.com.br"          # domínio final (canonical, sitemap, OG)
APP = "https://www.ipiscinas.com.br"            # onde moram login, cadastro e conta (app atual)
ZAP_IPISCINAS = "5517996123456"                 # número que está no site atual (ver seo/pendencias.md)
ZAP_TEXTO = "Olá, estou navegando pelo iPiscinas e gostaria de tirar uma dúvida."
FRESCO = "--fresco" in sys.argv
# prévia no GitHub Pages: python3 _fonte/build.py --base=/ipiscinas  (caminhos na subpasta + noindex)
BASE = next((a.split("=", 1)[1].rstrip("/") for a in sys.argv if a.startswith("--base=")), "")
PREVIA = bool(BASE)
HOJE = date.today().isoformat()
VERSAO = datetime.now().strftime("%Y%m%d%H%M")

CATS = [
    ("piscinas", "Piscinas", ["VENDA_PISCINA"], "waves"),
    ("piscineiro", "Piscineiro e limpeza", ["PISCINEIRO", "LIMPEZA"], "sparkles"),
    ("manutencao", "Manutenção", ["MANUTENCAO"], "wrench"),
    ("quimicos", "Produtos químicos", ["VENDA_PRODUTOS_LIMPEZA"], "flask"),
    ("acessorios", "Acessórios", ["VENDA_ACESSORIOS"], "buoy"),
]
FORMATO = {"RETANGULAR": "Retangular", "OVAL": "Oval", "LIVRE": "Formato livre", "REDONDA": "Redonda"}
TIPO = {"FIBRA": "Fibra", "ALVENARIA": "Alvenaria", "VINIL": "Vinil", "CONCRETO": "Concreto"}

# ------------------------------------------------------------------ dados

def baixar(caminho, arquivo):
    alvo = CACHE / arquivo
    if alvo.exists() and not FRESCO:
        return json.loads(alvo.read_text())
    req = urllib.request.Request(API + caminho, headers={"User-Agent": "Mozilla/5.0 (site estático iPiscinas)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        dado = json.loads(r.read().decode())
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(json.dumps(dado, ensure_ascii=False))
    return dado


def carregar():
    lojas = [l for l in baixar("/lojas", "lojas.json") if l.get("status", "ATIVA") == "ATIVA"]
    destaque = baixar("/piscinas?destaque=true", "destaque.json")
    posts = baixar("/blog/posts?page=1&perPage=50", "posts.json")["items"]
    categorias_blog = baixar("/blog/categorias", "blog-categorias.json")

    def det_loja(l):
        try:
            return baixar(f"/lojas/slug/{urllib.parse.quote(l['slug'])}", f"lojas/{l['slug']}.json")
        except Exception as e:  # loja que some da API no meio do caminho
            print("  ! loja", l["slug"], e)
            return None

    def det_post(p):
        return baixar(f"/blog/posts/{urllib.parse.quote(p['slug'])}", f"posts/{p['slug']}.json")

    with cf.ThreadPoolExecutor(12) as ex:
        detalhes = list(ex.map(det_loja, lojas))
        posts_full = list(ex.map(det_post, posts))

    por_id = {}
    for base, det in zip(lojas, detalhes):
        loja = dict(base)
        if det:
            for k in ("piscinas", "servicos", "produtos", "trabalhos", "descricao", "capaUrl", "logoUrl"):
                if det.get(k) is not None:
                    loja[k] = det[k]
        for k in ("piscinas", "servicos", "produtos", "trabalhos"):
            loja[k] = [x for x in (loja.get(k) or []) if x.get("ativa", x.get("ativo", True))]
        por_id[loja["id"]] = loja

    piscinas = {}
    for loja in por_id.values():
        for p in loja["piscinas"]:
            p = dict(p)
            p["loja"] = loja
            p["fotos"] = sorted(p.get("fotos") or [], key=lambda f: f.get("ordem", 0))
            piscinas[p["id"]] = p
    for p in destaque:  # piscina em destaque de loja que não veio no detalhe
        if p["id"] not in piscinas and p.get("lojaId") in por_id:
            p = dict(p)
            p["loja"] = por_id[p["lojaId"]]
            piscinas[p["id"]] = p
    destaque_ids = [p["id"] for p in destaque if p["id"] in piscinas]
    return list(por_id.values()), piscinas, destaque_ids, posts_full, categorias_blog


# ------------------------------------------------------------------ utilidades

def e(t):
    return html.escape(str(t if t is not None else ""), quote=True)


def limpa(t):
    return re.sub(r"\s+", " ", str(t or "")).strip()


def sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t or "").lower()) if unicodedata.category(c) != "Mn")


def preco(v):
    if v in (None, "", 0, "0"):
        return ""
    try:
        n = float(v)
    except ValueError:
        return ""
    if n.is_integer():
        return "R$ " + f"{int(n):,}".replace(",", ".")
    s = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + s


def medida(v, un="m"):
    if v in (None, "", 0):
        return ""
    s = f"{float(v):g}".replace(".", ",")
    return f"{s} {un}"


def litros(v):
    if not v:
        return ""
    return f"{int(float(v)):,}".replace(",", ".") + " L"


def img(url, w):
    """Foto do Supabase pelo serviço de redimensionamento deles (só reduz)."""
    if not url:
        return ""
    m = re.match(r"(https://[^/]+\.supabase\.co)/storage/v1/object/public/(.+)$", url)
    if m:
        return f"{m.group(1)}/storage/v1/render/image/public/{m.group(2)}?width={w}&quality=72"
    if "images.unsplash.com" in url:
        return url + ("&" if "?" in url else "?") + f"w={w}&q=70&auto=format"
    return url


def srcset(url, *ws):
    return ", ".join(f"{e(img(url, w))} {w}w" for w in ws)


def digitos(t):
    return re.sub(r"\D", "", str(t or ""))


def zap_de(numero):
    d = digitos(numero)
    if d.startswith("55") and len(d) in (12, 13):
        d = d[2:]
    if len(d) in (10, 11):
        return "55" + d
    return ""


def tel_fmt(numero):
    d = digitos(numero)
    if d.startswith("55") and len(d) in (12, 13):
        d = d[2:]
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return numero or ""


def wa(numero, texto):
    return f"https://wa.me/{numero}?text={urllib.parse.quote(texto)}"


def cidade_de(l):
    end = l.get("endereco") or {}
    c = l.get("cidadeNome") or end.get("cidade")
    uf = l.get("cidadeUf") or end.get("estado")
    if c and uf:
        return f"{c}, {uf}"
    return c or uf or ""


def geo_de(l):
    end = l.get("endereco") or {}
    lat, lng = end.get("latitude"), end.get("longitude")
    if lat and lng and abs(lat) > 0.5 and abs(lng) > 0.5 and -35 < lat < 6 and -75 < lng < -30:
        return round(lat, 5), round(lng, 5)
    return None


def cats_de(l):
    s = set(l.get("categorias") or [])
    if l.get("piscinas"):
        s.add("VENDA_PISCINA")
    return [k for k, _, chaves, _ in CATS if s & set(chaves)]


def iniciais(nome):
    p = [x for x in re.split(r"\s+", limpa(nome)) if x]
    if not p:
        return "iP"
    return (p[0][0] + (p[1][0] if len(p) > 1 else p[0][1:2])).upper()


def data_br(iso):
    meses = "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split()
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return f"{d.day} de {meses[d.month - 1]} de {d.year}"


def resumo(t, n=155):
    t = limpa(t)
    if len(t) <= n:
        return t
    return t[: n - 1].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def plural(n, um, varios):
    return f"{n} {um if n == 1 else varios}"


# ------------------------------------------------------------------ ícones (traço, 24×24)

ICONES = {
    "waves": '<path d="M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>',
    "sparkles": '<path d="M9.94 15.5A2 2 0 0 0 8.5 14.06l-6.14-1.58a.5.5 0 0 1 0-.96L8.5 9.94A2 2 0 0 0 9.94 8.5l1.58-6.14a.5.5 0 0 1 .96 0L14.06 8.5a2 2 0 0 0 1.44 1.44l6.14 1.58a.5.5 0 0 1 0 .96L15.5 14.06a2 2 0 0 0-1.44 1.44l-1.58 6.14a.5.5 0 0 1-.96 0z"/>',
    "wrench": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    "flask": '<path d="M10 2v7.53a2 2 0 0 1-.21.9L4.72 20.55a1 1 0 0 0 .9 1.45h12.76a1 1 0 0 0 .9-1.45l-5.07-10.13A2 2 0 0 1 14 9.53V2"/><path d="M8.5 2h7"/><path d="M7 16h10"/>',
    "buoy": '<circle cx="12" cy="12" r="10"/><path d="m4.93 4.93 4.24 4.24"/><path d="m14.83 9.17 4.24-4.24"/><path d="m14.83 14.83 4.24 4.24"/><path d="m9.17 14.83-4.24 4.24"/><circle cx="12" cy="12" r="4"/>',
    "search": '<circle cx="11" cy="11" r="7.5"/><path d="m20.5 20.5-4.2-4.2"/>',
    "map": '<path d="M14.1 5.55a2 2 0 0 0 1.8 0l3.66-1.83A1 1 0 0 1 21 4.62v12.76a1 1 0 0 1-.55.9l-4.56 2.27a2 2 0 0 1-1.78 0l-4.22-2.1a2 2 0 0 0-1.78 0l-3.66 1.83A1 1 0 0 1 3 19.38V6.62a1 1 0 0 1 .55-.9l4.56-2.27a2 2 0 0 1 1.78 0z"/><path d="M15 5.76v15"/><path d="M9 3.24v15"/>',
    "pin": '<path d="M20 10c0 5-5.54 10.19-7.4 11.8a1 1 0 0 1-1.2 0C9.54 20.19 4 15 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
    "seta": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "volta": '<path d="M19 12H5"/><path d="m12 19-7-7 7-7"/>',
    "dir": '<path d="m9 18 6-6-6-6"/>',
    "esq": '<path d="m15 18-6-6 6-6"/>',
    "fone": '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.9.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/>',
    "alvo": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3"/><path d="M12 19v3"/><path d="M2 12h3"/><path d="M19 12h3"/><circle cx="12" cy="12" r="7"/>',
    "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "casa": '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "jornal": '<path d="M15 18h-5"/><path d="M18 14h-8"/><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-4 0v-9a2 2 0 0 1 2-2h2"/><rect width="8" height="4" x="10" y="6" rx="1"/>',
    "regua": '<path d="M21.3 15.3a2.4 2.4 0 0 1 0 3.4l-2.6 2.6a2.4 2.4 0 0 1-3.4 0L2.7 8.7a2.41 2.41 0 0 1 0-3.4l2.6-2.6a2.41 2.41 0 0 1 3.4 0Z"/><path d="m14.5 12.5 2-2"/><path d="m11.5 9.5 2-2"/><path d="m8.5 6.5 2-2"/><path d="m17.5 15.5 2-2"/>',
    "relogio": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "estrela": '<path d="M12 2.5l2.94 5.96 6.56.95-4.75 4.63 1.12 6.54L12 17.5l-5.87 3.08 1.12-6.54L2.5 9.41l6.56-.95z"/>',
    "app": '<rect x="6" y="2" width="12" height="20" rx="3"/><path d="M11 18h2"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "olho": '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
}
ZAP_SVG = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><path fill="currentColor" d="M17.47 14.38c-.3-.15-1.76-.87-2.03-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.94 1.17-.17.2-.35.22-.64.07-.3-.15-1.26-.46-2.4-1.48-.88-.79-1.48-1.76-1.65-2.06-.17-.3-.02-.46.13-.6.13-.14.3-.35.45-.52.15-.18.2-.3.3-.5.1-.2.05-.37-.03-.52-.07-.15-.67-1.6-.92-2.2-.24-.58-.49-.5-.67-.5h-.57c-.2 0-.52.07-.8.37-.27.3-1.04 1.02-1.04 2.48 0 1.47 1.07 2.88 1.21 3.08.15.2 2.1 3.2 5.08 4.49.71.3 1.27.49 1.7.63.72.23 1.37.2 1.88.12.58-.09 1.76-.72 2-1.41.25-.7.25-1.29.18-1.41-.08-.13-.27-.2-.57-.35M12.05 21.79h-.01a9.87 9.87 0 0 1-5.03-1.38l-.36-.21-3.74.98 1-3.65-.24-.37a9.86 9.86 0 0 1-1.51-5.26c0-5.45 4.44-9.88 9.89-9.88 2.64 0 5.12 1.03 6.99 2.9a9.82 9.82 0 0 1 2.89 6.99c0 5.45-4.44 9.88-9.88 9.88m8.41-18.3A11.82 11.82 0 0 0 12.05 0C5.5 0 .16 5.34.16 11.89c0 2.1.55 4.14 1.59 5.95L.06 24l6.3-1.65a11.88 11.88 0 0 0 5.68 1.45h.01c6.55 0 11.89-5.34 11.89-11.9a11.82 11.82 0 0 0-3.48-8.41"/></svg>'


def ico(nome, tam=20, cls=""):
    c = f' class="{cls}"' if cls else ""
    return (f'<svg{c} viewBox="0 0 24 24" width="{tam}" height="{tam}" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{ICONES[nome]}</svg>')


LOGO = '<img class="logo" src="/assets/img/logo.png" alt="iPiscinas" width="159" height="40">'
LOGO_TOPO = ('<img class="logo logo--cor" src="/assets/img/logo.png" alt="iPiscinas" width="159" height="40">'
             '<img class="logo logo--branco" src="/assets/img/logo-branco.png" alt="" aria-hidden="true" width="159" height="40">')
RAIA_BOIAS = '<div class="boias" aria-hidden="true"><span></span></div>'
CREDITO = '<a class="credito" href="https://grbrands.com.br" target="_blank" rel="noopener">Desenvolvido por <b><svg class="gr-ico" viewBox="22.5 22 84 84" aria-hidden="true" focusable="false" style="display:inline-block;width:1.5em;height:1.5em;vertical-align:-.45em;margin-right:.4em;flex:none"><clipPath id="gr-ct"><rect x="-60" y="-60" width="220" height="107"/></clipPath><clipPath id="gr-cb"><rect x="-60" y="53" width="220" height="160"/></clipPath><g transform="translate(25.3 24) scale(1.00125) translate(-16 -8.2)"><g fill="currentColor" transform="rotate(-22 50 50)"><g clip-path="url(#gr-ct)"><circle cx="60" cy="50" r="38"/></g><g clip-path="url(#gr-cb)"><circle cx="50" cy="50" r="38"/></g></g></g></svg>GR Brands<i>.</i></b></a>'


# ------------------------------------------------------------------ moldura

NAV = [("/", "Início"), ("/buscar/", "Buscar"), ("/mapa/", "Mapa"), ("/blog/", "Blog")]


def cabeca(titulo, desc, caminho, og=None, ld=None, indexar=True, extra=""):
    url = SITE + caminho
    og = og or SITE + "/assets/img/og.jpg"
    robots = "index, follow, max-image-preview:large" if indexar and not PREVIA else "noindex, nofollow"
    lds = ""
    if ld:
        lds = f'<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@graph": ld}, ensure_ascii=False)}</script>'
    return f"""<!doctype html>
<html lang="pt-BR" data-base="{BASE}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(titulo)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta name="robots" content="{robots}">
<meta name="theme-color" content="#0EA5E9">
<link rel="icon" href="/assets/img/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/img/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="iPiscinas">
<meta property="og:title" content="{e(titulo)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(og)}">
<meta property="og:image:alt" content="{e(titulo)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(titulo)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{e(og)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://nwphnhntrdaiidsfymdk.supabase.co" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400..700&display=swap">
<link rel="stylesheet" href="/assets/css/site.css?v={VERSAO}">
{extra}{lds}
</head>
"""


TABS = [("/", "Início", "casa", "brilho"), ("/buscar/", "Buscar", "search", "procura"), ("/mapa/", "Mapa", "map", "cai"),
        ("/blog/", "Blog", "jornal", "folha"), ("/conta/", "Conta", "user", "aceno")]


def topo(atual):
    links = "".join(
        f'<a href="{h}"{" aria-current=page" if h == atual else ""}>{t}</a>' for h, t in NAV
    )
    # barra de vidro líquido do celular: a gota escorre até a aba tocada
    abas = "".join(
        f'<a class="abas__item" href="{h}" data-fx="{fx}"{" aria-current=page" if h == atual else ""}>'
        f'<span class="abas__ico">{ico(i, 22)}</span><span class="abas__txt">{t}</span></a>'
        for h, t, i, fx in TABS
    )
    return f"""<body>
<a class="pular" href="#conteudo">Pular para o conteúdo</a>
<header class="topo">
  <div class="topo__in">
    <a class="topo__marca" href="/" aria-label="iPiscinas, página inicial">{LOGO_TOPO}</a>
    <nav class="nav liquido" aria-label="Principal"><span class="liquido__gota" aria-hidden="true"></span>{links}</nav>
    <div class="topo__acoes" data-sessao-fora>
      <a class="btn btn--claro btn--p" href="/entrar/">Entrar</a>
      <a class="btn btn--p" href="/criar-conta/">Criar conta</a>
    </div>
    <a class="topo__eu btn btn--claro btn--p" href="/conta/" data-sessao-dentro hidden>{ico("user", 16)}<span data-sessao-nome>Minha conta</span></a>
  </div>
</header>
<nav class="abas liquido" aria-label="Atalhos"><span class="liquido__gota" aria-hidden="true"></span>{abas}</nav>
"""


def rodape():
    nav = "".join(f'<li><a href="{h}">{t}</a></li>' for h, t in NAV + [("/conta/", "Conta")])
    cats = "".join(f'<li><a href="/buscar/?cat={k}">{t}</a></li>' for k, t, _, _ in CATS)
    return f"""<div class="rodape__boias">{RAIA_BOIAS}</div>
<footer class="rodape" data-agua>
  <div class="rodape__in">
    <div class="rodape__col rodape__marca">
      {LOGO}
      <p>A mesma experiência do app iPiscinas, agora também no navegador. Descubra lojas, modelos de piscinas e solicite orçamentos.</p>
    </div>
    <div class="rodape__col"><h2>Navegue</h2><ul>{nav}</ul></div>
    <div class="rodape__col"><h2>Categorias</h2><ul>{cats}</ul></div>
    <div class="rodape__col"><h2>Fale com a gente</h2>
      <a class="rodape__zap" href="{e(wa(ZAP_IPISCINAS, ZAP_TEXTO))}" target="_blank" rel="noopener">{ZAP_SVG}<span>WhatsApp do iPiscinas<small>{tel_fmt(ZAP_IPISCINAS)}</small></span></a>
    </div>
  </div>
  <div class="rodape__base">
    <p>© <span data-ano>{date.today().year}</span> iPiscinas. Todos os direitos reservados.</p>
    {CREDITO}
  </div>
</footer>
<a class="zap-flut" href="{e(wa(ZAP_IPISCINAS, ZAP_TEXTO))}" target="_blank" rel="noopener" aria-label="Falar com o iPiscinas no WhatsApp">{ZAP_SVG}</a>
<script src="/assets/js/site.js?v={VERSAO}" defer></script>
<script src="/assets/js/agua.js?v={VERSAO}" defer></script>
"""


def fim(scripts=""):
    return f"{scripts}</body>\n</html>\n"


def migalhas(itens):
    li = []
    for i, (t, h) in enumerate(itens):
        if h and i < len(itens) - 1:
            li.append(f'<li><a href="{h}">{e(t)}</a></li>')
        else:
            li.append(f'<li aria-current="page">{e(t)}</li>')
    return f'<nav class="migalhas" aria-label="Você está em"><ol>{"".join(li)}</ol></nav>'


def heroi(titulo, em="", mig=None, sub="", extra="", cls=""):
    """Topo das páginas internas: o mesmo degradê azul do início, texto branco."""
    return f"""<section class="heroi heroi--int {cls}">
  <div class="wrap">
    {migalhas(mig) if mig else ''}
    <h1>{titulo}{f'<em>{em}</em>' if em else ''}</h1>
    {f'<p class="heroi__sub">{sub}</p>' if sub else ''}
    {extra}
  </div>
</section>"""


def ld_migalhas(itens):
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": t, "item": SITE + h}
            for i, (t, h) in enumerate(itens, 1)
        ],
    }


LD_ORG = {"@type": "Organization", "@id": SITE + "/#org", "name": "iPiscinas", "url": SITE + "/",
          "logo": SITE + "/assets/img/logo.png"}
LD_SITE = {"@type": "WebSite", "@id": SITE + "/#site", "name": "iPiscinas", "url": SITE + "/", "inLanguage": "pt-BR",
           "publisher": {"@id": SITE + "/#org"},
           "potentialAction": {"@type": "SearchAction", "target": SITE + "/buscar/?q={q}", "query-input": "required name=q"}}


def com_base(h):
    if not BASE:
        return h
    return re.sub(r'((?:href|src|action|content)=")/(?!/)', lambda m: m.group(1) + BASE + "/", h)


def escrever(caminho, conteudo):
    conteudo = com_base(conteudo)
    alvo = RAIZ / caminho.lstrip("/")
    if caminho.endswith("/"):
        alvo = alvo / "index.html"
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(conteudo)


# ------------------------------------------------------------------ peças

def logo_loja(l, tam=56, cls="selo"):
    if l.get("logoUrl"):
        return (f'<span class="{cls}"><img src="{e(img(l["logoUrl"], tam * 2))}" alt="" width="{tam}" height="{tam}" '
                f'loading="lazy" decoding="async"></span>')
    return f'<span class="{cls} {cls}--letras" aria-hidden="true">{e(iniciais(l["nome"]))}</span>'


def cartao_piscina(p, prioridade=False):
    l = p["loja"]
    foto = p["fotos"][0]["url"] if p.get("fotos") else ""
    pr = preco(p.get("precoBase"))
    carregar = 'fetchpriority="high"' if prioridade else 'loading="lazy" decoding="async"'
    tipo = TIPO.get(p.get("tipo"), "")
    midia = (f'<img src="{e(img(foto, 640))}" srcset="{srcset(foto, 400, 640)}" sizes="(max-width: 600px) 78vw, 300px" '
             f'alt="Piscina {e(limpa(p["nome"]))}, de {e(limpa(l["nome"]))}" width="400" height="500" {carregar}>'
             if foto else f'<span class="cp__vazio">{ico("waves", 40)}</span>')
    return f"""<a class="cp" href="/piscina/{e(p['id'])}/">
  <span class="cp__foto">{midia}{f'<span class="tag">{tipo}</span>' if tipo else ''}</span>
  <span class="cp__txt">
    <span class="cp__loja">{e(limpa(l['nome']))}</span>
    <strong class="cp__nome">{e(limpa(p['nome']))}</strong>
    <span class="cp__preco">{e(pr) if pr else 'Preço sob consulta'}</span>
  </span>
</a>"""


def contagens(l):
    partes = []
    if l.get("piscinas"):
        partes.append(plural(len(l["piscinas"]), "modelo", "modelos"))
    if l.get("servicos"):
        partes.append(plural(len(l["servicos"]), "serviço", "serviços"))
    if l.get("produtos"):
        partes.append(plural(len(l["produtos"]), "produto", "produtos"))
    return partes


def cartao_loja(l, extra=""):
    cid = cidade_de(l)
    cont = contagens(l)
    linha = " · ".join(x for x in [cid, extra] if x)
    return f"""<a class="cl" href="/loja/{e(l['slug'])}/">
  {logo_loja(l)}
  <span class="cl__txt">
    <strong>{e(limpa(l['nome']))}</strong>
    {f'<span class="cl__cid">{ico("pin", 14)}{e(linha)}</span>' if linha else ''}
    {f'<span class="cl__cont">{" · ".join(cont)}</span>' if cont else ''}
  </span>
  <span class="seta-bola" aria-hidden="true">{ico("seta", 16)}</span>
</a>"""


def carrossel(itens, rotulo, cls=""):
    return f"""<div class="carrossel {cls}" data-carrossel>
  <div class="carrossel__trilho" role="list" aria-label="{e(rotulo)}" tabindex="0">{"".join(f'<div role="listitem">{i}</div>' for i in itens)}</div>
  <div class="carrossel__setas">
    <button class="seta" type="button" aria-label="Anterior" data-ant>{ico("esq", 20)}</button>
    <button class="seta" type="button" aria-label="Próximo" data-prox>{ico("dir", 20)}</button>
  </div>
</div>"""


def form_orcamento(l, modelo=None):
    numero = zap_de(l.get("whatsapp")) or zap_de(l.get("telefone"))
    if not numero:
        return f"""<aside class="orc" id="orcamento">
  <h2>Solicite seu orçamento</h2>
  <p class="orc__sub">Esta loja ainda não informou um WhatsApp. Fale com o iPiscinas que a gente ajuda a encontrar o contato.</p>
  <a class="btn btn--zap btn--cheio" href="{e(wa(ZAP_IPISCINAS, f'Olá, vi a loja {limpa(l["nome"])} no iPiscinas e quero um orçamento.'))}" target="_blank" rel="noopener">{ZAP_SVG}Falar com o iPiscinas</a>
</aside>"""
    sufixo = re.sub(r"\W+", "-", sem_acento(modelo or "loja"))[:24]
    return f"""<aside class="orc" id="orcamento">
  <h2>Solicite seu orçamento</h2>
  <p class="orc__sub">Grátis e sem compromisso. O pedido vai direto para o WhatsApp da loja.</p>
  <form class="form" data-orcamento data-zap="{numero}" data-loja="{e(limpa(l['nome']))}" data-modelo="{e(limpa(modelo or ''))}" novalidate>
    <div class="campo"><label for="nome-{sufixo}">Seu nome</label>
      <input id="nome-{sufixo}" name="nome" type="text" autocomplete="name" required data-nome maxlength="80" placeholder="Nome e sobrenome">
      <small class="erro" aria-live="polite"></small></div>
    <div class="campo"><label for="fone-{sufixo}">WhatsApp com DDD</label>
      <input id="fone-{sufixo}" name="telefone" type="tel" inputmode="numeric" autocomplete="tel-national" required data-fone placeholder="(17) 99999-9999">
      <small class="erro" aria-live="polite"></small></div>
    <div class="campo"><label for="cid-{sufixo}">Cidade</label>
      <input id="cid-{sufixo}" name="cidade" type="text" autocomplete="address-level2" required data-cidade maxlength="60" placeholder="Sua cidade">
      <small class="erro" aria-live="polite"></small></div>
    <div class="campo"><label for="msg-{sufixo}">O que você procura?</label>
      <textarea id="msg-{sufixo}" name="mensagem" rows="3" required maxlength="600">{e(f'Quero saber preço, prazo e instalação da piscina {limpa(modelo)}.' if modelo else '')}</textarea>
      <small class="erro" aria-live="polite"></small></div>
    <button class="btn btn--zap btn--cheio" type="submit">{ZAP_SVG}Enviar pedido pelo WhatsApp</button>
    <p class="orc__nota">Seus dados ficam só com a loja.</p>
  </form>
  <div class="orc__ok" hidden>
    <span class="orc__ok-ico">{ico("check", 26)}</span>
    <h3>Pedido pronto no WhatsApp</h3>
    <p>Se a conversa não abriu, toque abaixo para abrir de novo.</p>
    <a class="btn btn--zap" data-reabrir href="#" target="_blank" rel="noopener">{ZAP_SVG}Abrir o WhatsApp</a>
  </div>
</aside>"""


def galeria(fotos, alt):
    if not fotos:
        return ""
    itens = []
    for i, u in enumerate(fotos):
        carregar = 'fetchpriority="high"' if i == 0 else 'loading="lazy" decoding="async"'
        itens.append(
            f'<button class="gal__item" type="button" data-foto="{e(img(u, 1400))}" data-i="{i}" aria-label="Ampliar foto {i + 1} de {len(fotos)}">'
            f'<img src="{e(img(u, 900))}" srcset="{srcset(u, 500, 900)}" sizes="(max-width: 900px) 92vw, 640px" '
            f'alt="{e(alt)}, foto {i + 1}" width="900" height="700" {carregar}></button>'
        )
    return f"""<div class="gal" data-galeria>
  <div class="gal__trilho">{"".join(itens)}</div>
  <button class="gal__seta gal__seta--esq" type="button" aria-label="Foto anterior" data-ant>{ico("esq", 20)}</button>
  <button class="gal__seta gal__seta--dir" type="button" aria-label="Próxima foto" data-prox>{ico("dir", 20)}</button>
  {f'<span class="gal__conta"><span data-atual>1</span> / {len(fotos)}</span>' if len(fotos) > 1 else ''}
</div>"""


VISOR = f"""<dialog class="visor" aria-label="Foto ampliada">
  <button class="visor__x" type="button" data-fechar aria-label="Fechar">{ico("x", 22)}</button>
  <button class="visor__seta visor__seta--esq" type="button" data-ant aria-label="Foto anterior">{ico("esq", 24)}</button>
  <img alt="" width="1400" height="1050">
  <button class="visor__seta visor__seta--dir" type="button" data-prox aria-label="Próxima foto">{ico("dir", 24)}</button>
</dialog>"""


def cabeca_secao(titulo, em="", nota="", acao="", hid=""):
    return f"""<div class="cab">
  <h2{f' id="{hid}"' if hid else ''}>{titulo}{f'<em>{em}</em>' if em else ''}</h2>
  {f'<p class="cab__nota">{nota}</p>' if nota else ''}
  {acao}
</div>"""


# ------------------------------------------------------------------ páginas

def pag_inicio(lojas, piscinas, destaque_ids, posts):
    dest = [piscinas[i] for i in destaque_ids]
    # vitrine do topo: fotos reais e deitadas dos modelos em destaque, escolhidas a dedo
    vit_sel = [("cmtnqeo0s00bnvror413358ub", 1), ("cmtjhoj0i03a76i825l6p7g3l", 1), ("cmqpgfryj0046egh5g8q322t0", 2)]
    # se algum modelo sair do ar, completa com outro destaque que tenha foto
    vit_sel = [(pid, nf) for pid, nf in vit_sel if pid in piscinas]
    for p in dest:
        if len(vit_sel) >= 3:
            break
        if p.get("fotos") and all(p["id"] != pid for pid, _ in vit_sel):
            vit_sel.append((p["id"], 0))
    vitrine = []
    for k, (pid, nf) in enumerate(vit_sel[:3]):
        p = piscinas.get(pid)
        if not p or not p.get("fotos"):
            continue
        u = p["fotos"][min(nf, len(p["fotos"]) - 1)]["url"]
        carregar = 'fetchpriority="high"' if k == 0 else 'loading="lazy" decoding="async"'
        tam = (f'srcset="{srcset(u, 800, 1400)}" sizes="(max-width: 700px) 92vw, 760px"' if k == 0
               else f'srcset="{srcset(u, 500, 900)}" sizes="(max-width: 700px) 46vw, 420px"')
        pr = preco(p.get("precoBase"))
        vitrine.append(f"""<a class="vit vit--{k + 1}" href="/piscina/{pid}/">
  <span class="vit__foto"><img src="{e(img(u, 900 if k else 1400))}" {tam} alt="Piscina {e(limpa(p['nome']))}, de {e(limpa(p['loja']['nome']))}" width="1400" height="930" {carregar}></span>
  <span class="vit__leg"><strong>{e(limpa(p['nome']))}</strong><span>{e(limpa(p['loja']['nome']))}{' · ' + e(pr) if pr else ''}</span></span>
</a>""")

    cont_cat = {k: sum(1 for l in lojas if k in cats_de(l)) for k, *_ in CATS}
    cats = "".join(
        f'<a class="cat" href="/buscar/?cat={k}"><span class="cat__ico">{ico(i, 22)}</span>'
        f'<strong>{t}</strong><span class="cat__n">{plural(cont_cat[k], "loja", "lojas")}</span>'
        f'<span class="seta-bola" aria-hidden="true">{ico("seta", 16)}</span></a>'
        for k, t, _, i in CATS
    )
    ufs = sorted({(l.get("endereco") or {}).get("estado") or l.get("cidadeUf") for l in lojas} - {None, ""})
    opcoes = '<option value="">Todo o Brasil</option>' + "".join(f'<option value="{u}">{u}</option>' for u in ufs)
    ricas = sorted(
        [l for l in lojas if l.get("logoUrl")],
        key=lambda l: -(len(l["piscinas"]) * 2 + len(l["servicos"]) + len(l["produtos"]) + (1 if cidade_de(l) else 0)),
    )
    # variar: no máximo uma unidade por rede (primeira palavra do nome)
    vistas, sel = set(), []
    for l in ricas:
        rede = sem_acento(limpa(l["nome"]).split(" ")[0])
        if rede in vistas:
            continue
        vistas.add(rede)
        sel.append(l)
        if len(sel) == 8:
            break
    ricas = sel
    pd, resto = destaque_e_resto(posts)
    blog = (post_destaque(pd) if pd else "") + (f'<div class="posts-lado">{"".join(cartao_post(x) for x in resto[:2])}</div>' if resto else "")
    n = len(lojas)
    ld = [LD_ORG, LD_SITE, {"@type": "WebPage", "@id": SITE + "/#pagina", "url": SITE + "/", "name": "iPiscinas",
                            "isPartOf": {"@id": SITE + "/#site"}, "inLanguage": "pt-BR"}]
    desc = f"Encontre lojas de piscinas, piscineiros, manutenção e produtos químicos perto de você. {n} lojas ativas no iPiscinas. Compare modelos e peça orçamento grátis."
    return cabeca("iPiscinas · Lojas de piscinas, piscineiros e orçamentos", desc, "/", ld=ld) + topo("/") + f"""
<main id="conteudo">
  <section class="heroi heroi--inicio heroi--centro">
    <div class="wrap">
      <div class="heroi__txt">
        <p class="heroi__ola">Olá 👋</p>
        <h1>Tudo para sua piscina<em>em um só lugar.</em></h1>
        <p class="heroi__sub">Descubra lojas, modelos de piscinas e solicite orçamentos.</p>
        <form class="busca-card" action="/buscar/" method="get" role="search">
          <div class="busca-card__campo busca-card__campo--q">
            <label for="q-heroi">O que você procura?</label>
            <input id="q-heroi" name="q" type="search" placeholder="Buscar lojas, modelos, cidades..." autocomplete="off" enterkeyhint="search">
          </div>
          <div class="busca-card__campo">
            <label for="uf-heroi">Estado</label>
            <select id="uf-heroi" name="uf">{opcoes}</select>
          </div>
          <button class="btn" type="submit">{ico("search", 18)}Buscar</button>
        </form>
        <p class="heroi__conta"><span class="heroi__estrelas">{ico("estrela", 15)}{ico("estrela", 15)}{ico("estrela", 15)}{ico("estrela", 15)}{ico("estrela", 15)}</span><span><strong>{n} lojas ativas</strong> no iPiscinas</span></p>
      </div>
      <div class="vitrine" aria-label="Modelos em destaque">{"".join(vitrine)}</div>
    </div>
    {RAIA_BOIAS}
  </section>

  <section class="sec" aria-labelledby="t-cats">
    <div class="wrap">
      {cabeca_secao("O que sua piscina precisa", "a gente encontra quem faz.", hid="t-cats")}
      <div class="cats">{cats}</div>
    </div>
  </section>

  <section class="sec" aria-labelledby="t-dest">
    <div class="wrap">
      {cabeca_secao("Em destaque", "modelos escolhidos pelas lojas.", acao=f'<a class="btn btn--claro" href="/buscar/?ver=piscinas">Ver todas as piscinas</a>', hid="t-dest")}
      {carrossel([cartao_piscina(p) for p in dest], "Piscinas em destaque")}
    </div>
  </section>

  <section class="sec" aria-labelledby="t-perto" data-perto>
    <div class="wrap">
      {cabeca_secao("Lojas próximas", "de quem atende você.", nota='<span data-perto-sub>Use sua localização para ver as lojas mais perto.</span>', acao=f'<button class="btn btn--claro" type="button" data-localizar>{ico("alvo", 18)}Usar minha localização</button>', hid="t-perto")}
      <div class="lojas" data-perto-lista>{"".join(cartao_loja(l) for l in ricas)}</div>
    </div>
  </section>

  <section class="sec">
    <div class="wrap">
      <a class="faixa" href="/mapa/">
        <span class="faixa__txt"><strong>Veja as lojas no mapa</strong><span>Lojas de piscinas, piscineiros e assistência pelo Brasil.</span></span>
        <span class="btn btn--branco">{ico("map", 18)}Abrir o mapa</span>
      </a>
    </div>
  </section>

  <section class="sec" aria-labelledby="t-blog">
    <div class="wrap">
      {cabeca_secao("Blog e notícias", "do mercado de piscinas.", acao=f'<a class="btn btn--claro" href="/blog/">Ver o blog</a>', hid="t-blog")}
      <div class="blog-capa">{blog}</div>
    </div>
  </section>

  <section class="sec sec--fim">
    <div class="wrap">
      <div class="app">
        <span class="app__ico">{ico("app", 24)}</span>
        <div><strong>Prefere o app?</strong><span>Em breve disponível para iOS e Android.</span></div>
      </div>
    </div>
  </section>
</main>
""" + rodape() + fim()


SIGLAS = {"ipiscinas": "iPiscinas", "uol": "UOL", "tse": "TSE", "meta": "Meta", "google": "Google", "brasil": "Brasil"}


def titulo_post(t):
    """Título todo em maiúsculas vira caixa normal (só a forma; o texto é o mesmo)."""
    t = limpa(t)
    letras = [c for c in t if c.isalpha()]
    if not letras or sum(c.isupper() for c in letras) / len(letras) < .8:
        return t
    palavras = t.lower().split(" ")
    palavras = [SIGLAS.get(w.strip(",.:;!?"), None) and w.replace(w.strip(",.:;!?"), SIGLAS[w.strip(",.:;!?")]) or w for w in palavras]
    s = " ".join(palavras)
    return s[:1].upper() + s[1:]


def tipo_post(p):
    return (p.get("categoria") or {}).get("nome") or ("Notícia" if p.get("tipo") == "NOTICIA" else "Blog")


def post_destaque(p, h="h3"):
    capa = p.get("capaUrl")
    rotulo = "Notícia" if p.get("tipo") == "NOTICIA" else tipo_post(p)
    return f"""<a class="post-d" href="/blog/{e(p['slug'])}/">
  <span class="post-d__capa">{f'<img src="{e(img(capa, 1100))}" srcset="{srcset(capa, 640, 1100)}" sizes="(max-width: 900px) 92vw, 640px" alt="{e(p.get("capaAlt") or "")}" width="1100" height="620" loading="lazy" decoding="async">' if capa else ''}</span>
  <span class="post-d__txt">
    <span class="post-d__meta"><span class="post-d__tipo">{e(rotulo)}</span><time datetime="{e(p.get('publicadoEm'))}">{data_br(p['publicadoEm'])}</time></span>
    <{h} class="post-d__tit">{e(titulo_post(p['titulo']))}</{h}>
    <span class="post-d__res">{e(resumo(p.get('resumo'), 230))}</span>
    <span class="post-d__ler">Ler {'a notícia' if p.get('tipo') == 'NOTICIA' else 'o artigo'} {ico("seta", 16)}</span>
  </span>
</a>"""


def destaque_e_resto(posts):
    """A notícia mais recente abre o blog; sem notícia, o post mais recente."""
    ordem = sorted(posts, key=lambda p: p.get("publicadoEm") or "", reverse=True)
    dest = next((p for p in ordem if p.get("tipo") == "NOTICIA"), ordem[0] if ordem else None)
    return dest, [p for p in ordem if p is not dest]


def cartao_post(p, h="h3"):
    cat = tipo_post(p)
    capa = p.get("capaUrl")
    return f"""<a class="post" href="/blog/{e(p['slug'])}/">
  <span class="post__capa">{f'<img src="{e(img(capa, 640))}" srcset="{srcset(capa, 400, 640)}" sizes="(max-width: 700px) 92vw, 380px" alt="{e(p.get("capaAlt") or "")}" width="640" height="360" loading="lazy" decoding="async">' if capa else ''}</span>
  <span class="post__txt">
    <span class="post__meta">{e(cat)} · <time datetime="{e(p.get('publicadoEm'))}">{data_br(p['publicadoEm'])}</time></span>
    <{h} class="post__tit">{e(titulo_post(p['titulo']))}</{h}>
    <span class="post__res">{e(resumo(p.get('resumo'), 140))}</span>
  </span>
</a>"""


def pag_loja(l):
    nome = limpa(l["nome"])
    cid = cidade_de(l)
    cats = [t for k, t, _, _ in CATS if k in cats_de(l)]
    numero = zap_de(l.get("whatsapp"))
    fone = digitos(l.get("telefone") or l.get("whatsapp"))
    acoes = f'<a class="btn" href="#orcamento">Pedir orçamento</a>'
    if numero:
        acoes += f'<a class="btn btn--zap" href="{e(wa(numero, f"Olá, {nome}! Vi vocês no iPiscinas e gostaria de mais informações."))}" target="_blank" rel="noopener">{ZAP_SVG}WhatsApp</a>'
    if len(fone) in (10, 11):
        acoes += f'<a class="btn btn--claro" href="tel:+55{fone}">{ico("fone", 18)}Ligar</a>'

    secoes = []
    if l["piscinas"]:
        cards = "".join(cartao_piscina(dict(p, loja=l, fotos=sorted(p.get("fotos") or [], key=lambda f: f.get("ordem", 0)))) for p in l["piscinas"])
        secoes.append(f'<section class="bloco" aria-labelledby="t-mod"><h2 id="t-mod">Modelos de piscina<span>{plural(len(l["piscinas"]), "modelo", "modelos")}</span></h2><div class="grade-p">{cards}</div></section>')
    for chave, titulo, rot in (("servicos", "Serviços", ("serviço", "serviços")), ("produtos", "Produtos", ("produto", "produtos"))):
        itens = l.get(chave) or []
        if not itens:
            continue
        lis = []
        for s in itens:
            foto = s.get("fotoUrl")
            pr = preco(s.get("preco"))
            lis.append(f"""<li class="item">
  {f'<img src="{e(img(foto, 200))}" alt="" width="72" height="72" loading="lazy" decoding="async">' if foto else f'<span class="item__ico">{ico("sparkles" if chave == "servicos" else "flask", 22)}</span>'}
  <div><h3>{e(limpa(s['nome']))}</h3>{f'<p>{e(limpa(s.get("descricao")))}</p>' if s.get('descricao') else ''}</div>
  <strong class="item__preco">{e(pr) if pr else 'Sob consulta'}</strong>
</li>""")
        secoes.append(f'<section class="bloco" aria-labelledby="t-{chave}"><h2 id="t-{chave}">{titulo}<span>{plural(len(itens), *rot)}</span></h2><ul class="itens">{"".join(lis)}</ul></section>')
    trab = [t for t in (l.get("trabalhos") or []) if t.get("fotoUrl") or t.get("url")]
    if trab:
        fotos = [t.get("fotoUrl") or t.get("url") for t in trab]
        secoes.append(f'<section class="bloco" aria-labelledby="t-trab"><h2 id="t-trab">Trabalhos realizados</h2>{galeria(fotos, f"Trabalho de {nome}")}</section>')
    end = l.get("endereco") or {}
    if end.get("cidade"):
        linha = ", ".join(x for x in [limpa(end.get("logradouro")) + (f", {end['numero']}" if end.get("numero") else ""), limpa(end.get("bairro"))] if x)
        g = geo_de(l)
        mapa = f'<a class="link" href="https://www.google.com/maps/search/?api=1&query={g[0]},{g[1]}" target="_blank" rel="noopener">Abrir no Google Maps {ico("seta", 16)}</a>' if g else ""
        secoes.append(f'<section class="bloco" aria-labelledby="t-end"><h2 id="t-end">Endereço</h2><div class="end">{ico("pin", 20)}<p>{e(linha)}{"<br>" if linha else ""}{e(end.get("cidade"))}, {e(end.get("estado"))}{(" · CEP " + e(end["cep"])) if end.get("cep") else ""}</p>{mapa}</div></section>')
    if not secoes:
        secoes.append('<section class="bloco"><p class="vazio">Esta loja ainda está montando a vitrine. Peça um orçamento e ela responde pelo WhatsApp.</p></section>')

    reput = (f'{float(l["reputacaoMedia"]):.1f}'.replace(".", ",") + f' · {plural(l["reputacaoTotal"], "avaliação", "avaliações")}') if l.get("reputacaoMedia") and l.get("reputacaoTotal") else "Sem avaliações"
    desc_txt = limpa(l.get("descricao"))
    desc_meta = resumo(f"{nome}{' em ' + cid if cid else ''} no iPiscinas. " + (desc_txt or ", ".join(cats) or "Loja de piscinas") + ". Peça orçamento grátis pelo WhatsApp.", 158)
    caminho = f"/loja/{l['slug']}/"
    mig = [("Início", "/"), ("Lojas", "/buscar/?ver=lojas"), (nome, caminho)]
    negocio = {"@type": "Store", "@id": SITE + caminho + "#loja", "name": nome, "url": SITE + caminho}
    if l.get("logoUrl"):
        negocio["image"] = l["logoUrl"]
    if desc_txt:
        negocio["description"] = desc_txt
    if end.get("cidade"):
        negocio["address"] = {"@type": "PostalAddress", "streetAddress": limpa(f"{end.get('logradouro') or ''} {end.get('numero') or ''}"),
                              "addressLocality": end.get("cidade"), "addressRegion": end.get("estado"), "postalCode": end.get("cep"), "addressCountry": "BR"}
        g = geo_de(l)
        if g:
            negocio["geo"] = {"@type": "GeoCoordinates", "latitude": g[0], "longitude": g[1]}
    if len(fone) in (10, 11):
        negocio["telephone"] = "+55" + fone
    capa = l.get("capaUrl")
    og = img(capa or l.get("logoUrl"), 1200) if (capa or l.get("logoUrl")) else None
    cartao = f"""<div class="loja-card{' loja-card--capa' if capa else ''}">
      {f'<div class="loja-card__capa"><img src="{e(img(capa, 1400))}" srcset="{srcset(capa, 800, 1400)}" sizes="(max-width: 1240px) 92vw, 1180px" alt="" width="1400" height="350" fetchpriority="high"></div>' if capa else ''}
      <div class="loja-card__in">
        {logo_loja(l, 104, "selo selo--g")}
        <div class="loja-card__txt">
          <p class="loja-card__meta">{f'<span>{ico("pin", 16)}{e(cid)}</span>' if cid else ''}<span>{ico("estrela", 16)}Reputação iPiscinas: {e(reput)}</span></p>
          {f'<p class="loja-card__desc">{e(desc_txt)}</p>' if desc_txt else ''}
          {f'<ul class="chips">{"".join(f"<li>{e(c)}</li>" for c in cats)}</ul>' if cats else ''}
        </div>
        <div class="loja-card__acoes">{acoes}</div>
      </div>
    </div>"""
    return cabeca(f"{nome}{' · ' + cid if cid else ''} | iPiscinas", desc_meta, caminho, og=og,
                  ld=[LD_ORG, LD_SITE, negocio, ld_migalhas(mig)]) + topo("/buscar/") + f"""
<main id="conteudo">
  {heroi(e(nome), mig=mig, extra=cartao, cls="heroi--loja")}
  <div class="wrap duas">
    <div class="duas__principal">{"".join(secoes)}</div>
    <div class="duas__lado">{form_orcamento(l)}</div>
  </div>
</main>
{VISOR}
""" + rodape() + fim()


def pag_piscina(p):
    l = p["loja"]
    nome = limpa(p["nome"])
    lnome = limpa(l["nome"])
    fotos = [f["url"] for f in p.get("fotos") or []]
    pr = preco(p.get("precoBase"))
    specs = [
        ("Comprimento", medida(p.get("comprimentoM"))),
        ("Largura", medida(p.get("larguraM"))),
        ("Profundidade", medida(p.get("profundidadeM"))),
        ("Capacidade", litros(p.get("capacidadeL"))),
    ]
    specs = [(a, b) for a, b in specs if b]
    chips = [x for x in (TIPO.get(p.get("tipo")), FORMATO.get(p.get("formato"))) if x]
    desc = (p.get("descricao") or "").strip()
    desc_html = "".join(f"<p>{e(par.strip())}</p>" for par in re.split(r"\n", desc) if par.strip())
    caminho = f"/piscina/{p['id']}/"
    mig = [("Início", "/"), ("Piscinas", "/buscar/?ver=piscinas"), (lnome, f"/loja/{l['slug']}/"), (nome, caminho)]
    cid = cidade_de(l)
    meta = resumo(f"Piscina {nome}{' de ' + chips[0].lower() if chips else ''}, vendida por {lnome}{' em ' + cid if cid else ''}. "
                  + (f"{pr}. " if pr else "") + (resumo(desc, 70) + " " if desc else "") + "Peça orçamento grátis no iPiscinas.", 158)
    prod = {"@type": "Product", "@id": SITE + caminho + "#produto", "name": nome, "brand": {"@type": "Brand", "name": lnome},
            "url": SITE + caminho}
    if fotos:
        prod["image"] = [img(u, 1200) for u in fotos[:4]]
    if desc:
        prod["description"] = limpa(desc)
    if pr:
        prod["offers"] = {"@type": "Offer", "price": f"{float(p['precoBase']):.2f}", "priceCurrency": "BRL",
                          "availability": "https://schema.org/InStock", "seller": {"@type": "Organization", "name": lnome},
                          "url": SITE + caminho}
    sem_foto = f'<div class="gal gal--vazia">{ico("waves", 56)}</div>'
    lis_chips = "".join(f"<li>{e(c)}</li>" for c in chips)
    extra = (f'<ul class="chips">{lis_chips}</ul>' if chips else "") + f'<p class="heroi__preco">{e(pr) if pr else "Preço sob consulta"}</p>'
    return cabeca(f"{nome} · {lnome} | iPiscinas", meta, caminho, og=img(fotos[0], 1200) if fotos else None,
                  ld=[LD_ORG, LD_SITE, prod, ld_migalhas(mig)]) + topo("/buscar/") + f"""
<main id="conteudo">
  {heroi(e(nome), mig=mig, extra=extra, cls="heroi--piscina")}
  <div class="wrap piscina">
    <div class="piscina__fotos">{galeria(fotos, f"Piscina {nome}") or sem_foto}</div>
    <div class="piscina__info">
      <a class="vendido" href="/loja/{e(l['slug'])}/">
        {logo_loja(l, 48)}
        <span class="vendido__txt"><small>Vendido por</small><strong>{e(lnome)}</strong>{f'<em>{e(cid)}</em>' if cid else ''}</span>
        <span class="seta-bola" aria-hidden="true">{ico("seta", 16)}</span>
      </a>
      {f'<section class="bloco"><h2>Especificações</h2><dl class="specs">{"".join(f"<div><dt>{a}</dt><dd>{b}</dd></div>" for a, b in specs)}</dl></section>' if specs else ''}
      {f'<section class="bloco"><h2>Descrição</h2><div class="texto">{desc_html}</div></section>' if desc_html else ''}
      {form_orcamento(l, nome)}
    </div>
  </div>
</main>
{VISOR}
""" + rodape() + fim()


def limpa_html(h, titulo=""):
    h = re.sub(r"(?is)<(script|style|iframe|object|embed)[^>]*>.*?</\1>", "", h or "")
    h = re.sub(r"(?is)<(p|div)[^>]*>(\s|&nbsp;|<br\s*/?>)*</\1>", "", h)
    if titulo:  # o título já está no topo da página; tira a repetição no começo do texto
        m = re.match(r"(?is)\s*<h[1-3][^>]*>(.*?)</h[1-3]>", h)
        if m and sem_acento(re.sub(r"<[^>]+>|\s+", "", m.group(1))) == sem_acento(re.sub(r"\s+", "", titulo)):
            h = h[m.end():]
    h = re.sub(r"(?i)\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", h)
    h = re.sub(r'(?i)href\s*=\s*"javascript:[^"]*"', 'href="#"', h)
    h = re.sub(r"(?i)<h1(\s|>)", r"<h2\1", h).replace("</h1>", "</h2>")
    h = re.sub(r"(?i)<img(?![^>]*loading=)", '<img loading="lazy" decoding="async"', h)
    h = re.sub(r'(?i)<a\s+(?=[^>]*href="https?://)(?![^>]*target=)', '<a target="_blank" rel="noopener" ', h)
    return h


def pag_blog(posts, categorias):
    chips = '<li><button type="button" class="chip" aria-pressed="true" data-filtro="">Tudo</button></li>' + "".join(
        f'<li><button type="button" class="chip" aria-pressed="false" data-filtro="{e(c["slug"])}">{e(c["nome"])}</button></li>'
        for c in categorias if any((p.get("categoria") or {}).get("slug") == c["slug"] for p in posts)
    )
    pd, resto = destaque_e_resto(posts)
    cartoes = "".join(
        f'<div data-cat="{e((p.get("categoria") or {}).get("slug") or "")}">{cartao_post(p, "h2")}</div>' for p in resto
    )
    mig = [("Início", "/"), ("Blog", "/blog/")]
    return cabeca("Blog e notícias sobre piscinas | iPiscinas",
                  "Pesquisas, notícias e dicas sobre o mercado de piscinas: compra, manutenção, lojas e atendimento ao consumidor. Leia no blog do iPiscinas.",
                  "/blog/", ld=[LD_ORG, LD_SITE, {"@type": "Blog", "@id": SITE + "/blog/#blog", "name": "Blog iPiscinas", "url": SITE + "/blog/"}, ld_migalhas(mig)]) + topo("/blog/") + f"""
<main id="conteudo">
  {heroi("Blog e notícias", "do mercado de piscinas.", mig=mig, sub="Pesquisas, notícias e dicas para quem compra, cuida e vende piscinas.", cls="heroi--centro")}
  <div class="wrap pag-corpo">
    {post_destaque(pd, "h2") if pd else ""}
    <h2 class="bloco-tit bloco-tit--centro">Todos os posts</h2>
    <ul class="chips chips--filtro" data-filtros>{chips}</ul>
    <div class="posts posts--lista" data-posts>{cartoes}</div>
  </div>
</main>
""" + rodape() + fim()


def pag_post(p, todos):
    caminho = f"/blog/{p['slug']}/"
    tit = titulo_post(p["titulo"])
    cat = tipo_post(p)
    autor = (p.get("autor") or {}).get("name") or "iPiscinas"
    capa = p.get("capaUrl")
    rel = [x for x in todos if x["slug"] != p["slug"]][:3]
    mig = [("Início", "/"), ("Blog", "/blog/"), (tit, caminho)]
    art = {"@type": "BlogPosting" if p.get("tipo") != "NOTICIA" else "NewsArticle", "@id": SITE + caminho + "#artigo",
           "headline": tit[:110], "description": limpa(p.get("resumo")), "datePublished": p.get("publicadoEm"),
           "dateModified": p.get("updatedAt") or p.get("publicadoEm"), "author": {"@type": "Person", "name": autor},
           "publisher": {"@id": SITE + "/#org"}, "mainEntityOfPage": SITE + caminho, "inLanguage": "pt-BR"}
    if capa:
        art["image"] = img(capa, 1200)
    if p.get("tags"):
        art["keywords"] = ", ".join(p["tags"])
    tags = "".join(f"<li>{e(t)}</li>" for t in (p.get("tags") or [])[:12])
    relacionados = ""
    if rel:
        relacionados = (f'<section class="sec sec--fim"><div class="wrap">'
                        + cabeca_secao("Continue lendo", acao='<a class="btn btn--claro" href="/blog/">Ver o blog</a>')
                        + f'<div class="posts">{"".join(cartao_post(x) for x in rel)}</div></div></section>')
    meta = f'<p class="heroi__meta"><span class="heroi__cat">{e(cat)}</span> por {e(autor)} · <time datetime="{e(p.get("publicadoEm"))}">{data_br(p["publicadoEm"])}</time> · {p.get("tempoLeituraMin") or 1} min de leitura</p>'
    return cabeca(f"{limpa(p.get('seoTitulo') or tit)} | iPiscinas", resumo(p.get("seoDescricao") or p.get("resumo"), 158), caminho,
                  og=img(capa, 1200) if capa else None, ld=[LD_ORG, LD_SITE, art, ld_migalhas(mig)]) + topo("/blog/") + f"""
<main id="conteudo">
  <article class="artigo">
    {heroi(e(tit), mig=mig, extra=meta, cls="heroi--centro heroi--artigo")}
    {f'<figure class="artigo__capa wrap"><img src="{e(img(capa, 1200))}" srcset="{srcset(capa, 700, 1200)}" sizes="(max-width: 1100px) 92vw, 1040px" alt="{e(p.get("capaAlt") or "")}" width="1200" height="675" fetchpriority="high"></figure>' if capa else ''}
    <div class="wrap wrap--texto">
      <div class="texto texto--artigo">{limpa_html(p.get('conteudoHtml'), tit)}</div>
      {f'<ul class="chips chips--tags">{tags}</ul>' if tags else ''}
    </div>
  </article>
  {relacionados}
</main>
""" + rodape() + fim()


def pag_buscar(lojas):
    chips = '<li><button type="button" class="chip" aria-pressed="true" data-cat="">Tudo</button></li>' + "".join(
        f'<li><button type="button" class="chip" aria-pressed="false" data-cat="{k}">{ico(i, 16)}{t}</button></li>' for k, t, _, i in CATS
    )
    ufs = sorted({(l.get("endereco") or {}).get("estado") or l.get("cidadeUf") for l in lojas} - {None, ""})
    opcoes = '<option value="">Todo o Brasil</option>' + "".join(f'<option value="{u}">{u}</option>' for u in ufs)
    mig = [("Início", "/"), ("Buscar", "/buscar/")]
    painel = f"""<form class="painel-busca" role="search" data-busca-form>
      <div class="busca-card__campo busca-card__campo--q"><label for="q">Loja, modelo ou cidade</label>
        <input id="q" name="q" type="search" placeholder="Buscar lojas, modelos, cidades..." autocomplete="off" enterkeyhint="search"></div>
      <div class="busca-card__campo"><label for="uf">Estado</label><select id="uf" name="uf">{opcoes}</select></div>
      <div class="busca-card__campo"><span class="rot" id="rot-ver">Mostrar</span>
        <div class="segmento" role="group" aria-labelledby="rot-ver">
          <button type="button" aria-pressed="true" data-ver="tudo">Tudo</button>
          <button type="button" aria-pressed="false" data-ver="lojas">Lojas</button>
          <button type="button" aria-pressed="false" data-ver="piscinas">Piscinas</button>
        </div></div>
    </form>"""
    return cabeca("Buscar lojas e modelos de piscina | iPiscinas",
                  "Busque lojas de piscinas, piscineiros, manutenção, produtos químicos e modelos de piscina de fibra por nome ou cidade. Peça orçamento grátis.",
                  "/buscar/", ld=[LD_ORG, LD_SITE, ld_migalhas(mig)]) + topo("/buscar/") + f"""
<main id="conteudo" data-buscar>
  {heroi("Buscar", "lojas, modelos e cidades.", mig=mig, sub="Piscinas, piscineiros, manutenção, produtos químicos e acessórios.", extra=painel, cls="heroi--centro")}
  <div class="wrap pag-corpo">
    <ul class="chips chips--filtro" data-cats aria-label="Categorias">{chips}</ul>
    <p class="resultado" aria-live="polite" data-resumo>Carregando…</p>
    <section data-bloco="piscinas"><h2 class="bloco-tit">Piscinas</h2><div class="grade-p" data-lista-piscinas></div>
      <p class="sec__mais"><button class="btn btn--claro" type="button" data-mais="piscinas" hidden>Mostrar mais piscinas</button></p></section>
    <section data-bloco="lojas"><h2 class="bloco-tit">Lojas</h2><div class="lojas" data-lista-lojas></div>
      <p class="sec__mais"><button class="btn btn--claro" type="button" data-mais="lojas" hidden>Mostrar mais lojas</button></p></section>
    <p class="vazio" data-vazio hidden>Nada encontrado. Tente outra palavra ou tire o filtro de estado.</p>
  </div>
</main>
""" + rodape() + fim()


def pag_mapa(lojas):
    n = sum(1 for l in lojas if geo_de(l))
    extra = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">'
    mig = [("Início", "/"), ("Mapa", "/mapa/")]
    botao = f'<div class="heroi__acoes"><button class="btn btn--branco" type="button" data-localizar>{ico("alvo", 18)}Perto de mim</button></div>'
    return cabeca("Mapa de lojas de piscinas | iPiscinas",
                  f"Veja no mapa {n} lojas de piscinas, piscineiros e assistência técnica pelo Brasil. Encontre a mais perto de você e peça orçamento.",
                  "/mapa/", ld=[LD_ORG, LD_SITE, ld_migalhas(mig)], extra=extra) + topo("/mapa/") + f"""
<main id="conteudo" data-mapa>
  {heroi("Mapa", "das lojas pelo Brasil.", mig=mig, sub=f"{n} lojas com endereço no mapa. Aproxime para ver a lista da região.", extra=botao, cls="heroi--centro heroi--curto")}
  <div class="wrap mapa">
    <div class="mapa__tela" id="mapa" role="region" aria-label="Mapa das lojas"></div>
    <aside class="mapa__lista" aria-label="Lojas nesta área">
      <p class="mapa__conta" aria-live="polite" data-mapa-conta></p>
      <div class="lojas lojas--uma" data-mapa-lista></div>
    </aside>
  </div>
</main>
""" + rodape() + fim('<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js" defer></script>\n')


def campo_senha(id_, rotulo, auto, ph):
    return f"""<div class="campo"><label for="{id_}">{rotulo}</label>
      <div class="senha"><input id="{id_}" name="senha" type="password" autocomplete="{auto}" required minlength="6" maxlength="72" placeholder="{ph}" data-senha>
      <button class="senha__ver" type="button" aria-label="Mostrar senha" aria-pressed="false" data-ver-senha>{ico("olho", 18)}</button></div>
      <small class="erro" aria-live="polite"></small></div>"""


def pag_acesso(caminho, titulo, em, sub, form, rodape_form):
    return cabeca(f"{titulo} | iPiscinas", sub, caminho, indexar=False) + topo("") + f"""
<main id="conteudo">
  {heroi(titulo, em, sub=sub, cls="heroi--centro heroi--acesso")}
  <div class="wrap acesso">
    <div class="acesso__card">
      {form}
      <p class="acesso__aviso" role="alert" aria-live="assertive" data-aviso hidden></p>
      {rodape_form}
    </div>
  </div>
</main>
""" + rodape() + fim()


def pag_entrar():
    form = f"""<form class="form" data-acesso="entrar" novalidate>
      <div class="campo"><label for="email-e">E-mail</label>
        <input id="email-e" name="email" type="email" inputmode="email" autocomplete="email" required maxlength="120" placeholder="seu@email.com" data-email>
        <small class="erro" aria-live="polite"></small></div>
      {campo_senha("senha-e", "Senha", "current-password", "Sua senha")}
      <button class="btn btn--cheio" type="submit" data-enviar>Entrar</button>
    </form>"""
    pe = f"""<p class="acesso__troca">Ainda não tem conta? <a class="link" href="/criar-conta/">Criar conta</a></p>
      <p class="acesso__volta"><a href="/">{ico("volta", 15)}Continuar sem entrar</a></p>
      <p class="acesso__loja">Tem uma loja ou presta serviço de piscina? <a class="link" href="{APP}/cadastrar-loja">Cadastre aqui</a></p>"""
    return pag_acesso("/entrar/", "Entrar na sua conta", "", "Acesse para solicitar orçamentos e acompanhar suas conversas.", form, pe)


def pag_criar_conta():
    form = f"""<form class="form" data-acesso="criar" novalidate>
      <div class="campo"><label for="nome-c">Nome completo</label>
        <input id="nome-c" name="nome" type="text" autocomplete="name" required maxlength="80" placeholder="Como podemos te chamar" data-nome>
        <small class="erro" aria-live="polite"></small></div>
      <div class="campo"><label for="email-c">E-mail</label>
        <input id="email-c" name="email" type="email" inputmode="email" autocomplete="email" required maxlength="120" placeholder="seu@email.com" data-email>
        <small class="erro" aria-live="polite"></small></div>
      <div class="campo"><label for="fone-c">WhatsApp com DDD</label>
        <input id="fone-c" name="telefone" type="tel" inputmode="numeric" autocomplete="tel-national" required placeholder="(17) 99999-9999" data-fone>
        <small class="erro" aria-live="polite"></small></div>
      {campo_senha("senha-c", "Senha", "new-password", "Mínimo 6 caracteres")}
      <button class="btn btn--cheio" type="submit" data-enviar>Criar conta</button>
    </form>"""
    pe = f"""<p class="acesso__troca">Já tem conta? <a class="link" href="/entrar/">Entrar</a></p>
      <p class="acesso__loja">Tem uma loja ou presta serviço de piscina? <a class="link" href="{APP}/cadastrar-loja">Cadastre aqui</a></p>"""
    return pag_acesso("/criar-conta/", "Bem-vindo ao iPiscinas", "", "Crie sua conta em menos de 1 minuto.", form, pe)


def pag_conta():
    fora = f"""<div class="heroi__acoes" data-sessao-fora>
        <a class="btn btn--branco" href="/entrar/">Entrar</a>
        <a class="btn btn--vidro" href="/criar-conta/">Criar conta {ico("seta", 16)}</a>
      </div>"""
    dentro = f"""<div class="wrap acesso" data-sessao-dentro hidden>
    <div class="acesso__card conta-card">
      <span class="conta-card__ico">{ico("user", 26)}</span>
      <h2 data-sessao-nome>Sua conta</h2>
      <p class="conta-card__email" data-sessao-email></p>
      <div class="conta-card__acoes">
        <a class="btn btn--claro" href="/buscar/">{ico("search", 18)}Buscar lojas e piscinas</a>
        <button class="btn btn--claro" type="button" data-sair>Sair da conta</button>
      </div>
    </div>
  </div>"""
    return cabeca("Acesse sua conta | iPiscinas", "Entre ou crie uma conta no iPiscinas para solicitar orçamentos e acompanhar conversas com as lojas.",
                  "/conta/", indexar=False) + topo("/conta/") + f"""
<main id="conteudo" data-conta>
  {heroi("Acesse sua conta", sub="Entre ou crie uma conta para solicitar orçamentos e acompanhar conversas.", extra=fora, cls="heroi--centro heroi--conta heroi--so")}
  {dentro}
</main>
""" + rodape() + fim()


def pag_404():
    busca = f"""<form class="busca-linha" action="/buscar/" method="get" role="search">
        <label class="sr" for="q404">Buscar</label>
        <input id="q404" name="q" type="search" placeholder="Buscar lojas, modelos, cidades...">
        <button class="btn" type="submit">{ico("search", 18)}Buscar</button>
      </form>"""
    return cabeca("Página não encontrada | iPiscinas", "Esta página não existe ou mudou de endereço.", "/404.html", indexar=False) + topo("") + f"""
<main id="conteudo">
  {heroi("Página não encontrada", sub="Esta página não existe ou mudou de endereço. Se era uma loja ou piscina nova, procure pela busca.", extra=busca, cls="heroi--centro heroi--so")}
</main>
""" + rodape() + fim()


# ------------------------------------------------------------------ dados para o JS, sitemap etc.

def dados_js(lojas, piscinas):
    L = []
    for l in lojas:
        g = geo_de(l)
        end = l.get("endereco") or {}
        L.append({
            "s": l["slug"], "n": limpa(l["nome"]), "l": img(l["logoUrl"], 112) if l.get("logoUrl") else "",
            "i": iniciais(l["nome"]), "c": cidade_de(l), "uf": end.get("estado") or l.get("cidadeUf") or "",
            "k": cats_de(l), "q": " · ".join(contagens(l)), "g": list(g) if g else None,
            "b": sem_acento(" ".join([l["nome"], cidade_de(l), end.get("bairro") or "", limpa(l.get("descricao"))]
                                     + [p["nome"] for p in l["piscinas"]] + [s["nome"] for s in l["servicos"]] + [s["nome"] for s in l["produtos"]])),
        })
    P = []
    for p in piscinas.values():
        l = p["loja"]
        end = l.get("endereco") or {}
        foto = p["fotos"][0]["url"] if p.get("fotos") else ""
        P.append({
            "id": p["id"], "n": limpa(p["nome"]), "f": img(foto, 400) if foto else "", "f2": img(foto, 640) if foto else "",
            "t": TIPO.get(p.get("tipo"), ""), "ln": limpa(l["nome"]), "pr": preco(p.get("precoBase")),
            "uf": end.get("estado") or l.get("cidadeUf") or "",
            "b": sem_acento(" ".join([p["nome"], l["nome"], cidade_de(l), p.get("descricao") or "", FORMATO.get(p.get("formato"), "")])),
        })
    (RAIZ / "dados").mkdir(exist_ok=True)
    (RAIZ / "dados" / "busca.json").write_text(json.dumps({"lojas": L, "piscinas": P, "gerado": HOJE}, ensure_ascii=False, separators=(",", ":")))


def sitemap(urls):
    corpo = "".join(f"<url><loc>{e(SITE + u)}</loc><lastmod>{HOJE}</lastmod></url>" for u in urls)
    (RAIZ / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{corpo}</urlset>\n')
    if PREVIA:
        (RAIZ / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    else:
        (RAIZ / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /conta/\nDisallow: /entrar/\nDisallow: /criar-conta/\n\nSitemap: {SITE}/sitemap.xml\n")


def main():
    print("baixando dados…")
    lojas, piscinas, destaque_ids, posts, cats_blog = carregar()
    print(f"  {len(lojas)} lojas · {len(piscinas)} piscinas · {len(posts)} posts")
    for pasta in ("loja", "piscina", "blog"):
        shutil.rmtree(RAIZ / pasta, ignore_errors=True)
    urls = ["/", "/buscar/", "/mapa/", "/blog/"]
    escrever("/", pag_inicio(lojas, piscinas, destaque_ids, posts))
    escrever("/buscar/", pag_buscar(lojas))
    escrever("/mapa/", pag_mapa(lojas))
    escrever("/blog/", pag_blog(posts, cats_blog))
    escrever("/conta/", pag_conta())
    escrever("/entrar/", pag_entrar())
    escrever("/criar-conta/", pag_criar_conta())
    (RAIZ / "404.html").write_text(com_base(pag_404()))
    for p in posts:
        escrever(f"/blog/{p['slug']}/", pag_post(p, posts))
        urls.append(f"/blog/{p['slug']}/")
    for l in lojas:
        escrever(f"/loja/{l['slug']}/", pag_loja(l))
        urls.append(f"/loja/{l['slug']}/")
    for p in piscinas.values():
        escrever(f"/piscina/{p['id']}/", pag_piscina(p))
        urls.append(f"/piscina/{p['id']}/")
    dados_js(lojas, piscinas)
    sitemap(urls)
    print(f"pronto: {len(urls)} páginas indexáveis")


if __name__ == "__main__":
    main()
