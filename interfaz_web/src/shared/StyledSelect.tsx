import {Children,isValidElement,useEffect,useId,useLayoutEffect,useRef,useState,type SelectHTMLAttributes,type ReactElement} from 'react';
import {Check,ChevronDown} from 'lucide-react';

/** La selección sigue disparando el change nativo; conserva los formularios existentes. */
export default function StyledSelect({children,label,...props}:SelectHTMLAttributes<HTMLSelectElement>&{label?:string}){
 const uid=useId(),root=useRef<HTMLSpanElement>(null),native=useRef<HTMLSelectElement>(null),button=useRef<HTMLButtonElement>(null),menu=useRef<HTMLSpanElement>(null);
 const [open,setOpen]=useState(false),[active,setActive]=useState(0),[inferred,setInferred]=useState('Seleccionar'),[invalid,setInvalid]=useState(''),[up,setUp]=useState(false),[menuHeight,setMenuHeight]=useState(260);
 const options=Children.toArray(children).filter(isValidElement).map(child=>{const p=(child as ReactElement<{value?:string|number;children?:React.ReactNode;disabled?:boolean}>).props;return {value:String(p.value??p.children??''),text:Children.toArray(p.children).join(''),disabled:!!p.disabled}});
 const selected=options.find(o=>o.value===String(props.value??props.defaultValue??'')),enabled=options.map((o,i)=>o.disabled?-1:i).filter(i=>i>=0);
 const accessible=props['aria-label']||label||inferred;
 useLayoutEffect(()=>{const enclosing=root.current?.closest('label');if(enclosing){const clone=enclosing.cloneNode(true) as HTMLElement;clone.querySelector('.select-root')?.remove();setInferred(clone.textContent?.trim()||'Seleccionar');enclosing.htmlFor=props.id||uid+'-trigger'}},[]);
 useEffect(()=>{setOpen(false)},[props.disabled,props.value]);
 useEffect(()=>{if(!open)return;const close=(e:PointerEvent)=>{if(!root.current?.contains(e.target as Node))setOpen(false)};document.addEventListener('pointerdown',close);return()=>document.removeEventListener('pointerdown',close)},[open]);
 useLayoutEffect(()=>{if(!open||!menu.current)return;const item=document.getElementById(uid+'-'+active),scroller=menu.current;if(item){const top=item.offsetTop,bottom=top+item.offsetHeight;if(top<scroller.scrollTop)scroller.scrollTop=top;else if(bottom>scroller.scrollTop+scroller.clientHeight)scroller.scrollTop=bottom-scroller.clientHeight}},[open,active,uid]);
 function choose(index:number){const option=options[index];if(!option||option.disabled||props.disabled)return;if(native.current){native.current.value=option.value;native.current.dispatchEvent(new Event('change',{bubbles:true}))}setInvalid('');setOpen(false);button.current?.focus()}
 function begin(){const rect=button.current?.getBoundingClientRect(),dialog=button.current?.closest('dialog')?.querySelector('form')?.getBoundingClientRect();if(rect){const below=Math.min(window.innerHeight,dialog?.bottom??window.innerHeight)-rect.bottom,above=rect.top-(dialog?.top??0),opensUp=below<190&&above>below;setUp(opensUp);setMenuHeight(Math.max(80,Math.min(260,(opensUp?above:below)-24)))}setActive(Math.max(0,options.findIndex(o=>o.value===String(props.value))));setOpen(true)}
 return <span className={'select-root '+(open?'is-open ':'')+(up?'opens-up':'')} ref={root}>
  <select {...props} id={undefined} aria-label={undefined} aria-hidden="true" tabIndex={-1} ref={native} className="select-native" onInvalid={e=>{e.preventDefault();setInvalid('Seleccione una opción.');button.current?.focus()}}>{children}</select>
  <button type="button" id={props.id||uid+'-trigger'} ref={button} role="combobox" aria-label={accessible} aria-expanded={open} aria-haspopup="listbox" aria-controls={uid} aria-activedescendant={open?uid+'-'+active:undefined} aria-required={props.required||undefined} aria-invalid={!!invalid||undefined} disabled={props.disabled||!enabled.length} className="select-trigger" onClick={()=>open?setOpen(false):begin()} onKeyDown={e=>{
   if(e.key==='Escape'){e.preventDefault();setOpen(false);return}if(e.key==='Tab'){setOpen(false);return}
   if(['ArrowDown','ArrowUp','Home','End'].includes(e.key)){e.preventDefault();if(!open){begin();return}const pos=enabled.indexOf(active);setActive(e.key==='Home'?enabled[0]:e.key==='End'?enabled.at(-1)!:enabled[(pos+(e.key==='ArrowDown'?1:-1)+enabled.length)%enabled.length]??0);return}
   if(e.key==='Enter'||e.key===' '){e.preventDefault();open?choose(active):begin();return}
   if(e.key.length===1&&!e.ctrlKey&&!e.metaKey){const next=options.findIndex(o=>!o.disabled&&o.text.toLocaleLowerCase().startsWith(e.key.toLocaleLowerCase()));if(next>=0){e.preventDefault();setActive(next);setOpen(true)}}
  }}><span>{selected?.text||'Seleccione una opción'}</span><ChevronDown size={15}/></button>
  {open&&<span id={uid} role="listbox" aria-label={accessible} className="select-options"><span className="select-options-scroll" ref={menu} style={{maxHeight:menuHeight}}>{options.map((o,i)=><span id={uid+'-'+i} role="option" aria-selected={selected?.value===o.value} aria-disabled={o.disabled||undefined} key={o.value} className={i===active?'is-active':''} onPointerMove={()=>!o.disabled&&setActive(i)} onPointerDown={e=>e.preventDefault()} onClick={e=>{e.preventDefault();choose(i)}}>{o.text}{selected?.value===o.value&&<Check size={15}/>}</span>)}</span></span>}
  {invalid&&<small role="alert">{invalid}</small>}
 </span>;
}
