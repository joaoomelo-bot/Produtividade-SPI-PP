# Produtividade SPI-PP — pacote de integração

**Atenção:** este ZIP contém módulos auxiliares, NÃO é o site completo e NÃO pode substituir diretamente a aplicação publicada no Render. É necessário integrar ao código-fonte atual e testar.

## Incluído
- `produtividade-patch.js`: filtro por múltiplos depósitos, cálculo de metas por HC fixo, separação de produção fixa e apoio, deduplicação de colaboradores por login, horários ordenados e substituição da base acumulada.
- `modo-tv.css`: rolagem para tabelas extensas, cabeçalho fixo e legibilidade em telas grandes.

## Integração
1. Identificar nomes reais das colunas da importação Excel e mapear para `login`, `deposito`, `unidades`, `caixas`, `horario`.
2. Criar cadastro persistente de logins fixos por operação (separação/conferência), depósito e período. **HC planejado sozinho não permite identificar quem é apoio.**
3. Criar interface de seleção múltipla; passar o array de depósitos a `filtrarPorDepositos` antes de calcular indicadores e rankings.
4. Calcular separação e conferência separadamente com `calcularIndicadores`, usando suas metas individuais.
5. Renderizar a lista completa de `horariosOrdenados` no Modo TV, em vez de aplicar `.slice(...)` ou um limite de linhas. Aplicar `.spi-tv-scroll` no contêiner da tabela.
6. Se o modo TV precisar rolar automaticamente, implementar o comportamento no componente de tela respeitando pausa por interação, ciclo e atualização. **CSS sozinho não realiza rolagem automática.**
7. Ao importar nova base acumulada, substituir os registros anteriores do dia, não somar uploads sucessivos.
8. Testar filtros, HC, deduplicação, bases acumuladas, horários e visualização nas cinco telas antes de publicar.

## Observações importantes
- O cálculo `meta = HC fixo × meta individual` é por hora. Para acumulado diário, multiplicar pela quantidade real de horas de produção aplicáveis; não comparar produção diária com meta de uma hora.
- Um login produtivo em vários depósitos conta uma vez no HC, mas suas produções são somadas.
- Se os logins fixos forem configurados por depósito, a meta de vários depósitos deve somar os HCs de cada depósito sem contar a mesma pessoa duas vezes.
- Verificar se o campo `horario` representa a hora inicial, final ou timestamp completo para respeitar a virada de dia.
- O pacote não altera senhas, autenticação, conexão de banco, login, logos nem deploy.
