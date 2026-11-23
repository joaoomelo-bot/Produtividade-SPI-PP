/* Patch não destrutivo para o HTML atual do SPI-PP */
(()=>{
 const table=document.getElementById('tbody'),head=document.getElementById('thead');
 if(!table||!head)return;
 function decorate(){
   const headers=[...head.querySelectorAll('th')].map(x=>x.textContent.trim().toLowerCase());
   const rankIdx=headers.findIndex(x=>x==='#'||x==='pos.'||x==='posição');
   const situationIdx=headers.findIndex(x=>x==='situação');
   const hourCols=headers.map((x,i)=>/\d{1,2}h/.test(x)?i:-1).filter(x=>x>=0);
   for(const row of table.querySelectorAll('tr')){
     const cells=[...row.cells];
     if(rankIdx>=0&&cells[rankIdx]){
       const el=cells[rankIdx];const m=el.textContent.trim().match(/^(\d+)[º°]?$/);
       if(m){const pos=+m[1];if(pos<=3){el.innerHTML=`<span class="rank-trophy" aria-label="${pos}º lugar">${['🏆','🥈','🥉'][pos-1]}</span>`}}
     }
     if(situationIdx>=0&&cells[situationIdx]&&hourCols.length>=2){
       const values=hourCols.map(i=>{
         const txt=cells[i]?.textContent||'';
         const n=txt.match(/[\d.]+/);return n?Number(n[0].replace(/\./g,'')):null;
       }).filter(v=>v!==null);
       const el=cells[situationIdx];
       if(values.length>=2){
         const prev=values.at(-2),cur=values.at(-1),change=prev?((cur-prev)/prev):cur?1:0;
         const kind=change>=0?'up':change>=-.1?'down':'act';
         const label=kind==='up'?'↗ Evoluindo':kind==='down'?'↘ Caindo':'! Agir';
         const width=Math.max(8,Math.min(100,Math.round((cur/(prev||cur||1))*75)));
         el.className='trend-cell trend-'+kind;
         el.innerHTML=`<strong>${label}</strong><div class="trend-bar"><div class="trend-fill" style="width:${width}%"></div></div>`;
       }else el.textContent='—';
     }
   }
 }
 const observer=new MutationObserver(()=>{observer.disconnect();decorate();observer.observe(table,{childList:true,subtree:true})});
 observer.observe(table,{childList:true,subtree:true});
 decorate();
})();
