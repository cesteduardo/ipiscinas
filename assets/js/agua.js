/* iPiscinas · ondas leves no rodapé
   O fundo do rodapé vira o piso de pastilhas visto através da água: ondas lentas e cáusticas,
   no shader do WaterRippleImage (adaptado do React para JS puro). O canvas fica atrás do
   conteúdo com opacidade baixa (.agua.pronta no CSS). Sem WebGL ou com "menos movimento",
   o rodapé fica liso como antes. Pausa quando o rodapé sai da tela ou a aba é escondida. */
(() => {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const caixa = document.querySelector('[data-agua]');
  if (!caixa) return;

  const VERT = `
attribute vec2 a_pos;
varying vec2 vUv;
void main() {
  vUv = .5 * (a_pos + 1.);
  gl_Position = vec4(a_pos, 0., 1.);
}`;

  const FRAG = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
varying vec2 vUv;
uniform sampler2D u_piso;
uniform float u_tempo;
uniform vec2 u_tam;      /* tamanho do rodapé em px de CSS */
uniform float u_ladrilho; /* lado da textura de pastilhas em px de CSS */
uniform float u_azul;
uniform float u_escala;
uniform float u_luz;
uniform float u_dist_sup;
uniform float u_dist_agua;

vec3 mod289(vec3 x) { return x - floor(x * (1. / 289.)) * 289.; }
vec2 mod289(vec2 x) { return x - floor(x * (1. / 289.)) * 289.; }
vec3 permute(vec3 x) { return mod289(((x * 34.) + 1.) * x); }
float snoise(vec2 v) {
  const vec4 C = vec4(.211324865405187, .366025403784439, -.577350269189626, .024390243902439);
  vec2 i = floor(v + dot(v, C.yy));
  vec2 x0 = v - i + dot(i, C.xx);
  vec2 i1 = (x0.x > x0.y) ? vec2(1., 0.) : vec2(0., 1.);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod289(i);
  vec3 p = permute(permute(i.y + vec3(0., i1.y, 1.)) + i.x + vec3(0., i1.x, 1.));
  vec3 m = max(.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.);
  m = m * m; m = m * m;
  vec3 x = 2. * fract(p * C.www) - 1.;
  vec3 h = abs(x) - .5;
  vec3 ox = floor(x + .5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - .85373472095314 * (a0 * a0 + h * h);
  vec3 g;
  g.x = a0.x * x0.x + h.x * x0.y;
  g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130. * dot(m, g);
}
mat2 gira(float r) { return mat2(cos(r), sin(r), -sin(r), cos(r)); }

float superficie(vec2 uv, float t, float escala) {
  vec2 n = vec2(.1), N = vec2(.1);
  mat2 m = gira(.5);
  for (int j = 0; j < 10; j++) {
    uv *= m; n *= m;
    float fj = float(j);
    vec2 q = uv * escala + fj + n + (.5 + .5 * fj) * (mod(fj, 2.) - 1.) * t;
    n += sin(q);
    N += cos(q) / escala;
    escala *= 1.2;
  }
  return N.x + N.y + .1;
}

void main() {
  /* coordenadas da onda em unidades de 300 px: o tamanho da onda não depende do tamanho do rodapé */
  vec2 px = vec2(vUv.x, 1. - vUv.y) * u_tam;
  vec2 uv = px / 300.;
  float t = u_tempo;

  float onda = snoise((.3 + .1 * sin(t)) * uv + vec2(0., .2 * t));
  float sup = superficie(2. * uv + onda * .2, t, u_escala);
  sup = pow(max(sup, 0.), 2.);

  /* as pastilhas se repetem; a água desloca o desenho delas */
  vec2 puv = px / u_ladrilho;
  puv += u_dist_agua * onda + u_dist_sup * sup;

  vec3 cor = texture2D(u_piso, puv).rgb;
  cor *= 1. + u_luz * sup;
  cor += u_luz * vec3(1. - u_azul, 1., 1.) * sup;
  gl_FragColor = vec4(min(cor, 1.), 1.);
}`;

  const PARAMS = { azul: 0.4, escala: 7, luz: 0.3, distSup: 0.05, distAgua: 0.04 };
  const LADO = 128;        // lado da textura em px de CSS (4 × 4 pastilhas de 32 px)
  const RES = 0.6;         // a onda é macia: desenha em resolução reduzida e o CSS amplia
  const MAX_W = 1400;

  /* piso de pastilhas para o rodapé azul: o canvas entra em "screen", então o escuro some no azul
     e só o rejunte e a luz da água clareiam; tamanho potência de 2 para repetir */
  const piso = () => {
    const c = document.createElement('canvas');
    c.width = c.height = 256;
    const x = c.getContext('2d');
    x.fillStyle = '#123c5c';
    x.fillRect(0, 0, 256, 256);
    const tons = ['#04121f', '#020c16', '#061827', '#010910', '#05141f', '#030f1a', '#020b14', '#06172a'];
    const n = 4, l = 256 / n, r = 10;
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        x.fillStyle = tons[(i * 3 + j * 5 + ((i * j) % 3)) % tons.length];
        x.beginPath();
        x.roundRect(i * l + 3, j * l + 3, l - 6, l - 6, r);
        x.fill();
      }
    }
    return c;
  };

  const shader = (gl, tipo, src) => {
    const s = gl.createShader(tipo);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) || 'shader');
    return s;
  };

  const montar = () => {
    const canvas = document.createElement('canvas');
    canvas.className = 'agua';
    canvas.setAttribute('aria-hidden', 'true');
    const gl = canvas.getContext('webgl', { alpha: false, antialias: false, powerPreference: 'low-power' });
    if (!gl || !CanvasRenderingContext2D.prototype.roundRect) return;

    let prog;
    try {
      prog = gl.createProgram();
      gl.attachShader(prog, shader(gl, gl.VERTEX_SHADER, VERT));
      gl.attachShader(prog, shader(gl, gl.FRAGMENT_SHADER, FRAG));
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog) || 'link');
    } catch (err) {
      console.warn('agua:', err);
      return;
    }
    gl.useProgram(prog);
    const u = (n) => gl.getUniformLocation(prog, n);
    const uTempo = u('u_tempo'), uTam = u('u_tam');
    gl.uniform1f(u('u_azul'), PARAMS.azul);
    gl.uniform1f(u('u_escala'), PARAMS.escala);
    gl.uniform1f(u('u_luz'), PARAMS.luz);
    gl.uniform1f(u('u_dist_sup'), PARAMS.distSup);
    gl.uniform1f(u('u_dist_agua'), PARAMS.distAgua);
    gl.uniform1f(u('u_ladrilho'), LADO);
    gl.uniform1i(u('u_piso'), 0);

    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const pos = gl.getAttribLocation(prog, 'a_pos');
    gl.enableVertexAttribArray(pos);
    gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0);

    const tex = gl.createTexture();
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, piso());
    gl.generateMipmap(gl.TEXTURE_2D);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);

    let visivel = false, quadro = 0, ultimo = 0, relogio = Math.random() * 40;

    const medir = () => {
      const cw = caixa.clientWidth, ch = caixa.clientHeight;
      if (!cw || !ch) return;
      const k = Math.min(RES, MAX_W / cw);
      const w = Math.round(cw * k), h = Math.round(ch * k);
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
      gl.viewport(0, 0, w, h);
      gl.uniform2f(uTam, cw, ch);
    };
    const desenhar = (agora) => {
      const dt = Math.min((agora - (ultimo || agora)) / 1000, 0.1);
      ultimo = agora;
      relogio += dt * 2; // mesmo ritmo do original (.002 por ms)
      if (relogio > 4000) relogio -= 4000;
      gl.uniform1f(uTempo, relogio);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    };
    const loop = (agora) => {
      quadro = 0;
      if (!visivel || document.hidden) { ultimo = 0; return; }
      desenhar(agora);
      quadro = requestAnimationFrame(loop);
    };
    const andar = () => { if (!quadro && visivel && !document.hidden) quadro = requestAnimationFrame(loop); };

    caixa.prepend(canvas);
    medir();
    desenhar(performance.now());
    requestAnimationFrame(() => canvas.classList.add('pronta'));

    new IntersectionObserver((es) => { visivel = es[0].isIntersecting; andar(); }, { rootMargin: '100px' }).observe(caixa);
    new ResizeObserver(() => { medir(); if (!quadro) desenhar(performance.now()); }).observe(caixa);
    document.addEventListener('visibilitychange', andar);
    canvas.addEventListener('webglcontextlost', (ev) => { ev.preventDefault(); canvas.remove(); });
  };

  // o rodapé está longe do topo: monta quando o navegador estiver livre
  if ('requestIdleCallback' in window) requestIdleCallback(montar, { timeout: 2000 });
  else setTimeout(montar, 600);
})();
