# SPI-PP — Pacote de atualização visual

Este ZIP é um PATCH DE INTEGRAÇÃO, não substitui sozinho o site Flask existente.

## Instalação
1. Faça backup do repositório e banco de dados.
2. Copie `tema-branco.css` e `ajustes-visuais.js` para a raiz do repositório (junto de `index.html`).
3. Em `index.html`, imediatamente antes de `</head>`, insira: `<link rel="stylesheet" href="/tema-branco.css?v=20261123">`.
4. Imediatamente antes de `</body>`, insira: `<script src="/ajustes-visuais.js?v=20261123"></script>`.
5. Faça commit na branch main. O Render está configurado com deploy automático.
6. Verifique no navegador usando atualização forçada para evitar cache.

## Indicador Situação
O indicador passa a mostrar a tendência por colaborador comparando a produtividade na última hora produtiva à hora anterior, quando ambas existem. Verde = evoluindo, amarelo = caindo até 10%, vermelho = queda superior a 10% ou produção zerada na última hora. Sem duas horas comparáveis = sem histórico suficiente.

## Observações
- Preserva imagens `gruposc.png` e `panpharma.png` do repositório.
- Mantém os tons verde/amarelo/vermelho nos rankings.
- Não exclua o serviço Render ou o banco PostgreSQL: isso não reduz necessariamente o peso do dashboard e pode causar perda de dados.
- O patch visual não implementa sozinho todas as regras de HC fixo/apoio; estas dependem de cadastro de equipe fixa e lógica do backend.
