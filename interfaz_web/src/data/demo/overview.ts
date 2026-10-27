import type {Overview} from '../../domain/models';
export function exampleOverview():Overview {
 const room='demo-aula-01',second='demo-aula-02',now=new Date().toISOString();
 return {classrooms:[{id:room,name:'Aula 01 · Robótica',school:'Escuela de ejemplo'},{id:second,name:'Aula 02 · Ciencias',school:'Escuela de ejemplo'}],memberships:[{classroom_id:room,role:'observador'},{classroom_id:second,role:'observador'}],
 snapshots:[{classroom_id:room,gateway_id:'ejemplo',source:'simulacion',sample_at:now,state:'alerta',observation:{mq_raw:560,temperature:26.4,humidity:58,ratio:1.87,dht_ok:true}},
 {classroom_id:second,gateway_id:'ejemplo-2',source:'simulacion',sample_at:now,state:'normal',observation:{mq_raw:305,temperature:24.8,humidity:53,ratio:1.02,dht_ok:true}}],
 incidents:[{id:'demo-incidente',coordinator_id:'demo-directora',classroom_id:room,source:'simulacion',severity:'alerta',status:'pendiente',opened_at:now,revision:1,note:'Escenario ilustrativo de una variación sostenida.',historical:false}],deliveries:[]};
}
