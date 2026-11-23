/** SPI-PP: helpers independentes para integrar ao dashboard existente. */
export const DEPOSITOS = ['101','102','104','105','106','107','110','302'];
export function normalizeDepositos(value) {
  return [...new Set((Array.isArray(value) ? value : [value]).filter(v=>v!==null && v!==undefined).map(String))];
}
export function filtrarPorDepositos(registros, selecionados, campo='deposito') {
  const deps = new Set(normalizeDepositos(selecionados));
  return registros.filter(r => deps.has(String(r[campo] ?? '').trim()));
}
export function somar(registros, campo) {
  return registros.reduce((acc,r)=>acc+(Number(r[campo])||0),0);
}
/**
 * Identifica apoio por login NÃO pertencente ao cadastro fixo.
 * registros: [{login, deposito, unidades, caixas, horario}]
 * loginsFixos: array de logins (não apenas a quantidade planejada).
 * hcFixoPlanejado: número de posições garantidas por hora.
 */
export function calcularIndicadores({registros=[], loginsFixos=[], hcFixoPlanejado=0, metaUnidades=0, metaCaixas=0}) {
  const fixos = new Set(loginsFixos.map(x=>String(x).trim().toLowerCase()));
  const login = r => String(r.login??'').trim().toLowerCase();
  const validos = registros.filter(r=>login(r));
  const pessoas = new Set(validos.map(login));
  const registrosFixos = validos.filter(r=>fixos.has(login(r)));
  const registrosApoio = validos.filter(r=>!fixos.has(login(r)));
  const pessoasFixas = new Set(registrosFixos.map(login));
  const pessoasApoio = new Set(registrosApoio.map(login));
  const metaTotalUnidades = hcFixoPlanejado * metaUnidades;
  const metaTotalCaixas = hcFixoPlanejado * metaCaixas;
  const unidadesFixas=somar(registrosFixos,'unidades'), unidadesApoio=somar(registrosApoio,'unidades');
  const caixasFixas=somar(registrosFixos,'caixas'), caixasApoio=somar(registrosApoio,'caixas');
  return {
    hcFixoPlanejado, hcFixoProdutivo:pessoasFixas.size, hcApoioProdutivo:pessoasApoio.size,
    hcProdutivoTotal:pessoas.size, alertaHC:pessoasFixas.size<hcFixoPlanejado,
    metaTotalUnidades,metaTotalCaixas,
    unidadesFixas,unidadesApoio,unidadesTotal:unidadesFixas+unidadesApoio,
    caixasFixas,caixasApoio,caixasTotal:caixasFixas+caixasApoio,
    atingimentoUnidadesFixo:metaTotalUnidades?unidadesFixas/metaTotalUnidades:null,
    atingimentoUnidadesTotal:metaTotalUnidades?(unidadesFixas+unidadesApoio)/metaTotalUnidades:null,
    atingimentoCaixasFixo:metaTotalCaixas?caixasFixas/metaTotalCaixas:null,
    atingimentoCaixasTotal:metaTotalCaixas?(caixasFixas+caixasApoio)/metaTotalCaixas:null,
  };
}
/** Ordena horários sem eliminar faixas; aceita 'HH:mm', 'HH:mm-HH:mm' e datas ISO. */
export function horariosOrdenados(registros, campo='horario') {
  const horarios=[...new Set(registros.map(r=>r[campo]).filter(v=>v!==null&&v!==undefined&&String(v).trim()!==''))];
  const minutes=v=>{const m=String(v).match(/(?:^|T|\s)(\d{1,2}):(\d{2})/);return m?Number(m[1])*60+Number(m[2]):Number.POSITIVE_INFINITY};
  return horarios.sort((a,b)=>minutes(a)-minutes(b)||String(a).localeCompare(String(b),'pt-BR'));
}
/** Para bases acumuladas, substituir o conjunto anterior; NÃO concatenar uploads. */
export function substituirBaseAcumulada(_baseAnterior, novaBase) {return [...novaBase];}
