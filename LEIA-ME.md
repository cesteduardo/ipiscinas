# iPiscinas · site reformulado

Site estático gerado a partir da API pública do iPiscinas (`api.ipiscinas.com.br`).

```
python3 _fonte/build.py                      # gera as páginas (usa o cache em _fonte/cache)
python3 _fonte/build.py --fresco             # baixa tudo de novo da API
python3 _fonte/build.py --base=/ipiscinas    # prévia no GitHub Pages (subpasta + noindex)
python3 -m http.server 4860                  # ver em http://localhost:4860
```

- Páginas: início, `/buscar/`, `/mapa/`, `/blog/`, `/loja/<slug>/`, `/piscina/<id>/`, `/blog/<slug>/`, `/entrar/`, `/criar-conta/`, `/conta/`, `404.html`.
- Identidade: no computador, topo colado que se solta em pílula ao rolar; no celular, topo fixo e centralizado (o menu é a barra de abas). Piso de pastilhas no degradê, raia flutuante (corda de boias) de ponta a ponta da tela, correndo devagar, e vitrine no topo com uma foto grande e duas menores.
- Hover: um sistema só, no fim do `site.css` ("a luz da água segue o cursor"). Luz azul rala por dentro e borda que acende perto do mouse; título azul-forte; cartão sobe 4px com sombra azulada. O JS só passa `--mx`/`--my`.
- Vidro líquido: no computador, uma gota de vidro corre pelo menu do topo (segue o mouse, com mola). No celular, a gaveta virou uma barra de abas de vidro embaixo (Início, Buscar, Mapa, Blog, Conta): a gota escorre até a aba, o ícone faz um gesto curto e a página troca. Tudo em `assets/js/site.js` (`liquido`).
- Ondas no rodapé: `assets/js/agua.js` (shader do WaterRippleImage) desenha um piso de pastilhas visto através da água atrás do rodapé `[data-agua]`, com opacidade .3. As fotos do topo não têm animação. Desliga com "menos movimento" e pausa fora da tela.
- Blog: a notícia mais recente abre a página e a seção do início.
- Login e cadastro falam com a API real e guardam a sessão com as mesmas chaves do app.
- CSS e JS em `assets/` são editados direto. A busca e o mapa leem `dados/busca.json`, gerado pelo build.
- Visual no molde do GR Vagas, nas cores do logo do iPiscinas. Fonte Inter.
- Orçamento: formulário validado (padrão GR Brands) que abre o WhatsApp da loja com a mensagem pronta.
- `_fonte/cache` guarda a resposta da API, com e-mails de lojistas, e fica FORA do git.
- Pendências em `seo/pendencias.md`.
