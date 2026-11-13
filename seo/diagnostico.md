# Diagnóstico

- **Segmento:** marketplace de piscinas (lojas de piscina de fibra, piscineiros, manutenção, produtos químicos e acessórios).
- **Tipo de página:** portal com vitrine. Início, busca, mapa, blog e uma página por loja (378), por modelo de piscina (265) e por artigo.
- **Conversão desejada:** pedido de orçamento à loja (WhatsApp) e criação de conta no app.
- **Público:** quem vai comprar ou cuidar de uma piscina e quer comparar lojas e modelos perto de casa; do outro lado, lojistas que querem aparecer.
- **Abrangência:** nacional, com intenção local forte ("piscina de fibra em [cidade]", "piscineiro perto de mim").
- **Intenção de busca:** comercial e local (modelo, preço, loja na cidade), mais informacional no blog.
- **Entidade principal:** iPiscinas (Organization + WebSite com SearchAction); cada loja vira `Store` e cada modelo vira `Product`.

## O que mudou em relação ao site atual

O site atual é um app Next.js que monta tudo no navegador: o HTML entregue ao Google tem só esqueletos cinza, nenhuma loja, nenhum modelo e uma única descrição para todas as páginas. O site novo é estático e já sai com o conteúdo no HTML:

- 650 páginas indexáveis com `title`, `description`, canonical e Open Graph próprios.
- JSON-LD por página: Organization, WebSite (com busca), Store, Product (com Offer só quando há preço), BlogPosting/NewsArticle e BreadcrumbList.
- `sitemap.xml` e `robots.txt` gerados a cada build.
