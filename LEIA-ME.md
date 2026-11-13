# iPiscinas · site reformulado

Site estático gerado a partir da API pública do iPiscinas (`api.ipiscinas.com.br`).

```
python3 _fonte/build.py                      # gera as páginas (usa o cache em _fonte/cache)
python3 _fonte/build.py --fresco             # baixa tudo de novo da API
python3 _fonte/build.py --base=/ipiscinas    # prévia no GitHub Pages (subpasta + noindex)
python3 -m http.server 4860                  # ver em http://localhost:4860
```

- Páginas: início, `/buscar/`, `/mapa/`, `/blog/`, `/loja/<slug>/`, `/piscina/<id>/`, `/blog/<slug>/`, `/conta/`, `404.html`.
- CSS e JS em `assets/` são editados direto. A busca e o mapa leem `dados/busca.json`, gerado pelo build.
- Visual no molde do GR Vagas, nas cores do logo do iPiscinas. Fonte Inter.
- Orçamento: formulário validado (padrão GR Brands) que abre o WhatsApp da loja com a mensagem pronta.
- `_fonte/cache` guarda a resposta da API, com e-mails de lojistas, e fica FORA do git.
- Pendências em `seo/pendencias.md`.
