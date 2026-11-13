# iPiscinas · site reformulado

Site estático gerado a partir da API pública do iPiscinas (`api.ipiscinas.com.br`).

```
python3 _fonte/build.py                      # gera as páginas (usa o cache em _fonte/cache)
python3 _fonte/build.py --fresco             # baixa tudo de novo da API
python3 _fonte/build.py --base=/ipiscinas    # prévia no GitHub Pages (subpasta + noindex)
python3 -m http.server 4860                  # ver em http://localhost:4860
```

- Páginas: início, `/buscar/`, `/mapa/`, `/blog/`, `/loja/<slug>/`, `/piscina/<id>/`, `/blog/<slug>/`, `/entrar/`, `/criar-conta/`, `/conta/`, `404.html`.
- Identidade: topo colado que se solta em pílula ao rolar, piso de pastilhas no degradê, raia flutuante (corda de boias) como divisor e fotos do topo com moldura de borda de piscina.
- Blog: a notícia mais recente abre a página e a seção do início.
- Login e cadastro falam com a API real e guardam a sessão com as mesmas chaves do app.
- CSS e JS em `assets/` são editados direto. A busca e o mapa leem `dados/busca.json`, gerado pelo build.
- Visual no molde do GR Vagas, nas cores do logo do iPiscinas. Fonte Inter.
- Orçamento: formulário validado (padrão GR Brands) que abre o WhatsApp da loja com a mensagem pronta.
- `_fonte/cache` guarda a resposta da API, com e-mails de lojistas, e fica FORA do git.
- Pendências em `seo/pendencias.md`.
