import {useEffect,useState} from 'react';
export default function InvitationQr({url}:{url:string}){
 const [open,setOpen]=useState(false),[image,setImage]=useState(''),[error,setError]=useState('');
 useEffect(()=>{let active=true;if(open){void import('qrcode').then(q=>q.toDataURL(url,{width:240,margin:2,errorCorrectionLevel:'M'})).then(data=>{if(active)setImage(data)}).catch(()=>{if(active)setError('No se pudo preparar el QR. Copia el enlace.')})}return()=>{active=false}},[url,open]);
 return <div><button type="button" className="secondary" aria-expanded={open} onClick={()=>setOpen(v=>!v)}>{open?'Ocultar QR':'Mostrar QR'}</button>{open&&image&&<p><img src={image} width={240} height={240} style={{maxWidth:'100%',height:'auto',borderRadius:12}} alt="QR privado para aceptar la invitación"/><small>Escanéalo con el celular de la persona invitada.</small></p>}{error&&<p role="alert">{error}</p>}</div>;
}
