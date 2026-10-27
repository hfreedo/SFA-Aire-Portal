import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig(({mode})=>{
 const input:Record<string,string>=mode==='hosting'?{portal:'portal.html'}:{local:'index.html',remoto:'remoto.html'};
 return {plugins:[react()],build:{outDir:mode==='hosting'?'dist-hosting':'dist',rollupOptions:{input}},server:{proxy:{'/api':'http://127.0.0.1:8766','/health':'http://127.0.0.1:8766'}}};
});
