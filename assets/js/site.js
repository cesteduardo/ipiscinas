/* iPiscinas · ilha, menu, carrosséis, galeria, orçamento, busca, mapa e lojas próximas */
(() => {
  const doc = document.documentElement;
  const BASE = doc.dataset.base || '';
  const calmo = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (t) => String(t ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const semAcento = (t) => String(t || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const SVG = (d, t = 18) => `<svg viewBox="0 0 24 24" width="${t}" height="${t}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
  const I_PIN = '<path d="M20 10c0 5-5.54 10.19-7.4 11.8a1 1 0 0 1-1.2 0C9.54 20.19 4 15 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>';
  const I_SETA = '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>';
  const I_ONDA = '<path d="M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>';

  $$('[data-ano]').forEach((el) => { el.textContent = new Date().getFullYear(); });

  /* se o redimensionador do Supabase falhar, cai para a foto original */
  const original = (u) => u.replace('/storage/v1/render/image/public/', '/storage/v1/object/public/').replace(/\?width=\d+&quality=\d+$/, '');
  addEventListener('error', (ev) => {
    const img = ev.target;
    if (!(img instanceof HTMLImageElement) || !img.src.includes('/render/image/') || img.dataset.caiu) return;
    img.dataset.caiu = '1';
    img.removeAttribute('srcset');
    img.src = original(img.src);
  }, true);

  /* ---------- ilha ---------- */
  const marcar = () => doc.classList.toggle('solido', scrollY > 40);
  marcar();
  addEventListener('scroll', marcar, { passive: true });

  const btn = $('.menu-btn');
  const gaveta = $('#gaveta');
  if (btn && gaveta) {
    const abrir = (sim) => {
      btn.setAttribute('aria-expanded', String(sim));
      btn.setAttribute('aria-label', sim ? 'Fechar menu' : 'Abrir menu');
      doc.classList.toggle('menu-aberto', sim);
    };
    btn.addEventListener('click', () => abrir(btn.getAttribute('aria-expanded') !== 'true'));
    $('.veu')?.addEventListener('click', () => abrir(false));
    gaveta.addEventListener('click', (ev) => { if (ev.target.closest('a')) abrir(false); });
    addEventListener('keydown', (ev) => { if (ev.key === 'Escape' && doc.classList.contains('menu-aberto')) { abrir(false); btn.focus(); } });
    matchMedia('(min-width: 861px)').addEventListener('change', (m) => { if (m.matches) abrir(false); });
  }

  /* ---------- carrossel infinito: no fim volta ao começo ---------- */
  const passo = (trilho, dir) => {
    const item = trilho.firstElementChild;
    if (!item) return;
    const gap = parseFloat(getComputedStyle(trilho).columnGap || getComputedStyle(trilho).gap) || 0;
    const largura = item.getBoundingClientRect().width + gap;
    const fim = trilho.scrollWidth - trilho.clientWidth;
    const comportamento = calmo ? 'auto' : 'smooth';
    if (dir > 0 && trilho.scrollLeft >= fim - 4) trilho.scrollTo({ left: 0, behavior: comportamento });
    else if (dir < 0 && trilho.scrollLeft <= 4) trilho.scrollTo({ left: fim, behavior: comportamento });
    else trilho.scrollBy({ left: dir * largura, behavior: comportamento });
  };
  $$('[data-carrossel]').forEach((c) => {
    const t = $('.carrossel__trilho', c);
    $('[data-ant]', c).addEventListener('click', () => passo(t, -1));
    $('[data-prox]', c).addEventListener('click', () => passo(t, 1));
  });

  /* ---------- galeria + visor ---------- */
  const visor = $('.visor');
  let fotosVisor = [];
  let iVisor = 0;
  const mostrar = (i) => {
    iVisor = (i + fotosVisor.length) % fotosVisor.length;
    const img = $('img', visor);
    img.src = fotosVisor[iVisor].src;
    img.alt = fotosVisor[iVisor].alt;
  };
  if (visor) {
    $('[data-fechar]', visor).addEventListener('click', () => visor.close());
    $('[data-ant]', visor).addEventListener('click', () => mostrar(iVisor - 1));
    $('[data-prox]', visor).addEventListener('click', () => mostrar(iVisor + 1));
    visor.addEventListener('click', (ev) => { if (ev.target === visor) visor.close(); });
    visor.addEventListener('keydown', (ev) => {
      if (ev.key === 'ArrowLeft') mostrar(iVisor - 1);
      if (ev.key === 'ArrowRight') mostrar(iVisor + 1);
    });
    let x0 = null;
    visor.addEventListener('touchstart', (ev) => { x0 = ev.touches[0].clientX; }, { passive: true });
    visor.addEventListener('touchend', (ev) => {
      if (x0 === null) return;
      const dx = ev.changedTouches[0].clientX - x0;
      if (Math.abs(dx) > 50) mostrar(iVisor + (dx < 0 ? 1 : -1));
      x0 = null;
    });
  }
  $$('[data-galeria]').forEach((g) => {
    const t = $('.gal__trilho', g);
    const itens = $$('.gal__item', g);
    const atual = $('[data-atual]', g);
    const indice = () => Math.round(t.scrollLeft / t.clientWidth);
    $('[data-ant]', g).addEventListener('click', () => passo(t, -1));
    $('[data-prox]', g).addEventListener('click', () => passo(t, 1));
    if (atual) t.addEventListener('scroll', () => { atual.textContent = indice() + 1; }, { passive: true });
    itens.forEach((it, i) => it.addEventListener('click', () => {
      if (!visor) return;
      fotosVisor = itens.map((x) => ({ src: x.dataset.foto, alt: $('img', x).alt }));
      visor.classList.toggle('so-uma', fotosVisor.length < 2);
      mostrar(i);
      visor.showModal();
    }));
  });

  /* ---------- formulário de orçamento (padrão GR: nome, telefone, tudo obrigatório) ---------- */
  const soNome = (v) => v.replace(/[^A-Za-zÀ-ÖØ-öø-ÿ' -]/g, '').replace(/\s{2,}/g, ' ').replace(/^\s+/, '');
  const soCidade = (v) => v.replace(/[^A-Za-zÀ-ÖØ-öø-ÿ' .-]/g, '').replace(/\s{2,}/g, ' ').replace(/^\s+/, '');
  const normFone = (bruto, colado = false) => {
    let v = String(bruto || '');
    const temMais55 = /^\s*\+\s*55/.test(v);
    v = v.replace(/\D/g, '');
    if (temMais55) v = v.slice(2);
    else if (v.startsWith('55') && v.length >= 12) v = v.slice(2); // 55 + DDD + número: o 55 é do país
    else if (colado && v.startsWith('55') && v.length > 11) v = v.slice(2);
    return v.slice(0, 11);
  };
  const mascara = (d) => {
    if (!d) return '';
    if (d.length <= 2) return `(${d}`;
    const ddd = d.slice(0, 2);
    const r = d.slice(2);
    if (d.length <= 6) return `(${ddd}) ${r}`;
    if (d.length <= 10) return `(${ddd}) ${r.slice(0, 4)}-${r.slice(4)}`;
    return `(${ddd}) ${r.slice(0, 5)}-${r.slice(5)}`;
  };
  const foneValido = (d) => /^[1-9][1-9]\d{8,9}$/.test(d) && (d.length === 10 ? /^[2-5]/.test(d[2]) : d[2] === '9');

  $$('[data-orcamento]').forEach((form) => {
    const nome = $('[data-nome]', form);
    const fone = $('[data-fone]', form);
    const cidade = $('[data-cidade]', form);
    const msg = $('textarea', form);
    const ok = form.parentElement.querySelector('.orc__ok');
    const reabrir = ok && $('[data-reabrir]', ok);

    /* o caractere inválido nem aparece; o input limpa o que escapar (autocorretor, arrastar) */
    const filtrar = (el, fn, permitido) => {
      el.addEventListener('beforeinput', (ev) => {
        if (ev.data && ev.inputType.startsWith('insert') && ev.inputType !== 'insertFromPaste' && !permitido.test(ev.data)) ev.preventDefault();
      });
      el.addEventListener('input', () => { const v = fn(el.value); if (v !== el.value) el.value = v; });
    };
    filtrar(nome, soNome, /^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$/);
    filtrar(cidade, soCidade, /^[A-Za-zÀ-ÖØ-öø-ÿ' .-]+$/);
    fone.addEventListener('beforeinput', (ev) => {
      if (ev.inputType === 'insertText' && ev.data && /\D/.test(ev.data)) ev.preventDefault();
      const dig = fone.value.replace(/\D/g, '');
      if (ev.inputType === 'insertText' && fone.selectionStart === fone.selectionEnd && dig.length >= 11 && !(dig.length === 11 && dig.startsWith('55'))) ev.preventDefault();
    });
    fone.addEventListener('input', () => { fone.value = mascara(normFone(fone.value)); });
    fone.addEventListener('paste', (ev) => {
      ev.preventDefault();
      fone.value = mascara(normFone((ev.clipboardData || window.clipboardData).getData('text'), true));
      fone.dispatchEvent(new Event('change'));
    });
    nome.addEventListener('paste', (ev) => {
      ev.preventDefault();
      nome.value = soNome((ev.clipboardData || window.clipboardData).getData('text')).slice(0, 80);
    });
    cidade.addEventListener('paste', (ev) => {
      ev.preventDefault();
      cidade.value = soCidade((ev.clipboardData || window.clipboardData).getData('text')).slice(0, 60);
    });

    const erro = (el, texto) => {
      const campo = el.closest('.campo');
      campo.classList.toggle('tem-erro', !!texto);
      $('.erro', campo).textContent = texto || '';
      el.setAttribute('aria-invalid', texto ? 'true' : 'false');
      return !texto;
    };
    const checar = () => {
      const n = nome.value.trim();
      const d = normFone(fone.value);
      const c = cidade.value.trim();
      const m = msg.value.trim();
      const r = [
        [nome, !n ? 'Digite seu nome.' : n.replace(/[^A-Za-zÀ-ÖØ-öø-ÿ]/g, '').length < 2 || !/\s\S/.test(n) ? 'Digite nome e sobrenome.' : ''],
        [fone, !d ? 'Digite seu WhatsApp com DDD.' : !foneValido(d) ? 'Confira o número: DDD + celular, como (17) 99999-9999.' : ''],
        [cidade, !c ? 'Digite sua cidade.' : c.replace(/[^A-Za-zÀ-ÖØ-öø-ÿ]/g, '').length < 2 ? 'Digite o nome da cidade.' : ''],
        [msg, !m ? 'Conte o que você procura.' : m.length < 5 ? 'Escreva um pouco mais.' : ''],
      ];
      r.forEach(([el, t]) => erro(el, t));
      return r.find(([, t]) => t)?.[0] || null;
    };
    [nome, fone, cidade, msg].forEach((el) => el.addEventListener('blur', () => { if (el.closest('.campo').classList.contains('tem-erro')) checar(); }));

    form.addEventListener('submit', (ev) => {
      ev.preventDefault();
      const ruim = checar();
      if (ruim) { ruim.focus(); return; }
      const d = normFone(fone.value);
      const modelo = form.dataset.modelo;
      const texto = [
        `Olá, *${form.dataset.loja}*! Vi vocês no iPiscinas e quero um orçamento.`,
        '',
        '*Interesse*',
        `• ${modelo ? `Piscina ${modelo}` : 'Atendimento da loja'}`,
        '',
        '*Meus dados*',
        `• Nome: ${nome.value.trim()}`,
        `• WhatsApp: ${mascara(d)}`,
        `• Cidade: ${cidade.value.trim()}`,
        '',
        '*Mensagem*',
        msg.value.trim(),
      ].join('\n');
      const url = `https://wa.me/${form.dataset.zap}?text=${encodeURIComponent(texto)}`;
      window.open(url, '_blank', 'noopener');
      if (ok) {
        reabrir.href = url;
        form.hidden = true;
        ok.hidden = false;
        $('h3', ok).setAttribute('tabindex', '-1');
        $('h3', ok).focus();
      }
    });
  });

  /* ---------- dados das lojas (busca, mapa, perto de mim) ---------- */
  let dadosP = null;
  const dados = () => (dadosP ||= fetch(`${BASE}/dados/busca.json`).then((r) => r.json()));
  const seloHTML = (l, cls = 'selo') => (l.l
    ? `<span class="${cls}"><img src="${esc(l.l)}" alt="" width="56" height="56" loading="lazy" decoding="async"></span>`
    : `<span class="${cls} ${cls}--letras" aria-hidden="true">${esc(l.i)}</span>`);
  const lojaHTML = (l, extra = '') => `<a class="cl" href="${BASE}/loja/${esc(l.s)}/" data-s="${esc(l.s)}">
    ${seloHTML(l)}
    <span class="cl__txt"><strong>${esc(l.n)}</strong>
      ${l.c || extra ? `<span class="cl__cid">${SVG(I_PIN, 14)}${esc([l.c, extra].filter(Boolean).join(' · '))}</span>` : ''}
      ${l.q ? `<span class="cl__cont">${esc(l.q)}</span>` : ''}</span>
    <span class="seta-bola" aria-hidden="true">${SVG(I_SETA, 16)}</span></a>`;
  const piscinaHTML = (p) => `<a class="cp" href="${BASE}/piscina/${esc(p.id)}/">
    <span class="cp__foto">${p.f ? `<img src="${esc(p.f2)}" srcset="${esc(p.f)} 400w, ${esc(p.f2)} 640w" sizes="(max-width: 600px) 46vw, 260px" alt="Piscina ${esc(p.n)}, de ${esc(p.ln)}" width="400" height="500" loading="lazy" decoding="async">` : `<span class="cp__vazio">${SVG(I_ONDA, 40)}</span>`}${p.t ? `<span class="tag">${esc(p.t)}</span>` : ''}</span>
    <span class="cp__txt"><span class="cp__loja">${esc(p.ln)}</span><strong class="cp__nome">${esc(p.n)}</strong><span class="cp__preco">${esc(p.pr || 'Preço sob consulta')}</span></span></a>`;
  const km = (a, b) => {
    const R = 6371;
    const r = Math.PI / 180;
    const dLat = (b[0] - a[0]) * r;
    const dLng = (b[1] - a[1]) * r;
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin(dLng / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  };
  const fmtKm = (d) => (d < 1 ? `${Math.round(d * 1000)} m` : `${d < 10 ? d.toFixed(1).replace('.', ',') : Math.round(d)} km`);
  const localizar = () => new Promise((ok, falha) => {
    if (!navigator.geolocation) { falha(new Error('sem geolocalização')); return; }
    navigator.geolocation.getCurrentPosition((p) => ok([p.coords.latitude, p.coords.longitude]), falha, { enableHighAccuracy: false, timeout: 12000, maximumAge: 600000 });
  });

  /* início: lojas próximas */
  const perto = $('[data-perto]');
  if (perto) {
    const b = $('[data-localizar]', perto);
    const sub = $('[data-perto-sub]', perto);
    const lista = $('[data-perto-lista]', perto);
    b.addEventListener('click', async () => {
      b.disabled = true;
      sub.textContent = 'Buscando sua localização…';
      try {
        const [eu, d] = await Promise.all([localizar(), dados()]);
        const ord = d.lojas.filter((l) => l.g).map((l) => ({ l, d: km(eu, l.g) })).sort((a, z) => a.d - z.d).slice(0, 8);
        lista.innerHTML = ord.map(({ l, d: dist }) => lojaHTML(l, `a ${fmtKm(dist)}`)).join('');
        sub.textContent = 'As mais perto de você, por distância.';
        b.hidden = true;
      } catch (err) {
        sub.textContent = 'Não deu para usar sua localização. Veja as lojas no mapa ou busque pela cidade.';
        b.disabled = false;
      }
    });
  }

  /* blog: filtro por categoria */
  const filtros = $('[data-filtros]');
  if (filtros) {
    filtros.addEventListener('click', (ev) => {
      const c = ev.target.closest('[data-filtro]');
      if (!c) return;
      $$('[data-filtro]', filtros).forEach((x) => x.setAttribute('aria-pressed', String(x === c)));
      $$('[data-posts] > div').forEach((p) => { p.hidden = !!c.dataset.filtro && p.dataset.cat !== c.dataset.filtro; });
    });
  }

  /* ---------- página de busca ---------- */
  const pagBusca = $('[data-buscar]');
  if (pagBusca) {
    const q = $('#q');
    const uf = $('#uf');
    const resumo = $('[data-resumo]');
    const listaL = $('[data-lista-lojas]');
    const listaP = $('[data-lista-piscinas]');
    const blocoL = $('[data-bloco="lojas"]');
    const blocoP = $('[data-bloco="piscinas"]');
    const maisL = $('[data-mais="lojas"]');
    const maisP = $('[data-mais="piscinas"]');
    const vazio = $('[data-vazio]');
    const params = new URLSearchParams(location.search);
    const estado = { q: params.get('q') || '', uf: params.get('uf') || '', cat: params.get('cat') || '', ver: params.get('ver') || 'tudo', nL: 20, nP: 12 };
    q.value = estado.q;
    if ([...uf.options].some((o) => o.value === estado.uf)) uf.value = estado.uf;
    const marcarUI = () => {
      $$('[data-ver]').forEach((x) => x.setAttribute('aria-pressed', String(x.dataset.ver === estado.ver)));
      $$('[data-cat]').forEach((x) => x.setAttribute('aria-pressed', String(x.dataset.cat === estado.cat)));
    };
    const url = () => {
      const p = new URLSearchParams();
      if (estado.q) p.set('q', estado.q);
      if (estado.uf) p.set('uf', estado.uf);
      if (estado.cat) p.set('cat', estado.cat);
      if (estado.ver !== 'tudo') p.set('ver', estado.ver);
      history.replaceState(null, '', `${location.pathname}${p.toString() ? `?${p}` : ''}`);
    };
    const render = (d) => {
      const termos = semAcento(estado.q).split(/\s+/).filter(Boolean);
      const bate = (b) => termos.every((t) => b.includes(t));
      const L = d.lojas.filter((l) => bate(l.b) && (!estado.uf || l.uf === estado.uf) && (!estado.cat || l.k.includes(estado.cat)));
      const P = d.piscinas.filter((p) => bate(p.b) && (!estado.uf || p.uf === estado.uf) && (!estado.cat || estado.cat === 'piscinas'));
      const verL = estado.ver !== 'piscinas';
      const verP = estado.ver !== 'lojas' && (!estado.cat || estado.cat === 'piscinas');
      blocoL.hidden = !verL || !L.length;
      blocoP.hidden = !verP || !P.length;
      listaL.innerHTML = L.slice(0, estado.nL).map((l) => lojaHTML(l)).join('');
      listaP.innerHTML = P.slice(0, estado.nP).map(piscinaHTML).join('');
      maisL.hidden = L.length <= estado.nL;
      maisP.hidden = P.length <= estado.nP;
      const partes = [];
      if (verL) partes.push(`${L.length} ${L.length === 1 ? 'loja' : 'lojas'}`);
      if (verP) partes.push(`${P.length} ${P.length === 1 ? 'piscina' : 'piscinas'}`);
      resumo.textContent = partes.join(' e ') + (estado.q ? ` para “${estado.q}”` : '');
      vazio.hidden = !((verL ? L.length : 0) + (verP ? P.length : 0) === 0);
    };
    let t = null;
    const atualizar = () => { marcarUI(); url(); dados().then(render).catch(() => { resumo.textContent = 'Não foi possível carregar a busca agora. Tente de novo em instantes.'; }); };
    q.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => { estado.q = q.value.trim(); estado.nL = 20; estado.nP = 12; atualizar(); }, 180); });
    $('[data-busca-form]').addEventListener('submit', (ev) => { ev.preventDefault(); estado.q = q.value.trim(); atualizar(); q.blur(); });
    uf.addEventListener('change', () => { estado.uf = uf.value; atualizar(); });
    $$('[data-ver]').forEach((x) => x.addEventListener('click', () => { estado.ver = x.dataset.ver; atualizar(); }));
    $$('[data-cat]').forEach((x) => x.addEventListener('click', () => { estado.cat = x.dataset.cat; if (estado.cat && estado.cat !== 'piscinas' && estado.ver === 'piscinas') estado.ver = 'tudo'; atualizar(); }));
    maisL.addEventListener('click', () => { estado.nL += 20; dados().then(render); });
    maisP.addEventListener('click', () => { estado.nP += 12; dados().then(render); });
    atualizar();
  }

  /* ---------- mapa ---------- */
  const pagMapa = $('[data-mapa]');
  if (pagMapa) {
    const iniciar = async () => {
      const d = await dados();
      const L = window.L;
      const mapa = L.map('mapa', { scrollWheelZoom: true, zoomControl: true }).setView([-15.8, -50.5], 4);
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>',
      }).addTo(mapa);
      const pino = L.divIcon({ className: '', html: '<span class="pino"></span>', iconSize: [16, 16], iconAnchor: [8, 8] });
      const lojas = d.lojas.filter((l) => l.g);
      const marcadores = new Map();
      lojas.forEach((l) => {
        const m = L.marker(l.g, { icon: pino, title: l.n, keyboard: true }).addTo(mapa);
        m.bindPopup(`<div class="pop">${seloHTML(l)}<div><strong>${esc(l.n)}</strong>${l.c ? `<span>${esc(l.c)}</span><br>` : ''}<a class="link" href="${BASE}/loja/${esc(l.s)}/">Ver loja ${SVG(I_SETA, 14)}</a></div></div>`);
        marcadores.set(l.s, m);
      });
      if (lojas.length) mapa.fitBounds(L.latLngBounds(lojas.map((l) => l.g)), { padding: [30, 30], maxZoom: 9 });
      const lista = $('[data-mapa-lista]');
      const conta = $('[data-mapa-conta]');
      let eu = null;
      const listar = () => {
        const b = mapa.getBounds();
        let vis = lojas.filter((l) => b.contains(l.g));
        if (eu) vis = vis.map((l) => ({ ...l, dist: km(eu, l.g) })).sort((a, z) => a.dist - z.dist);
        conta.textContent = `${vis.length} ${vis.length === 1 ? 'loja' : 'lojas'} nesta área${vis.length > 60 ? ' · aproxime para ver menos' : ''}`;
        lista.innerHTML = vis.slice(0, 60).map((l) => lojaHTML(l, l.dist != null ? `a ${fmtKm(l.dist)}` : '')).join('');
      };
      mapa.on('moveend', listar);
      listar();
      lista.addEventListener('pointerover', (ev) => {
        const a = ev.target.closest('[data-s]');
        if (!a || !matchMedia('(hover: hover)').matches) return;
        const m = marcadores.get(a.dataset.s);
        if (m && !m.isPopupOpen()) m.openPopup();
      });
      const b = $('[data-localizar]', pagMapa);
      b.addEventListener('click', async () => {
        b.disabled = true;
        try {
          eu = await localizar();
          L.marker(eu, { icon: L.divIcon({ className: '', html: '<span class="pino pino--eu"></span>', iconSize: [18, 18], iconAnchor: [9, 9] }), title: 'Você está aqui' }).addTo(mapa);
          mapa.setView(eu, 10);
        } catch (err) {
          conta.textContent = 'Não deu para usar sua localização. Arraste o mapa até a sua cidade.';
        }
        b.disabled = false;
      });
    };
    const esperar = () => (window.L ? iniciar() : setTimeout(esperar, 60));
    esperar();
  }

  /* ---------- entradas suaves ---------- */
  if (!calmo && 'IntersectionObserver' in window) {
    const alvos = $$('main .sec .cab, main .cats, main .carrossel, main .lojas:not([data-lista-lojas]):not([data-mapa-lista]), main .faixa, main .posts, main .app');
    alvos.forEach((el) => el.classList.add('surge'));
    const io = new IntersectionObserver((itens) => {
      itens.filter((it) => it.isIntersecting).forEach((it, k) => {
        it.target.style.setProperty('--d', `${Math.min(k, 4) * 80}ms`);
        it.target.classList.add('visto');
        io.unobserve(it.target);
      });
    }, { rootMargin: '0px 0px -8% 0px' });
    alvos.forEach((el) => io.observe(el));
  }
})();
