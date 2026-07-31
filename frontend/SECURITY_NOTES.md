# Notas de segurança do frontend

## Auditoria de dependências

Data da validação: 31 de julho de 2026.

O comando:

```bash
npm audit --omit=dev
```

identificou advisories de severidade alta em dependências transitivas utilizadas
pelo Next.js durante o processo de build.

## PostCSS

Os advisories identificados exigem que o processo receba e processe CSS
controlado por um atacante.

O PS Munnin processa somente arquivos CSS versionados no próprio repositório.
O sistema não permite upload, edição ou processamento de CSS fornecido por
usuários.

## Sharp e libvips

Os advisories identificados afetam aplicações que processam imagens não
confiáveis.

O PS Munnin não possui upload ou processamento de imagens fornecidas por
usuários. O frontend usa um SVG local e está configurado com
`images.unoptimized: true`.

## Ambiente publicado

O frontend é exportado estaticamente e publicado no GitHub Pages. O ambiente de
produção não executa Node.js, Next.js, PostCSS ou Sharp. Apenas HTML, CSS,
JavaScript e assets estáticos são publicados.

## Decisão

O risco residual foi aceito para o MVP porque os vetores descritos nos
advisories não são alcançáveis pelo fluxo funcional atual.

Não foi utilizado `npm audit fix --force`, não foram aplicados overrides em
dependências internas do Next.js e não foram feitos downgrades.

A decisão deve ser revisada se o projeto futuramente:

* aceitar upload de imagens;
* processar imagens no servidor;
* aceitar CSS ou temas fornecidos por usuários;
* deixar de ser uma exportação estática;
* executar Next.js em runtime de produção.
