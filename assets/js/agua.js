/* iPiscinas · água sobre as fotos do topo
   A foto fica vista através da superfície de uma piscina: ondas lentas, cáusticas de luz
   e um balanço mais forte quando o mouse passa. Adaptado do WaterRippleImage (React) para
   JS puro: cada foto [data-agua] ganha um canvas WebGL por cima da <img>, que continua
   lá embaixo como reserva (sem WebGL, com "menos movimento" ou se a textura falhar). */
(() => {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const fotos = [...document.querySelectorAll('[data-agua]')];
  if (!fotos.length) return;

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
uniform sampler2D u_img;
uniform float u_tempo;
uniform float u_ratio;
uniform float u_img_ratio;
uniform float u_azul;
uniform float u_escala;
uniform float u_luz;
uniform float u_dist_sup;
uniform float u_dist_agua;
uniform float u_forca;

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
  vec2 uv = vUv;
  uv.y = 1. - uv.y;
  uv.x *= u_ratio;
  float t = u_tempo;

  float onda = snoise((.3 + .1 * sin(t)) * uv + vec2(0., .2 * t));
  float sup = superficie(2. * uv + onda * .2, t, u_escala);
  sup *= pow(max(uv.y, 0.), .3);
  sup = pow(sup, 2.);

  /* cobre a moldura como object-fit: cover, com um zoom leve para a onda nunca mostrar a borda */
  vec2 iuv = vUv - .5;
  if (u_ratio > u_img_ratio) iuv.y *= u_img_ratio / u_ratio;
  else iuv.x *= u_ratio / u_img_ratio;
  iuv *= .93;
  iuv += .5;
  iuv.y = 1. - iuv.y;
  iuv += u_forca * (u_dist_agua * onda + u_dist_sup * sup);
  iuv = clamp(iuv, .001, .999);

  vec4 img = texture2D(u_img, iuv);
  float luz = u_luz * u_forca;
  vec3 cor = img.rgb * (1. + luz * sup);
  cor += luz * vec3(1. - u_azul, 1., 1.) * sup;
  gl_FragColor = vec4(min(cor, 1.), 1.);
}`;

  const PARAMS = { azul: 0.45, escala: 7, luz: 0.12, distSup: 0.028, distAgua: 0.016 };
  const DPR = Math.min(devicePixelRatio || 1, 1.5);

  const shader = (gl, tipo, src) => {
    const s = gl.createShader(tipo);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) || 'shader');
    return s;
  };

  const montar = (caixa) => {
    const img = caixa.querySelector('img');
    if (!img) return;
    const canvas = document.createElement('canvas');
    canvas.className = 'agua';
    canvas.setAttribute('aria-hidden', 'true');
    const gl = canvas.getContext('webgl', { alpha: false, antialias: false, premultipliedAlpha: false, powerPreference: 'low-power' });
    if (!gl) return;

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
    const U = {
      tempo: u('u_tempo'), ratio: u('u_ratio'), imgRatio: u('u_img_ratio'), forca: u('u_forca'),
    };
    gl.uniform1f(u('u_azul'), PARAMS.azul);
    gl.uniform1f(u('u_escala'), PARAMS.escala);
    gl.uniform1f(u('u_luz'), PARAMS.luz);
    gl.uniform1f(u('u_dist_sup'), PARAMS.distSup);
    gl.uniform1f(u('u_dist_agua'), PARAMS.distAgua);
    gl.uniform1i(u('u_img'), 0);

    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const pos = gl.getAttribLocation(prog, 'a_pos');
    gl.enableVertexAttribArray(pos);
    gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0);

    const tex = gl.createTexture();
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

    let pronto = false, visivel = false, quadro = 0, ultimo = 0, relogio = Math.random() * 40;
    let forca = 1, alvo = 1;

    const medir = () => {
      const w = Math.round(caixa.clientWidth * DPR), h = Math.round(caixa.clientHeight * DPR);
      if (!w || !h) return;
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
      gl.viewport(0, 0, w, h);
      gl.uniform1f(U.ratio, w / h);
    };

    const textura = () => {
      try {
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
      } catch (err) {
        // foto sem CORS deixa o canvas sujo: fica só a <img>
        console.warn('agua: textura recusada', err);
        canvas.remove();
        return;
      }
      gl.uniform1f(U.imgRatio, img.naturalWidth / img.naturalHeight);
      pronto = true;
      medir();
      desenhar(performance.now());
      requestAnimationFrame(() => canvas.classList.add('pronta'));
      andar();
    };

    function desenhar(agora) {
      const dt = Math.min((agora - (ultimo || agora)) / 1000, 0.1);
      ultimo = agora;
      relogio += dt * 2; // mesmo ritmo do original (.002 por ms)
      if (relogio > 4000) relogio -= 4000;
      // força do balanço anda por tempo, não por quadro
      forca += (alvo - forca) * (1 - Math.exp(-dt * 4));
      gl.uniform1f(U.tempo, relogio);
      gl.uniform1f(U.forca, forca);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }
    const loop = (agora) => {
      quadro = 0;
      if (!pronto || !visivel || document.hidden) { ultimo = 0; return; }
      desenhar(agora);
      quadro = requestAnimationFrame(loop);
    };
    const andar = () => { if (!quadro && pronto && visivel && !document.hidden) quadro = requestAnimationFrame(loop); };

    new IntersectionObserver((es) => { visivel = es[0].isIntersecting; andar(); }, { rootMargin: '80px' }).observe(caixa);
    new ResizeObserver(() => { if (pronto) { medir(); if (!quadro) desenhar(performance.now()); } }).observe(caixa);
    document.addEventListener('visibilitychange', andar);
    const raia = caixa.closest('a') || caixa;
    raia.addEventListener('pointerenter', () => { alvo = 1.9; });
    raia.addEventListener('pointerleave', () => { alvo = 1; });
    canvas.addEventListener('webglcontextlost', (ev) => { ev.preventDefault(); pronto = false; canvas.remove(); });

    img.after(canvas);
    const usar = () => (img.naturalWidth ? textura() : null);
    if (img.complete && img.naturalWidth) usar();
    else img.addEventListener('load', usar, { once: true });
  };

  // as fotos já estão no navegador; o WebGL entra depois do primeiro desenho da página
  const iniciar = () => fotos.forEach(montar);
  if ('requestIdleCallback' in window) requestIdleCallback(iniciar, { timeout: 1200 });
  else setTimeout(iniciar, 300);
})();
