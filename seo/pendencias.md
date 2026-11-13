# Pendências

1. **WhatsApp do iPiscinas:** o número no site atual é `(17) 99612-3456`, que parece de teste (sequência). Mantive igual; confirmar o número real em `ZAP_IPISCINAS` no `_fonte/build.py`.
2. **Login e cadastro:** as páginas `/entrar/` e `/criar-conta/` agora são do site novo e usam a API real (`/auth/login`, `/auth/register`, `/auth/me`, `/auth/logout`), com as mesmas chaves de sessão do app (`ipiscinas-cliente-token`). No domínio final, a sessão é a mesma do app. **Atenção:** quem se cadastrar pela prévia do GitHub cria conta de verdade no sistema deles. O telefone virou obrigatório (padrão GR: sem campo opcional) e vai no formato `(17) 99999-9999`. "Cadastre aqui", para lojistas, continua indo para `/cadastrar-loja` do app (`APP` no build), assim como o orçamento interno (`/orcamento/novo`).
3. **Orçamento:** no site novo o pedido vai pelo WhatsApp da loja, sem passar pelo sistema de orçamentos do app. Confirmar se é isso que querem ou se o formulário deve gravar na API (precisa de endpoint público ou token).
4. **Atualização dos dados:** o site é uma fotografia da API no momento do build. Rodar `python3 _fonte/build.py --fresco` todo dia (cron ou GitHub Action) para lojas e modelos novos aparecerem.
5. **Coordenadas:** 346 lojas têm endereço, mas só 34 têm latitude/longitude válidas; o resto está com 0,0 e fica fora do mapa.
6. **Cidade:** 30 lojas não têm cidade nem no cadastro nem no endereço.
7. **Destaque de loja suspensa:** o modelo "Enseada" aparece em destaque no site atual, mas a loja dele está SUSPENSA na API. O site novo filtra lojas não ativas.
8. **Imagem de compartilhamento:** `assets/img/og.jpg` foi montada com uma foto real da Solário Piscinas Rio Preto e o logo. Trocar se houver arte oficial 1200×630.
9. **Fotos:** vêm pelo redimensionador do Supabase deles (`/render/image/`). Se o plano desligar esse recurso, o JS volta para a foto original, que chega a 6 MB.
10. **Lighthouse:** não rodei, porque não há Lighthouse instalado nesta máquina. Rodar no PageSpeed Insights depois de publicar no domínio.
